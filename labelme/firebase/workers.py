#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import os
import datetime

from qtpy.QtCore import QThread, Signal

from labelme.firebase.constants import (
    TaskStatus,
    StoragePath,
    LOAD_SOURCE_STATUSES,
    LOAD_NEXT_STATUS,
    USER_FIELD_MAP,
    STATUS_TRANSITIONS,
)
from labelme.firebase.database_manager import DatabaseManager
from labelme.firebase.image_manager import ImageUpload, ImageDownload


class FirebaseWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def run(self):
        try:
            result = self.execute()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def execute(self):
        raise NotImplementedError


class LoadTaskWorker(FirebaseWorker):
    def __init__(
        self, mode, user_id, processing_dir,
        source_statuses=None, user_filter_field=None, parent=None,
    ):
        super().__init__(parent)
        self.mode = mode
        self.user_id = user_id
        self.processing_dir = processing_dir
        self.source_statuses = source_statuses
        self.user_filter_field = user_filter_field
        self.db = DatabaseManager()
        self.downloader = ImageDownload()

    def execute(self):
        os.makedirs(self.processing_dir, exist_ok=True)

        # Get source statuses from mode if not explicitly provided
        statuses = self.source_statuses
        if statuses is None:
            statuses = LOAD_SOURCE_STATUSES.get(self.mode, [])

        # Filter by user if user_filter_field specified
        doc = None
        if self.user_filter_field:
            for status in statuses:
                docs = self.db.get_documents_by_status_and_user(
                    status, self.user_filter_field, self.user_id
                )
                if docs:
                    doc = docs[0]
                    break
        else:
            if len(statuses) == 1:
                doc = self.db.get_oldest_by_status(statuses[0])
            else:
                doc = self.db.get_oldest_by_statuses(statuses)

        if not doc:
            return {'found': False}

        doc_id = doc.get('image_name', '')
        source_status_val = doc.get('status', '')

        # Determine source TaskStatus enum
        source_status = None
        for s in TaskStatus:
            if s.value == source_status_val:
                source_status = s
                break

        if source_status is None:
            return {'found': False}

        # Determine next status
        next_status_map = LOAD_NEXT_STATUS.get(self.mode, {})
        next_status = next_status_map.get(source_status)
        if next_status is None:
            return {'found': False}

        # Update document status
        user_field = USER_FIELD_MAP.get(self.mode, 'worker_id')
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_data = {
            'status': next_status.value,
            'assigned_at': now_str,
            user_field: self.user_id,
        }
        self.db.update_document(doc_id, update_data)

        # Download files to processing_dir
        basename = os.path.splitext(doc_id)[0]
        downloads = {}

        img_path = doc.get('storage_image_path', '')
        if img_path:
            downloads[img_path] = os.path.join(
                self.processing_dir, os.path.basename(img_path)
            )

        json_path = doc.get('storage_json_path', '')
        if json_path:
            downloads[json_path] = os.path.join(
                self.processing_dir, f"{basename}.json"
            )

        encrypt_path = doc.get('storage_encrypt_path', '')
        if encrypt_path:
            downloads[encrypt_path] = os.path.join(
                self.processing_dir, f"{basename}_encrypt.bin"
            )

        comment_path = doc.get('storage_comment_path', '')
        if comment_path:
            downloads[comment_path] = os.path.join(
                self.processing_dir, f"{basename}_comments.json"
            )

        if downloads:
            self.downloader.download_files(downloads)

        # Determine local image path
        local_image_path = ''
        if img_path:
            local_image_path = downloads[img_path]

        return {
            'found': True,
            'doc_id': doc_id,
            'image_name': doc.get('image_name', ''),
            'local_image_path': local_image_path,
            'document': doc,
            'next_status': next_status.value,
        }


