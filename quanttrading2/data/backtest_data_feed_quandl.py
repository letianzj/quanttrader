#!/usr/bin/env python
# -*- coding: utf-8 -*-
import quandl
import pandas as pd
pd.core.common.is_list_like = pd.api.types.is_list_like
import pandas_datareader.data as web
from datetime import datetime, timedelta

from .data_feed_base import DataFeedBase
from .bar_event import BarEvent

class BacktestDataFeedQuandl(DataFeedBase):
    """
    BacktestDataFeed retrieves historical data; which is pulled out by backtest_event_engine.
	data_source = 'yahoo', 'quandl'
    """
    def __init__(
        self, data_source = 'quandl',
        start_date=None, end_date=None
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

        self._data_source = data_source
        self._hist_data = {}        # It holds historical data

    # ------------------------------------ private functions -----------------------------#
    def _retrieve_online_historical_data(self, symbol):
        """
        Retrieve historical data from web
        """
        if self._data_source == 'yahoo':
            data = web.DataReader(symbol, 'yahoo', self._start_date, self._end_date)
        else:
            data = quandl.get('wiki/'+symbol, start_date=self._start_date, end_date=self._end_date, authtoken='ay68s2CUzKbVuy8GAqxj')
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
        b.open_price = row["Open"]
        b.high_price = row["High"]
        b.low_price = row["Low"]
        b.close_price = row["Close"]
        if self._data_source == 'yahoo':
            b.adj_close_price = row["Adj Close"]
        else:
            b.adj_close_price = row['Adj. Close']

        b.volume = int(row["Volume"])

        return b
    # ------------------------------- end of public functions -----------------------------#