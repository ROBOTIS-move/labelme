from cryptography.fernet import Fernet
import os
import datetime as dt
import sys
import platform

class MeasureTime():
    def __init__(self, crypto_mode = True):
        self.crypto_mode = crypto_mode
        self.working_total_time = 0
        self.break_total_time = 0
        self.pre_interaction_time = dt.datetime.now().hour * 3600 + dt.datetime.now().minute * 60 + dt.datetime.now().second
        self.break_standard_time = 10
        self.limit_time = 3600 * 24 # 24시 이후 diff time이 - 값이 나오는 현상 방지
        self.working_count = 0
        self.worker_name = ''
        self.init_write_worker_name = True
        self.name_file_path = os.path.join(sys.path[0], 'worker_name.txt')
        if self.crypto_mode:
            self.crypto_key = b'lGJqH-91ET5Xv5U48HwmJYxY3VgNXilmqVwuWuOz4BA='

    def read_worker_name(self):
        if os.path.exists(self.name_file_path):
            with open(self.name_file_path, "r") as f:
                for line in f:
                    self.worker_name = line
            print(self.worker_name)
            return True
        else:
            return False

    def read_crypt_description(self, file_path):
        decode_text = []
        with open(file_path, "r") as file:
            for i, line in enumerate(file):
                bytes_str = line.strip().replace("b'", "").replace("'", "").encode()
                # bytes를 일반 문자열로 변환
                result_str = bytes_str.decode()
                decode_text.append(result_str)
        return decode_text

    def write_crypt_description(self, save_path):
        folder_path , img_name = os.path.split(save_path)

        with open(os.path.join(folder_path, 'Cache.txt'), "a") as f:
            description_text = img_name + ' - working_time : ' + str(self.working_total_time) + ', break_time : ' + str(self.break_total_time) + ', working_count : ' + str(self.working_count)
            if self.init_write_worker_name:
                text = self.worker_name + '\n' + description_text
                self.init_write_worker_name = False
            else :
                text = description_text
            if self.crypto_mode:
                encrypted_text = self.encrypt_text(text)
                f.write(str(encrypted_text) + '\n')
            else :
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
        cur_interaction_time = cur_interaction_time_date.hour * 3600 + cur_interaction_time_date.minute * 60 + cur_interaction_time_date.second
        diff_interaction_time = cur_interaction_time - self.pre_interaction_time
        if diff_interaction_time < 0 :
            diff_interaction_time = cur_interaction_time + self.limit_time - self.pre_interaction_time
        self.pre_interaction_time = cur_interaction_time
        if diff_interaction_time > self.break_standard_time:
            self.break_total_time += diff_interaction_time
        else :
            self.working_total_time += diff_interaction_time
