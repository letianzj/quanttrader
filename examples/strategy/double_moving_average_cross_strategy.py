#!/usr/bin/env python
# -*- coding: utf-8 -*-
from quanttrader.strategy.strategy_base import StrategyBase
from quanttrader.data.tick_event import TickType
from quanttrader.order.order_event import OrderEvent
from quanttrader.order.order_status import OrderStatus
from quanttrader.order.order_type import OrderType
from datetime import datetime
import numpy as np
import talib
import pandas as pd
import logging

_logger = logging.getLogger('qtlive')


class DoubleMovingAverageCrossStrategy(StrategyBase):
    """
    EMA
    """
    def __init__(self):
        super(DoubleMovingAverageCrossStrategy, self).__init__()
        today = datetime.today()
        midnight = today.replace(hour=0, minute=0, second=0, microsecond=0)
        self.start_time = today.replace(hour=9, minute=30, second=0, microsecond=0)        # 9:00 to start initiation
        self.end_time = today.replace(hour=16, minute=0, second=0, microsecond=0)
        seconds = (self.end_time - self.start_time).seconds                 # start_time is always positive even if start_time - end_time
        # 6.5*60*60 = 23400
        self.df_bar = pd.DataFrame(index=range(seconds), columns=['Open', 'High', 'Low', 'Close', 'Volume'])     # filled with
        self.df_bar_idx = -1
        self.current_pos = 0
        self.n_fast_ma = 20
        self.n_slow_ma = 200
        _logger.info('DoubleMovingAverageCrossStrategy initiated')

    def on_tick(self, k):
        super().on_tick(k)     # extra mtm calc

        if k.tick_type != TickType.TRADE:
            return

        if k.timestamp < self.start_time:
            return

        print(k)

        if k.timestamp >= self.end_time:          # don't add to new bar
            return

        seconds =  (k.timestamp - self.start_time).seconds

        if seconds == self.df_bar_idx:          # same bar
            self.df_bar['High'].iloc[seconds] = max(self.df_bar['High'].iloc[seconds], k.price)
            self.df_bar['Low'].iloc[seconds] = min(self.df_bar['Low'].iloc[seconds],  k.price)
            self.df_bar['Close'].iloc[seconds] = k.price
            self.df_bar['Volume'].iloc[seconds] += k.size
        else:                               # new bar
            self.df_bar['Open'].iloc[seconds] = k.price
            self.df_bar['High'].iloc[seconds] = k.price
            self.df_bar['Low'].iloc[seconds] = k.price
            self.df_bar['Close'].iloc[seconds] = k.price
            self.df_bar['Volume'].iloc[seconds] = k.size
            self.df_bar_idx = seconds

        df1 = self.df_bar['Close'].dropna()

        if df1.shape[0] < self.n_slow_ma:
            _logger.info(f'DoubleMovingAverageCrossStrategy wait for enough bars, {df1.shape[0]} / {self.n_slow_ma}')
            return

        ma_fast = talib.SMA(df1, self.n_fast_ma).iloc[-1]        # talib actually calculates rolling SMA; not as efficient
        ma_slow = talib.SMA(df1, self.n_slow_ma).iloc[-1]

        if ma_fast > ma_slow:
            if self.current_pos <= 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = 1 - self.current_pos
                _logger.info(f'DoubleMovingAverageCrossStrategy long order placed, on tick time {k.timestamp}, current size {self.current_pos}, order size {o.order_size}, ma_fast {ma_fast}, ma_slow {ma_slow}')
                self.current_pos = 1
                self.place_order(o)
        elif ma_fast < ma_slow:
            if self.current_pos >= 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = -1 - self.current_pos
                _logger.info(f'DoubleMovingAverageCrossStrategy short order placed, on tick time {k.timestamp}, current size {self.current_pos}, order size {o.order_size}, ma_fast {ma_fast}, ma_slow {ma_slow}')
                self.current_pos = -1
                self.place_order(o)
