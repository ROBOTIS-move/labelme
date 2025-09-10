import os
import sys
import yaml
import json

from cryptography.fernet import Fernet


class EncryptCache():

    def __init__(self):
        crypto_key = b'lGJqH-91ET5Xv5U48HwmJYxY3VgNXilmqVwuWuOz4BA='
        self.fernet = Fernet(crypto_key)

        self.worker_name = self._extract_worker_name()
        self.prev_worker_name = None

        self.cache_path = None
        self.encrypt_path = None

    def run(self, dir_path):
        self.cache_path = f'{dir_path}/cache.yaml'
        self.encrypt_path = f'{dir_path}/encrypt.bin'

        if self._check_bin_file():
            self._decrypt_file()
        else:
            self._create_yaml_file()
            self._encrypt_file()
            return
        if not self._check_same_worker():
            self._update_yaml_contents(dir_path)
            self._encrypt_file()

    def _extract_worker_name(self):
        name_file_path = os.path.join(sys.path[0], 'worker_name.txt')
        if os.path.exists(name_file_path):
            with open(name_file_path, "r") as f:
                for line in f:
                    content = line
            worker_name = content.split(':')[-1].strip()
            return worker_name

    def _check_bin_file(self):
        if os.path.exists(self.encrypt_path):
            return True
        return False

    def _create_yaml_file(self):
        if not os.path.exists(self.cache_path):
            self._write_yaml({'prev_worker': self.worker_name})

    def _check_same_worker(self):
        yaml_contents = self._read_yaml()
        prev_worker = yaml_contents.get('prev_worker', None)
        if prev_worker == self.worker_name:
            return True
        self.prev_worker_name = prev_worker
        return False

    def _update_yaml_contents(self, dir_path):
        yaml_contents = self._read_yaml()
        for file in os.listdir(dir_path):
            if file.endswith('.json'):
                json_path = os.path.join(dir_path, file)
                json_data = self.read_json(json_path)
                shape_list = self._extract_shape_list(json_data)
                if shape_list is not None:
                    img_name = json_data.get('imagePath', None)
                img_data = yaml_contents.get(img_name, None)
                if img_data is None:
                    yaml_contents[img_name] = [{
                        'worker': self.prev_worker_name,
                        'shapes': shape_list
                    }]
                else:
                    save_flag = False
                    for working_data in yaml_contents[img_name]:
                        if working_data['worker'] == self.prev_worker_name:
                            working_data['shapes'] = shape_list
                            save_flag = True
                            break
                    if not save_flag:
                        yaml_contents[img_name].append({
                            'worker': self.prev_worker_name,
                            'shapes': shape_list
                        })
        yaml_contents['prev_worker'] = self.worker_name
        self._write_yaml(yaml_contents)

    def _extract_shape_list(self, json_data):
        if json_data is not None:
            shape_list = json_data.get('shapes', [])
            edited_shape_list = self._edit_shape_list(shape_list)
            return edited_shape_list
        return None

    def _encrypt_file(self):
        cache_file = open(self.cache_path, 'r')
        encrypt_file = open(self.encrypt_path, 'wb')

        contents = cache_file.read()
        encrypted_content = self.fernet.encrypt(bytes(contents, 'utf-8'))
        encrypt_file.write(encrypted_content)

        cache_file.close()
        encrypt_file.close()

        self._remove_file(self.cache_path)

    def _decrypt_file(self):
        encrypt_file = open(self.encrypt_path, 'rb')
        cache_file = open(self.cache_path, 'w', encoding='utf-8')

        cache_contents = encrypt_file.read()
        encrypt_contents = self.fernet.decrypt(cache_contents)
        cache_file.write(encrypt_contents.decode())

        cache_file.close()
        encrypt_file.close()

    def _edit_shape_list(self, shape_list):
        edited_shape_list = []
        for shape in shape_list:
            content_dict = {
                'label' : shape['label'],
                'points' : shape['points'],
            }
            edited_shape_list.append(content_dict)
        return edited_shape_list

    def _remove_file(self, target_file_path):
        if os.path.exists(target_file_path):
            os.remove(target_file_path)

    def _write_yaml(self, data):
        with open(self.cache_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True)

    def _read_yaml(self):
        with open(self.cache_path, 'r', encoding='utf-8') as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        return data

    def read_json(self, json_path):
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        return None

if __name__ == '__main__':
    encrypt_cache = EncryptCache()
    test_dir = '/home/hun/GT_manager/GT_ALGO/review/ODAS_286_original'
    encrypt_cache.encrypt_path = f'{test_dir}/encrypt.bin'
    encrypt_cache.cache_path = f'{test_dir}/cache.yaml'
    encrypt_cache._decrypt_file()
    # print(encrypt_cache._read_yaml())