#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent import monkey

from base.base_m3u8 import SnippetMerge

monkey.patch_all()
import importme

importme.init()

from base.base_model import CNNModel
from base.base_spider import ThumbnailProcess

process = ThumbnailProcess('rlrlvkvk123')
model = CNNModel('rlrlvkvk123')

valid_set = {
    # '38350720': {
    #     '38350720_0:15:0': [(1, 66)],
    #     '38350720_1:50:0': [(1, 100)],
    #     '38350720_1:55:0': [(1, 23)],
    #     '38350720_2:30:0': [(4, 53)],
    #     '38350720_4:5:0': [(2, 78)],
    #     '38350720_4:15:0': [(25, 99)],
    #     '38350720_4:25:0': [(94, 100)],
    #     '38350720_4:30:0': [(1, 54)],
    # },
    '47974231': {
        '47974231_0:5:0': [(50, 100)],
        '47974231_2:10:0': [(34, 100)],
        '47974231_2:15:0': [(1, 35)],
        '47974231_2:20:0': [(1, 69)],
    },
}


def valid(tar_station: str):
    process.valid_set(valid_set)
    model.valid_run(tar_station, small_range_sec=60)


def get_vod_by_set(user_id: str, tar_station: str, ):
    sm = SnippetMerge(user_id)
    model_result = sm._trans_set2result(valid_set)
    sm.run(tar_station, tar_time_range=model_result[tar_station])

valid('47974231')
# get_vod_by_set('rlrlvkvk123', '47974231')
