#!/usr/bin/env python
# -*- coding: utf-8 -*-
import importme
from base.base_m3u8 import SnippetMerge

importme.init()

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
    '37604625': {
        '37604625_0:20:0': [(51, 59)],
        '37604625_0:55:0': [(26, 91)],
        '37604625_1:55:0': [(77, 100)],
        '37604625_2:0:0': [(1, 81)],
        '37604625_3:0:0': [(91, 100)],
        '37604625_3:5:0': [(1, 57)],
        '37604625_3:15:0': [(79, 100)],
        '37604625_3:20:0': [(1, 32)],
    },
}


def get_vod_by_set(user_id: str, tar_station: str, ):
    sm = SnippetMerge(user_id)
    model_result = sm._trans_set2result(valid_set)
    sm.run(tar_station, tar_time_range=model_result[tar_station])


get_vod_by_set('rlrlvkvk123', '37604625')
