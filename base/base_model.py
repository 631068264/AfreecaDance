#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import random
import statistics
import typing
from collections import defaultdict
from pathlib import Path
from pprint import pprint

import numpy as np
import tensorflow as tf
from tensorflow.python.ops import init_ops

from base import cvutil
from base.logger import AutoLog
from base.stash import Stash
from base.timeutil import Duration
from etc import config

WIDTH, HEIGHT = config.THUMBNAIL_SIZE.WIDTH, config.THUMBNAIL_SIZE.HEIGHT
BATCH_SIZE = 11 * 22
EPOCHS = 10000
TOTAL_DURATION = config.THUMBNAIL_SIZE.DURATION_SEC * config.THUMBNAIL_SIZE.ROW_COUNT * config.THUMBNAIL_SIZE.COLUMN_COUNT


class CNNModel:

    def __init__(self, user_id: str):
        self.image_height = config.THUMBNAIL_SIZE.HEIGHT
        self.image_width = config.THUMBNAIL_SIZE.WIDTH
        # process label
        self.label_set = '01'
        self.label_set_len = len(self.label_set)
        self.label_len = 1
        self.label_size = self.label_set_len * self.label_len

        self.X = tf.compat.v1.placeholder(tf.float32, [None, HEIGHT * WIDTH])  # 特征向量
        self.Y = tf.compat.v1.placeholder(tf.float32, [None, self.label_size])  # 标签
        self.keep_prob = tf.compat.v1.placeholder(tf.float32)  # dropout值

        self.user_id = user_id
        self.stash = Stash('thumbnail_process')
        self.model_save_dir = self.pre_path(Path('model_save_dir', self.user_id))
        self.model_name = self.model_save_dir + '/atv'
        self.model_log_dir = self.pre_path('model_logs', build=False)
        self.train_images_list = self.stash['train_data']
        self.verify_images_list = self.stash['test_data']

        self.log = AutoLog.file_log('model')

    def label2onehot(self, label: str):
        label_set_len = len(self.label_set)
        vec = np.zeros(label_set_len * len(label))
        for i, ch in enumerate(label):
            idx = i * self.label_len + self.label_set.index(ch)
            vec[idx] = 1
        return vec

    def pre_path(self, dir_name: str, build=True) -> str:
        data_path = Path(config.DATA.DATA_PATH, self.user_id, dir_name)
        if not data_path.exists() and build:
            data_path.mkdir(parents=True)
        return str(data_path)

    def model(self):
        x = tf.reshape(self.X, shape=[-1, self.image_height, self.image_width, 1])

        for conv_filter in [32, 64, 128]:
            x = tf.layers.conv2d(x, filters=conv_filter, kernel_size=3, padding='SAME',
                                 activation=tf.nn.relu,
                                 kernel_initializer=init_ops.glorot_uniform_initializer(),
                                 bias_initializer=init_ops.random_uniform_initializer(),
                                 )
            x = tf.layers.max_pooling2d(x, pool_size=2, strides=2, padding='SAME')
            x = tf.layers.dropout(x, rate=self.keep_prob)

        x = tf.layers.flatten(x)
        x = tf.layers.dense(x, 1024,
                            kernel_initializer=init_ops.glorot_uniform_initializer(),
                            bias_initializer=init_ops.random_uniform_initializer(),
                            activation=tf.nn.relu)
        with tf.name_scope('y_prediction'):
            y = tf.layers.dense(x, self.label_size,
                                kernel_initializer=init_ops.glorot_uniform_initializer(),
                                bias_initializer=init_ops.random_uniform_initializer(), )
        return y

    @staticmethod
    def _prepare_img_by_path(path: str) -> np.array:
        img = cvutil.load_img(path)
        img = cvutil.gray(img)
        # flatten 转为一维
        img = img.flatten() / 255
        return img

    def gen_cnn_image_label(self, path: str):
        img = self._prepare_img_by_path(path)
        p = Path(path)
        lable = p.stem.split('_')[-1]
        return img, lable

    def get_batch(self, epoch: int, size: int = BATCH_SIZE):
        max_batch = len(self.train_images_list) // size
        if epoch > max_batch - 1:
            epoch = epoch % max_batch
        s = epoch * size
        e = (epoch + 1) * size
        this_batch = self.train_images_list[s:e]
        batch_x = np.zeros([size, self.image_height * self.image_width])  # 初始化
        batch_y = np.zeros([size, self.label_size])  # 初始化

        for i, img_name in enumerate(this_batch):
            image_array, label = self.gen_cnn_image_label(img_name)
            batch_x[i, :] = image_array
            batch_y[i, :] = self.label2onehot(label)
        return batch_x, batch_y

    def get_validation_batch(self, size: int = BATCH_SIZE):
        batch_x = np.zeros([size, self.image_height * self.image_width])  # 初始化
        batch_y = np.zeros([size, self.label_size])  # 初始化
        validation_images = []
        for i in range(size):
            validation_images.append(random.choice(self.verify_images_list))

        for i, img_name in enumerate(validation_images):
            image_array, label = self.gen_cnn_image_label(img_name)
            batch_x[i, :] = image_array
            batch_y[i, :] = self.label2onehot(label)
        return batch_x, batch_y

    def train(self):
        y_predict = self.model()

        with tf.name_scope('cost'):
            cost = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=y_predict, labels=self.Y))
            tf.compat.v1.summary.scalar('loss', cost)
        with tf.name_scope('train'):
            optimizer = tf.compat.v1.train.AdamOptimizer(learning_rate=0.0001).minimize(cost)
        with tf.name_scope('acc'):
            correct_prediction = tf.equal(tf.argmax(y_predict, -1), tf.argmax(self.Y, -1))
            accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32), name='acc')
            tf.compat.v1.summary.scalar('acc', accuracy)

        merged_summary_op = tf.compat.v1.summary.merge_all()
        saver = tf.compat.v1.train.Saver()
        with tf.compat.v1.Session() as sess:
            init = tf.compat.v1.global_variables_initializer()
            sess.run(init)

            # 恢复模型
            if os.listdir(self.model_save_dir):
                try:
                    saver.restore(sess, self.model_name)
                # 判断捕获model文件夹中没有模型文件的错误
                except ValueError:
                    print("model文件夹为空，将创建新模型")
            else:
                pass

            # 写入日志
            writer = tf.compat.v1.summary.FileWriter(self.model_log_dir, sess.graph)
            step = 1
            early_stop_tmp, early_stop_count, early_stop_tar = 0, 5, 0.95
            for epoch in range(EPOCHS):
                batch_x, batch_y = self.get_batch(epoch, size=BATCH_SIZE)
                summary_str, _, cost_, _ = sess.run([merged_summary_op, optimizer, cost, y_predict],
                                                    feed_dict={self.X: batch_x, self.Y: batch_y, self.keep_prob: 0.75})
                writer.add_summary(summary_str, step)
                if step % 10 == 0:
                    batch_x_test, batch_y_test = self.get_batch(epoch, size=BATCH_SIZE)
                    acc = sess.run(accuracy, feed_dict={self.X: batch_x_test, self.Y: batch_y_test, self.keep_prob: 1.})
                    print(f"第{step}次训练 >>> ")
                    print(f"[Train Set] acc = {acc:.5%} >>> loss = {cost_:.5}")

                    batch_x_verify, batch_y_verify = self.get_validation_batch(size=100)
                    acc = sess.run(accuracy, feed_dict={self.X: batch_x_verify, self.Y: batch_y_verify, self.keep_prob: 1.})
                    print(f"第{step}次测试 >>> ")
                    print(f"[Test Set] acc = {acc:.5%} >>> loss = {cost_:.5}")

                    # early_stop
                    if acc >= early_stop_tar:
                        early_stop_tmp += 1
                    else:
                        early_stop_tmp = 0
                    if early_stop_tmp >= early_stop_count:
                        # 测试集正确率连续early_stop_count次大于early_stop_tar就早停
                        saver.save(sess, self.model_name)
                        print("定时保存模型成功 early stop")
                        return

                # 每训练一定就保存一次
                if step % 50 == 0:
                    saver.save(sess, self.model_name)
                    print("定时保存模型成功")

                step += 1

            saver.save(sess, self.model_name)

    def valid_run(self, dir_name: str, small_range_sec=15):
        """run model"""
        # 小图总时长
        total_duration = config.THUMBNAIL_SIZE.DURATION_SEC * config.THUMBNAIL_SIZE.ROW_COUNT * config.THUMBNAIL_SIZE.COLUMN_COUNT
        # 目标时长
        TAR_SEC = 3 * 60
        # small range 时长
        SMALL_RANGE_SEC = small_range_sec

        def gen_valid_img():
            data_path = Path(config.DATA.DATA_PATH, self.user_id, 'valid_data')
            for img_path in data_path.glob(dir_name + '*'):
                img = self._prepare_img_by_path(str(img_path))
                yield img_path, img

        def get_duration_key(vod_time: str):
            vod_time_duration = Duration.set_time(vod_time).to_duration() - 1
            set_time_key = vod_time_duration // total_duration * total_duration

            return Duration.set_duration(set_time_key).to_str()

        def get_duration_range(raw_duration: typing.List):
            range_long = TAR_SEC // config.THUMBNAIL_SIZE.DURATION_SEC
            if len(raw_duration) <= range_long:
                return None

            tar_duration = sorted(raw_duration)
            result, tmp = [], []

            for i in range(1, len(raw_duration)):
                if tar_duration[i] - tar_duration[i - 1] == config.THUMBNAIL_SIZE.DURATION_SEC:
                    tmp.append(tar_duration[i - 1])
                elif tmp:
                    if tar_duration[i - 1] - tmp[-1] == config.THUMBNAIL_SIZE.DURATION_SEC:
                        tmp.append(tar_duration[i - 1])
                    if len(tmp) > SMALL_RANGE_SEC // config.THUMBNAIL_SIZE.DURATION_SEC:
                        start_time = Duration.set_duration(tmp[0]).to_str()
                        end_time = Duration.set_duration(tmp[-1]).to_str()
                        result.append((start_time, end_time))
                    tmp = []

            # 到最后都是连续的
            if tmp:
                if tar_duration[i - 1] - tmp[-1] == config.THUMBNAIL_SIZE.DURATION_SEC:
                    tmp.append(tar_duration[i - 1])
                if len(tmp) > SMALL_RANGE_SEC // config.THUMBNAIL_SIZE.DURATION_SEC:
                    start_time = Duration.set_duration(tmp[0]).to_str()
                    end_time = Duration.set_duration(tmp[-1]).to_str()
                    result.append((start_time, end_time))

            return result

        def precition(TP, FP: int):
            return TP / (TP + FP)

        def recall(TP, FN: int):
            return TP / (TP + FN)

        def f_score(TP, FP, FN: int):
            return 2 * TP / (2 * TP + FP + FN)

        y_predict = self.model()
        saver = tf.train.Saver()
        with tf.compat.v1.Session() as sess:
            saver.restore(sess, self.model_name)
            predict_y = tf.argmax(y_predict, -1)
            # stat
            stat_dict = defaultdict(dict)
            TP, TN, FP, FN = 0, 0, 0, 0
            # result
            raw_result = []

            for img_path, img in gen_valid_img():
                predict = sess.run(predict_y, feed_dict={self.X: [img], self.keep_prob: 1.0})
                predict_value = predict[0]
                vod_name, vod_time, label = img_path.stem.split('_')
                vod_time_key = get_duration_key(vod_time)
                if predict_value == 1:
                    raw_result.append(Duration.set_time(vod_time).to_duration())

                # acc
                stat_dict[vod_time_key].setdefault('right', 0)
                stat_dict[vod_time_key].setdefault('sum', 0)
                stat_dict[vod_time_key].setdefault('error_list', [])
                stat_dict[vod_time_key]['sum'] += 1
                if int(label) == predict_value:
                    stat_dict[vod_time_key]['right'] += 1
                else:
                    stat_dict[vod_time_key]['error_list'].append(img_path.stem.replace(':', '/'))
                # confusion matrix
                if int(label) == predict_value == 1:
                    TP += 1
                elif int(label) == predict_value == 0:
                    TN += 1
                elif int(label) == 1 and predict_value == 0:
                    FN += 1
                elif int(label) == 0 and predict_value == 1:
                    FP += 1
        # res
        result = get_duration_range(raw_result)
        self.log.info(f'[{self.user_id}/{dir_name}] {result}')
        # stat
        rate = []
        for k, v in stat_dict.items():
            v['rate'] = v.pop('right') / v.pop('sum')
            rate.append(v['rate'])
        pprint(stat_dict)
        acc_msg = f'acc {statistics.mean(rate):.4%}'
        confusion_matrix_msg = f'precition {precition(TP, FP):.4} recall {recall(TP, FN):.4} f_score {f_score(TP, FP, FN):.4}'
        self.log.info(f'[{self.user_id}/{dir_name} valid] {acc_msg} {confusion_matrix_msg}')
        pprint(acc_msg)
        pprint(confusion_matrix_msg)
        pprint(result)

    def _gen_valid_img(self, dir_name: str, data_name: str = 'valid_data'):
        data_path = Path(config.DATA.DATA_PATH, self.user_id, data_name)
        for img_path in data_path.glob(dir_name + '*'):
            img = self._prepare_img_by_path(str(img_path))
            yield img_path, img

    def _get_duration_key(self, vod_time: str):
        vod_time_duration = Duration.set_time(vod_time).to_duration() - 1
        set_time_key = vod_time_duration // TOTAL_DURATION * TOTAL_DURATION
        return Duration.set_duration(set_time_key).to_str()

    def _get_duration_range(self, tar_sec: int, raw_duration: typing.List) -> typing.List:
        range_long = tar_sec // config.THUMBNAIL_SIZE.DURATION_SEC
        if len(raw_duration) < range_long:
            raise Exception(f'tar vod should logger than {tar_sec}')

        tar_duration = sorted(raw_duration)
        result, tmp = [], []

        for i in range(1, len(raw_duration)):
            if tar_duration[i] - tar_duration[i - 1] == config.THUMBNAIL_SIZE.DURATION_SEC:
                # 同一时间段先塞
                tmp.append(tar_duration[i - 1])
            elif tmp:
                if tar_duration[i - 1] - tmp[-1] == config.THUMBNAIL_SIZE.DURATION_SEC:
                    # 出现断层塞时间段的最后一个
                    tmp.append(tar_duration[i - 1])
                if len(tmp) > tar_sec // config.THUMBNAIL_SIZE.DURATION_SEC:
                    # 时间段长度
                    start_time = Duration.set_duration(tmp[0]).to_str()
                    end_time = Duration.set_duration(tmp[-1]).to_str()
                    result.append((start_time, end_time))
                tmp = []

        # 到最后都是连续的没有断层
        if tmp:
            if tar_duration[i - 1] - tmp[-1] == config.THUMBNAIL_SIZE.DURATION_SEC:
                tmp.append(tar_duration[i - 1])
            if len(tmp) > tar_sec // config.THUMBNAIL_SIZE.DURATION_SEC:
                start_time = Duration.set_duration(tmp[0]).to_str()
                end_time = Duration.set_duration(tmp[-1]).to_str()
                result.append((start_time, end_time))

        return result

    def local_run(self, dir_name: str, tar_sec: int = 60) -> typing.List:
        """
        :param dir_name:
        :param tar_sec: 目标时长 (视频总时长，连续时间段时长)
        :return:
        """
        y_predict = self.model()
        saver = tf.compat.v1.train.Saver()
        with tf.compat.v1.Session() as sess:
            saver.restore(sess, self.model_name)
            predict_y = tf.argmax(y_predict, -1)
            # result
            raw_result = []

            for img_path, img in self._gen_valid_img(dir_name):
                predict = sess.run(predict_y, feed_dict={self.X: [img], self.keep_prob: 1.0})
                predict_value = predict[0]
                _, vod_time, _ = img_path.stem.split('_')
                if predict_value == 1:
                    raw_result.append(Duration.set_time(vod_time).to_duration())

        self.log.info(f'[{self.user_id}/{dir_name} local run raw_result] {raw_result}')
        # res
        try:
            result = self._get_duration_range(tar_sec, raw_result)
            self.log.info(f'[{self.user_id}/{dir_name} local run] {result}')
            return result
        except Exception as e:
            self.log.error(f'[{self.user_id}/{dir_name} local run] {str(e)}')
