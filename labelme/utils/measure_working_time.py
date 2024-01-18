from cryptography.fernet import Fernet
import os
import datetime as dt

class MeasureTime():
    def __init__(self, save_path, crypto_mode = False):
        self.save_path = save_path
        self.crypto_mode = crypto_mode
        self.working_total_time = 0
        self.break_total_time = 0
        self.pre_interaction_time = 0
        self.break_standard_time = 5
        self.limit_time = 3600 * 24
        if self.crypto_mode:
            self.crypto_key = b'lGJqH-91ET5Xv5U48HwmJYxY3VgNXilmqVwuWuOz4BA='
        
    def write_description(self, description):
        with open(self.save_path + '/Cache.txt', "a") as f:
            for text in description:
                if self.crypto_mode:
                    encrypted_text = self.encrypt_text(text)
                    f.write(str(encrypted_text) + '\n')
                else :
                    f.write(text + '\n')

    def encrypt_text(self, text):
        cipher_suite = Fernet(self.crypto_key)
        encrypted_text = cipher_suite.encrypt(text.encode())
        return encrypted_text
    
    def measure_time(self):
        cur_interaction_time_date = dt.datetime.now()
        cur_interaction_time = cur_interaction_time_date.hour * 3600 + cur_interaction_time_date.minute * 60 + cur_interaction_time_date.second
        diff_interaction_time = cur_interaction_time - self.pre_interaction_time
        if diff_interaction_time < 0 :
            diff_interaction_time = cur_interaction_time + self.limit_time - self.pre_interaction_time
        print("Interaction time check : ", diff_interaction_time)
        self.pre_interaction_time = cur_interaction_time
        if diff_interaction_time > self.break_standard_time:
            self.break_total_time += diff_interaction_time
        else :
            self.working_total_time += diff_interaction_time
        print("Total Time - break : ", self.break_total_time)
        print("Total Time - working : ", self.working_total_time)

