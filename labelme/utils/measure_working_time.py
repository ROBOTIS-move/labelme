from cryptography.fernet import Fernet
import os
import datetime as dt
import sys


def get_user_data_dir(app_name="labelme"):
    """
    Returns user data directory path.
    """
    if sys.platform.startswith('win'):
        base_dir = os.path.expandvars('%APPDATA%')
    else:
        # Linux/Mac support
        base_dir = os.path.expanduser('~/.config')
    
    user_data_dir = os.path.join(base_dir, app_name)
    
    # Create directory if it doesn't exist
    os.makedirs(user_data_dir, exist_ok=True)
    
    return user_data_dir


def get_worker_name_file_path():
    """
    Returns worker_name.txt file path.
    Uses user data directory in all environments (dev/dist).
    """
    # Check environment variable first (Set in Runtime Hook)
    env_path = os.environ.get('LABELME_WORKER_NAME_FILE')
    if env_path:
        return env_path
    
    # Use user data directory in all environments
    user_data_dir = get_user_data_dir()
    worker_name_file = os.path.join(user_data_dir, 'worker_name.txt')
    
    # Migrate if existing file is in current directory
    old_file_path = os.path.join(sys.path[0], 'worker_name.txt')
    if os.path.exists(old_file_path) and not os.path.exists(worker_name_file):
        try:
            import shutil
            shutil.copy2(old_file_path, worker_name_file)
            print(f"[INFO] Migrated worker_name.txt to: {worker_name_file}")
        except Exception:
            pass  # Fail silently
    
    return worker_name_file


class MeasureTime():
    def __init__(self, crypto_mode=True):
        self.crypto_mode = crypto_mode
        self.working_total_time = 0
        self.break_total_time = 0
        self.pre_interaction_time = (
            dt.datetime.now().hour * 3600 +
            dt.datetime.now().minute * 60 +
            dt.datetime.now().second +
            dt.datetime.now().microsecond * 0.000001)
        self.break_standard_time = 10
        self.limit_time = 3600 * 24  # Prevent negative diff time after midnight
        self.working_count = 0
        self.worker_name = ''
        self.init_write_worker_name = True
        self.name_file_path = get_worker_name_file_path()
        if self.crypto_mode:
            self.crypto_key = b'lGJqH-91ET5Xv5U48HwmJYxY3VgNXilmqVwuWuOz4BA='

    def read_worker_name(self):
        if os.path.exists(self.name_file_path):
            with open(self.name_file_path, "r", encoding='utf-8') as f:
                for line in f:
                    self.worker_name = line
            print(f"[INFO] Worker name: {self.worker_name.strip()}", flush=True)
            return True
        else:
            return False

    def read_crypt_description(self, file_path):
        decode_text = []
        with open(file_path, "r") as file:
            for i, line in enumerate(file):
                bytes_str = line.strip().replace("b'", "").replace("'", "").encode()
                # Convert bytes to normal string
                result_str = bytes_str.decode()
                decode_text.append(result_str)
        return decode_text

    def write_crypt_description(self, save_path):
        folder_path, img_name = os.path.split(save_path)

        with open(os.path.join(folder_path, 'Cache.txt'), "a") as f:
            description_text = (
                img_name +
                ' - working_time : '
                + str(self.working_total_time) +
                ', break_time : ' + str(self.break_total_time) +
                ', working_count : ' + str(self.working_count))
            if self.init_write_worker_name:
                text = self.worker_name + '\n' + description_text
                self.init_write_worker_name = False
            else:
                text = description_text
            if self.crypto_mode:
                encrypted_text = self.encrypt_text(text)
                f.write(str(encrypted_text) + '\n')
            else:
                f.write(text + '\n')
        self.working_total_time = 0
        self.break_total_time = 0
        self.working_count = 0

    def encrypt_text(self, text):
        cipher_suite = Fernet(self.crypto_key)
        encrypted_text = cipher_suite.encrypt(text.encode())
        return encrypted_text

    def decrypt_text(key, encrypted_text):
        cipher_suite = Fernet(key)
        decrypted_text = cipher_suite.decrypt(encrypted_text).decode()
        return decrypted_text

    def measure_time(self):
        cur_interaction_time_date = dt.datetime.now()
        cur_interaction_time = (
            cur_interaction_time_date.hour * 3600 +
            cur_interaction_time_date.minute * 60 +
            cur_interaction_time_date.second +
            cur_interaction_time_date.microsecond * 0.000001)
        diff_interaction_time = cur_interaction_time - self.pre_interaction_time
        if diff_interaction_time < 0:
            diff_interaction_time = (
                cur_interaction_time +
                self.limit_time -
                self.pre_interaction_time)
        self.pre_interaction_time = cur_interaction_time
        if diff_interaction_time > self.break_standard_time:
            self.break_total_time += diff_interaction_time
        else:
            self.working_total_time += diff_interaction_time
