#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import datetime
import requests

from labelme.firebase.utils import ConfigLoader


class DatabaseManager:
    def __init__(self):
        cfg_loader = ConfigLoader()
        self.collection = cfg_loader.database_config.get('collection')
        self.common_url = cfg_loader.common_config.get('base_url')

    def create_document(self, image_name):
        url = f"{self.common_url}/annotation"
        datetime_now = datetime.datetime.now()
        str_now = datetime_now.strftime("%Y-%m-%d %H:%M:%S")
        body = {
            'id': image_name,
            'data': {
                'image_name': image_name,
                'status': 'ready',
                'worker_id': '',
                'reviewer_id': '',
                'final_reviewer_id': '',
                'created_at': str_now,
                'assigned_at': '',
                'updated_at': '',
                'storage_image_path': '',
                'storage_json_path': '',
                'storage_encrypt_path': '',
                'storage_comment_path': '',
                'class_type': '',
                'discard_reason': '',
                'is_gt': '',
            }
        }
        response = requests.post(url, json=body)
        if response.status_code == 201:
            print(f"Successfully created document: {image_name}")
        else:
            raise RuntimeError(
                f"Failed to create document: {response.status_code}, "
                f"{response.text}"
            )

    def delete_document(self, image_name):
        url = f"{self.common_url}/annotation?docId={image_name}"
        response = requests.delete(url)

        if response.status_code == 200:
            print(f"Successfully deleted document: {image_name}")
        else:
            raise RuntimeError(
                f"Failed to delete document: {response.status_code}, "
                f"{response.text}"
            )

    def get_all_document(self):
        url = f"{self.common_url}/annotations"
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(
                f"Failed to get all document: {response.status_code}, "
                f"{response.text}"
            )

    def update_document(self, doc_id, data):
        # --- Original PATCH implementation (server not ready) ---
        # url = f"{self.common_url}/annotation"
        # body = {'id': doc_id, 'data': data}
        # response = requests.patch(url, json=body)
        # if response.status_code in (200, 201):
        #     print(f"Successfully updated document: {doc_id}")
        # else:
        #     raise RuntimeError(
        #         f"Failed to update document: {response.status_code}, "
        #         f"{response.text}"
        #     )

        # Workaround: GET all → merge → POST (overwrite)
        all_docs = self.get_all_document()
        existing = None
        for d in all_docs:
            if d.get('image_name') == doc_id:
                existing = d
                break

        if existing is None:
            raise RuntimeError(f"Document not found: {doc_id}")

        existing.update(data)

        url = f"{self.common_url}/annotation"
        body = {'id': doc_id, 'data': existing}
        response = requests.post(url, json=body)

        if response.status_code in (200, 201):
            print(f"Successfully updated document: {doc_id}")
        else:
            raise RuntimeError(
                f"Failed to update document: {response.status_code}, "
                f"{response.text}"
            )

    def get_documents_by_status(self, status):
        all_docs = self.get_all_document()
        if not all_docs:
            return []
        status_val = status.value if hasattr(status, 'value') else status
        filtered = [
            d for d in all_docs if d.get('status') == status_val
        ]
        # FIFO sort by created_at ASC
        filtered.sort(key=lambda d: d.get('created_at', ''))
        return filtered

    def get_oldest_by_status(self, status):
        docs = self.get_documents_by_status(status)
        return docs[0] if docs else None

    def get_oldest_by_statuses(self, statuses):
        all_docs = self.get_all_document()
        if not all_docs:
            return None
        status_vals = [
            s.value if hasattr(s, 'value') else s for s in statuses
        ]
        filtered = [
            d for d in all_docs if d.get('status') in status_vals
        ]
        if not filtered:
            return None
        filtered.sort(key=lambda d: d.get('created_at', ''))
        return filtered[0]

    def get_documents_by_status_and_user(self, status, field, user_id):
        all_docs = self.get_all_document()
        if not all_docs:
            return []
        status_val = status.value if hasattr(status, 'value') else status
        filtered = [
            d for d in all_docs
            if d.get('status') == status_val and d.get(field) == user_id
        ]
        filtered.sort(key=lambda d: d.get('created_at', ''))
        return filtered

if __name__ == '__main__':
    db = DatabaseManager()
    for i in range(1, 700):
        db.delete_document(f"test_image_{i}.jpg")