import requests
import xml.etree.ElementTree as ET
import os

class VersionChecker:
    def __init__(self):
        self.url = 'https://raw.githubusercontent.com/ROBOTIS-move/labelme/feature-add-version-checker/version.xml'
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.local_path = self.current_path + '/../../version.xml'

    def fetch_file(self, mode):
        if mode == 'github':
            try:
                response = requests.get(self.url)
                return True, response.content

            except requests.exceptions.ConnectionError:
                print('INTERNET CONECTION Fail')
                return False, None
        elif mode == 'local':
            try:
                with open(self.local_path, 'r', encoding='utf-8') as file:
                    return True, file.read()
            except Exception as e:
                return False, None

    def get_version(self, mode):
        file_open_check, file_content = self.fetch_file(mode)
        if mode == 'github' and not file_open_check:
            return False, None
        root = ET.fromstring(file_content)
        version = root.find('version').text
        return True, version
    
    def check_version(self):
        internet_status, github_version = self.get_version('github')
        _, local_version = self.get_version('local')
        self.github_version = github_version
        self.local_version = local_version
        if github_version != local_version:
            self.version_result = False
        else:
            self.version_result = True
        self.internet_status = internet_status
            
