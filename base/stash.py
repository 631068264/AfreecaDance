#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author = 'wyx'
@time = 2018/12/1 16:53
@annotation = ''
"""
import os
import pprint
import sqlite3
from contextlib import contextmanager

import six

# Python 3 vs 2 imports
if six.PY3:
    from collections import UserDict as DictMixin
    from pickle import dumps, loads, HIGHEST_PROTOCOL as PICKLE_PROTOCOL
else:
    from UserDict import DictMixin
    from cPickle import dumps, loads, HIGHEST_PROTOCOL as PICKLE_PROTOCOL

try:
    from collections.abc import Sequence
except ImportError:
    from collections import Sequence


def encode(obj):
    return sqlite3.Binary(dumps(obj, protocol=PICKLE_PROTOCOL))


def decode(obj):
    return loads(bytes(obj)) if obj is not None else None


class Stash(DictMixin):
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "stash")

    def __init__(self, file_name, table_name='kv', encode=encode, decode=decode):
        # TODO:use other Serialization
        file_name = os.path.join(self.path, file_name + '.sqlite3')
        dir_name = os.path.dirname(file_name)
        if dir_name and not os.path.exists(dir_name):
            raise RuntimeError('The directory does not exist, %s' % dir_name)
        self.table_name = table_name
        self.file_name = file_name
        self.encode = encode
        self.decode = decode
        self.conn = None
        # sql schema
        self._CREATE_TABLE = 'CREATE TABLE IF NOT EXISTS {} (key TEXT PRIMARY KEY, val BLOB)'.format(self.table_name)
        self._SET = 'REPLACE INTO {} (key, val) VALUES (?, ?)'.format(self.table_name)
        self._GET = 'SELECT val FROM {} WHERE key = ?'.format(self.table_name)
        self._GET_MANY = 'SELECT key, val FROM {} WHERE key IN (%s)'.format(self.table_name)
        self._GET_ITEM = 'SELECT key, val FROM {} ORDER BY key'.format(self.table_name)
        self._GET_KEY = 'SELECT key FROM {} ORDER BY key'.format(self.table_name)
        self._GET_VALUE = 'SELECT val FROM {} ORDER BY key'.format(self.table_name)
        self._DEL = 'DELETE FROM {} WHERE key = ?'.format(self.table_name)
        self._COUNT = 'SELECT COUNT(*) FROM {}'.format(self.table_name)
        # VACUUM can reduce size of table after clear table
        self._CLEAR = 'DELETE FROM {}; VACUUM;'.format(self.table_name)

        self._create()

    def _connect(self):
        # self._sql()
        self.conn = sqlite3.connect(self.file_name)
        self.conn.text_factory = str
        self.cursor = self.conn.cursor()
        # self.cursor.execute(self._CREATE_TABLE)
        # self._commit()

    def _commit(self):
        if self.conn:
            self.conn.commit()

    def _create(self):
        with self.with_stash():
            self.cursor.execute(self._CREATE_TABLE)

    def __setitem__(self, key, value):
        """x.__setitem__(k, v) <==> x[k] = v"""
        with self.with_stash():
            self.cursor.execute(self._SET, (key, self.encode(value)))

    def _select(self, key_list, default=None):
        temp_get_many_sql = self._GET_MANY % ','.join('?' * len(key_list))
        self.cursor.execute(temp_get_many_sql, key_list)
        k_v = dict(self.cursor.fetchall())
        return {k: self.decode(k_v.get(k, default)) for k in key_list}

    def __getitem__(self, key):
        """x.__getitem__(k) <==> x[k]"""
        with self.with_stash():
            if not isinstance(key, six.string_types) and isinstance(key, Sequence):
                return self._select(key)

            self.cursor.execute(self._GET, (key,))
            val = self.cursor.fetchone()
            if not val:
                raise KeyError(key)
            return self.decode(val[0])

    def __contains__(self, key):
        """x.__contains__(k) -> True if key in x, else False"""
        with self.with_stash():
            self.cursor.execute(self._GET, (key,))
            val = self.cursor.fetchone()
            if not val:
                return False
            return True

    def __delitem__(self, key):
        """x.__delitem__(k) <==> del x[k] don't raise error when key not exist"""
        with self.with_stash():
            self.cursor.execute(self._DEL, (key,))

    def __len__(self):
        with self.with_stash():
            self.cursor.execute(self._COUNT)
            count = self.cursor.fetchone()[0]
            return count if count else 0

    def __repr__(self):
        return pprint.pformat(dict(self.items()))

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default=None):
        if key in self:
            return self[key]
        self[key] = default
        return default

    def update(self, items=(), **kwargs):
        """
        x.update(red=1, blue=3)
        x.update({'red':1,'blue':3})
        """
        try:
            items = six.iteritems(items)
        except AttributeError:
            pass
        items = [(k, self.encode(v)) for k, v in items]
        with self.with_stash():
            self.cursor.executemany(self._SET, items)
        if kwargs:
            self.update(kwargs)

    def clear(self):
        with self.with_stash():
            self.cursor.executescript(self._CLEAR)

    def close(self):
        if self.conn is not None:
            self.conn.commit()
            self.conn.close()
            self.conn = None
            self.cursor = None

    def rm_db(self):
        """remove file"""
        if self.conn is not None:
            self.close()
        try:
            if os.path.isfile(self.file_name):
                os.remove(self.file_name)
        except:
            pass

    # Iteration
    def items(self):
        with self.with_stash():
            for k, v in self.cursor.execute(self._GET_ITEM):
                yield k, self.decode(v)

    def keys(self):
        with self.with_stash():
            for k in self.cursor.execute(self._GET_KEY):
                yield k[0]

    def values(self):
        with self.with_stash():
            for v in self.cursor.execute(self._GET_VALUE):
                yield self.decode(v[0])

    def __iter__(self):
        return self.keys()

    # With contextmanager
    # def __enter__(self):
    #     if not hasattr(self, 'conn') or self.conn is None:
    #         self._connect()
    #     return self
    #
    # def __exit__(self, exc_type, exc_val, exc_tb):
    #     self.close()

    @contextmanager
    def with_stash(self):
        self._connect()
        try:
            yield self.cursor
        finally:
            self.close()

    def __del__(self):
        if self.conn is not None:
            self.close()


