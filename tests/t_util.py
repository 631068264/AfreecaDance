#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import typing

from gevent import monkey

monkey.patch_all()

import importme

importme.init()

from PIL import Image
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True
from base import cvutil
from base.timeutil import Duration, duration_delta
from pathlib import Path


def sub_path(path: str, num, label: int = 0) -> str:
    p = Path(path)
    station_str, raw_duration = p.stem.split('_')
    duration = (Duration.set_time(raw_duration) + duration_delta(s=num)).to_str()
    file_name = f'{station_str}_{duration}_{label}{p.suffix}'
    file_dir = 'img'
    sub_img_path = Path(file_dir, file_name)
    return str(sub_img_path)


def pil_load(path: str):
    img = Image.open(path)
    total_width, total_height = img.size
    return img, total_width, total_height


def pil_cut(img, path: str, num: int, left_top_width, left_top_height, right_bottom_width, right_bottom_height: int):
    roi = img.crop((left_top_width, left_top_height, right_bottom_width, right_bottom_height))
    a = sub_path(path, num)
    roi.save(a)
    if os.path.getsize(a) < 1024 * 1:
        os.remove(a)


def cv_load(path: str):
    img = cvutil.load_img(path)
    total_height, total_width = img.shape[:2]
    return img, total_width, total_height


def cv_cut(img, path: str, num: int, left_top_width, left_top_height, right_bottom_width, right_bottom_height: int):
    roi = img[left_top_height:right_bottom_height, left_top_width:right_bottom_width]
    a = sub_path(path, num)
    cvutil.save_img(a, roi)
    if os.path.getsize(a) < 1024 * 3:
        os.remove(a)


def split_img_by_size(load_func: typing.Callable, path: str, row_len, column_len: int, cut_func: typing.Callable):
    img, total_width, total_height = load_func(path)
    width, height = total_width // column_len, total_height // row_len
    num = 0
    for i in range(0, row_len):
        left_top_height = i * height
        right_bottom_height = (i + 1) * height
        for j in range(0, column_len):
            left_top_width = j * width
            right_bottom_width = (j + 1) * width
            print(f'{left_top_width}:{left_top_height}:, {right_bottom_width}:{right_bottom_height}')
            cut_func(img, path, num * 3, left_top_width, left_top_height, right_bottom_width, right_bottom_height)
            num += 1


# PATH = '36997061_0:10:0.jpg'
# # img_load, img_cut = cv_load,cv_cut
# img_load, img_cut = sk_load, sk_cut
# # img_load, img_cut = pil_load, pil_cut
# split_img_by_size(img_load, PATH, 10, 10, img_cut)
