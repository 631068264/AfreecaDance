#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 2017/2/3 16:16
@annotation = ''
"""

import os

project_home = os.path.realpath(__file__)
project_home = os.path.split(project_home)[0]
import sys

sys.path.append(os.path.split(project_home)[0])
sys.path.append(project_home)


def init():
    from base import logger
    from etc import config

    # log setting
    logger.init_log([(n, os.path.join("logs", p), l)
                     for n, p, l in config.log_config])
    logger.AutoLog.log_path = 'logs'
