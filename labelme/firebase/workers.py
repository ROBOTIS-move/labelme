#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import logging
import os
import time
import datetime

from qtpy.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

from labelme.firebase.constants import (
    TaskStatus,
    StoragePath,
    LOAD_SOURCE_STATUSES,
    LOAD_NEXT_STATUS,
    USER_FIELD_MAP,
    STATUS_TRANSITIONS,
)
from labelme.firebase.authority_checker import AuthorityChecker
from labelme.firebase.database_manager import DatabaseManager
from labelme.firebase.image_manager import (
    ImageManager,
    ImageUpload,
    ImageDownload,
)


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
        source_statuses=None, user_filter_field=None,
        is_5_generation=False, is_supervisor=False,
        drop_image_list=None, parent=None,
    ):
        super().__init__(parent)
        self.mode = mode
        self.user_id = user_id
        self.processing_dir = processing_dir
        self.source_statuses = source_statuses
        self.user_filter_field = user_filter_field
        self.is_5_generation = is_5_generation
        self.is_supervisor = is_supervisor
        self.drop_image_list = drop_image_list or []
        self.db = DatabaseManager()
        self.downloader = ImageDownload()

    MAX_CLAIM_RETRIES = 3
    MAX_VERIFY_RETRIES = 2
    VERIFY_DELAY = 0.3

    def execute(self):
        os.makedirs(self.processing_dir, exist_ok=True)

        statuses = self.source_statuses
        if statuses is None:
            statuses = LOAD_SOURCE_STATUSES.get(self.mode, [])

        candidates = self._get_candidates(statuses)
        if not candidates:
            return {'found': False}

        user_field = USER_FIELD_MAP.get(self.mode, 'workerId')
        next_status_map = LOAD_NEXT_STATUS.get(self.mode, {})

        # Retry loop: try up to MAX_CLAIM_RETRIES candidates
        for doc in candidates[:self.MAX_CLAIM_RETRIES]:
            source_status_val = doc.get('status', '')
            source_status = None
            for s in TaskStatus:
                if s.value == source_status_val:
                    source_status = s
                    break
            if source_status is None:
                continue

            next_status = next_status_map.get(source_status)
            if next_status is None:
                continue

            claimed = self._try_claim_and_verify(
                doc, user_field, next_status,
            )
            if not claimed:
                continue

            return self._download_task(
                doc, next_status,
            )

        return {'found': False}

    def _get_candidates(self, statuses):
        if self.user_filter_field:
            candidates = []
            for status in statuses:
                docs = self.db.get_documents_by_status_and_user(
                    status, self.user_filter_field, self.user_id,
                )
                candidates.extend(docs)
            return self._filter_by_drop_list(
                self._filter_by_class_type(candidates)
            )

        if self.mode == 'review':
            candidates = (
                self.db.get_candidates_by_statuses_excluding_user(
                    statuses, 'workerId', self.user_id,
                )
            )
            return self._filter_by_drop_list(
                self._filter_by_class_type(candidates)
            )

        candidates = self.db.get_candidates_by_statuses(statuses)
        return self._filter_by_drop_list(
            self._filter_by_class_type(candidates)
        )

    def _filter_by_class_type(self, candidates):
        if self.is_supervisor:
            return candidates
        if self.is_5_generation:
            return [
                c for c in candidates
                if c.get('classType') == 'FrontViewSegmentation'
            ]
        return [
            c for c in candidates
            if c.get('classType') != 'FrontViewSegmentation'
        ]

    def _filter_by_drop_list(self, candidates):
        if not self.drop_image_list:
            return candidates
        return [
            c for c in candidates
            if c.get('imageName', '') not in self.drop_image_list
        ]

    def _try_claim_and_verify(self, doc, user_field, next_status):
        doc_id = doc.get('imageName', '')
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        claim_data = {
            'status': next_status.value,
            'assignedAt': now_str,
            user_field: self.user_id,
        }
        self.db.update_document(doc_id, claim_data)

        time.sleep(self.VERIFY_DELAY)

        # Verify ownership with network retry
        for attempt in range(self.MAX_VERIFY_RETRIES):
            try:
                all_docs = self.db.get_all_document()
            except Exception as e:
                if attempt < self.MAX_VERIFY_RETRIES - 1:
                    time.sleep(self.VERIFY_DELAY)
                    continue
                # Claim POST succeeded but verify failed
                # Assume ownership to avoid orphan claim
                logger.warning(
                    "Verify failed after %d retries, "
                    "assuming ownership: %s", attempt + 1, e,
                )
                return True

            for d in all_docs:
                if d.get('imageName') == doc_id:
                    return d.get(user_field) == self.user_id
            # Document disappeared
            return False

        return True

    def _download_task(self, doc, next_status):
        doc_id = doc.get('imageName', '')
        basename = os.path.splitext(doc_id)[0]
        downloads = {}

        img_path = doc.get('storageImagePath', '')
        if img_path:
            downloads[img_path] = os.path.join(
                self.processing_dir, os.path.basename(img_path),
            )

        json_path = doc.get('storageJsonPath', '')
        if json_path:
            downloads[json_path] = os.path.join(
                self.processing_dir, f"{basename}.json",
            )

        encrypt_path = doc.get('storageEncryptPath', '')
        if encrypt_path:
            downloads[encrypt_path] = os.path.join(
                self.processing_dir, f"{basename}_encrypt.bin",
            )

        comment_path = doc.get('storageCommentPath', '')
        if comment_path:
            downloads[comment_path] = os.path.join(
                self.processing_dir, f"{basename}_comments.json",
            )

        if downloads:
            self.downloader.download_files(downloads)

        local_image_path = ''
        if img_path:
            local_image_path = downloads[img_path]

        return {
            'found': True,
            'doc_id': doc_id,
            'imageName': doc.get('imageName', ''),
            'local_image_path': local_image_path,
            'document': doc,
            'next_status': next_status.value,
        }


