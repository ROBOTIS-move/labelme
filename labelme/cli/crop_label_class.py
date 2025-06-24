#!/usr/bin/env python3
# Copyright 2025 ROBOTISAI CO., LTD.
# Authors: Sunghun Jung

import cv2
import os
import sys
import yaml
import glob
import json
import shutil
import argparse

from colorama import Fore, Style


class CropLabelClass:
    def __init__(self, config, input_dir, popup=None):
        self.config = config
        self.allow_class = self.config['ELStateDetection']
        _, self.folder_name = os.path.split(input_dir)

        self._delete_class_dir(input_dir)
        self._created_class_dir(input_dir)

        json_list = glob.glob(os.path.join(input_dir, '*.json'))

        if popup is not None:
            popup.show()

        print('===========================================')
        print('Crop label class')
        print('{0}The folder name : {1}'.format(' ' * 2, self.folder_name))
        print('{0}The total number of the files : {1}'.format(' ' * 2, len(json_list)))
        print('===========================================')

        for index, json_file in enumerate(json_list):
            self._crop_image(input_dir, json_file)
            if popup is not None:
                popup.set_progress(int(index * (100 / len(json_list))))

        self._delete_empty_class_dir(input_dir)

        print('Completed convert [{0}] folder'.format(self.folder_name))

        if popup is not None:
            popup.close()


    def _created_class_dir(self, input_dir):
        for class_name in self.allow_class.keys():
            class_dir = os.path.join(input_dir, class_name)
            if not os.path.exists(class_dir):
                os.makedirs(class_dir)

    def _crop_image(self, root_path, json_file):
        json_data = self._load_json(json_file)

        for index, shape in enumerate(json_data['shapes']):
            if shape['shape_type'] == 'rectangle':
                label = shape['label']
                image_name = json_data['imagePath']
                if label not in self.allow_class:
                    print(Fore.RED + f"{image_name}: '{label}'" + Style.RESET_ALL)
                    continue

                image_path = os.path.join(root_path, image_name)
                image = cv2.imread(image_path)
                if image is None:
                    print(f"Error: Could not read image {image_name}")

                points = shape['points']
                x1, y1 = int(points[0][0]), int(points[0][1])
                x2, y2 = int(points[1][0]), int(points[1][1])

                height, width = image.shape[:2]
                margin_x = int((x2 - x1) * 0.15)
                margin_y = int((y2 - y1) * 0.15)

                x1 = max(0, x1 - margin_x)
                y1 = max(0, y1 - margin_y)
                x2 = min(width, x2 + margin_x)
                y2 = min(height, y2 + margin_y)

                cropped_image = image[y1:y2, x1:x2]

                class_dir = os.path.join(root_path, label)

                output_path = os.path.join(class_dir, f'{os.path.basename(image_name)}_{index}')
                cv2.imwrite(output_path, cropped_image)
            else:
                print(f"Warning: Unsupported shape type '{shape['shape_type']}' in {json_file}. Only 'rectangle' is supported.")

    def _delete_class_dir(self, input_dir):
        class_dirs = [os.path.join(input_dir, class_name) for class_name in self.allow_class.keys()]
        for class_dir in class_dirs:
            if os.path.exists(class_dir):
                shutil.rmtree(class_dir)

    def _delete_empty_class_dir(self, input_dir):
        class_dirs = [os.path.join(input_dir, class_name) for class_name in self.allow_class.keys()]
        for class_dir in class_dirs:
            if os.path.exists(class_dir) and not os.listdir(class_dir):
                os.rmdir(class_dir)

    def _load_json(self, json_file):
        with open(json_file, mode='r', encoding='utf-8') as f:
            data = json.load(f)
        return data


def crop_labels(input_dir, popup=None):
    class_data_yaml = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'class.yaml')

    try:
        print('Opening data file : {0}'.format(class_data_yaml))
        f = open(class_data_yaml, 'r')
        CONFIG = yaml.load(f, Loader=yaml.FullLoader)
    except Exception as e:
        print('Error opening data yaml file! {0}'.format(e))
        sys.exit()

    CropLabelClass(CONFIG, input_dir, popup)

def delete_class_dir(input_dir):
    folder_list = os.listdir(input_dir)
    for folder in folder_list:
        folder_path = os.path.join(input_dir, folder)
        if os.path.isdir(folder_path):
            shutil.rmtree(folder_path)

    folder_name = os.path.basename(input_dir)
    print(f"Deleted all class directories in {folder_name}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir', help='input annotated directory')
    args = parser.parse_args()

    crop_labels(args.input_dir)