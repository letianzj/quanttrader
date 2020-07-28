#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import tushare as ts
from datetime import datetime, timedelta

from .data_feed_base import DataFeedBase
from .bar_event import BarEvent

class BacktestDataFeedTushare(DataFeedBase):
    """
    BacktestDataFeed retrieves historical data; which is pulled out by backtest_event_engine.
    """
    def __init__(
        self, start_date=None, end_date=None
    ):
        """
        events_queue receives feed of tick/bar events
        """
        if end_date is not None:
            self._end_date = end_date
        else:
            self._end_date = datetime.today()
        if start_date is not None:
            self._start_date = start_date
        else:
            self._start_date = self._end_date- timedelta(days = 365)

        self._hist_data = {}        # It holds historical data

    # ------------------------------------ private functions -----------------------------#
    def _retrieve_online_historical_data(self, symbol):
        """
        Retrieve historical data from web
        """
        data = ts.get_hist_data(symbol, start=self._start_date.strftime('%Y-%m-%d'), end=self._end_date.strftime('%Y-%m-%d'))
        data = data.sort_index()
        data.index = data.index.to_datetime()
        #data.index = data.index.tz_localize('UTC')

        self._hist_data[symbol] = data
        self._hist_data[symbol]["FullSymbol"] = symbol         # attach symbol to data; it will be merged into _data_stream

    def _retrieve_local_historcial_data(self, symbol):
        """ TODO """
        pass

    # -------------------------------- end of private functions -----------------------------#

    # ------------------------------------ public functions -----------------------------#
    def subscribe_market_data(self, symbols):
        if symbols is not None:
            for sym in symbols:
                self._retrieve_online_historical_data(sym)       # retrieve historical data

        # merge sort data into stream
        df = pd.concat(self._hist_data.values()).sort_index()
        self._data_stream = df.iterrows()

    def unsubscribe_market_data(self, symbols):
        pass

    def stream_next(self):
        """
        Place the next BarEvent onto the event queue.
        """
        index, row = next(self._data_stream)

        # Obtain all elements of the bar from the dataframe
        b = BarEvent()
        b.bar_start_time = index
        b.interval = 86400
        b.full_symbol = row["FullSymbol"]
        b.open_price = row["open"]
        b.high_price = row["high"]
        b.low_price = row["low"]
        b.close_price = row["close"]
        b.adj_close_price = row['close']
        b.volume = int(row["volume"])

        return b
    # ------------------------------- end of public functions -----------------------------#