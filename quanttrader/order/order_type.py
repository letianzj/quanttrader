#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum

# OrderType.MKT.name == 'MKT'  OderType.MKT.value == 1
class OrderType(Enum):
    UNKNOWN = 0
    MARKET = 1
    LIMIT = 2
    STOP = 3
    STOP_LIMIT = 4
    TRAIING_STOP = 5