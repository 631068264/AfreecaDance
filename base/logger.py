#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@author = 'wyx'
@time = 2017/2/3 16:02
@annotation = ''
"""
import datetime
import logging
import os
from logging.handlers import RotatingFileHandler

from etc import config

_log_config = [
    ['', '', 'debug'],
    ['error-log', '', 'debug'],
]


class MyLoggerFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None):
        super(MyLoggerFormatter, self).__init__(fmt=fmt, datefmt=datefmt)

    def formatTime(self, record, datefmt=None):
        return datetime.datetime.now(config.tz_info).strftime(datefmt)


def init_log(log_config=None):
    formater = MyLoggerFormatter('%(name)-12s %(asctime)s %(levelname)-8s %(message)s',
                                 '%a, %d %b %Y %H:%M:%S', )

    """
    logging.basicConfig(level=logging.DEBUG,
        format='%(name)-12s %(asctime)s %(levelname)-8s %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S',
        filename=log_file,
        filemode='a')
    """

    if not log_config:
        log_config = _log_config

    for log in log_config:
        logger = logging.getLogger(log[0])
        if log[1]:
            handler = RotatingFileHandler(log[1], 'a', maxBytes=pow(1024, 3), backupCount=2, encoding="utf8")
        else:
            import sys
            handler = logging.StreamHandler(sys.stderr)
            logger.propagate = False
        handler.setFormatter(formater)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, log[2].upper()))


class AutoLog(object):
    log_path = None

    @classmethod
    def file_log(cls, log_name, level='debug'):
        formater = MyLoggerFormatter('%(name)-12s %(asctime)s %(levelname)-8s %(message)s',
                                     '%a, %d %b %Y %H:%M:%S', )
        logger = logging.getLogger(log_name)
        log_path = os.path.join(cls.log_path, log_name + '.log')
        handler = RotatingFileHandler(log_path, 'a', maxBytes=pow(1024, 3), backupCount=2, encoding="utf8")
        # if log_path:
        #     pass
        # else:
        #     import sys
        #     handler = logging.StreamHandler(sys.stderr)
        #     logger.propagate = False
        handler.setFormatter(formater)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level.upper()))
        return logger


def get(log_name=''):
    return logging.getLogger(log_name)


def error(msg, *args, **kwargs):
    get("cgi-log").error(msg, *args, **kwargs)


def warn(msg, *args, **kwargs):
    get("cgi-log").warn(msg, *args, **kwargs)


def info(msg, *args, **kwargs):
    get("cgi-log").info(msg, *args, **kwargs)


def debug(msg, *args, **kwargs):
    get("cgi-log").debug(msg, *args, **kwargs)


def log(level, msg, *args, **kwargs):
    get("cgi-log").log(level, msg, *args, **kwargs)


def test():
    init_log(_log_config)
    logger1 = logging.getLogger('debug.logger')
    logger2 = logging.getLogger('debug.logger2')

    logging.debug('test')
    logging.error('test-error')
    logger1.info('test2')

    logger2.error('test2')
    logger2.error("hello %s", 1)


if __name__ == "__main__":
    test()
