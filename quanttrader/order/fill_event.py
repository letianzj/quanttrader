#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pandas import Timestamp
from ..event.event import *
from ..position.position import Position

class FillEvent(Event):
    """
    Fill event, with filled quantity/size and price
    """
    def __init__(self):
        """
        Initialises fill
        """
        self.event_type = EventType.FILL
        self.order_id = -1
        self.fill_id = -1
        self.full_symbol = ''
        self.fill_time = ''
        self.fill_price = 0.0
        self.fill_size = 0     # size < 0 means short order is filled
        self.exchange = ''
        self.commission = 0.0
        self.account = ''
        self.source = -1
        self.api = ''

    def to_position(self, multiplier=1):
        """
        if there is no existing position for this symbol, this fill will create a new position
        (otherwise it will be adjusted to exisitng position)
        """
        if self.fill_size > 0:
            average_price_including_commission = self.fill_price + self.commission/multiplier
        else:
            average_price_including_commission = self.fill_price - self.commission/multiplier

        new_position = Position(self.full_symbol, average_price_including_commission, self.fill_size)
        return new_position

    def __str__(self):
        return "Time: %s, Source: %s, Oid: %s, Ticker: %s, Price: %s, Size %s Comm %s" % (
            self.fill_time, str(self.source), str(self.order_id), self.full_symbol, str(self.fill_price), str(self.fill_size), str(self.commission)
        )