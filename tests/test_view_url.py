#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pprint import pprint

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import talib as ta

from base import SnippetMerge
from base.base_spider import ViewCnt
from base.timeutil import Duration, duration_delta, MIN_SEC


def test_data():
    bj_id = 'rlrlvkvk123'
    mod = ViewCnt(bj_id)
    target_dict = mod.run()
    for station_num, time_range in target_dict.items():
        if time_range:
            SnippetMerge(bj_id).run(str(station_num), tar_time_range=time_range, ignore=True)


def test_a():
    bj_id = 'rlrlvkvk123'
    mod = ViewCnt(bj_id)
    target_dict = mod.run()
    pprint(target_dict)

def test_raw_data():
    raw_data = {
        'cnt': [[0, 0], [1, 589], [2, 599], [3, 574], [4, 538], [5, 486], [6, 466], [7, 460], [8, 451], [9, 457], [10, 441], [11, 442], [12, 437],
                [13, 453], [14, 502], [15, 549], [16, 558], [17, 553], [18, 541], [19, 498], [20, 508], [21, 508], [22, 494], [23, 476], [24, 485],
                [25, 459], [26, 454], [27, 455], [28, 438], [29, 437], [30, 456], [31, 459], [32, 441], [33, 398], [34, 399], [35, 387], [36, 381],
                [37, 370], [38, 382], [39, 377], [40, 369], [41, 354], [42, 361], [43, 359], [44, 359], [45, 372], [46, 357], [47, 347], [48, 347],
                [49, 367], [50, 362], [51, 359], [52, 356], [53, 360], [54, 366], [55, 358], [56, 350], [57, 365], [58, 348], [59, 320], [60, 330],
                [61, 328], [62, 331], [63, 327], [64, 334], [65, 346], [66, 334], [67, 361], [68, 366], [69, 374], [70, 359], [71, 364], [72, 366],
                [73, 351], [74, 340], [75, 334], [76, 328], [77, 337], [78, 341], [79, 368], [80, 363], [81, 344], [82, 337], [83, 334], [84, 320],
                [85, 310], [86, 323], [87, 339], [88, 353], [89, 373], [90, 375], [91, 384], [92, 421], [93, 442], [94, 436], [95, 443], [96, 472],
                [97, 505], [98, 442], [99, 431], [100, 417], [101, 423], [102, 410], [103, 399], [104, 397], [105, 380], [106, 367], [107, 410],
                [108, 428], [109, 450], [110, 470], [111, 450], [112, 467], [113, 434], [114, 422], [115, 401], [116, 407], [117, 397], [118, 408],
                [119, 423], [120, 437], [121, 395], [122, 372], [123, 358], [124, 352], [125, 357], [126, 351], [127, 374], [128, 373], [129, 396],
                [130, 355], [131, 345], [132, 353], [133, 353], [134, 359], [135, 358], [136, 360], [137, 377], [138, 404], [139, 413], [140, 387],
                [141, 386], [142, 366], [143, 346], [144, 352], [145, 342], [146, 350], [147, 341], [148, 321], [149, 317], [150, 305], [151, 308],
                [152, 304], [153, 328], [154, 354], [155, 373], [156, 380], [157, 394], [158, 464], [159, 455], [160, 450], [161, 479], [162, 518],
                [163, 581], [164, 539], [165, 527], [166, 450], [167, 413], [168, 367], [169, 349], [170, 338], [171, 332], [172, 327], [173, 328],
                [174, 318], [175, 316], [176, 307], [177, 305], [178, 314], [179, 326], [180, 344], [181, 332], [182, 323], [183, 318], [184, 319],
                [185, 311], [186, 300], [187, 299], [188, 306], [189, 288], [190, 286], [191, 279], [192, 276], [193, 277], [194, 279], [195, 277]],
        'text': '%s人观看'}

    time_duration = 11685
    pl(raw_data['cnt'], time_duration, 4)


def pl(raw_data, time_duration, station_num):
    if raw_data and time_duration:
        cnt = pd.DataFrame(raw_data, columns=['index', 'value'])
        x = list(range(0, len(cnt)))

        perfect_duration = (Duration.set_duration(time_duration) - duration_delta(m=5)).to_duration()
        per_index = time_duration // len(cnt)
        diff_duration = time_duration - perfect_duration
        perfect_start = diff_duration // per_index

        y = pd.DataFrame(raw_data[perfect_start:], columns=['index', 'value'])

        sma_period = perfect_start * 2
        Y = ta.SMA(y['value'].values.astype('float64'), timeperiod=sma_period).tolist()

        top = []

        for i, d in enumerate(Y):
            if d > 0 and i < len(Y) - 1:
                if (Y[i - 1] <= d and d >= Y[i + 1]) or (i == 0 and d >= Y[i + 1]):
                    top.append((i + perfect_start, d))
                # elif Y[i - 1] >= d and d <= Y[i + 1]:
                #     bottom.append((i, d))

        def row_sma(row):
            cond = (row['start_index'] <= cnt['index']) & (cnt['index'] <= row['index'])
            max_id = cnt.where(cond).dropna()['value'].idxmax()
            result = cnt.loc[max_id]
            row['ori_index'] = result['index']
            row['ori_value'] = result['value']
            row['ori_duration'] = result['index'] * per_index
            row['ori_range_duration'] = (row['ori_duration'] - MIN_SEC * 3, row['ori_duration'] + MIN_SEC * 3)
            return row

        top_df = pd.DataFrame(top, columns=['index', 'value'])
        top_df['value'].where(top_df['value'] > top_df['value'].mean(), inplace=True)
        top_df = top_df.where(top_df['value'] > 0).dropna()
        top_df['start_index'] = top_df['index'] - sma_period + 1
        top_df['index'] = top_df['index']

        a = top_df.apply(row_sma, axis=1)

        plt.plot(x, cnt['value'].values, 'r', linewidth=1, label='ori')
        plt.plot(x[5:], Y, 'b', linewidth=1, label=f'sma-{sma_period}')

        plt.scatter(top_df['index'], top_df['value'], 100, marker='^', label='max')
        plt.scatter(a['ori_index'], a['ori_value'], 100, marker='v', label='ori_max')
        plt.title(station_num)
        plt.legend()
        plt.show()


def test_top():
    max_top = [(18, 518.7), (46, 359.0), (49, 359.3), (53, 359.1), (69, 356.1), (75, 349.2), (96, 443.2), (111, 433.9), (137, 376.3), (162, 487.6),
               (175, 321.7), (176, 321.7), (179, 320.4)]
    df = pd.DataFrame(max_top, columns=['index', 'value'])
    df['value'].where(df['value'] > df['value'].mean(), inplace=True)
    df.where(df['value'] > 0).dropna()

    top = np.array(max_top)

    a = np.average(top, axis=0)

    print(a)
    # np.where(np.average)
