#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pandas import Timestamp
from enum import Enum
from ..event.event import *


class TickType(Enum):
    TRADE = 0
    BID = 1
    ASK = 2
    FULL = 3

class TickEvent(Event):
    """
    Tick event
    """

    def __init__(self):
        """
        Initialises Tick
        """
        self.event_type = EventType.TICK
        self.tick_type = TickType.TRADE
        self.timestamp = Timestamp('1970-01-01', tz='UTC')
        self.full_symbol = ''
        self.price = 0.0
        self.size = 0
        self.depth = 1
        self.bid_price_L1 = 0.0
        self.bid_size_L1 = 0
        self.ask_price_L1 = 0.0
        self.ask_size_L1 = 0
        self.open_interest = 0
        self.open = 0.0
        self.high = 0.0
        self.low = 0.0
        self.pre_close = 0.0
        self.upper_limit_price = 0.0
        self.lower_limit_price = 0.0

    def __str__(self):
        return "Time: %s, Ticker: %s, Type: %s,  Price: %s, Size %s" % (
            str(self.timestamp), str(self.full_symbol), (self.tick_type),
            str(self.price), str(self.size)
        )
