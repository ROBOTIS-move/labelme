#!/usr/bin/env python3
# Copyright 2019 ROBOTIS CO., LTD.
# Authors: Gilbert, Eungi Cho

import argparse
import base64
import copy
import glob
import json
import multiprocessing
import os
import sys
import yaml

import numpy as np
import PIL.Image

from labelme import utils


class Convertor:
    def __init__(self, CONFIG, input_dir):
        os.environ["QT_LOGGING_RULES"] = "qt5ct.debug=false"

        self.config = CONFIG
        _, self.folder_name = os.path.split(input_dir)
        self.origin_image_dir, self.masked_image_dir, self.overlayed_image_dir = \
            self.created_output_dir(input_dir)

        json_list = glob.glob(os.path.join(input_dir, '*.json'))
        num_core = multiprocessing.cpu_count()
        if num_core >= 10:
            num_core = 10
        elif num_core >= 5:
            num_core = 5
        elif num_core >= 2:
            num_core = 2
        else:
            num_core = 1

        print('===========================================')
        print('Convert mask image')
        print('{0}The folder name : {1}'.format(' '*2, self.folder_name))
        print('{0}The total number of the files : {1}'.format(' '*2, len(json_list)))
        print('{0}The number of the process core : {1}'.format(' '*2, num_core))
        print('===========================================')

        process_num, process_remainder = divmod(len(json_list), num_core)
        pool = multiprocessing.Pool(processes=num_core)
        if len(json_list) <= num_core:
            pool.map(self.multi_convert_json_to_mask, json_list)
        else:
            for i in range(process_num):
                pool.map(
                    self.multi_convert_json_to_mask,
                    json_list[i * num_core : (i+1) * num_core])

            pool.close()
            pool.join()

        print('Completed convert [{0}] folder'.format(self.folder_name))

    def get_class(self, class_type):
        segmentation_class = []
        mask_color_rgb = []
        for class_name, color in self.config[class_type].items():
            segmentation_class.append(class_name)
            mask_color_rgb.append(color)

        mask_color_rgb = np.array(mask_color_rgb, np.uint16)

        return segmentation_class, mask_color_rgb

    def created_output_dir(self, dir_):
        origin_image_dir = os.path.join(dir_, 'original_image')
        masked_image_dir = os.path.join(dir_, 'masked_image')
        overlayed_image_dir = os.path.join(dir_, 'overlayed_image')

        if not os.path.exists(masked_image_dir):
            os.mkdir(masked_image_dir)
        if not os.path.exists(overlayed_image_dir):
            os.mkdir(overlayed_image_dir)

        return origin_image_dir, masked_image_dir, overlayed_image_dir

    def get_polygon_point(self, data):
        polygon_points = []
        for index in range(len(data['shapes'])):
            if data['shapes'][index].get('shape_type') == 'polygon':
                polygon_points.append(data['shapes'][index])

        return polygon_points

    def get_label(self, data):
        detected_labels = {'_background_': 0}
        for shape in sorted(data['shapes'], key=lambda x: x['label']):
            label_name = shape['label']
            if label_name in self.segmentation_class:
                if label_name in detected_labels:
                    label_value = detected_labels[label_name]
                else:
                    label_value = len(detected_labels)
                    detected_labels[label_name] = label_value

        return detected_labels

    def load_json_file(self, json_file):
        with open(json_file, encoding='ISO-8859-1') as file_:
            json_data = json.load(file_)
        if json_data['imageData']:
            imageData = json_data['imageData']
        else:
            imagePath = os.path.join(os.path.dirname(json_file), json_data['imagePath'])
            with open(imagePath, 'rb') as f:
                imageData = f.read()
                imageData = base64.b64encode(imageData).decode('utf-8')
        image = utils.img_b64_to_arr(imageData)

        return image, json_data

    def multi_convert_json_to_mask(self, json_file):
        try:
            file_name = os.path.splitext(os.path.basename(json_file))[0]
            image_name = file_name + '.jpg'

            image, json_data = self.load_json_file(json_file)
            self.segmentation_class, self.class_rgb = self.get_class(json_data['classType'])
            polygon_points = self.get_polygon_point(json_data)
            detected_labels = self.get_label(json_data)

            label, names = utils.shapes_to_label(
                image.shape,
                polygon_points,
                detected_labels,
                self.segmentation_class,
                file_name=file_name)

            label_names = [None] * (max(detected_labels.values()) + 1)

            for name, value in detected_labels.items():
                label_names[value] = name

            overlayed_image = utils.draw_label(
                label,
                image,
                label_names,
                names,
                copy.deepcopy(self.class_rgb),
                self.segmentation_class)

            utils.lblsave_old(
                os.path.join(self.masked_image_dir, file_name),
                label,
                names,
                copy.deepcopy(self.class_rgb),
                self.segmentation_class)

            PIL.Image.fromarray(overlayed_image).save(os.path.join(
                self.overlayed_image_dir,
                image_name))

        except:
            pass


def convert_segments(input_dir):
    class_data_yaml = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'class.yaml')

    try:
        print('Opening data file : {0}'.format(class_data_yaml))
        f = open(class_data_yaml, 'r')
        CONFIG = yaml.load(f, Loader=yaml.FullLoader)
    except:
        print('Error opening data yaml file!')
        sys.exit()

    Convertor(CONFIG, input_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir', help='input annotated directory')
    args = parser.parse_args()

    convert_segments(args.input_dir)
