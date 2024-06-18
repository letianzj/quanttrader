#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum

__all__ = ["OrderFlag"]


class OrderFlag(Enum):
    OPEN = 0  # in use
    CLOSE = 1
    CLOSE_TODAY = 2  # in use
    CLOSE_YESTERDAY = 3  # in use