class SubmitTaskWorker(FirebaseWorker):
    def __init__(
        self, doc_id, current_status, processing_dir,
        basename, mode, parent=None,
    ):
        super().__init__(parent)
        self.doc_id = doc_id
        self.current_status = current_status
        self.processing_dir = processing_dir
        self.basename = basename
        self.mode = mode
        self.db = DatabaseManager()
        self.uploader = ImageUpload()

    def execute(self):
        # Upload files from processing_dir
        storage_paths = {}

        # Image file
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
        for ext in image_exts:
            img_file = os.path.join(
                self.processing_dir, f"{self.basename}{ext}"
            )
            if os.path.exists(img_file):
                sp = StoragePath.normal(StoragePath.IMAGE, f"{self.basename}{ext}")
                self.uploader.upload_single(img_file, sp)
                storage_paths['storage_image_path'] = f"{sp}/{self.basename}{ext}"
                break

        # JSON file
        json_file = os.path.join(self.processing_dir, f"{self.basename}.json")
        if os.path.exists(json_file):
            sp = StoragePath.normal(StoragePath.JSON, f"{self.basename}.json")
            self.uploader.upload_single(json_file, sp)
            storage_paths['storage_json_path'] = f"{sp}/{self.basename}.json"

        # Encrypt file
        encrypt_file = os.path.join(
            self.processing_dir, f"{self.basename}_encrypt.bin"
        )
        if os.path.exists(encrypt_file):
            sp = StoragePath.normal(
                StoragePath.ENCRYPT, f"{self.basename}_encrypt.bin"
            )
            self.uploader.upload_single(encrypt_file, sp)
            storage_paths['storage_encrypt_path'] = (
                f"{sp}/{self.basename}_encrypt.bin"
            )

        # Comment file
        comment_file = os.path.join(
            self.processing_dir, f"{self.basename}_comments.json"
        )
        if os.path.exists(comment_file):
            sp = StoragePath.normal(
                StoragePath.COMMENT, f"{self.basename}_comments.json"
            )
            self.uploader.upload_single(comment_file, sp)
            storage_paths['storage_comment_path'] = (
                f"{sp}/{self.basename}_comments.json"
            )

        # Determine next status
        current_enum = None
        for s in TaskStatus:
            if s.value == self.current_status:
                current_enum = s
                break

        if current_enum is None:
            raise RuntimeError(
                f"Unknown current status: {self.current_status}"
            )

        assert current_enum is not None
        next_status = STATUS_TRANSITIONS.get(current_enum)
        if next_status is None:
            raise RuntimeError(
                f"No transition defined for status: {self.current_status}"
            )

        # Update document
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_data = {
            'status': next_status.value,
            'updated_at': now_str,
        }
        update_data.update(storage_paths)
        self.db.update_document(self.doc_id, update_data)

        return {
            'doc_id': self.doc_id,
            'next_status': next_status.value,
        }


class PostponeTaskWorker(FirebaseWorker):
    def __init__(
        self, doc_id, user_id, processing_dir,
        basename, parent=None,
    ):
        super().__init__(parent)
        self.doc_id = doc_id
        self.user_id = user_id
        self.processing_dir = processing_dir
        self.basename = basename
        self.db = DatabaseManager()
        self.uploader = ImageUpload()

    def execute(self):
        # Upload files to postpone path
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
        for ext in image_exts:
            img_file = os.path.join(
                self.processing_dir, f"{self.basename}{ext}"
            )
            if os.path.exists(img_file):
                sp = StoragePath.postpone(
                    self.user_id, StoragePath.IMAGE,
                    f"{self.basename}{ext}",
                )
                self.uploader.upload_single(img_file, sp)
                break

        # JSON
        json_file = os.path.join(self.processing_dir, f"{self.basename}.json")
        if os.path.exists(json_file):
            sp = StoragePath.postpone(
                self.user_id, StoragePath.JSON, f"{self.basename}.json"
            )
            self.uploader.upload_single(json_file, sp)

        # Encrypt
        encrypt_file = os.path.join(
            self.processing_dir, f"{self.basename}_encrypt.bin"
        )
        if os.path.exists(encrypt_file):
            sp = StoragePath.postpone(
                self.user_id, StoragePath.ENCRYPT,
                f"{self.basename}_encrypt.bin",
            )
            self.uploader.upload_single(encrypt_file, sp)

        # Comment
        comment_file = os.path.join(
            self.processing_dir, f"{self.basename}_comments.json"
        )
        if os.path.exists(comment_file):
            sp = StoragePath.postpone(
                self.user_id, StoragePath.COMMENT,
                f"{self.basename}_comments.json",
            )
            self.uploader.upload_single(comment_file, sp)

        # Update status to postpone
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_document(self.doc_id, {
            'status': TaskStatus.POSTPONE.value,
            'updated_at': now_str,
        })

        return {'doc_id': self.doc_id}


