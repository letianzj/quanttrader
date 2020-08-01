#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import re
import matplotlib.pyplot as plt


class PerformanceManager(object):
    """
    https://www.quantopian.com/docs/api-reference/pyfolio-api-reference
    Record equity, positions, and trades in accordance to pyfolio format
    First date will be the first data start date
    """
    def __init__(self, fvp=None):
        self._symbols = []
        self._df_fvp = pd.DataFrame(columns=['dvp'])

        self._equity = None
        self._df_positions = None
        self._df_trades = None

    def add_watch(self, data_key, data):
        if 'Close' in data.columns:
            self._symbols.append(data_key)
        else:
            self._symbols.extend(data.columns)

    def set_dvp(self, df_dvp=None):
        self._df_fvp = df_dvp

    #  or each sid
    def reset(self):
        self._realized_pnl = 0.0
        self._unrealized_pnl = 0.0

        self._equity = pd.Series()      # equity line
        self._equity.name = 'total'

        self._df_positions = pd.DataFrame(columns=self._symbols + ['cash'])
        self._df_trades = pd.DataFrame(columns=['amount', 'price', 'symbol'])

    def on_fill(self, fill_event):
        # self._df_trades.loc[fill_event.timestamp] = [fill_event.fill_size, fill_event.fill_price, fill_event.full_symbol]
        self._df_trades = self._df_trades.append(pd.DataFrame(
            {'amount': [fill_event.fill_size], 'price': [fill_event.fill_price], 'symbol': [fill_event.full_symbol]},
            index=[fill_event.fill_time]))

    def update_performance(self, current_time, position_manager, data_board):
        if self._equity.empty:
            self._equity[current_time] = 0.0
            return

        # on a new time/date, calculate the performances for previous time/date
        if current_time != self._equity.index[-1]:
            performance_time = self._equity.index[-1]
        else:
            # When a new data date comes in, it calcuates performances for the previous day
            # This leaves the last date not updated.
            # So we call the update explicitly
            performance_time = current_time

        equity = 0.0
        self._df_positions.loc[performance_time] = [0] * len(self._df_positions.columns)
        for sym, pos in position_manager.positions.items():
            multiplier = 1
            try:
                multiplier = self._df_fvp.loc[sym, 'dvp']
            except:
                pass

            # data_board hasn't been updated yet
            equity += pos.size * data_board.get_last_price(sym) * multiplier
            self._df_positions.loc[performance_time, sym] = pos.size * data_board.get_last_price(sym) * multiplier

        self._df_positions.loc[performance_time, 'cash'] = position_manager.cash
        self._equity[performance_time] = equity + position_manager.cash
        self._df_positions.loc[performance_time, 'total'] = self._equity[performance_time]

        if performance_time != current_time:     # not final day
            self._equity[current_time] = 0.0
        else:  # final day, re-arrange column order
            self._df_positions = self._df_positions[self._symbols + ['cash']]
