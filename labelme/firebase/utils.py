#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import os
import yaml
import requests


class ConfigLoader:
    def __init__(self):
        self.config = self._load_config()
        self.common_config = self.config.get('common')
        self.database_config = self.config.get('database')
        self.user_config = self.config.get('user')

    def _load_config(self):
        config_path = os.path.join(
            os.path.dirname(__file__), 'config', 'config.yaml'
        )
        with open(config_path, 'r') as f:
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