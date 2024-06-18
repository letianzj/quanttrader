#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Iterator

import pandas as pd

from .data_feed_base import DataFeedBase
from .tick_event import TickEvent

__all__ = ["BacktestDataFeed"]


class BacktestDataFeed(DataFeedBase):
    """
    BacktestDataFeed uses PLACEHOLDER to stream_next;
    actual data comes from data_board.get_hist_price
    This is an easy way to handle multiple sources
    """

    def __init__(
        self,
        start_date: pd.Timestamp | None = None,
        end_date: pd.Timestamp | None = None,
    ) -> None:
        self._end_date: pd.Timestamp = end_date
        self._start_date: pd.Timestamp = start_date
        self._data_stream: pd.Index = None
        self._data_stream_iter: Iterator[pd.Timestamp] = iter([])

    def set_data_source(self, data: pd.DataFrame) -> None:
        if self._data_stream is None:
            self._data_stream = data.index
        else:
            self._data_stream = self._data_stream.join(
                data.index, how="outer", sort=True
            )

    def subscribe_market_data(self, symbols: str | list[str]) -> None:
        _ = symbols
        if self._start_date:
            if self._end_date:
                self._data_stream = self._data_stream[
                    (self._data_stream >= self._start_date)
                    & (self._data_stream <= self._end_date)
                ]
            else:
                self._data_stream = self._data_stream[
                    self._data_stream >= self._start_date
                ]

        self._data_stream_iter = self._data_stream.__iter__()

    def unsubscribe_market_data(self, symbols: str | list[str]) -> None:
        _ = symbols

    def stream_next(self) -> TickEvent:
        """
        Place the next TickEvent into the event queue.
        """
        index = next(self._data_stream_iter)

        t = TickEvent()
        t.full_symbol = "PLACEHOLDER"  # place holders
        t.timestamp = index

        return t
