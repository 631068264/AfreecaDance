#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gevent import monkey

monkey.patch_all()

import importme

importme.init()

from base.base_spider import ThumbnailSpider


def update():
    spider = ThumbnailSpider('rlrlvkvk123')
    spider.run(login=True)


def fix():
    spider = ThumbnailSpider('rlrlvkvk123')
    spider.fix(station_num=37691534, login=True)

update()
