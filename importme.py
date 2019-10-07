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

    # log setting
    logger.AutoLog.log_path = 'logs'