class LoadPostponeWorker(FirebaseWorker):
    def __init__(self, user_id, processing_dir, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.processing_dir = processing_dir
        self.db = DatabaseManager()
        self.downloader = ImageDownload()

    def execute(self):
        # Get postponed documents for this user
        docs = self.db.get_documents_by_status_and_user(
            TaskStatus.POSTPONE, 'worker_id', self.user_id
        )
        if not docs:
            return {'found': False, 'documents': []}

        return {'found': True, 'documents': docs}


class RestorePostponeWorker(FirebaseWorker):
    def __init__(self, doc, user_id, processing_dir, parent=None):
        super().__init__(parent)
        self.doc = doc
        self.user_id = user_id
        self.processing_dir = processing_dir
        self.db = DatabaseManager()
        self.downloader = ImageDownload()

    def execute(self):
        os.makedirs(self.processing_dir, exist_ok=True)

        doc_id = self.doc.get('image_name', '')
        basename = os.path.splitext(doc_id)[0]

        # Download from postpone paths
        downloads = {}

        # Try postpone storage paths first, then normal
        img_name = doc_id
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
        for ext in image_exts:
            sp = StoragePath.postpone(
                self.user_id, StoragePath.IMAGE, f"{basename}{ext}"
            )
            local = os.path.join(self.processing_dir, f"{basename}{ext}")
            downloads[sp] = local
            break  # Try first extension only, rely on stored path

        # Use stored paths if available
        stored_img = self.doc.get('storage_image_path', '')
        if stored_img:
            img_name = os.path.basename(stored_img)
            downloads = {}
            downloads[stored_img] = os.path.join(
                self.processing_dir, img_name
            )

        json_sp = StoragePath.postpone(
            self.user_id, StoragePath.JSON, f"{basename}.json"
        )
        downloads[json_sp] = os.path.join(
            self.processing_dir, f"{basename}.json"
        )

        encrypt_sp = StoragePath.postpone(
            self.user_id, StoragePath.ENCRYPT, f"{basename}_encrypt.bin"
        )
        downloads[encrypt_sp] = os.path.join(
            self.processing_dir, f"{basename}_encrypt.bin"
        )

        comment_sp = StoragePath.postpone(
            self.user_id, StoragePath.COMMENT, f"{basename}_comments.json"
        )
        downloads[comment_sp] = os.path.join(
            self.processing_dir, f"{basename}_comments.json"
        )

        # Download (ignore errors for optional files)
        for sp, local in downloads.items():
            try:
                self.downloader.download_single(sp, local)
            except Exception:
                pass

        # Update status back to processing
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_document(doc_id, {
            'status': TaskStatus.PROCESSING.value,
            'assigned_at': now_str,
        })

        local_image_path = os.path.join(self.processing_dir, img_name)

        return {
            'found': True,
            'doc_id': doc_id,
            'image_name': doc_id,
            'local_image_path': local_image_path,
            'document': self.doc,
        }


class DropTaskWorker(FirebaseWorker):
    def __init__(self, doc_id, mode, parent=None):
        super().__init__(parent)
        self.doc_id = doc_id
        self.mode = mode
        self.db = DatabaseManager()

    def execute(self):
        user_field = USER_FIELD_MAP.get(self.mode, 'worker_id')
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_document(self.doc_id, {
            'status': TaskStatus.READY.value,
            user_field: '',
            'assigned_at': '',
            'updated_at': now_str,
        })
        return {'doc_id': self.doc_id}


class DiscardTaskWorker(FirebaseWorker):
    def __init__(self, doc_id, discard_reason, parent=None):
        super().__init__(parent)
        self.doc_id = doc_id
        self.discard_reason = discard_reason
        self.db = DatabaseManager()

    def execute(self):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_document(self.doc_id, {
            'discard_reason': self.discard_reason,
            'updated_at': now_str,
        })
        self.db.delete_document(self.doc_id)
        return {'doc_id': self.doc_id}


class ReadyGtWorker(FirebaseWorker):
    def __init__(self, doc_id, is_gt, discard_reason='', parent=None):
        super().__init__(parent)
        self.doc_id = doc_id
        self.is_gt = is_gt
        self.discard_reason = discard_reason
        self.db = DatabaseManager()

    def execute(self):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_document(self.doc_id, {
            'is_gt': self.is_gt,
            'discard_reason': self.discard_reason,
            'updated_at': now_str,
        })
        self.db.delete_document(self.doc_id)
        return {
            'doc_id': self.doc_id,
            'is_gt': self.is_gt,
        }
