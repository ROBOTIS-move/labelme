#!/usr/bin/env python3
# Copyright 2025 ROBOTIS AI CO., LTD.
# Authors: Sunghun Jung

import os
import sys


def get_resource_path(relative_path):
    try:
        # Use _MEIPASS if built with PyInstaller
        base_path = sys._MEIPASS
    except AttributeError:
        # Use current file directory in development environment
        base_path = os.path.dirname(os.path.realpath(__file__))

    return os.path.join(base_path, relative_path)


def get_class_yaml_path():
    # First, check for PyInstaller's bundled path (_MEIPASS)
    try:
        base_path = sys._MEIPASS
        path = os.path.join(base_path, 'labelme', 'cli', 'class.yaml')
        if os.path.exists(path):
            return path
    except AttributeError:
        # Not running in a PyInstaller bundle, continue to dev path
        pass

    # Fallback for development environment
    # Assumes this file is in labelme/utils/
    try:
        utils_dir = os.path.dirname(os.path.realpath(__file__))
        labelme_dir = os.path.dirname(utils_dir)
        path = os.path.join(labelme_dir, 'cli', 'class.yaml')
        if os.path.exists(path):
            return path
    except Exception as e:
        # This path is for safety, should not be hit in normal dev env
        print(f"Error constructing dev path: {e}")

    raise FileNotFoundError('class.yaml not found in standard paths.')
