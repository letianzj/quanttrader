#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pandas as pd
from datetime import datetime, time, timedelta

from .data_feed_base import DataFeedBase
from .bar_event import BarEvent

class BacktestDataFeedLocalSingleSymbol(DataFeedBase):
    """
    BacktestDataFeed retrieves historical data; which is pulled out by backtest_event_engine.
    """
    def __init__(
        self, hist_dir=None, start_date=None, end_date=None
    ):
        """
        events_queue receives feed of tick/bar events
        """
        self._hist_dir = hist_dir

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
    def _retrieve_historical_data(self, symbol):
        """
        Retrieve historical data from web
        """
        hist_file = os.path.join(self._hist_dir, "%s.csv" % symbol)

        data = pd.read_csv(
            hist_file, header=0, parse_dates=True, sep=',',
            index_col=0
            #, names=("DateTime", "Open", "High", "Low", "Close", "Volume")
        )

        data.index.name = 'DateTime'
        data.rename(columns = {'Adj Close':'AdjClose'}, inplace = True)

        # start_idx = data.index.searchsorted(self._start_date)
        # end_idx = data.index.searchsorted(self._end_date)
        # data = data.iloc[start_idx:end_idx]       # might not be inclusive
        # data = data.iloc[data.index.indexer_between_time(time(9, 30, 0), time(16, 0, 0), True, True)]       # 9:30am to 16:00pm

        data.loc[:, 'FullSymbol'] = symbol
        self._hist_data[symbol] = data[self._start_date:self._end_date]  # start/end date inclusive
        # self._hist_data[symbol].loc[:, "FullSymbol"] = symbol         # attach symbol to data (add column); it will be merged into _data_stream

    def _retrieve_local_historcial_data(self, symbol):
        """ TODO """
        pass

    # -------------------------------- end of private functions -----------------------------#

    # ------------------------------------ public functions -----------------------------#
    def subscribe_market_data(self, symbols):
        cols = set()
        if symbols is not None:
            for sym in symbols:
                self._retrieve_historical_data(sym)       # retrieve historical data
                if len(cols) == 0:
                    cols = set(self._hist_data[sym].columns)
                else:
                    cols = cols.intersection(self._hist_data[sym].columns)

        # merge sort data into stream
        df = pd.DataFrame()
        for sym in self._hist_data.keys():
            df = pd.concat([df, self._hist_data[sym][list(cols)]], sort=True)
        df.sort_index()
        # df = pd.concat(self._hist_data.values(), sort=True).sort_index()
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
        b.interval = 86400-1                # daily bar in seconds; set it to 0 will do the same
        try:
            b.full_symbol = row["FullSymbol"]
            b.open_price = row["Open"]
            b.high_price = row["High"]
            b.low_price = row["Low"]
            b.close_price = row["Close"]
            b.adj_close_price = row["AdjClose"]
            try:
                b.volume = int(row["Volume"])
            except:
                b.volume = 0
        except:
            b.full_symbol = row["FullSymbol"]
            b.open_price = row["Close"]
            b.high_price = row["Close"]
            b.low_price = row["Close"]
            b.close_price = row["Close"]
            b.adj_close_price = row["Close"]
            try:
                b.volume = int(row["Volume"])
            except:
                b.volume = 0

        return b
    # ------------------------------- end of public functions -----------------------------#