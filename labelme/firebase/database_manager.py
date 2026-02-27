#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import os
import time
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
                'worker_id':'',
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
            print(f"Failed to create document: {response.status_code}, {response.text}")

    def delete_document(self, image_name):
        url = f"{self.common_url}/annotation?docId={image_name}"
        response = requests.delete(url)

        if response.status_code == 201:
            print(f"Successfully deleted document: {image_name}")
        else:
            print(f"Failed to delete document: {response.status_code}, {response.text}")

    def get_all_document(self):
        url = f"{self.common_url}/annotations"
        response = requests.get(url)

        if response.status_code == 200:
            print(f"Successfully get all document")
            return response.json()
        else:
            print(f"Failed to get all document: {response.status_code}, {response.text}")
            return None

    def compare_create_time(self, all_documents):
        earliest_create_time = None
        earliest_image_name = None
        for document in all_documents:
            create_time = document.get('created_at')
            if earliest_create_time is None:
                earliest_create_time = create_time
                earliest_image_name = document.get('image_name')
            else:
                if create_time < earliest_create_time:
                    earliest_create_time = create_time
                    earliest_image_name = document.get('image_name')
        print(earliest_image_name)
        return earliest_image_name


if __name__ == '__main__':
    db_manager = DatabaseManager()
    # for i in range(0, 300):
    #     db_manager.create_document(f'test_image_{i}.jpg')
    # db_manager.delete_document('test_image.jpg')
    start_time = time.time()
    all_documents = db_manager.get_all_document()
    db_manager.compare_create_time(all_documents)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time}")

