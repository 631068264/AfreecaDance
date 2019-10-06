#!/usr/bin/env python
# -*- coding: utf-8 -*-
from base import cvutil
from pathlib import Path

def test_shape():
    path = 'img/0:0:3_0.jpg'

    img = cvutil.load_img(path)
    img = cvutil.gray(img)
    img = img.flatten() / 255
    print(img.shape)
    p = Path(path)
    print(p.stem.split('_')[-1])
    print()
    
