#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 2019-04-20 14:57
@annotation = ''
"""
import shutil
from functools import partial

import gevent
from gevent import monkey
from gevent.pool import Pool

monkey.patch_all()

import importme

importme.init()

from base.logger import AutoLog
import random
from base.timeutil import Duration, duration_delta
import re
import os
import typing
import requests
from requests import Timeout, ConnectionError
from base.stash import Stash
from lxml import etree
from base import util, cvutil
from etc import config
from pathlib import Path
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


class VOD_TYPE:
    VOD = 'vod'
    USER_VOD = 'user_vod'
    BAD = 'bad_vod'


PIC_TYPE = ['.jpg', '.png', '.jpeg']

cookie_stash = Stash('afreecatv')


class AfreecaTV:
    def __init__(self):
        self.LOGIN_URL = 'https://login.afreecatv.com/app/LoginAction.php'
        self.cookie_stash = cookie_stash
        self.log = None
        self.stash = None
        self.session = None
        # account
        self._init_account()
        # self.account_id = config.AfricaAccount.UID
        # self.account_pwd = config.AfricaAccount.PWD

    def _init_account(self):
        if config.AfricaAccount.UID and config.AfricaAccount.PWD:
            self.account_id = config.AfricaAccount.UID
            self.account_pwd = config.AfricaAccount.PWD
        else:
            Exception('AfricaAccount should not be none')

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
                            self.log.error(f'retry[{retry_time}:{self.user_id}:{func.__name__}]:{args}')
                            retry_time += 1
                        except Exception:
                            self.log.error(
                                f'retry[{retry_time}:{self.user_id}:{func.__name__}]:{args} \n' + util.error_msg())

                elif times > 0:
                    for i in range(times):
                        try:
                            is_ok = func(self, *args, **kwargs)
                            if is_ok:
                                return is_ok
                            self.log.error(f'retry[{retry_time}:{self.user_id}:{func.__name__}]:{args}')
                            retry_time += 1
                        except Exception:
                            self.log.error(
                                f'retry[{retry_time}:{self.user_id}:{func.__name__}]:{args} \n' + util.error_msg())
                    self.log.error(f'Fail retry[{retry_time}:{self.user_id}:{func.__name__}]:{args}')

            return new_handler

        return deco

    @retry(times=-1)
    def get(self, url, params=None, timeout=3):
        try:
            resp = self.session.get(url, params=params, timeout=timeout)
            return resp
        except (Timeout, ConnectionError):
            self.log.error(f'[TIMEOUT get]:{url}:{params}')
        except Exception:
            self.log.error(f'[get]:{url}:{params} \n' + util.error_msg())
            return None

    @retry(times=3)
    def post(self, url, params=None, timeout=3):

        try:
            resp = self.session.post(url, data=params, timeout=timeout)
            return resp
        except (Timeout, ConnectionError):
            self.log.error(f'[TIMEOUT get]:{url}:{params}')
        except Exception:
            self.log.error(f'[post]:{url}:{params} \n' + util.error_msg())
            return None

    @retry(times=7)
    def down_img(self, url, param, path, chunk_size=1024 * 3, timeout=8):
        path_dir = os.path.dirname(path)
        os.makedirs(path_dir, exist_ok=True)
        try:
            resp = self.session.get(url, params=param, stream=True, timeout=timeout)
            if resp.status_code == 200:
                with open(path, 'wb') as f:
                    for r in resp.iter_content(chunk_size=chunk_size):
                        f.write(r)
                return True
        except (Timeout, ConnectionError):
            self.log.error(f'[TIMEOUT get]:{url}:{param}')
        except Exception:
            self.log.error(f'[Download]:{url}:{param} \n' + util.error_msg())
            return False

    def login(self):
        session = requests.session()
        resp = session.post(self.LOGIN_URL, data={
            'szWork': 'login',
            'szType': 'json',
            'szUid': self.account_id,
            'szPassword': self.account_pwd,
            'isSaveId': 'true',
            'szScriptVar': 'oLoginRet',
            'szAction': None,
        })
        if resp.status_code == 200:
            self.cookie_stash['cookie'] = requests.utils.dict_from_cookiejar(session.cookies)

    def get_session(self):
        self.session = requests.session()

        self.session.cookies.update(self.cookie_stash.get('cookie', {}))
        self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36',
        }


class ThumbnailSpider(AfreecaTV):
    """
    采集缩略图
    """

    def __init__(self, user_id: str):
        super().__init__()
        self.user_id = user_id
        self.stash = Stash(f'afreecatv_{self.user_id}')

        # public url
        self.INFO_URL = 'http://afbbs.afreecatv.com:8080/api/video/get_video_info.php'
        self.THUMBNAIL_URL = 'http://videoimg.afreecatv.com/php/SnapshotLoad.php'
        self.VOD_URL_FORMAT = 'http://bjapi.afreecatv.com/api/%s/vods?page={page}' \
                              '&per_page=20&orderby=reg_date' % (self.user_id,)
        self.USER_VOD_FORMAT = 'http://bjapi.afreecatv.com/api/%s/vods/user?page={page}' \
                               '&orderby=reg_date' % (self.user_id,)
        self.STATION_URL = 'http://vod.afreecatv.com/PLAYER/STATION/{station_num}'
        # path
        self.STATION_PATH = str(Path(config.PROJECT_PATH, f'afreecatv_vod_thumbnail/{self.user_id}'))
        # thumbnail 参数
        self.thumbnailDuration = config.THUMBNAIL_SIZE.DURATION_SEC
        self.rowCount = config.THUMBNAIL_SIZE.ROW_COUNT
        self.columnCount = config.THUMBNAIL_SIZE.COLUMN_COUNT
        self.log = AutoLog.file_log('spider_thumbnail')

    def video_key(self, station_num):
        return f'{station_num}:video_info'

    def station_key(self, station_num):
        return f'{station_num}:vodparam'

    def add_bad_vod(self, station_num: int):
        """诡异的station"""
        self.log.error(f'[add_bad_vod]:{station_num}')
        bad_vod = self.stash.setdefault(VOD_TYPE.BAD, set())
        bad_vod.add(station_num)
        self.stash[VOD_TYPE.BAD] = bad_vod

    def check_bad_vod(self, station_num: int) -> bool:
        """诡异的station"""
        bad_vod = self.stash.get(VOD_TYPE.BAD, set())
        return station_num in bad_vod

    def _get_thumbnail_param(self, station_num: int, pos_time: float) -> dict:
        """
        缩略图按sec分成几份 找出pos_time 在那一份（row）里面 的哪一个column

        self.thumbnailDuration 每张图秒数
        self.rowCount * self.columnCount 张图 为一column

        :param station_num:
        :param pos_time:
        :return:
        """
        video_info = self.stash.get(self.video_key(station_num))['video']
        if video_info:
            tmp = 0
            for v in video_info:
                tmp += v['duration']
                if tmp >= pos_time:
                    row_key = v['key'] + '_t'
                    # 在某一row里面起始时间
                    row_time = pos_time - (tmp - v['duration'])
                    # 在第几张图
                    thumbnail_time = row_time // self.thumbnailDuration
                    # 图在第几column
                    column = thumbnail_time // (self.rowCount * self.columnCount) + 1

                    param = {
                        'rowKey': row_key,
                        'column': int(column),
                    }
                    return param

    def download_img(self, station_num: int, time: float, rewrite=False) -> bool:
        path = str(Path(self.STATION_PATH, str(station_num), f'{station_num}_{Duration.set_duration(time).to_str()}.jpg'))
        if not rewrite and os.path.exists(path):
            return True
        param = self._get_thumbnail_param(station_num, time)
        is_ok = self.down_img(self.THUMBNAIL_URL, param, path)
        if is_ok:
            self.log.info(f'[{station_num}:{time}] success')
        return is_ok

    def _get_video_info(self, station_num: int) -> dict:
        result = {}
        if self.check_bad_vod(station_num):
            return result

        if self.video_key(station_num) in self.stash and self.stash[self.video_key(station_num)]['total'] > 0:
            return self.stash[self.video_key(station_num)]

        def _parse_vod_info(html):
            files = html.xpath('//file')
            duration = 0
            video_info = []
            for f in files:
                try:
                    int(f.get('duration'))
                except:
                    continue
                try:
                    video_info.append({
                        'key': f.get('key'),
                        'duration': int(f.get('duration')),
                        'url': f.text,
                        'cum_duration': duration,
                    })
                    duration += int(f.get('duration'))
                except:
                    self.log.error(f'[parse_video_info]:{self.video_key(station_num)}:{url} \n' + util.error_msg())
            result = {
                'video': video_info,
                'total': duration,
                'type': VOD_TYPE.VOD,
            }
            self.stash[self.video_key(station_num)] = result
            return result

        vod_param = self.station(station_num)

        if vod_param:
            url = self.INFO_URL + '?' + vod_param + '&szSysType=html5'

            resp = self.get(url)
            # TODO: user_vod
            if resp.status_code == 200:
                self.log.info(f'[get_video_info]:{station_num}')
                html = etree.HTML(resp.text)
                try:
                    category = html.xpath('//video[@category]')[0].get('category')
                    if category == '00210000':
                        result = _parse_vod_info(html)
                except Exception:
                    self.log.error(f'[get_video_info]:{self.video_key(station_num)}:{url} \n' + util.error_msg())
                    self.add_bad_vod(station_num)
                    return result

        return result

    def station(self, station_num: int) -> str:
        station_key = self.station_key(station_num)
        if station_key in self.stash:
            return self.stash[station_key]

        resp = self.get(self.STATION_URL.format(station_num=station_num))
        result = re.search(r'document.VodParameter = (.*?);', resp.text, re.S)
        if result:
            self.log.info(f'[station]:{station_num}')
            x = result.group(1).replace('\'', '')
            self.stash[station_key] = x
            return x

    def _get_vod(self, page: int, url: str, stash_key: str, append=True, is_check=False) -> typing.Optional[
        typing.Tuple[bool, dict]]:

        def parse_raw(raw: dict):
            self.log.info(f'[get_vod]:{url.format(page=page)}')
            if append:
                data_set = self.stash.get(stash_key, set())
            else:
                data_set = set()
            for d in raw['data']:
                data_set.add(d['title_no'])
            self.stash[stash_key] = data_set
            return raw['meta']

        resp = self.get(url.format(page=page))
        try:
            raw = resp.json()
        except:
            return None
        if not is_check:
            return False, parse_raw(raw)
        else:
            vod_data = self.stash.get(stash_key, set())
            if raw['meta']['total'] != len(vod_data):
                return False, parse_raw(raw)
            return True, vod_data

    def vod(self, url: str, stash_key: str) -> set:
        """
        获取vod_id
        :param url:
        :param key:
        :return:
        """
        is_ok, meta = self._get_vod(1, url, stash_key, append=False, is_check=True)
        if not is_ok:
            pool = Pool(10)
            for i in range(2, meta['last_page'] + 1):
                pool.add(gevent.spawn(self._get_vod, i, url, stash_key))
            pool.join()
            return self.stash.get(stash_key, set())
        return meta

    def download_vod(self, station_num: int, rewrite=False):
        video_info = self._get_video_info(station_num)
        if not video_info:
            self.log.error(f'BAD VOD {station_num}')
            return
        total = video_info['total']

        step = self.thumbnailDuration * self.rowCount * self.columnCount
        pool = Pool(10)
        for i in range(0, total, step):
            pool.add(gevent.spawn(self.download_img, station_num, i, rewrite))
        pool.join()
        self.log.info(f'[{station_num}:vod] success')

    def test_img(self, img_name: str):
        station_num, h, m, s = re.search(r'(.*?)_(.*?):(.*?):(.*)\.jpg', img_name).groups()
        param = self._get_thumbnail_param(int(station_num), Duration.delta(int(h), int(m), int(s)).to_duration())
        print(self.THUMBNAIL_URL + util.join_params(**param))

    def test_download_img(self, station_num: int, t: float):
        param = self._get_thumbnail_param(int(station_num), t)
        print(self.THUMBNAIL_URL + util.join_params(**param))

    def valid_thumbnail(self):
        dirs = os.listdir(self.STATION_PATH)
        dirs = set(dirs) - {'.DS_Store'}

        def del_bad_video_info():
            vod = self.stash.get(VOD_TYPE.VOD, set()) | self.stash.get(VOD_TYPE.USER_VOD, set())
            diff = vod - set(map(int, dirs))
            for d in diff:
                del self.stash[self.video_key(d)]

        def del_bad_img():
            for d in dirs:
                fd = os.path.join(self.STATION_PATH, d)
                for f in os.listdir(fd):
                    fp = os.path.join(fd, f)
                    size = os.path.getsize(fp)
                    if size < 1024 * self.rowCount * self.columnCount:
                        os.remove(fp)

        del_bad_img()
        del_bad_video_info()
        self.log.info('valid thumbnail success')

    def _init_spider(self, login=False):
        if login:
            self.login()
        self.get_session()

    def run(self, login=False):
        """

        tv = ThumbnailSpider('rlrlvkvk123')
        tv.run(login=True)

        # print(tv.stash[VOD_TYPE.BAD])
        # tv.test()
        # tv.test_img('36997061_0:0:0.jpg')

        # tv.test_download_img(43764953,3600)

        :return:
        """
        self._init_spider(login)
        self.log.info('spider start')

        self.valid_thumbnail()

        vod = self.vod(self.VOD_URL_FORMAT, VOD_TYPE.VOD)
        self.log.info('prepare vod')

        # user_vod = self.vod(self.USER_VOD_FORMAT, VOD_TYPE.USER_VOD)
        self.log.info('prepare user vod')

        # vod = vod | user_vod
        # vod = user_vod
        self.log.info('prepare vod success')

        pool = Pool(4)
        for v in vod:
            pool.add(gevent.spawn(self.download_vod, v))
        pool.join()

        self.log.info('spider end')

    def fix(self, station_num: int, rewrite=True, login: bool = False):
        self._init_spider(login)
        self.log.info(f'fix start [{self.user_id}:{station_num}]')
        self.download_vod(station_num=station_num, rewrite=rewrite)


class ThumbnailProcess(ThumbnailSpider):
    """
    缩略图处理
    """

    def __init__(self, user_id: str):
        super().__init__(user_id)
        self.TRAIN_PATH = self.pre_path('train_data')
        self.TEST_PATH = self.pre_path('test_data')
        self.VALID_PATH = self.pre_path('valid_data')
        self.log = AutoLog.file_log('thumbnail_process')
        self.resize_width = config.THUMBNAIL_SIZE.WIDTH
        self.resize_height = config.THUMBNAIL_SIZE.HEIGHT
        self.stash = Stash('thumbnail_process')
        self.label_info = None

    def pre_path(self, dir_name: str) -> str:
        data_path = Path(config.DATA.DATA_PATH, self.user_id, dir_name)
        if not data_path.exists():
            data_path.mkdir(parents=True)
        return str(data_path)

    def _split_label_img_by_size(self, path: str, row_len, column_len: int, label_func: typing.Callable[[int], int],
                                 sub_path_func: typing.Callable[[str, int], str], replace_exist=True):
        """图片分割"""
        img = cvutil.load_img(path)
        total_height, total_width = img.shape[:2]
        width, height = total_width // column_len, total_height // row_len
        num = 1
        station_str = Path(path).stem.split('_')[0]
        for i in range(0, row_len):
            left_top_height = i * height
            right_bottom_height = (i + 1) * height
            for j in range(0, column_len):
                sub_path = sub_path_func(path=path, num=num * self.thumbnailDuration, label=label_func(num=num))
                if Path(sub_path).exists() and replace_exist:
                    continue
                left_top_width = j * width
                right_bottom_width = (j + 1) * width
                roi = img[left_top_height:right_bottom_height, left_top_width:right_bottom_width]
                roi = cvutil.resize(roi, self.resize_width, self.resize_height)
                cvutil.save_img(sub_path, roi)
                if os.path.getsize(sub_path) < 1024:
                    self.log.info(f'[{self.user_id}:{station_str}] invalid img size DEL {sub_path}')
                    os.remove(sub_path)
                num += 1
        return width, height

    def _split_normal_img_by_size(self, path: str, row_len, column_len: int, sub_path_func: typing.Callable[[str, int], str], replace_exist=True):
        """图片分割"""
        img = cvutil.load_img(path)
        total_height, total_width = img.shape[:2]
        width, height = total_width // column_len, total_height // row_len
        num = 1
        station_str = Path(path).stem.split('_')[0]
        for i in range(0, row_len):
            left_top_height = i * height
            right_bottom_height = (i + 1) * height
            for j in range(0, column_len):
                sub_path = sub_path_func(path=path, num=num * self.thumbnailDuration)
                if Path(sub_path).exists() and replace_exist:
                    continue
                left_top_width = j * width
                right_bottom_width = (j + 1) * width
                roi = img[left_top_height:right_bottom_height, left_top_width:right_bottom_width]
                roi = cvutil.resize(roi, self.resize_width, self.resize_height)
                cvutil.save_img(sub_path, roi)
                if os.path.getsize(sub_path) < 1024:
                    self.log.info(f'[{self.user_id}:{station_str}] invalid img size DEL {sub_path}')
                    os.remove(sub_path)
                num += 1
        return width, height

    def sub_path(self, path, file_dir: str, num, label: int = 0, ) -> str:
        p = Path(path)
        station_str, raw_duration = p.stem.split('_')
        duration = (Duration.set_time(raw_duration) + duration_delta(s=num)).to_str()
        file_name = f'{duration}_{label}{p.suffix}'
        # self.log.info(f'[{self.user_id}:{station_str}] {file_name}')
        file_dir = file_dir
        # sub_img_path = Path(file_dir, station_str, file_name)
        sub_img_path = Path(file_dir, f'{station_str}_{file_name}')
        if not sub_img_path.parent.exists():
            sub_img_path.parent.mkdir(parents=True)
        return str(sub_img_path)

    def get_label(self, dir_name: str, file_name: Path, num: int) -> int:
        if dir_name not in self.label_info:
            return 0
        label = self.label_info[dir_name].get(file_name.stem, [(0, 0)])
        for x, y in label:
            if x < num < y:
                return 1
        return 0

    def train_set(self, label_info: typing.Dict, test_size: float = 0.05, label_balance: float = 1):
        """

        :param label_info:
        :param test_size:
        :param label_balance:
        :return:
        """
        self.label_info = label_info

        for dir_name, label in self.label_info.items():
            for img_path in Path(self.STATION_PATH, dir_name).iterdir():
                if img_path.suffix in PIC_TYPE:
                    get_label = partial(self.get_label, dir_name=dir_name, file_name=img_path)
                    sub_path = partial(self.sub_path, file_dir=self.TRAIN_PATH)
                    w, h = self._split_label_img_by_size(str(img_path), self.rowCount, self.columnCount, get_label, sub_path)
                    # sise_dict[w * h] = (w, h, str(i))
            self.log.info(f'[{self.user_id}:{dir_name}] SUCCESS')

        self._split_train_test(test_size, label_balance)
        self._stat()

    def valid_set(self, label_info: typing.Dict):
        self.label_info = label_info
        shutil.rmtree(self.VALID_PATH)
        for dir_name, label in self.label_info.items():
            for img_path in Path(self.STATION_PATH, dir_name).iterdir():
                if img_path.suffix in PIC_TYPE:
                    get_label = partial(self.get_label, dir_name=dir_name, file_name=img_path)
                    sub_path = partial(self.sub_path, file_dir=self.VALID_PATH)
                    w, h = self._split_label_img_by_size(str(img_path), self.rowCount, self.columnCount, get_label, sub_path, replace_exist=False)
                    # sise_dict[w * h] = (w, h, str(i))
            self.log.info(f'[{self.user_id}:{dir_name}] SUCCESS')

    def split_img(self, dir_name: str):
        shutil.rmtree(self.VALID_PATH)
        for img_path in Path(self.STATION_PATH, dir_name).iterdir():
            if img_path.suffix in PIC_TYPE:
                sub_path = partial(self.sub_path, file_dir=self.VALID_PATH)
                self._split_normal_img_by_size(str(img_path), self.rowCount, self.columnCount, sub_path, replace_exist=False)

    def _stat(self, record=True):
        """统计比列"""

        def _stat_path(path: str, data_name: str) -> typing.Tuple[int, typing.List]:
            path = Path(path)

            other_list = list(path.glob('*_0.*'))
            tar_list = list(path.glob('*_1.*'))
            total_list = other_list + tar_list

            other_count = len(other_list)
            tar_count = len(tar_list)
            total_count = other_count + tar_count

            self.log.info(f'[{self.user_id}:{data_name}] : {tar_count}/{total_count} {(tar_count / total_count):.2%}')
            return total_count, total_list

        train_count, train_list = _stat_path(self.TRAIN_PATH, 'train')
        self.stash['train_data'] = list(map(str, train_list))
        test_count, test_list = _stat_path(self.TEST_PATH, 'test')
        self.stash['test_data'] = list(map(str, test_list))
        self.log.info(f'[{self.user_id}] : TRAIN {train_count} TEST {test_count} {(test_count / (train_count + test_count)):.2%}')

    def _split_train_test(self, test_size: float = 0.05, label_balance: float = 1):
        """
        训练集 测试集 分离
        :param test_size:  数据集分训练和测试 测试比列
        :param label_balance: 数据集正负数量比
        :return:
        """
        test_path = Path(self.TEST_PATH)
        # del all file in test_path
        shutil.rmtree(test_path)
        self.TEST_PATH = self.pre_path('test_data')

        train_path = Path(self.TRAIN_PATH)

        def _balance_class(path: Path):
            other_list = list(path.glob('*_0.*'))
            tar_list = list(path.glob('*_1.*'))

            other_count = len(other_list)
            tar_count = len(tar_list)
            total_count = other_count + tar_count
            self.log.info(f'[{self.user_id}:平衡种类前] : {tar_count}/{total_count} {(tar_count / total_count):.2%}')

            balance_count = min(other_count, int(tar_count * label_balance))
            other_set = random.sample(other_list, balance_count)
            rm_other_list = set(other_list) - set(other_set)
            if rm_other_list:
                for i in rm_other_list:
                    i.unlink()

        _balance_class(train_path)

        img_list = list(train_path.iterdir())
        total = len(img_list)
        test_count = int(test_size * total)

        test_img_set = random.sample(img_list, test_count)

        for test_img in test_img_set:
            test_img.replace(Path(self.TEST_PATH, test_img.name))
