#!/usr/bin/env python3
# Copyright 2019 ROBOTIS CO., LTD.
# Authors: Gilbert, Eungi Cho

import argparse
import base64
import copy
import glob
import json
import math
import multiprocessing
import os
import sys
import yaml

import numpy as np
import PIL.Image

from labelme import utils


class Convertor:
    def __init__(self, CONFIG, input_dir, output_dir):
        self.segmentation_class, self.class_rgb = self.get_class(CONFIG)
        self.INPUT_DIR = input_dir
        if output_dir:
            self.merge_save = True
            self.OUTPUT_DIR = output_dir
        else:
            self.merge_save = False

        self.origin_image_dir, self.masked_image_dir, self.overlayed_image_dir = \
            self.created_output_dir(self.INPUT_DIR)

    def get_class(self, CONFIG):
        segmentation_class = []
        mask_color_rgb = []
        for class_name, color in CONFIG['segmentation'].items():
            segmentation_class.append(class_name)
            mask_color_rgb.append(color)

        mask_color_rgb = np.array(mask_color_rgb, np.uint16)

        return segmentation_class, mask_color_rgb

    def created_output_dir(self, dir_):
        if self.merge_save:
            dir_ = self.OUTPUT_DIR

        origin_image_dir = os.path.join(dir_, 'original_image')
        masked_image_dir = os.path.join(dir_, 'masked_image')
        overlayed_image_dir = os.path.join(dir_, 'overlayed_image')

        if self.merge_save:
            if not os.path.exists(origin_image_dir):
                os.mkdir(origin_image_dir)

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
        _, folder_name = os.path.split(self.INPUT_DIR)
        try:
            file_name = os.path.splitext(os.path.basename(json_file))[0]
            image_name = file_name + '.jpg'

            image, json_data = self.load_json_file(json_file)
            polygon_points = self.get_polygon_point(json_data)
            detected_labels = self.get_label(json_data)

            label, names = utils.shapes_to_label(
                image.shape,
                polygon_points,
                detected_labels,
                self.segmentation_class)

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

            if self.merge_save:
                PIL.Image.fromarray(image).save(os.path.join(
                    self.origin_image_dir,
                    image_name))

            PIL.Image.fromarray(overlayed_image).save(os.path.join(
                self.overlayed_image_dir,
                image_name))

        except:
            print('[{0}] folder : {1} error'.format(folder_name, file_name))


def convert_segments(input_dir, output_dir=None, num_core=10, labeler_name=''):
    class_data_yaml = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'class.yaml')
    _, folder_name = os.path.split(input_dir)

    try:
        print('Opening data file : {0}'.format(class_data_yaml))
        f = open(class_data_yaml, 'r')
        CONFIG = yaml.load(f, Loader=yaml.FullLoader)
    except:
        print('Error opening data yaml file!')
        sys.exit()

    json_list = glob.glob(os.path.join(input_dir, '*.json'))

    convertor = Convertor(CONFIG, input_dir, output_dir)

    print('===========================================')
    print('Convert mask image')
    print('{0}The total number of the files : {1}'.format(' '*2, len(json_list)))
    print('{0}The number of the process core : {1}'.format(' '*2, num_core))
    print('===========================================')

    for json_file in json_list:
        convertor.multi_convert_json_to_mask(json_file)

    print('Completed convert [{0}] folder'.format(folder_name))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir', help='input annotated directory')
    parser.add_argument('--num_core', default=10, help='The number of process folder')
    parser.add_argument('--output_dir', default=None, help='The output directory path')
    parser.add_argument('--labeler_name', default='')
    args = parser.parse_args()

    convert_segments(args.input_dir, args.output_dir, args.num_core, args.labeler_name)


if __name__ == '__main__':
    main()
