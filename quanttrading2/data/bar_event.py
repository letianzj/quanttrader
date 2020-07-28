#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
from ..event.event import *

class BarEvent(Event):
    """
    Bar event, aggregated from TickEvent
    """
    def __init__(self):
        """
        Initialises bar
        """
        self.event_type = EventType.BAR
        self.bar_start_time = pd.Timestamp('1970-01-01', tz='UTC')
        self.interval = 86400       # 1day in secs = 24hrs * 60min * 60sec
        self.full_symbol = ''
        self.open_price = 0.0
        self.high_price = 0.0
        self.low_price = 0.0
        self.close_price = 0.0
        self.adj_close_price = 0.0
        self.volume = 0

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
                str(self.close_price), str(self.adj_close_price), str(self.volume)
            )