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
    import os
    from base import logger
    from etc import config

    # log setting
    logger.init_log([(n, os.path.join("logs", p), l)
                     for n, p, l in config.log_config])
    logger.AutoLog.log_path = 'logs'

    # pool setting
    smartpool.coroutine_mode = config.pool_coroutine_mode
    if config.debug and getattr(config, "pool_log", None) is not None:
        smartpool.pool_logger = logger.get(config.pool_log).info

    # mysql setting
    if config.debug and getattr(config, "db_query_log", None) is not None:
        smartpool.query_logger = logger.get(config.db_query_log).info

    for name, setting in config.db_config.items():
        smartpool.init_pool(
            name, setting, smartpool.MySQLdbConnection, *config.db_conn_pool_size,
            maxidle=config.db_connection_idle, clean_interval=config.db_pool_clean_interval
        )
