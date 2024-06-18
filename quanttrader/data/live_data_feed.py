#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import queue
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from ..data.bar_event import BarEvent
from .data_feed_base import DataFeedBase

_logger = logging.getLogger(__name__)


__all__ = ["LiveDataFeed"]


class LiveDataFeed(DataFeedBase):
    """
    Live DataFeed class
    gets data from online sources instead of from IB
    """

    def __init__(
        self,
        events_queue: queue.Queue,
        init_tickers: list[str] = [],
        start_date: datetime = datetime.today() - timedelta(days=365),
        end_date: datetime = datetime.today(),
        calc_adj_returns: bool = False,
    ) -> None:
        """
        Takes the CSV directory, the events queue and a possible
        list of initial ticker symbols then creates an (optional)
        list of ticker subscriptions and associated prices.
        """
        self.events_queue = events_queue
        self.continue_backtest: bool = True
        self.tickers: dict[str, dict[str, float]] = {}
        self.tickers_data: dict[str, Any] = {}
        self.start_date = start_date
        self.end_date = end_date

        if init_tickers is not None:
            for ticker in init_tickers:
                self.subscribe_ticker(ticker)

        self.bar_stream = self._merge_sort_ticker_data()
        self.calc_adj_returns = calc_adj_returns
        if self.calc_adj_returns:
            self.adj_close_returns: list[float] = []

    def _open_ticker_price_online(self, ticker: str) -> None:
        """
        Opens the CSV online from yahoo finance, then store in a dictionary.
        """
        # data = quandl.get(
        #     "wiki/" + ticker,
        #     start_date=self.start_date,
        #     end_date=self.end_date,
        #     authtoken="your_token",
        # )
        # self.tickers_data[ticker] = data
        # self.tickers_data[ticker]["Ticker"] = ticker
        pass

    def _merge_sort_ticker_data(self) -> pd.DataFrame:
        """
        Concatenates all of the separate equities DataFrames
        into a single DataFrame that is time ordered, allowing tick
        data events to be added to the queue in a chronological fashion.

        Note that this is an idealised situation, utilised solely for
        backtesting. In live trading ticks may arrive "out of order".
        """
        df = pd.concat(self.tickers_data.values()).sort_index()
        start = None
        end = None
        if self.start_date is not None:
            start = df.index.searchsorted(self.start_date)
        if self.end_date is not None:
            end = df.index.searchsorted(self.end_date)
        # Determine how to slice
        if start is None and end is None:
            return df.iterrows()
        elif start is not None and end is None:
            return df.ix[start:].iterrows()
        elif start is None and end is not None:
            return df.ix[:end].iterrows()
        else:
            return df.ix[start:end].iterrows()

    def subscribe_ticker(self, ticker: str) -> None:
        """
        Subscribes the price handler to a new ticker symbol.
        """
        if ticker not in self.tickers:
            try:
                self._open_ticker_price_online(ticker)
                dft = self.tickers_data[ticker]
                row0 = dft.iloc[0]

                close = row0["Close"]
                adj_close = row0["Adj. Close"]

                ticker_prices = {
                    "close": close,
                    "adj_close": adj_close,
                    "timestamp": dft.index[0],
                }
                self.tickers[ticker] = ticker_prices
            except OSError:
                _logger.error(
                    f"Could not subscribe ticker {ticker} as no data CSV found for pricing."
                )
        else:
            _logger.error(
                f"Could not subscribe ticker {ticker} as is already subscribed."
            )

    def _create_event(
        self, index: int, period: int, ticker: str, row: dict[str, int | float]
    ) -> BarEvent:
        """
        Obtain all elements of the bar from a row of dataframe
        and return a BarEvent
        """
        open_price = row["Open"]
        high_price = row["High"]
        low_price = row["Low"]
        close_price = row["Close"]
        adj_close_price = row["Adj. Close"]
        volume = int(row["Volume"])
        bev = BarEvent()
        # bev.bar_start_time = index
        bev.full_symbol = ticker
        bev.interval = period
        bev.open_price = open_price
        bev.high_price = high_price
        bev.low_price = low_price
        bev.close_price = close_price
        bev.adj_close_price = adj_close_price
        bev.volume = volume
        return bev

    def _store_event(self, event: BarEvent) -> None:
        """
        Store price event for closing price and adjusted closing price
        """
        ticker = event.full_symbol
        # If the calc_adj_returns flag is True, then calculate
        # and store the full list of adjusted closing price
        # percentage returns in a list
        # TODO: Make this faster
        if self.calc_adj_returns:
            prev_adj_close = self.tickers[ticker]["adj_close"]
            cur_adj_close = event.adj_close_price
            self.tickers[ticker]["adj_close_ret"] = cur_adj_close / prev_adj_close - 1.0
            self.adj_close_returns.append(self.tickers[ticker]["adj_close_ret"])
        self.tickers[ticker]["close"] = event.close_price
        self.tickers[ticker]["adj_close"] = event.adj_close_price
        self.tickers[ticker]["timestamp"] = event.bar_start_time

    def stream_next(self) -> BarEvent:
        """
        Place the next BarEvent onto the event queue.
        """
        try:
            index, row = next(self.bar_stream)
        except StopIteration:
            self.continue_backtest = False
            return BarEvent()
        # Obtain all elements of the bar from the dataframe
        ticker = row["Ticker"]
        period = 86400  # Seconds in a day
        # Create the tick event for the queue
        bev = self._create_event(index, period, ticker, row)
        # Store event
        self._store_event(bev)
        # Send event to queue
        self.events_queue.put(bev)
        return bev
