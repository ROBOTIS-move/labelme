#!/usr/bin/env python3
# Copyright 2020 ROBOTIS CO., LTD.
# Authors: Eungi Cho

import argparse
import glob
import json
import math
import multiprocessing
import os
import sys
import yaml

try:
    import lxml.builder
    import lxml.etree
except ImportError:
    print('Please install lxml:\n\n    pip install lxml\n')
    sys.exit(1)
import numpy as np
import PIL.Image

import labelme


class Convertor:
    def __init__(self, CONFIG, input_dir, popup=None):
        self.CONFIG = CONFIG
        self.input_dir = input_dir
        _, self.folder_name = os.path.split(input_dir)
        self.output_dir = self.create_folder(input_dir + '/obj')

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

        if not popup == None:
            popup.show()

        print('===========================================')
        print('Convert bounding box')
        print('{0}The total number of the files : {1}'.format(' '*2, len(json_list)))
        print('{0}The number of the process core : {1}'.format(' '*2, num_core))
        print('===========================================')

        process_num, process_remainder = divmod(len(json_list), num_core)
        pool = multiprocessing.Pool(processes=num_core)
        if len(json_list) <= num_core:
            pool.map(self.convert_bounding_box, json_list)
        else:
            for i in range(process_num):
                pool.map(
                    self.convert_bounding_box,
                    json_list[i * num_core:(i+1) * num_core])
                if not popup is None:
                    popup.set_progress(i / process_num * 100)

            pool.close()
            pool.join()

        print('Completed convert [{0}] folder'.format(self.folder_name))

    def create_folder(self, _dir):
        if not os.path.exists(_dir):
            os.mkdir(_dir)

        return _dir

    def convert_bounding_box(self, json_file):
        check_wrong_class = False
        with open(json_file, encoding='ISO-8859-1') as f:
            data = json.load(f)
        base = os.path.splitext(os.path.basename(json_file))[0]

        out_image_file = os.path.join(self.output_dir, base + '.png')

        class_names = self.CONFIG[data['classType']]
        new_path = data['imagePath']
        _, new_path = os.path.split(new_path)
        image_file = os.path.join(os.path.dirname(json_file), new_path)
        image = np.asarray(PIL.Image.open(image_file))
        result_image = labelme.utils.draw_instances(
            image, [], [], captions=''
        )
        PIL.Image.fromarray(result_image).save(out_image_file)

        maker = lxml.builder.ElementMaker()
        xml = maker.annotation(
            maker.folder(),
            maker.filename(base + '.png'),
            maker.database(),    # e.g., The VOC2007 Database
            maker.annotation(),  # e.g., Pascal VOC2007
            maker.image(),       # e.g., flickr
            maker.size(
                maker.height(str(image.shape[0])),
                maker.width(str(image.shape[1])),
                maker.depth(str(image.shape[2])),
            ),
            maker.segmented(),
        )

        bboxes_2d = []
        labels_2d = []
        for shape in data['shapes']:
            if shape['shape_type'] != 'rectangle':
                continue

            class_name = shape['label']

            if class_name not in class_names:
                print('Generating dataset from : {0}'.format(json_file))
                print('wrong class name : {0}'.format(class_name))
                check_wrong_class = True

            if shape['shape_type'] == 'rectangle':
                if not check_wrong_class:
                    class_id = class_names.index(class_name)

                    (xmin, ymin), (xmax, ymax) = shape['points']
                    bboxes_2d.append([xmin, ymin, xmax, ymax])
                    labels_2d.append(class_id)

                    captions = [class_names[l] for l in labels_2d]
                    result_image = labelme.utils.draw_instances(
                        result_image, bboxes_2d, labels_2d, captions=captions
                    )
                    PIL.Image.fromarray(result_image).save(out_image_file)


def convert_objects(input_dir, popup=None):
    class_data_yaml = os.path.dirname(os.path.realpath(__file__)) + '/class.yaml'
    try:
        print('Opening data file : {0}'.format(class_data_yaml))
        f = open(class_data_yaml, 'r')
        CONFIG = yaml.load(f, Loader=yaml.FullLoader)
    except:
        print('Error opening data yaml file!')
        sys.exit()

    Convertor(CONFIG, input_dir, popup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir', help='input annotated directory')
    args = parser.parse_args()

    convert_objects(args.input_dir)
