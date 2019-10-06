AfreecaTV BJ Dance Video


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

<img src="https://tva1.sinaimg.cn/large/006y8mN6ly1g7ov37dzcjj319y0ritjs.jpg" style="zoom:40%"/>

##  Split thumbnail

Split and resize thumbnail into small pictures by opencv and they are assigned to train set and test set

<img src="https://tva1.sinaimg.cn/large/006y8mN6ly1g7ov1n39aej305q03874e.jpg" style="zoom:40%"/>

## CNN Model

Train a CNN model to classify and get dance time range in vod

## Get vod

According to the time range to download ts files and than merge to a mp4 (ts to mp4)


