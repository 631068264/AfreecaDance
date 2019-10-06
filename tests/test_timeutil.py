#!/usr/bin/env python
# -*- coding: utf-8 -*-
import typing

from base.timeutil import Duration, duration_delta
from etc import config


def test_duration():
    assert Duration.set_time('2:5:0').to_str() == '2:5:0'
    assert Duration.set_time('2:5:0').to_duration() == 7500
    assert Duration.set_duration(7500).to_duration() == 7500
    assert Duration.set_duration(7500).to_str() == '2:5:0'
    assert (Duration.set_duration(7500) - duration_delta(m=5)).to_str() == '2:0:0'
    assert (Duration.set_duration(7500) - duration_delta(s=5)).to_str() == '2:4:55'


def test_d():
    d = Duration.set_time('5:9:57').to_duration()
    total_duration = config.THUMBNAIL_SIZE.DURATION_SEC * config.THUMBNAIL_SIZE.DURATION_SEC * config.THUMBNAIL_SIZE.COLUMN_COUNT
    print(total_duration)
    print(Duration.set_duration(d - (d % total_duration)).to_str())


def test_a():
    a = [387, 390, 393, 396, 399, 402, 405, 408, 411, 414, 420, 423, 849, 894, 897, 900, 903, 906, 909, 912, 915, 918, 921, 924, 927, 930, 933, 936,
         939, 942, 945, 948, 951, 954, 957, 960, 963, 966, 969, 972, 975, 978, 981, 984, 987, 990, 993, 996, 999, 1002, 1005, 1008, 1011, 1014, 1017,
         1020, 1023, 1026, 1029, 1032, 1035, 1038, 1041, 1044, 1047, 1050, 1053, 1056, 1059, 1062, 1065, 1068, 1071, 1074, 1077, 1080, 1083, 1086,
         1089, 1092, 1095, 1098, 1284, 1287, 1290, 1302, 6603, 6606, 6609, 6612, 6615, 6618, 6621, 6624, 6627, 6630, 6633, 6636, 6639, 6642]
    TAR_SEC = 3 * 60
    SMALL_RANGE_SEC = 15

    def get_duration_range(raw_duration: typing.List):

        range_long = TAR_SEC // config.THUMBNAIL_SIZE.DURATION_SEC
        if len(raw_duration) <= range_long:
            return None

        tar_duration = sorted(raw_duration)
        result, tmp = [], []

        for i in range(1, len(raw_duration)):
            if tar_duration[i] - tar_duration[i - 1] == config.THUMBNAIL_SIZE.DURATION_SEC:
                tmp.append(tar_duration[i - 1])
            elif tmp:
                if tar_duration[i - 1] - tmp[-1] == config.THUMBNAIL_SIZE.DURATION_SEC:
                    tmp.append(tar_duration[i - 1])
                if len(tmp) > SMALL_RANGE_SEC // config.THUMBNAIL_SIZE.DURATION_SEC:
                    start_time = Duration.set_duration(tmp[0]).to_str()
                    end_time = Duration.set_duration(tmp[-1]).to_str()
                    result.append((start_time, end_time))
                tmp = []

        # 到最后都是连续的
        if tmp:
            if tar_duration[i - 1] - tmp[-1] == config.THUMBNAIL_SIZE.DURATION_SEC:
                tmp.append(tar_duration[i - 1])
            if len(tmp) > SMALL_RANGE_SEC // config.THUMBNAIL_SIZE.DURATION_SEC:
                start_time = Duration.set_duration(tmp[0]).to_str()
                end_time = Duration.set_duration(tmp[-1]).to_str()
                result.append((start_time, end_time))

        return result

    print(get_duration_range(a))


def test_c():
    d = Duration.set_time('0:59:33').to_duration() - Duration.set_time('0:55:00').to_duration()
    print(d/3)