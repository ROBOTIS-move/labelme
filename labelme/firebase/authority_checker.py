#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import requests

from labelme.firebase.utils import ConfigLoader


class AuthorityChecker:
    def __init__(self):
        cfg_loader = ConfigLoader()
        self.url = cfg_loader.user_config.get('url')

    def get_all_users(self):
        url = f"{self.url}/users"
        response = requests.get(url)
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
            'data': {
                'name': name,
                'reviewer': False,
                'finalReviewer': False,
                'supervisor': False,
                '5-generation': False,
                'dropCount': 0,
            }
        }
        response = requests.post(url, json=body)
        if response.status_code == 201:
            print(f"Successfully created user: {user_id}")
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
        response = requests.patch(url, json=body)
        if response.status_code == 200:
            print(f"Successfully updated user: {user_id}")
        else:
            raise RuntimeError(
                f"Failed to update user: {response.status_code}, "
                f"{response.text}"
            )

    def delete_user(self, user_email):
        url = f'{self.url}/user?email={user_email}'
        response = requests.delete(url)
        if response.status_code == 200:
            print(f"Successfully deleted user: {user_email}")
        else:
            raise RuntimeError(
                f"Failed to delete user: {response.status_code}, "
                f"{response.text}"
            )

if __name__ == '__main__':
    authority_checker = AuthorityChecker()
    authority_checker.create_user('label_test@robotis.com', 'test')
    # authority_checker.delete_user('labelme@robotis.com')
    print(authority_checker.get_all_users())