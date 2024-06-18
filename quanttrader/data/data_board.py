#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd

from .tick_event import TickEvent

__all__ = ["DataBoard"]


class DataBoard(object):
    """
    Data tracker that holds current market data info
    """

    def __init__(self) -> None:
        self._hist_data_dict: dict[str, pd.DataFrame] = {}
        self._current_data_dict: dict[str, TickEvent] = {}
        self._current_time: pd.Timestamp | None = None
        self._PLACEHOLDER: str = "PLACEHOLDER"
        self._data_index: pd.Index = None

    def initialize_hist_data(self, data_key: str, data: pd.DataFrame) -> None:
        self._hist_data_dict[data_key] = data

    def on_tick(self, tick: TickEvent) -> None:
        self._current_data_dict[tick.full_symbol] = tick
        self._current_time = tick.timestamp

    def get_last_price(self, symbol: str) -> float:
        """
        Returns last price for a given ticker
        because self._current_time has not been updated by current tick
        """
        return self.get_current_price(symbol, self._current_time)

    def get_current_price(self, symbol: str, timestamp: pd.Timestamp) -> float:
        """
        Returns the most recent price for a given ticker
        based on current timestamp updated outside of data_board
        """
        if symbol in self._current_data_dict.keys():
            return self._current_data_dict[symbol].price
        elif symbol in self._hist_data_dict.keys():
            return self._hist_data_dict[symbol].loc[timestamp, "Close"]  # type: ignore
        elif (
            symbol[:-5] in self._hist_data_dict.keys()
        ):  # FUT root symbol e.g. CL, -5 assumes CLZ2020
            # column series up to timestamp inclusive
            return self._hist_data_dict[symbol[:-5]].loc[timestamp, symbol]  # type: ignore
        else:
            return 0.0

    def get_last_timestamp(self, symbol: str) -> pd.Timestamp:
        """
        Returns the most recent timestamp for a given ticker
        """
        if symbol in self._current_data_dict.keys():
            return self._current_data_dict[symbol].timestamp
        elif self._PLACEHOLDER in self._current_data_dict:
            return self._current_data_dict[self._PLACEHOLDER].timestamp
        else:
            return self._current_time

    def get_current_timestamp(self) -> pd.Timestamp:
        return self._current_time

    def get_hist_price(self, symbol: str, timestamp: pd.Timestamp) -> pd.DataFrame:
        if symbol in self._hist_data_dict.keys():
            # up to timestamp inclusive
            return self._hist_data_dict[symbol][:timestamp]  # type: ignore
        elif symbol[:-5] in self._hist_data_dict.keys():  # FUT root symbol e.g. CL
            # column series up to timestamp inclusive
            return self._hist_data_dict[symbol[:-5]][symbol][:timestamp]  # type: ignore
        else:
            raise ValueError(symbol)

    def get_hist_sym_time_index(self, symbol: str) -> pd.Index | None:
        """
        retrieve historical calendar for a symbol
        this is not look forwward
        """
        if symbol in self._hist_data_dict.keys():
            return self._hist_data_dict[symbol].index
        elif symbol[:-5] in self._hist_data_dict.keys():  # FUT root symbol e.g. CL
            return self._hist_data_dict[symbol[:-5]].index
        else:
            return None

    def get_hist_time_index(self) -> pd.Index:
        """
        retrieve historical calendar
        this is not look forwward
        """
        if self._data_index is None:
            for _, v in self._hist_data_dict.items():
                self._data_index = (
                    self._data_index.join(v.index, how="outer", sort=True)  # type: ignore
                    if self._data_index is not None
                    else v.index.copy()
                )
        return self._data_index
