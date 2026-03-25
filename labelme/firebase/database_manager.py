#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import logging
import time

import requests
from requests.exceptions import ConnectionError as ReqConnectionError
from requests.exceptions import ChunkedEncodingError
from requests.exceptions import Timeout as ReqTimeout

from labelme.firebase.utils import ConfigLoader

logger = logging.getLogger(__name__)


def _created_at_seconds(doc):
    val = doc.get('createdAt', '')
    if isinstance(val, dict):
        return val.get('_seconds', 0)
    return val


class DatabaseManager:
    def __init__(self):
        cfg_loader = ConfigLoader()
        self.common_url = cfg_loader.common_config.get('base_url')

    def get_all_document(self):
        url = f"{self.common_url}/annotations"
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(
                f"Failed to get all document: {response.status_code}, "
                f"{response.text}"
            )

    MAX_WRITE_RETRIES = 3
    WRITE_RETRY_DELAY = 1.0

    def update_document(self, doc_id, data):
        url = f"{self.common_url}/annotation"
        body = {'id': doc_id, 'data': data}
        last_error = None

        for attempt in range(self.MAX_WRITE_RETRIES):
            try:
                response = requests.patch(url, json=body, timeout=30)
                if response.status_code in (200, 201):
                    logger.info(
                        "Successfully updated document: %s", doc_id,
                    )
                    return
                raise RuntimeError(
                    f"Failed to update document: "
                    f"{response.status_code}, {response.text}"
                )
            except ReqTimeout as e:
                # Timeout: PATCH may have been applied on server
                if self._verify_update_applied(doc_id, data):
                    logger.info(
                        "Timeout but PATCH verified for %s", doc_id,
                    )
                    return
                last_error = e
                logger.warning(
                    "Timeout retry %d/%d for %s: %s",
                    attempt + 1, self.MAX_WRITE_RETRIES, doc_id, e,
                )
                if attempt < self.MAX_WRITE_RETRIES - 1:
                    time.sleep(self.WRITE_RETRY_DELAY)
            except (ReqConnectionError, ChunkedEncodingError) as e:
                last_error = e
                logger.warning(
                    "Write retry %d/%d for %s: %s",
                    attempt + 1, self.MAX_WRITE_RETRIES, doc_id, e,
                )
                if attempt < self.MAX_WRITE_RETRIES - 1:
                    time.sleep(self.WRITE_RETRY_DELAY)

        raise RuntimeError(
            f"Network error after {self.MAX_WRITE_RETRIES} retries "
            f"for document '{doc_id}'.\n"
            f"Please contact the administrator with the following info:\n"
            f"  Document: {doc_id}\n"
            f"  Error: {last_error}"
        )

    def _verify_update_applied(self, doc_id, data):
        try:
            all_docs = self.get_all_document()
        except Exception:
            return False
        for d in all_docs:
            if d.get('imageName') != doc_id:
                continue
            # Check if key fields from data match
            for key, val in data.items():
                if d.get(key) != val:
                    return False
            return True
        return False

    def get_candidates_by_statuses(self, statuses):
        all_docs = self.get_all_document()
        if not all_docs:
            return []
        status_vals = [
            s.value if hasattr(s, 'value') else s for s in statuses
        ]
        filtered = [
            d for d in all_docs if d.get('status') in status_vals
        ]
        filtered.sort(key=lambda d: (
            not d.get('isPriority', False), _created_at_seconds(d)
        ))
        return filtered

    def get_candidates_by_statuses_excluding_user(
        self, statuses, exclude_field, exclude_user_id,
        required_empty_field=None,
    ):
        all_docs = self.get_all_document()
        if not all_docs:
            return []
        status_vals = [
            s.value if hasattr(s, 'value') else s for s in statuses
        ]
        filtered = [
            d for d in all_docs
            if d.get('status') in status_vals
            and d.get(exclude_field) != exclude_user_id
            and (
                required_empty_field is None
                or d.get(required_empty_field, '') == ''
            )
        ]
        filtered.sort(key=lambda d: (
            not d.get('isPriority', False), _created_at_seconds(d)
        ))
        return filtered

    def get_documents_by_status_and_user(self, status, field, user_id):
        all_docs = self.get_all_document()
        if not all_docs:
            return []
        status_val = status.value if hasattr(status, 'value') else status
        filtered = [
            d for d in all_docs
            if d.get('status') == status_val and d.get(field) == user_id
        ]
        filtered.sort(key=lambda d: (
            not d.get('isPriority', False), _created_at_seconds(d)
        ))
        return filtered
