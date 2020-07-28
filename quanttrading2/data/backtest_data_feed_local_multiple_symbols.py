#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pandas as pd
from datetime import datetime, date, time, timedelta
from .data_feed_base import DataFeedBase
from .bar_event import BarEvent

class BacktestDataFeedLocalMultipleSymbols(DataFeedBase):
    """
    BacktestDataFeed retrieves historical data; which is pulled out by backtest_event_engine.
    It uses PLACEHOLDER to stream_next; actual data comes from data_board.get_hist_price
    """
    def __init__(
        self, hist_dir=None, start_date=None, end_date=None
    ):
        """
        hist_dir: str
        start_date, end_date: datetime.datetime
        events_queue receives feed of tick/bar events
        """
        self._hist_dir = hist_dir

        if end_date is not None:
            self._end_date = end_date
        else:
            self._end_date = datetime.today().date()
        if start_date is not None:
            self._start_date = start_date
        else:
            self._start_date = self._end_date-timedelta(days = 365)

        self._data_stream = None

    # ------------------------------------ private functions -----------------------------#
    def _retrieve_historical_data(self, symbol):
        """
        Retrieve historical data from web
        """
        hist_file = os.path.join(self._hist_dir, "%s.csv" % symbol)

        data = pd.read_csv(hist_file, header=0, parse_dates=True, sep=',', index_col=0)
        data = data.iloc[:, 0]                       # to be dataframe

        # self._date_index = None
        # for sym in self._hist_data.keys():
        #     if self._date_index is None:
        #         self._date_index = self._hist_data[sym]['historical_prices'].index
        #     else:
        #         self._date_index = self._date_index.join(self._hist_data[sym]['historical_prices'].index, how='outer')
        # self._start_idx = self._hist_data.index.searchsorted(self._start_date)        # first after
        # self._end_idx = self._hist_data.index.searchsorted(self._end_date)            # might be len+1
        return data[self._start_date:self._end_date]           # start/end date inclusive

    def _retrieve_local_historcial_data(self, symbol):
        """ TODO """
        pass

    # -------------------------------- end of private functions -----------------------------#

    # ------------------------------------ public functions -----------------------------#
    def subscribe_market_data(self, symbols):
        df = None
        for sym in symbols:
            df_hist = self._retrieve_historical_data(sym)  # retrieve historical data
            if df is None:
                df = df_hist
            else:
                df = pd.concat([df, df_hist], axis=1, join='inner', sort=True)

        #df.dropna(axis=0, how='any', inplace=True)
        self._data_stream = df.index.__iter__()

    def unsubscribe_market_data(self, symbols):
        pass

    def stream_next(self):
        """
        Place the next BarEvent onto the event queue.
        """
        index = next(self._data_stream)

        # Obtain all elements of the bar from the dataframe
        b = BarEvent()
        b.full_symbol = 'PLACEHOLDER'       # place holders
        b.bar_start_time = index
        b.interval = 0                   # specific for daily

        return b
    # ------------------------------- end of public functions -----------------------------#