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

## Detail

### cmd
use `click` lib for cmd

```
Usage: run.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  fix-thumbnail  fix thumbnail by station_num
  thumbnail      get thumbnails by bj_id
  train          cnn model train
  vod            create target video
```

### get label data

Use `split_img.py`

```
train_set = {
    '40911313': {
        '40911313_2:15:0': [(45, 100)],
        '40911313_2:20:0': [(1, 7)],
        '40911313_2:30:0': [(53, 100)],
        '40911313_2:35:0': [(1, 32)],
        '40911313_3:5:0': [(52, 100)],
        '40911313_3:10:0': [(1, 37)],
        '40911313_4:55:0': [(57, 100)],
        '40911313_5:0:0': [(1, 41)],
        '40911313_9:30:0': [(62, 94)],
    },
}

```

according **afreecatv_vod_thumbnail** dir
```
format

train_set = {
    'station_num': {
        'jpg_name': [(target_range_min, target_range_max)],
    },
}
```


# Step

## Get thumbnail

Get vod thumbnail from AfreecaTV

##  Split thumbnail

Split and resize thumbnails into small pictures by **opencv** and they are divided into some data set

## CNN Model

Train a CNN model to get dance time range in vod

## Get vod

Parse **.m3u8**, download **ts** files and  merge/compress to mp4 (ts to mp4) by **ffmpeg**
