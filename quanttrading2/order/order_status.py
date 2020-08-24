#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum
from functools import total_ordering

@total_ordering
class OrderStatus(Enum):
    UNKNOWN = 0
    NEWBORN = 1              # in use
    ACKNOWLEDGED = 2        # in use
    PENDING_SUBMIT = 3      # or PRE-SUBMIT
    SUBMITTED = 4           # in use
    PARTIALLY_FILLED = 5
    FILLED = 6              # in use
    PENDING_CANCEL = 7
    CANCELED = 8            # in use
    API_PENDING = 10
    API_CANCELLED = 11
    ERROR = 12

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented
