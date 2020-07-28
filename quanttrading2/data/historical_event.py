#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
from ..event.event import *

class HistoricalEvent(Event):
    """
    Bar event, aggregated from TickEvent
    """
    def __init__(self):
        """
        Initialises bar
        """
        self.event_type = EventType.HISTORICAL
        self.bar_start_time = pd.Timestamp('1970-01-01', tz='UTC')
        self.interval = 86400       # 1day in secs = 24hrs * 60min * 60sec
        self.full_symbol = ''
        self.open_price = 0.0
        self.high_price = 0.0
        self.low_price = 0.0
        self.close_price = 0.0
        self.weighted_average_price = 0.0
        self.volume = 0
        self.count = 0           # number of trades in this bar

    def bar_end_time(self):
        # To be consistent with (daily) bar backtest, bar_end_time is set to be bar_start_time
        return self.bar_start_time
        # return self.bar_start_time + pd.Timedelta(seconds=self.interval)

    def __str__(self):
        return "Time: %s, Symbol: %s, Interval: %s, " \
            "Open: %s, High: %s, Low: %s, Close: %s, " \
            "Adj Close: %s, Volume: %s" % (
                str(self.bar_start_time), str(self.full_symbol), str(self.interval),
                str(self.open_price), str(self.high_price), str(self.low_price),
                str(self.close_price), str(self.weighted_average_price), str(self.volume)
            )

    def deserialize(self, msg):
        v = msg.split('|')
        self.full_symbol = v[1]
        self.bar_start_time = v[2]          # string
        self.open_price = float(v[3])
        self.high_price = float(v[4])
        self.low_price = float(v[5])
        self.close_price = float(v[6])
        self.volume = int(v[7])
        self.count = int(v[8])
        self.weighted_average_price = float(v[9])