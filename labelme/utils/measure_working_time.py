from cryptography.fernet import Fernet
import os
import datetime as dt

class MeasureTime():
    def __init__(self, crypto_mode = False):
        self.crypto_mode = crypto_mode
        self.working_total_time = 0
        self.break_total_time = 0
        self.pre_interaction_time = dt.datetime.now().hour * 3600 + dt.datetime.now().minute * 60 + dt.datetime.now().second
        self.break_standard_time = 5
        self.limit_time = 3600 * 24
        self.working_count = 0
        if self.crypto_mode:
            self.crypto_key = b'lGJqH-91ET5Xv5U48HwmJYxY3VgNXilmqVwuWuOz4BA='
        
    def write_description(self, save_path):
        folder_path = save_path.split('\\')[0]
        img_name = save_path.split('\\')[1]
        with open(folder_path + '/Cache.txt', "a") as f:
            working_time_text = img_name + ' - working_time : ' + str(self.working_total_time) + ', break_time : ' + str(self.break_total_time)
            working_count_text = img_name + ' - working_time : ' + str(self.working_count)
            text = working_count_text + '\n' + working_count_text
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

