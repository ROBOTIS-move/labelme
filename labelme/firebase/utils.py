#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import yaml
import requests


class ConfigLoader:
    def __init__(self):
        self.config = self._load_config()
        self.common_config = self.config.get('common')
        self.database_config = self.config.get('database')

    def _load_config(self):
        # with open('./config/config.yaml', 'r') as f:
        with open('/home/hun/gaemi_ws/src/labelme/labelme/firebase/config/config.yaml', 'r') as f:
            return yaml.safe_load(f)

    def get(self, key):
        return self.config.get(key)


class APIManager:
    def request_post(self, url, body):
        response = requests.post(url, json=body)
        return response

    def request_get(self, url):
        response = requests.get(url)
        return response

    def request_delete(self, url):
        response = requests.delete(url)
        return response