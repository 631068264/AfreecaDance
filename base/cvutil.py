#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 2019-04-08 21:34
@annotation = ''
"""
from contextlib import contextmanager
from decimal import Decimal

import cv2 as cv
import numpy as np


def show(*args, is_seq=False):
    if args:
        for img in args:
            cv.imshow('', img)
            # wait 毫秒 0是永远

            if is_seq:
                cv.waitKey(0)
                cv.destroyAllWindows()

        if not is_seq:
            cv.waitKey(0)
            cv.destroyAllWindows()


def plt_color_img(img):
    """
    彩色图片使用opencv加载是使用BGR模式，但是使用Matplotlib库是用RGB模式
    :param img:
    :return:
    """
    from matplotlib import pyplot as plt
    b, g, r = cv.split(img)
    img2 = cv.merge([r, g, b])
    plt.imshow(img2)
    plt.xticks([])
    plt.yticks([])
    plt.show()


def plt_gray_img(*img):
    from matplotlib import pyplot as plt
    for i in img:
        plt.imshow(i, cmap='gray', interpolation='bicubic')
        plt.xticks([])
        plt.yticks([])
        plt.show()


def load_img(path: str, mode=cv.IMREAD_COLOR):
    return cv.imread(path, mode)


def save_img(path, img):
    cv.imwrite(path, img)


@contextmanager
def test_time():
    start = cv.getTickCount()
    try:
        yield
    finally:
        end = cv.getTickCount()
        sec = (end - start) / cv.getTickFrequency()
        msg = 'Total time running %s sec' % (Decimal(sec))
        print(msg)


def blank_img(width, height, rgb_color=(0, 0, 0)):
    image = np.zeros((int(height), int(width), 3), np.uint8)
    color = tuple(reversed(rgb_color))
    image[:] = color
    return image


def rgb2bgr(rgb_color):
    return tuple(reversed(rgb_color))


def hsv(img):
    return cv.cvtColor(img, cv.COLOR_BGR2HSV)


def gray(img):
    return cv.cvtColor(img, cv.COLOR_BGR2GRAY)


def resize(img, width, height):
    return cv.resize(img, (int(width), int(height)))
