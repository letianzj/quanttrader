#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pandas as pd
from datetime import datetime, date, time, timedelta
from .data_feed_base import DataFeedBase
from .tick_event import TickEvent


class BacktestDataFeed(DataFeedBase):
    """
    BacktestDataFeed uses PLACEHOLDER to stream_next; actual data comes from data_board.get_hist_price
    This is an easy way to handle multiple sources
    """
    def __init__(
        self, start_date=None, end_date=None
    ):
        self._end_date = end_date
        self._start_date = start_date
        self._data_stream = None
        self._data_stream_iter = None

    def set_data_source(self, data):
        if not self._data_stream:
            self._data_stream = data.index
        else:
            self._data_stream = self._data_stream.join(data.index, how='outer', sort=True)

    def subscribe_market_data(self, symbols=None):
        if self._start_date:
            if self._end_date:
                self._data_stream = self._data_stream[(self._data_stream >= self._start_date) & (self._data_stream <= self._end_date)]
            else:
                self._data_stream = self._data_stream[self._data_stream >= self._start_date]

        self._data_stream_iter = self._data_stream.__iter__()

    def unsubscribe_market_data(self, symbols=None):
        pass

    def stream_next(self):
        """
        Place the next TickEvent into the event queue.
        """
        index = next(self._data_stream_iter)

        t = TickEvent()
        t.full_symbol = 'PLACEHOLDER'       # place holders
        t.timestamp = index

        return t
