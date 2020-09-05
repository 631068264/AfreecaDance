#!/usr/bin/env python
# -*- coding: utf-8 -*-
from base.stash import Stash
from base.util import url_params, get_url_params
from pprint import pprint

def test_vod():
    stash = Stash(f'afreecatv_rlrlvkvk123')
    # vods = stash['rlrlvkvk123:vod']
    station = 60946442
    key = f'{station}:vodparam'
    vodparam = stash[key]
    pprint(get_url_params(vodparam))
