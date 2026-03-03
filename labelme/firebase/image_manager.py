#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import os
import requests
import mimetypes

from labelme.firebase.utils import ConfigLoader


class ImageManager:
    def __init__(self):
        cfg_loader = ConfigLoader()
        self.base_url = cfg_loader.common_config.get('base_url')
        self.bucket_name = cfg_loader.common_config.get('bucket_name')

    def delete_file(self, storage_path):
        url = f"{self.base_url}/delete-file"
        params = {
            'bucketName': self.bucket_name,
            'filePath': storage_path,
        }
        response = requests.delete(url, params=params)
        if response.status_code == 200:
            print(f"Deleted: {storage_path}")
        else:
            print(
                f"Failed to delete {storage_path}: "
                f"{response.status_code}"
            )


class ImageUpload(ImageManager):
    def upload(self, file_path_list, storage_dir='images/'):
        if storage_dir and not storage_dir.endswith('/'):
            storage_dir += '/'
        for file_path in file_path_list:
            file_name = os.path.basename(file_path)
            self.upload_single(file_path, f"{storage_dir}{file_name}")

    def upload_single(self, local_path, storage_path):
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"File not found: {local_path}")

        content_type = self._get_mime_type(local_path)
        upload_info = self._get_upload_url(content_type, storage_path)
        if not upload_info:
            raise RuntimeError(f"Failed to get upload URL for {local_path}")

        upload_url = upload_info.get('uploadUrl')
        self._upload_to_signed_url(local_path, upload_url, content_type)

    def _get_mime_type(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            return 'application/octet-stream'
        return mime_type

    def _get_upload_url(self, mime_type, storage_path):
        url = f"{self.base_url}/upload-url"

        payload = {
            'bucketName': self.bucket_name,
            'filePath': storage_path,
            'contentType': mime_type,
        }

        response = requests.post(url, json=payload)

        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(
                f"Error getting upload URL: {response.status_code}, "
                f"{response.text}"
            )

    def _upload_to_signed_url(self, local_path, upload_url, content_type):
        headers = {
            'Content-Type': content_type,
        }

        with open(local_path, 'rb') as f:
            response = requests.put(upload_url, data=f, headers=headers)

            if response.status_code == 200:
                print(f"Successfully uploaded: {local_path}")
            else:
                raise RuntimeError(
                    f"Upload failed: {response.status_code}, "
                    f"{response.text}"
                )


class ImageDownload(ImageManager):
    def get_file_list(self):
        url = f"{self.base_url}/files"
        params = {'bucketName': self.bucket_name}

        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(
                f"Failed to get file list: {response.status_code}, "
                f"{response.text}"
            )

    def download_single(self, storage_path, local_path):
        download_url = self._get_download_url(storage_path)
        if not download_url:
            raise RuntimeError(
                f"Failed to get download URL for {storage_path}"
            )

        local_dir = os.path.dirname(local_path)
        if local_dir:
            os.makedirs(local_dir, exist_ok=True)

        response = requests.get(download_url, stream=True)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded: {local_path}")
        else:
            raise RuntimeError(
                f"Failed to download {storage_path}: "
                f"{response.status_code}"
            )

    def download_files(self, storage_to_local):
        for storage_path, local_path in storage_to_local.items():
            if storage_path:
                self.download_single(storage_path, local_path)

    def download_all_images(self, local_dir):
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        file_list = self.get_file_list()
        if not file_list:
            print("No files to download.")
            return

        for file_info in file_list:
            if isinstance(file_info, str):
                file_path = file_info
            elif isinstance(file_info, dict):
                file_path = (
                    file_info.get('name')
                    or file_info.get('path')
                    or file_info.get('filePath')
                )
            else:
                print(f"Unknown file info format: {file_info}")
                continue

            if not file_path:
                continue

            filename = os.path.basename(file_path)
            local_path = os.path.join(local_dir, filename)
            try:
                self.download_single(file_path, local_path)
            except Exception as e:
                print(f"Error downloading {file_path}: {e}")

    def _get_download_url(self, file_path):
        url = f"{self.base_url}/download-url"
        params = {
            'bucketName': self.bucket_name,
            'filePath': file_path
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json().get('downloadUrl')
        else:
            raise RuntimeError(
                f"Failed to get download URL for {file_path}: "
                f"{response.status_code}, {response.text}"
            )
