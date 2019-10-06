AfreecaTV BJ Dance Video

AfreecaTV 从某个BJ的视频中精炼出💃的片段 (仅献给能番羽土啬的同学)


# Usage

## Install

```shell
virtualenv -p python3 .env

pip install -r requirements.txt
```

## Set config

`config_global/default.py`

```
class AfricaAccount:
    #  account
    UID = ''
    PWD = ''


class DATA:
    #  data save
    DATA_PATH = '/data/atv'
```


# Step

## Get thumbnail

Get vod thumbnail from AfreecaTV

##  Split thumbnail

Split and resize thumbnail into small pictures by opencv and they are assigned to train set and test set

## CNN Model

Train a CNN model to classify and get dance time range in vod

## Get vod

According to the time range to download ts files and than merge to a mp4 (ts to mp4)


