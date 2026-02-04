import os
import requests
import mimetypes

class FirebaseUpload:
    def __init__(self):
        self.base_url = 'https://gaemi-storage-manager-675180880514.asia-northeast3.run.app'
        self.bucket_name = 'label-0001'

    def upload(self, file_path_list):
        for file_path in file_path_list:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue

            # 1. 인증된 업로드 URL 가져오기
            try:
                # API 호출 시 사용한 contentType을 그대로 사용해야 함
                content_type = self._get_mime_type(file_path)
                upload_info = self._get_upload_url(file_path, content_type)
                if not upload_info:
                    continue

                upload_url = upload_info.get('uploadUrl')

                # 2. 실제 파일 업로드
                self._upload_to_signed_url(file_path, upload_url, content_type)

            except Exception as e:
                print(f"Failed to upload {file_path}: {e}")

    def _get_mime_type(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            return 'application/octet-stream'
        return mime_type

    def _get_upload_url(self, local_path, mime_type):
        url = f"{self.base_url}/upload-url"
        file_name = os.path.basename(local_path)
        storage_path = 'images/'

        payload = {
            'bucketName': self.bucket_name,
            'filePath': f'{storage_path}{file_name}',
            'contentType': mime_type,
        }

        # JSON body로 전송 (spec: body json structure)
        response = requests.post(url, json=payload)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting upload URL: {response.status_code}, {response.text}")
            return None

    def _upload_to_signed_url(self, local_path, upload_url, content_type):
        headers = {
            'Content-Type': content_type,
        }

        with open(local_path, 'rb') as f:
            # PUT method 사용 (spec: method PUT)
            response = requests.put(upload_url, data=f, headers=headers)

            if response.status_code == 200:
                print(f"Successfully uploaded: {local_path}")
            else:
                print(f"Upload failed: {response.status_code}, {response.text}")


if __name__ == '__main__':
    firebase_upload = FirebaseUpload()
    # 테스트용 경로 (실제 경로에 맞게 수정 필요)
    test_file = '/home/hun/Downloads/2026_01_30_13_11_57/csi/floor_1/outside/2026_01_30_10_57_40_330.jpg'
    firebase_upload.upload([test_file])