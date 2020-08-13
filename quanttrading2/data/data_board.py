#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pandas as pd


class DataBoard(object):
    """
    Data tracker that holds current market data info
    """
    def __init__(self):
        self._hist_data_dict = {}
        self._current_data_dict = {}
        self._current_time = None
        self._PLACEHOLDER = 'PLACEHOLDER'
        self._data_index = None

    def initialize_hist_data(self, data_key, data):
        self._hist_data_dict[data_key] = data

    def on_tick(self, tick):
        if tick.full_symbol not in self._current_data_dict:
            self._current_data_dict[tick.full_symbol] = None

        self._current_data_dict[tick.full_symbol] = tick
        self._current_time = tick.timestamp

    def get_last_price(self, symbol):
        """
        Returns the most recent price for a given ticker
        """
        if symbol in self._current_data_dict.keys():
            return self._current_data_dict[symbol].price
        elif symbol in self._hist_data_dict.keys():
            return self._hist_data_dict[symbol].loc[self._current_time, 'Close']
        elif symbol[:2] in self._hist_data_dict.keys():       # FUT root symbol e.g. CL
            return self._hist_data_dict[symbol[:2]].loc[self._current_time, symbol]      # column series up to timestamp inclusive
        else:
            return None

    def get_last_timestamp(self, symbol):
        """
        Returns the most recent timestamp for a given ticker
        """
        if symbol in self._current_data_dict.keys():
            return self._current_data_dict[symbol].timestamp
        elif self._PLACEHOLDER in self._current_data_dict:
            return self._current_data_dict[self._PLACEHOLDER].timestamp
        else:
            return self._current_time

    def get_current_timestamp(self):
        return self._current_time

    def get_hist_price(self, symbol, timestamp):
        if symbol in self._hist_data_dict.keys():
            return self._hist_data_dict[symbol][:timestamp]  # up to timestamp inclusive
        elif symbol[:2] in self._hist_data_dict.keys():       # FUT root symbol e.g. CL
            return self._hist_data_dict[symbol[:2]][symbol][:timestamp]      # column series up to timestamp inclusive
        else:
            return None

    def get_hist_sym_time_index(self, symbol):
        """
        retrieve historical calendar for a symbol
        this is not look forwward
        """
        if symbol in self._hist_data_dict.keys():
            return self._hist_data_dict[symbol].index
        elif symbol[:2] in self._hist_data_dict.keys():       # FUT root symbol e.g. CL
            return self._hist_data_dict[symbol[:2]].index
        else:
            return None

    def get_hist_time_index(self):
        """
        retrieve historical calendar
        this is not look forwward
        """
        if self._data_index is None:
            for k, v in self._hist_data_dict.items():
                if self._data_index is None:
                    self._data_index = v.index
                else:
                    self._data_index_data_stream = self._data_index.join(v.index, how='outer', sort=True)

        return self._data_index