class SubmitTaskWorker(FirebaseWorker):
    def __init__(
        self, doc_id, current_status, processing_dir,
        basename, mode, user_id='',
        from_postpone=False, working_time=0, parent=None,
    ):
        super().__init__(parent)
        self.doc_id = doc_id
        self.current_status = current_status
        self.processing_dir = processing_dir
        self.basename = basename
        self.mode = mode
        self.user_id = user_id
        self.from_postpone = from_postpone
        self.working_time = working_time
        self.db = DatabaseManager()
        self.uploader = ImageUpload()

    def execute(self):
        # Upload files from processing_dir
        storage_paths = {}

        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

        # Image file
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
        for ext in image_exts:
            img_file = os.path.join(
                self.processing_dir, f"{self.basename}{ext}"
            )
            if os.path.exists(img_file):
                sp = f"{StoragePath.IMAGE}/{ts}/{self.basename}{ext}"
                self.uploader.upload_single(img_file, sp)
                storage_paths['storageImagePath'] = sp
                break

        # JSON file
        json_file = os.path.join(self.processing_dir, f"{self.basename}.json")
        if os.path.exists(json_file):
            sp = f"{StoragePath.JSON}/{ts}/{self.basename}.json"
            self.uploader.upload_single(json_file, sp)
            storage_paths['storageJsonPath'] = sp

        # Encrypt file
        encrypt_file = os.path.join(
            self.processing_dir, f"{self.basename}_encrypt.bin"
        )
        if os.path.exists(encrypt_file):
            sp = (
                f"{StoragePath.ENCRYPT}/{ts}/"
                f"{self.basename}_encrypt.bin"
            )
            self.uploader.upload_single(encrypt_file, sp)
            storage_paths['storageEncryptPath'] = sp

        # Comment file
        comment_file = os.path.join(
            self.processing_dir, f"{self.basename}_comments.json"
        )
        if os.path.exists(comment_file):
            sp = (
                f"{StoragePath.COMMENT}/{ts}/"
                f"{self.basename}_comments.json"
            )
            self.uploader.upload_single(comment_file, sp)
            storage_paths['storageCommentPath'] = sp
        else:
            storage_paths['storageCommentPath'] = ''

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

        has_comment = os.path.exists(comment_file)
        # No comment on review → skip modify, go to final review
        if (
            current_enum == TaskStatus.REVIEWING
            and not has_comment
        ):
            next_status = TaskStatus.REQUEST_FINAL_REVIEW
        else:
            next_status = STATUS_TRANSITIONS.get(current_enum)
        if next_status is None:
            raise RuntimeError(
                f"No transition defined for status: {self.current_status}"
            )

        # Update document
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_data = {
            'status': next_status.value,
            'updatedAt': now_str,
        }
        if self.working_time > 0:
            update_data['workingTime'] = round(self.working_time, 2)
        update_data.update(storage_paths)
        self.db.update_document(self.doc_id, update_data)

        # Cleanup postpone storage only when submitting a restored postpone task
        if self.from_postpone and self.user_id:
            self._cleanup_postpone_storage()

        return {
            'doc_id': self.doc_id,
            'next_status': next_status.value,
        }

    def _cleanup_postpone_storage(self):
        manager = ImageManager()
        image_exts = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']
        for ext in image_exts:
            sp = StoragePath.postpone(
                self.user_id, StoragePath.IMAGE,
                f"{self.basename}{ext}",
            )
            manager.delete_file(sp)

        sp = StoragePath.postpone(
            self.user_id, StoragePath.JSON,
            f"{self.basename}.json",
        )
        manager.delete_file(sp)

        sp = StoragePath.postpone(
            self.user_id, StoragePath.ENCRYPT,
            f"{self.basename}_encrypt.bin",
        )
        manager.delete_file(sp)

        sp = StoragePath.postpone(
            self.user_id, StoragePath.COMMENT,
            f"{self.basename}_comments.json",
        )
        manager.delete_file(sp)


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
            'updatedAt': now_str,
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
            TaskStatus.POSTPONE, 'workerId', self.user_id
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
        doc_id = self.doc.get('imageName', '')
        basename = os.path.splitext(doc_id)[0]

        # Determine image extension from stored path or doc_id
        stored_img = self.doc.get('storageImagePath', '')
        img_ext = os.path.splitext(stored_img or doc_id)[1]
        img_filename = f"{basename}{img_ext}"

        downloads = {}

        # Always download from postpone paths
        img_sp = StoragePath.postpone(
            self.user_id, StoragePath.IMAGE, img_filename
        )
        local_img = os.path.join(self.processing_dir, img_filename)
        downloads[img_sp] = local_img

        json_sp = StoragePath.postpone(
            self.user_id, StoragePath.JSON, f"{basename}.json"
        )
        downloads[json_sp] = os.path.join(
            self.processing_dir, f"{basename}.json"
        )

        encrypt_sp = StoragePath.postpone(
            self.user_id, StoragePath.ENCRYPT,
            f"{basename}_encrypt.bin",
        )
        downloads[encrypt_sp] = os.path.join(
            self.processing_dir, f"{basename}_encrypt.bin"
        )

        comment_sp = StoragePath.postpone(
            self.user_id, StoragePath.COMMENT,
            f"{basename}_comments.json",
        )
        downloads[comment_sp] = os.path.join(
            self.processing_dir, f"{basename}_comments.json"
        )

        for sp, local in downloads.items():
            try:
                self.downloader.download_single(sp, local)
            except Exception as e:
                if sp == img_sp:
                    raise  # Image is required
                logger.warning(
                    "Optional file download skipped (%s): %s", sp, e,
                )

        # Update status back to processing
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_document(doc_id, {
            'status': TaskStatus.PROCESSING.value,
            'assignedAt': now_str,
        })

        return {
            'found': True,
            'doc_id': doc_id,
            'imageName': doc_id,
            'local_image_path': local_img,
            'document': self.doc,
        }


