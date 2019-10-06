#!/usr/bin/env python
# -*- coding: utf-8 -*-
import typing


class Duration:
    h = 0
    m = 0
    s = 0
    MIN = 0
    MAX = 86399

    @classmethod
    def set_duration(cls, duration: typing.Union[int, float]) -> 'Duration':
        if cls.MIN > duration or duration > cls.MAX:
            raise OverflowError("result out of range")
        cls.h = duration // 3600
        cls.m = (duration - cls.h * 3600) // 60
        cls.s = (duration - cls.h * 3600) - cls.m * 60
        return cls()

    @classmethod
    def to_str(cls) -> str:
        return f'{cls.h}:{cls.m}:{cls.s}'

    @classmethod
    def to_duration(cls) -> int:
        return cls.h * 3600 + cls.m * 60 + cls.s

    @classmethod
    def delta(cls, h=0, m=0, s: int = 0) -> 'Duration':
        cls.h = h
        cls.m = m
        cls.s = s
        return cls()

    @classmethod
    def set_time(cls, time_str: str) -> 'Duration':
        cls.h, cls.m, cls.s = map(int, time_str.split(':'))
        return cls()

    def __add__(self, other):
        if isinstance(other, duration_delta):
            duration = self.to_duration() + other.to_duration()
            return Duration.set_duration(duration)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, duration_delta):
            duration = self.to_duration() - other.to_duration()
            return Duration.set_duration(duration)
        return NotImplemented


class duration_delta:
    def __init__(self, h=0, m=0, s: int = 0):
        self.h = h
        self.m = m
        self.s = s

    def to_duration(self) -> int:
        return self.h * 3600 + self.m * 60 + self.s

    def __add__(self, other):
        if isinstance(other, Duration):
            return Duration.delta(self.h + other.h,
                                  self.m + other.m,
                                  self.s + other.s)
        return NotImplemented

    def __sub__(self, other):
        if isinstance(other, Duration):
            return Duration.delta(self.h - other.h,
                                  self.m - other.m,
                                  self.s - other.s)
        return NotImplemented
