#!/usr/bin/env python
# -*- coding: utf-8 -*-
import click
from gevent import monkey

monkey.patch_all()

import importme

importme.init()

from base import SnippetMerge, ThumbnailSpider, ThumbnailProcess, CNNModel


@click.group()
def cli():
    pass


@cli.command()
@click.argument('bj_id')
def thumbnail(bj_id):
    """获取所有缩略图"""
    spider = ThumbnailSpider(bj_id)
    spider.run(login=True)


@cli.command()
@click.argument('bj_id')
@click.argument('station_num')
def fix_thumbnail(bj_id, station_num):
    """获取某个station缩略图"""
    spider = ThumbnailSpider(bj_id)
    spider.fix(station_num=int(station_num), login=True)


@cli.command()
@click.argument('bj_id')
def train(bj_id):
    """cnn模型训练"""
    model = CNNModel(bj_id)
    model.train()


@cli.command()
@click.argument('bj_id')
@click.argument('station_num')
@click.option('--tar_sec', type=int, default=60)
def vod(bj_id, station_num, tar_sec):
    """生成目标视频"""
    ThumbnailProcess(bj_id).split_img(station_num)
    model_result = CNNModel(bj_id).local_run(station_num, tar_sec=tar_sec)
    if model_result:
        SnippetMerge(bj_id).run(station_num, tar_time_range=model_result)


if __name__ == '__main__':
    cli()
