#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent import monkey

monkey.patch_all()

import importme

importme.init()

from base.base_spider import ThumbnailProcess

process = ThumbnailProcess('rlrlvkvk123')

test_tar = {
    'bad_pic_test': {
        '38350720_4:5:0': [(2, 78)],
        '47974231_2:15:0': [(1, 35)],
        '47974231_2:20:0': [(1, 69)],
    },
}


def test_bad_pic():
    process.valid_set(test_tar)
