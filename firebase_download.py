import os
import requests


class FirebaseDownload:
    def __init__(self):
        self.base_url = 'https://gaemi-storage-manager-675180880514.asia-northeast3.run.app'
        self.bucket_name = 'label-0001'

    def get_file_list(self):
        url = f"{self.base_url}/files"
        params = {'bucketName': self.bucket_name}

        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get file list: {response.status_code}, {response.text}")
            return []

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
            print(f"Failed to get download URL for {file_path}: {response.status_code}, {response.text}")
            return None

    def download_all_images(self, local_dir):
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        file_list = self.get_file_list()
        if not file_list:
            print("No files to download.")
            return

        for file_info in file_list:
            # Assuming file_info contains 'name' or 'path' key
            # Adjust based on actual API response structure
            if isinstance(file_info, str):
                file_path = file_info
            elif isinstance(file_info, dict):
                file_path = file_info.get('name') or file_info.get('path') or file_info.get('filePath')
            else:
                print(f"Unknown file info format: {file_info}")
                continue

            if not file_path:
                continue

            try:
                download_url = self._get_download_url(file_path)
                if not download_url:
                    continue

                # Extract filename from path (flatten directory structure)
                filename = os.path.basename(file_path)
                local_path = os.path.join(local_dir, filename)

                # Download file with streaming for memory efficiency
                response = requests.get(download_url, stream=True)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Downloaded: {filename}")
                else:
                    print(f"Failed to download {filename}: {response.status_code}")

            except Exception as e:
                print(f"Error downloading {file_path}: {e}")


if __name__ == '__main__':
    downloader = FirebaseDownload()
    # Test download to local directory
    # downloader.download_all_images('./downloaded_images')