#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pandas as pd
import re


class DataBoard(object):
    """
    Data tracker that holds current market data info
    """
    def __init__(self):
        self._hist_data = {}
        self._symbol_tick_dict = {}
        self._symbol_bar_dict = {}
        self._PLACEHOLDER = 'PLACEHOLDER'

    def initialize_hist_data(self, data_key, data):
        self._hist_data[data_key] = data

    def on_tick(self, tick):
        if tick.full_symbol not in self._symbol_tick_dict:
            self._symbol_tick_dict[tick.full_symbol] = None

        self._symbol_tick_dict[tick.full_symbol] = tick

    def on_bar(self, bar):
        if bar.full_symbol not in self._symbol_bar_dict:
            self._symbol_bar_dict[bar.full_symbol] = None

        self._symbol_bar_dict[bar.full_symbol] = bar

    def get_last_price(self, symbol):
        """
        Returns the most recent actual timestamp for a given ticker
        """
        if symbol in self._symbol_tick_dict:       # tick takes priority
            return self._symbol_tick_dict[symbol].price
        elif symbol in self._symbol_bar_dict:
            return self._symbol_bar_dict[symbol].adj_close_price             # TODO: switch back to close_price
        elif self._PLACEHOLDER in self._symbol_bar_dict:             # TODO: change this hack to hist price
            tmp = None
            try:
                if '|' in symbol:
                    ss = symbol.split('|')
                    match = re.match(r"([a-z ]+)([0-9]+)?", ss[0], re.I)
                    root_ticker = match.groups()[0]
                    tmp = self._hist_data[root_ticker][ss[1]].loc[self.get_last_timestamp(self._PLACEHOLDER)]
                else:
                    # date slice is <= inclusive; slice by datetime not present is allowed
                    if 'Price' in self._hist_data[symbol].columns:
                        tmp = self._hist_data[symbol].loc[self.get_last_timestamp(self._PLACEHOLDER)]['Price']
                    else: # USE Adj Close as fill price
                        tmp = self._hist_data[symbol].loc[self.get_last_timestamp(self._PLACEHOLDER)]['AdjClose']
            except:
                pass
            return tmp
        else:
            print(
                "LastPrice for ticker %s is not found" % (symbol)
            )
            return None

    def get_last_timestamp(self, symbol):
        """
        Returns the most recent actual timestamp for a given ticker
        """
        if symbol in self._symbol_tick_dict:         # tick takes priority
            return self._symbol_tick_dict[symbol].timestamp
        elif symbol in self._symbol_bar_dict:
            return self._symbol_bar_dict[symbol].bar_end_time()
        elif self._PLACEHOLDER in self._symbol_bar_dict:
            return self._symbol_bar_dict[self._PLACEHOLDER].bar_end_time()
        else:
            print(
                "Timestamp for ticker %s is not found" % (symbol)
            )
            return None

    def get_hist_price(self, symbol, timestamp):
        if '|' in symbol:
            ss = symbol.split('|')
            match = re.match(r"([a-z ]+)([0-9]+)?", ss[0], re.I)
            root_ticker = match.groups()[0]
            return self._hist_data[root_ticker][ss[1]][:timestamp]            # up to timestamp inclusive
        else:
            # date slice is <= inclusive; slice by datetime not present is allowed
            return self._hist_data[symbol][:timestamp]            # up to timestamp inclusive

    def get_hist_time_index(self, symbol):
        """
        retrieve historical calendar
        this is not look forwward
        :param symbol:
        :return:
        """
        if '|' in symbol:
            ss = symbol.split('|')
            match = re.match(r"([a-z ]+)([0-9]+)?", ss[0], re.I)
            root_ticker = match.groups()[0]
            return self._hist_data[root_ticker][ss[1]].index
        else:
            # date slice is <= inclusive; slice by datetime not present is allowed
            return self._hist_data[symbol].index