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
    class_data_yaml = None

    # Solution 1: PyInstaller bundle path (_MEIPASS/labelme/cli/class.yaml)
    try:
        class_data_yaml = get_resource_path('labelme/cli/class.yaml')
        if not os.path.exists(class_data_yaml):
            class_data_yaml = None
    except:
        pass

    # Solution 2: Current file location in development environment
    # Assumes this is called from cli/ directory
    if class_data_yaml is None or not os.path.exists(class_data_yaml):
        # Go up from utils/ to labelme/, then to cli/class.yaml
        utils_dir = os.path.dirname(os.path.realpath(__file__))
        labelme_dir = os.path.dirname(utils_dir)
        class_data_yaml = os.path.join(labelme_dir, 'cli', 'class.yaml')

    # Solution 3: Directly use sys._MEIPASS (PyInstaller)
    if not os.path.exists(class_data_yaml):
        try:
            class_data_yaml = os.path.join(sys._MEIPASS, 'labelme', 'cli', 'class.yaml')
        except AttributeError:
            pass

    # Verify the file exists
    if not os.path.exists(class_data_yaml):
        error_msg = f"class.yaml not found. Searched paths:\n"
        error_msg += f"  - {class_data_yaml}\n"
        try:
            error_msg += f"  - sys._MEIPASS: {sys._MEIPASS}\n"
        except:
            pass
        raise FileNotFoundError(error_msg)

    return class_data_yaml
