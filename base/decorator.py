#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from contextlib import contextmanager
from functools import wraps

from etc import config


def func_time(log=None, tag=None):
    def deco(old_handler):
        @wraps(old_handler)
        def new_handler(*args, **kwargs):
            if not config.debug:
                return old_handler(*args, **kwargs)
            start = time.time()
            result = old_handler(*args, **kwargs)
            end = time.time()
            msg = "Total time running [%s]: %s seconds" % (
                old_handler.__name__ if tag is None else tag, str(end - start))
            if log:
                log(msg)
            else:
                print(msg)
            return result

        return new_handler

    return deco


@contextmanager
def with_func_time(tag, log=None, is_log=False):
    if config.debug or is_log:
        start = time.time()
    try:
        yield
    finally:
        if config.debug or is_log:
            end = time.time()
            msg = "Total time running %s: %s seconds" % (tag, str(end - start))
            if log:
                log(msg)
                return
            print(msg)