if __name__ == '__main__':
    class Test(object):
        t = 1

        def __init__(self):
            self.a = 0

        def c(self, d):
            self.a = self.t + d
            return self.t + d


    stash = Stash('sss', table_name='ss')
    stash.clear()
    assert len(stash) == 0
    stash["13"] = "qwer"
    assert stash["13"] == "qwer"
    stash['和谐'] = '健康'
    assert stash['和谐'] == '健康'

    assert ("13" in stash) is True

    del stash["13"]
    del stash["15"]
    del stash['和谐']
    del stash['inexistence key']

    assert (stash.get("15")) is None
    assert (stash.get('15', default=123) == 123)

    stash.setdefault('sd', default=123)
    assert stash['sd'] == 123
    stash.setdefault('sd', default=444)
    assert stash['sd'] == 123

    assert stash == {'sd': 123}
    assert len(stash) == 1

    assert list(stash.keys()) == ['sd']
    assert list(stash.values()) == [123]
    assert list(stash.items()) == [('sd', 123)]

    stash.update(red=1, blue='adfdfaf')
    assert len(stash) == 3
    assert stash['blue'] == 'adfdfaf'
    # assert stash == {'blue': 'adfdfaf', 'red': 1, 'sd': 123}

    stash.update({'red': 2, 'blue': 4})
    # assert stash == {'red': 2, 'blue': 4, 'sd': 123}
    assert stash['blue'] == 4

    stash['obj'] = Test()
    assert stash['obj'].c(2) == 3
    assert stash['obj'].a == 0

    stash['123'] = 1
    stash['啦啦啦'] = 1
    s = stash['123', '啦啦啦', 'aaa']
    assert s['aaa'] is None
    s = stash[['123', '啦啦啦', 'aaa']]
    assert s['aaa'] is None

    stash['123'] = [0] * 100000

    stash[1] = 123
    assert stash[1] == 123

    print(stash)
    stash.clear()
    stash.rm_db()
