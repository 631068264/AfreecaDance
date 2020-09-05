#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import subprocess

from gevent import monkey

monkey.patch_all()
import os
import typing
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import gevent
import m3u8
import requests

from gevent.pool import Group, Pool
from requests import Timeout

from base import util
from base.base_spider import VOD_TYPE
from base.logger import AutoLog
from base.stash import Stash
from base.timeutil import Duration, duration_delta
from etc import config


class SnippetMerge:
    def __init__(self, bj_id: str):
        self.bj_id = bj_id
        self.stash = Stash(f'afreecatv_{self.bj_id}')
        self.log = AutoLog.file_log('m3u8_merge')
        self.VOD_PATH = self.pre_path('vod')

    def pre_path(self, dir_name: str) -> str:
        data_path = Path(config.DATA.DATA_PATH, self.bj_id, dir_name)
        if not data_path.exists():
            data_path.mkdir(parents=True)
        return str(data_path)

    def video_key(self, station_num: str):
        return f'{station_num}:video_info'

    def retry(times=3):
        """
        times == -1 forever
        :return:
        """

        def deco(func):
            def new_handler(self, *args, **kwargs):
                retry_time = 1

                if times == -1:
                    while True:
                        try:
                            is_ok = func(self, *args, **kwargs)
                            if is_ok:
                                return is_ok
                            self.log.error(f'retry[{retry_time}:{self.bj_id}:{func.__name__}]:{args, kwargs}')
                            retry_time += 1
                        except Exception:
                            self.log.error(
                                f'retry[{retry_time}:{self.bj_id}:{func.__name__}]:{args, kwargs} \n' + util.error_msg())

                elif times > 0:
                    for i in range(times):
                        try:
                            is_ok = func(self, *args, **kwargs)
                            if is_ok:
                                return is_ok
                            self.log.error(f'retry[{retry_time}:{self.bj_id}:{func.__name__}]:{args, kwargs}')
                            retry_time += 1
                        except Exception:
                            self.log.error(
                                f'retry[{retry_time}:{self.bj_id}:{func.__name__}]:{args} \n' + util.error_msg())
                    self.log.error(f'Fail retry[{retry_time}:{self.bj_id}:{func.__name__}]:{args, kwargs}')

            return new_handler

        return deco

    @retry(times=7)
    def down(self, url: str, path: Path, param: typing.Dict = None, chunk_size: int = 1024 * 9, timeout: int = 8):
        path_dir = os.path.dirname(path)
        os.makedirs(path_dir, exist_ok=True)
        try:
            resp = requests.get(url, params=param, stream=True, timeout=timeout)
            if resp.status_code == 200:
                with open(str(path), 'wb') as f:
                    for r in resp.iter_content(chunk_size=chunk_size):
                        f.write(r)
                self.log.info(f'[{self.bj_id}:{str(path.parent).split("/")[-1]}] download {path.name} success')
                return True
        except (Timeout, ConnectionError):
            self.log.error(f'[TIMEOUT get]:{url}:{param}')
            return False
        except Exception:
            self.log.error(f'[{self.bj_id}:{str(path.parent).split("/")[-1]}] : {path.name}\n' + util.error_msg())
            return False

    def _prepare_video(self, vod: typing.Dict) -> typing.Dict:
        video_info = vod['video']
        result = {v['cum_duration']: v['url'] for v in video_info}
        return result

    def _parse_m3u8(self, vod: typing.Dict) -> typing.Dict:
        video_info = self._prepare_video(vod)

        def _m3u8(args: typing.Tuple[int, str]) -> typing.Dict:
            cum, url = args
            variant_m3u8 = m3u8.load(url)
            tmp = cum
            tar_video = {}
            if variant_m3u8.is_variant:
                bandwidth_uri = {p.stream_info.bandwidth: p.uri for p in variant_m3u8.playlists}
                # best_bandwidth = 2000000 if 2000000 in bandwidth_uri else min(list(bandwidth_uri.keys()))
                best_bandwidth = max(list(bandwidth_uri.keys()))
                bandwidth_uri = bandwidth_uri[best_bandwidth]

                tar_m3u8 = m3u8.load(bandwidth_uri)
                for s in tar_m3u8.segments:
                    tmp += Decimal(str(s.duration)).quantize(Decimal('0'), rounding=ROUND_HALF_UP)
                    tar_video[int(tmp)] = s.absolute_uri
            return tar_video

        group = Group()
        result = {}
        for tar_video in group.imap_unordered(_m3u8, video_info.items()):
            result.update(tar_video)
        return result

    def _ts2mp4(self, dirname: str, output_name: str = 'output'):
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
        output_mp4_name = f'{output_name}.mp4'
        compress_mp4_name = f'{output_name}_tmp.mp4'
        file_list = list(Path(dirname).glob('*.ts'))
        ordered_files = sorted(file_list, key=lambda x: (int(re.search(r'([0-9]+)(?=\.ts)', str(x))[0]), x))
        if ordered_files:
            merge_path = os.path.abspath(Path(dirname, 'merge.txt'))
            output_path = os.path.abspath(Path(dirname, output_mp4_name))
            compress_path = os.path.abspath(Path(dirname, compress_mp4_name))

            with open(merge_path, 'w') as f:
                for i in ordered_files:
                    if os.path.isfile(str(i)):
                        f.write(f'file {i.name}\n')

            ffmpeg_cmd = f'ffmpeg -y -f concat -safe 0 -i {merge_path} -codec copy -bsf:a  aac_adtstoasc {compress_path}'
            compress_cmd = f'ffmpeg -y -i {compress_path} -c:v libx264 -crf 28 {output_path}'
            try:
                self.log.info(f'start to merge {output_path}')
                subprocess.check_call(ffmpeg_cmd, shell=True)
                os.remove(merge_path)
                for i in file_list:
                    i.unlink()
                # subprocess.check_call(compress_cmd, shell=True)
                # os.remove(compress_path)
            except subprocess.CalledProcessError as e:
                self.log.error(util.error_msg())
                return

            self.log.info(f'merge {output_path} success')

    def _merge_m3u8_by_tar_time(self, station_num: str, vod: typing.Dict, tar_time_range: typing.List):
        path = Path(self.VOD_PATH, str(station_num))
        os.makedirs(path, exist_ok=True)
        self.log.info(f'[{self.bj_id}:{station_num}] get vod m3u8 info')
        tar_video = self._parse_m3u8(vod)
        self.log.info(f'[{self.bj_id}:{station_num}] get vod m3u8 info success')
        pool = Pool(20)
        for t in tar_time_range:
            min_range, max_range = t
            min_d, max_d = Duration.set_time(min_range).to_duration(), Duration.set_time(max_range).to_duration()
            for i in range(min_d, max_d + 1):
                if i in tar_video:
                    ts_path = path.joinpath(f'{i}.ts')
                    if os.path.isfile(ts_path) and ts_path.stat().st_size > 1024 * 500:
                        continue
                    pool.add(gevent.spawn(self.down, url=tar_video[i], path=ts_path))

        pool.join()
        self.log.info(f'[{self.bj_id}:{station_num}] download ts success')
        self._ts2mp4(path, output_name=station_num)

    def _trans_set2result(self, vod_set: dict) -> typing.Dict:
        result = {}
        for station_num, vod_range in vod_set.items():
            result[station_num] = []
            for start, s_range in vod_range.items():
                s = start.split('_')[-1]
                for min_r, max_r in s_range:
                    min_r_str = (Duration.set_time(s) + duration_delta(s=min_r * config.THUMBNAIL_SIZE.DURATION_SEC)).to_str()
                    max_r_str = (Duration.set_time(s) + duration_delta(s=max_r * config.THUMBNAIL_SIZE.DURATION_SEC)).to_str()
                    result[station_num].append((min_r_str, max_r_str))

        return result

    def _prepare_vod_cum(self, vod: typing.Dict):
        video_info = vod['video']
        tmp = 0
        for v in video_info:
            v.setdefault('cum_duration', tmp)
            tmp += v['duration']

    def run(self, station_num: str, tar_time_range: typing.List, ignore=False):
        vod = self.stash.get(self.video_key(station_num))
        self._prepare_vod_cum(vod)
        if not vod or vod['type'] != VOD_TYPE.VOD:
            return
        if ignore and Path.exists(Path(self.VOD_PATH, station_num)):
            return
        os.makedirs(Path(self.VOD_PATH, station_num), exist_ok=True)
        self._merge_m3u8_by_tar_time(station_num, vod, tar_time_range)
