#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 2017/2/4 09:05
@annotation = ''
"""
import base64
import datetime
import hashlib
import io
import json
import os
import pickle
import random
import re
import time
from urllib import parse

import cchardet
import gevent
import requests
from PIL import Image
from bs4 import BeautifulSoup
from gevent.pool import Pool

from base import const, logger
from base.decorator import with_func_time
from etc import config


def error_msg():
    import traceback
    return traceback.format_exc()


class FileLock(object):
    """阻止多个脚本同时运行 增加系统内存负担(特别是耗时脚本)"""

    def __init__(self, file_name, path):
        self._file = os.path.join(path, file_name)
        self._fd = None
        self._locked = False

    def lock(self):
        import fcntl
        if self._locked:
            return True

        fd = open(self._file, 'a+b')
        try:
            fcntl.flock(fd.fileno(), fcntl.LOCK_NB | fcntl.LOCK_EX)
        except IOError:
            fd.close()
            return False

        self._fd = fd
        self._locked = True
        return True

    def release(self):
        import fcntl
        if self._locked:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            self._fd.close()
            self._fd = None
            self._locked = False

    # def get_data(self):
    #     if not self._locked:
    #         return None
    #
    #     self._fd.seek(0)
    #     data = self._fd.read()
    #     if len(data) < 1:
    #         return None
    #
    #     return Serializer.to_object(data)
    #
    # def set_data(self, data):
    #     if not self._locked:
    #         return
    #
    #     self._fd.truncate(0)
    #     self._fd.write(Serializer.to_string(data))
    #     self._fd.flush()

    def __del__(self):
        self.release()


def import_mod(mod_name):
    try:
        from importlib import import_module
        return import_module(mod_name)
    except Exception as e:
        print(error_msg())


def now():
    return datetime.datetime.now(tz=config.tz_info)


def nowts():
    return int(time.time())


def daystart():
    return now().replace(hour=0, minute=0, second=0, microsecond=0)


def safedt(dt):
    return dt.replace(tzinfo=config.tz_info)


def str2dt(dt_str, fmt='%Y-%m-%d %H:%M:%S'):
    return safedt(datetime.datetime.strptime(dt_str, fmt))


def ts2dt(timestamp):
    if not isinstance(timestamp, float):
        timestamp = float(timestamp)
    return datetime.datetime.fromtimestamp(timestamp, config.tz_info)


def join_params(**kwargs):
    return "?" + parse.urlencode(kwargs)


def url_params(url):
    query = parse.urlparse(url).query
    return {k: v[0] for k, v in parse.parse_qs(query).items()}


def post_json(url, params=None, method=const.METHOD.GET, without_ua=False, **kwargs):
    headers = kwargs.get("headers", {})
    if not without_ua:
        headers.setdefault('User-Agent', random.choice(config.HEADER.USER_AGENT))

    kwargs["headers"] = headers
    kwargs.setdefault('timeout', config.request_timeout)
    try:
        resp = None
        if method == const.METHOD.POST:
            resp = requests.post(url, data=params, **kwargs)
        else:
            resp = requests.get(url, params=params, **kwargs)
        resp_json = resp.json()
        return resp_json
    except Exception as e:
        msg = u"%s [%s]:%s" % (method,
                               url if params is None else url + join_params(**params), resp.content if resp else e)
        logger.get("error-log").error(msg)


def post_content(url, params=None, method=const.METHOD.GET, without_ua=False, **kwargs):
    headers = kwargs.get("headers", {})
    if not without_ua:
        headers.setdefault('User-Agent', random.choice(config.HEADER.USER_AGENT))

    kwargs["headers"] = headers
    kwargs.setdefault('timeout', config.request_timeout)
    try:
        resp = None
        if method == const.METHOD.POST:
            resp = requests.post(url, data=params, **kwargs)
        else:
            resp = requests.get(url, params=params, **kwargs)
        resp_content = resp.content
        return resp_content
    except Exception as e:
        msg = u"%s [%s]:%s" % (method,
                               url if params is None else url + join_params(**params), resp.content if resp else e)
        logger.get("error-log").error(msg)


def get_html_soup(url, **kwargs):
    headers = kwargs.get("headers", {})
    headers.setdefault('User-Agent', random.choice(config.HEADER.USER_AGENT))
    kwargs["headers"] = headers
    try:
        html = requests.get(url, timeout=config.request_timeout, **kwargs)
        if ('content-type' in html.headers and 'charset' not in html.headers['content-type']) \
                or ('content-type' not in html.headers):
            # html.encoding = config.encoding
            html.encoding = cchardet.detect(html.content)['encoding']
        soup = BeautifulSoup(html.text, "lxml")
        return soup
    except Exception as e:
        msg = u"get [%s] : %s" % (url, e)
        logger.get("error-log").error(msg)


def unique_id(title, content):
    s = '{}:{}'.format(title, content)
    return hashlib.md5(s.encode()).hexdigest()


def pool_func(funcs, tag, is_log=True):
    with with_func_time(tag, logger.get("error-log").error, is_log=is_log):
        pool = Pool(config.concurrent)
        for func in funcs:
            pool.add(gevent.spawn(func.run))
        pool.join()


class LoginSession(object):
    CACHE_HEADER_KEY = 'header'
    CACHE_COOKIE_KEY = 'cookie'

    # def __init__(self):
    #     # self.headers = session.headers
    #     # self.cookies = session.cookies
    @classmethod
    def load(cls, file_path):
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            return data
        except (KeyError, EOFError):
            return None

    @classmethod
    def save(cls, file_path, session):
        with open(file_path, 'wb') as f:
            pickle.dump(session, f)

    @classmethod
    def load_json_cookie(cls, file_path):
        with open(file_path) as f:
            raw_json = json.load(f)
            return raw_json
            # return {r['name']: r['value'] for r in raw_json}

    @classmethod
    def save_session_cookie(cls, session, path):
        with open(path, 'w') as f:
            json.dump(requests.utils.dict_from_cookiejar(session.cookies), f)

    @classmethod
    def save_driver_cookie(cls, driver, path):
        cookies = driver.get_cookies()
        cookies = {cookie['name']: cookie['value'] for cookie in cookies}
        with open(path, 'w') as f:
            json.dump(cookies, f)


def down_img(url, param, path, chunk_size=1024 * 4):
    path_dir = os.path.dirname(path)
    if not os.path.exists(path_dir):
        os.makedirs(path_dir)

    resp = requests.get(url, params=param, stream=True)
    if resp.status_code == 200:
        with open(path, 'wb') as f:
            for r in resp.iter_content(chunk_size=chunk_size):
                f.write(r)
        return True
    return False


def b642img_save(base64_data, path, img_type='jpg', url=False):
    if url:
        img_type, base64_data = re.search(r'data:image/(.*?);base64,(.*)', base64_data).groups()

    path_dir = os.path.dirname(path)
    if path_dir and not os.path.exists(path_dir):
        os.makedirs(path_dir)

    with open(f'{path}.{img_type}', 'wb') as f:
        f.write(base64.b64decode(base64_data))


def b64img(base64_data, url=False):
    if url:
        base64_data = re.search(r'.*base64,(.*)"\)', base64_data).group(1)
    return base64.b64decode(base64_data)


def img2b64(content):
    return base64.b64encode(content)


def contentIO(content):
    img = Image.open(io.BytesIO(content))
    return img