class DropTaskWorker(FirebaseWorker):
    def __init__(
        self, doc_id, mode, user_id, drop_count,
        drop_image_list, parent=None,
    ):
        super().__init__(parent)
        self.doc_id = doc_id
        self.mode = mode
        self.user_id = user_id
        self.drop_count = drop_count
        self.drop_image_list = drop_image_list
        self.db = DatabaseManager()
        self.authority = AuthorityChecker()

    def execute(self):
        user_field = USER_FIELD_MAP.get(self.mode, 'workerId')
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_document(self.doc_id, {
            'status': TaskStatus.READY.value,
            user_field: '',
            'assignedAt': '',
            'updatedAt': now_str,
        })
        new_count = self.drop_count + 1
        new_list = self.drop_image_list + [self.doc_id]
        self.authority.update_user(
            self.user_id,
            {'dropCount': new_count, 'dropImageList': new_list},
        )
        return {
            'doc_id': self.doc_id,
            'dropCount': new_count,
            'dropImageList': new_list,
        }


class DiscardTaskWorker(FirebaseWorker):
    def __init__(self, doc_id, discard_reason, parent=None):
        super().__init__(parent)
        self.doc_id = doc_id
        self.discard_reason = discard_reason
        self.db = DatabaseManager()

    def execute(self):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_document(self.doc_id, {
            'status': TaskStatus.DISCARD.value,
            'discardReason': self.discard_reason,
            'updatedAt': now_str,
        })
        return {'doc_id': self.doc_id}
