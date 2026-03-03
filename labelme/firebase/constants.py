#!/usr/bin/env python3
# Copyright 2026 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

from enum import Enum


class TaskStatus(str, Enum):
    READY = 'ready'
    PROCESSING = 'processing'
    POSTPONE = 'postpone'
    REQUEST_REVIEW = 'request_review'
    REVIEWING = 'reviewing'
    MODIFY = 'modify'
    MODIFYING = 'modifying'
    FINISHED_MODIFY = 'finished_modify'
    RE_REVIEWING = 're_reviewing'
    REQUEST_FINAL_REVIEW = 'request_final_review'
    FINAL_REVIEWING = 'final_reviewing'
    READY_GT = 'ready_gt'


# Status transition map: current_status -> next_status on submit
STATUS_TRANSITIONS = {
    # Worker submit
    TaskStatus.PROCESSING: TaskStatus.REQUEST_REVIEW,
    TaskStatus.MODIFYING: TaskStatus.FINISHED_MODIFY,
    # Reviewer submit
    TaskStatus.REVIEWING: TaskStatus.MODIFY,
    TaskStatus.RE_REVIEWING: TaskStatus.REQUEST_FINAL_REVIEW,
    # Supervisor submit
    TaskStatus.FINAL_REVIEWING: TaskStatus.READY_GT,
}

# Source statuses for Load Task by mode
LOAD_SOURCE_STATUSES = {
    'labeling': [TaskStatus.READY],
    'review': [TaskStatus.REQUEST_REVIEW, TaskStatus.FINISHED_MODIFY],
    'final_review': [TaskStatus.REQUEST_FINAL_REVIEW],
}

# Status to set after loading by mode
LOAD_NEXT_STATUS = {
    'labeling': {
        TaskStatus.READY: TaskStatus.PROCESSING,
    },
    'review': {
        TaskStatus.REQUEST_REVIEW: TaskStatus.REVIEWING,
        TaskStatus.FINISHED_MODIFY: TaskStatus.RE_REVIEWING,
    },
    'final_review': {
        TaskStatus.REQUEST_FINAL_REVIEW: TaskStatus.FINAL_REVIEWING,
    },
}

# User ID field name per mode
USER_FIELD_MAP = {
    'labeling': 'worker_id',
    'review': 'reviewer_id',
    'final_review': 'final_reviewer_id',
}


class StoragePath:
    IMAGE = 'image'
    JSON = 'json'
    ENCRYPT = 'encrypt'
    COMMENT = 'comment'

    @staticmethod
    def normal(folder, filename):
        # e.g. "image/xxx.jpg"
        return f"{folder}/{filename}"

    @staticmethod
    def postpone(user_id, folder, filename):
        # e.g. "postpone/user1/image/xxx.jpg"
        return f"postpone/{user_id}/{folder}/{filename}"
