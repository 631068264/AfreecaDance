#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent import monkey

monkey.patch_all()

import importme

importme.init()
import os
import re
import subprocess
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import m3u8

from base import util
from base.base_m3u8 import SnippetMerge
from base.timeutil import Duration

tar = [('0:14:54', '0:18:18'), ('1:50:3', '1:56:3'), ('2:30:3', '2:32:39'), ('3:21:9', '3:23:12'), ('4:4:54', '4:8:51'), ('4:16:15', '4:19:57'),
       ('4:29:33', '4:32:42')]


def merge_m3u8(tar_video: dict):
    path = 'video/47859255'
    os.makedirs(path, exist_ok=True)

    for t in tar:
        min_range, max_range = t
        min_d = Duration.set_time(min_range).to_duration()
        max_d = Duration.set_time(max_range).to_duration()

        for i in range(min_d, max_d):
            if i in tar_video:
                content = util.post_content(tar_video[i])
                if content is not None:
                    with open(os.path.join(path, f'{i}.ts'), 'wb') as f:
                        f.write(content)

    merge_ts2mp4(path)


def merge_ts2mp4(dirname: str, output_name: str = 'output.mp4'):
    """
    https://ffmpeg.org/ffmpeg.html
    https://moejj.com/ffmpeghe-bing-shi-pin-wen-jian-guan-fang-wen-dang/

    从文件夹中获取所有对应后缀名文件列表，并按照序号排序

    ffmpeg -i "concat:input1.ts|input2.ts|input3.ts" -c copy output.ts

    # this is a comment
    file '/path/to/file1'
    file '/path/to/file2'
    file '/path/to/file3'
    ffmpeg -f concat -safe 0 -i mylist.txt -c copy output
    """
    file_list = list(Path(dirname).glob('*.ts'))
    ordered_files = sorted(file_list, key=lambda x: (int(re.search(r'([0-9]+)(?=\.ts)', str(x))[0]), x))
    if ordered_files:
        merge_path = os.path.abspath(os.path.join(dirname, 'merge.txt'))
        output_path = os.path.abspath(os.path.join(dirname, output_name))
        with open(merge_path, 'w') as f:
            for i in ordered_files:
                if os.path.isfile(str(i)):
                    f.write(f'file {i.name}\n')

        ffmpeg_cmd = f'ffmpeg -y -f concat -safe 0 -i {merge_path} -codec copy -bsf:a  aac_adtstoasc {output_path}'
        try:
            subprocess.check_call(ffmpeg_cmd, shell=True)
            os.remove(merge_path)
        except subprocess.CalledProcessError as e:
            print(util.error_msg())


def test_m3u8_vod():
    variant_m3u8 = m3u8.load(
        'http://videofile-hls-ko-record-cf.afreecatv.com/video/_definst_/smil:vod/20190920/152/3E89D294_217387152_4.smil/playlist.m3u8')
    if variant_m3u8.is_variant:
        bandwidth_uri = {p.stream_info.bandwidth: p.uri for p in variant_m3u8.playlists}
        max_bandwidth = max(list(bandwidth_uri.keys()))
        bandwidth_uri = bandwidth_uri[max_bandwidth]
        print(bandwidth_uri)

        tar_m3u8 = m3u8.load(bandwidth_uri)

        tmp = 0
        tar_video = {}
        for s in tar_m3u8.segments:
            tmp += Decimal(str(s.duration)).quantize(Decimal('0'), rounding=ROUND_HALF_UP)
            tar_video[tmp] = s.absolute_uri
        merge_m3u8(tar_video)


def test_order_file():
    print(merge_ts2mp4('video/47859255'))


def test_a():
    sm = SnippetMerge('rlrlvkvk123')

    # tar_time_range = [('0:55:15', '0:57:6'), ('0:57:12', '0:59:33'), ('1:58:51', '2:3:9'), ('2:5:9', '2:6:21'), ('3:4:30', '3:7:33'), ('3:15:39', '3:18:51'), ('3:18:57', '3:21:36')]
    tar_time_range = [('0:34:33', '0:36:42'), ('0:36:48', '0:37:51'), ('0:49:54', '0:57:33'), ('4:9:0', '4:10:6'), ('4:11:27', '4:13:15'),
                      ('5:1:45', '5:4:57')]
    sm.run('41071597', tar_time_range)
