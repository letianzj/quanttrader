#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum

# OrderType.MKT.name == 'MKT'  OderType.MKT.value == 0
class OrderType(Enum):
    MARKET = 0
    LIMIT = 1
    STOP = 5
    STOP_LIMIT = 6
    TRAIING_STOP = 7