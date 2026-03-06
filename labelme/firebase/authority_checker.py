#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import logging

import requests

from labelme.firebase.utils import ConfigLoader

logger = logging.getLogger(__name__)


DEFAULT_DATA = {
    'name': '',
    'reviewer': False,
    'finalReviewer': False,
    'supervisor': False,
    '5-generation': False,
    'dropCount': 0,
    'dropImageList': [],
}


class AuthorityChecker:
    def __init__(self):
        cfg_loader = ConfigLoader()
        self.url = cfg_loader.user_config.get('url')

    def get_all_users(self):
        url = f"{self.url}/users"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(
                f"Failed to get users: {response.status_code}, "
                f"{response.text}"
            )

    def create_user(self, user_id, name):
        url = f"{self.url}/user"
        body = {
            'email': user_id,
            'data': DEFAULT_DATA
        }
        body['data']['name'] = name
        response = requests.post(url, json=body, timeout=30)
        if response.status_code == 201:
            logger.info("Successfully created user: %s", user_id)
        else:
            raise RuntimeError(
                f"Failed to create user: {response.status_code}, "
                f"{response.text}"
            )

    def update_user(self, user_id, data):
        url = f"{self.url}/user"
        body = {
            'email': user_id,
            'data': data
        }
        response = requests.patch(url, json=body, timeout=30)
        if response.status_code == 200:
            logger.info("Successfully updated user: %s", user_id)
        else:
            raise RuntimeError(
                f"Failed to update user: {response.status_code}, "
                f"{response.text}"
            )

    def change_authority(self, user_id):
        url = f"{self.url}/user/grant"
        body = {
            'email': user_id,
        }

        response = requests.post(url, json=body, timeout=30)
        if response.status_code == 200:
            logger.info("Successfully updated user: %s", user_id)
        else:
            raise RuntimeError(
                f"Failed to update user: {response.status_code}, "
                f"{response.text}"
            )

    def delete_user(self, user_email):
        response = requests.delete(
            f'{self.url}/user',
            params={'email': user_email},
            timeout=30,
        )
        if response.status_code == 200:
            logger.info("Successfully deleted user: %s", user_email)
        else:
            raise RuntimeError(
                f"Failed to delete user: {response.status_code}, "
                f"{response.text}"
            )
