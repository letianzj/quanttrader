#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from datetime import datetime

import numpy as np
import pandas as pd
import ta
import ta.momentum

from quanttrader.data.tick_event import TickType
from quanttrader.order.order_event import OrderEvent
from quanttrader.order.order_type import OrderType
from quanttrader.strategy.strategy_base import StrategyBase

_logger = logging.getLogger("qtlive")


class ActiveBuySellStrengthStrategy(StrategyBase):
    """
    EMA
    """

    def __init__(self):
        super(ActiveBuySellStrengthStrategy, self).__init__()
        today = datetime.today()
        # midnight = today.replace(hour=0, minute=0, second=0, microsecond=0)
        self.start_time = today.replace(
            hour=9, minute=0, second=0, microsecond=0
        )  # 9:00 to start initiation
        self.end_time = today.replace(hour=16, minute=15, second=0, microsecond=0)
        minutes = int(
            (self.end_time - self.start_time).seconds / 60
        )  # start_time is always positive even if start_time - end_time
        # 6.5*60 = 390
        self.df_bar = pd.DataFrame(
            index=range(minutes),
            columns=["Open", "High", "Low", "Close", "Volume"],
        )  # filled with
        self.df_bar_idx = -1

        self.current_pos = 0
        self.n_rsi = 14
        self.last_bid_price = np.NaN
        self.last_ask_price = np.NaN
        self.active_buy_size = 0
        self.active_sell_size = 0
        self.strength_abs_threshold = 200
        self.stength_threshold1 = 0.05
        self.stength_threshold2 = 0.10
        _logger.info("ActiveBuySellStrengthStrategy initiated")

    def on_tick(self, tick_event):
        super().on_tick(tick_event)  # extra mtm calc

        k = tick_event
        if k.tick_type == TickType.BID:
            self.last_bid_price = k.bid_price_L1
            return

        if k.tick_type == TickType.ASK:
            self.last_ask_price = k.ask_price_L1
            return

        if self.last_bid_price >= self.last_ask_price:
            _logger.info(
                f"ActiveBuySellStrengthStrategy: can bid greater than ask {self.last_bid_price}, {self.last_ask_price}"
            )
            return

        if k.timestamp < self.start_time:
            return

        if k.timestamp >= self.end_time:  # don't add to new bar
            return

        minutes = int((k.timestamp - self.start_time).seconds / 60)  # int(0.9) = 0

        if minutes == self.df_bar_idx:  # same bar
            self.df_bar["High"].iloc[minutes] = max(
                self.df_bar["High"].iloc[minutes], k.price
            )
            self.df_bar["Low"].iloc[minutes] = min(
                self.df_bar["Low"].iloc[minutes], k.price
            )
            self.df_bar["Close"].iloc[minutes] = k.price
            self.df_bar["Volume"].iloc[minutes] += k.size
        else:  # new bar
            self.df_bar["Open"].iloc[minutes] = k.price
            self.df_bar["High"].iloc[minutes] = k.price
            self.df_bar["Low"].iloc[minutes] = k.price
            self.df_bar["Close"].iloc[minutes] = k.price
            self.df_bar["Volume"].iloc[minutes] = k.size
            self.df_bar_idx = minutes

        if k.price <= self.last_bid_price:
            self.active_sell_size += k.size
        elif k.price >= self.last_ask_price:
            self.active_buy_size += k.size
        # else:
        # _logger.info(f'ActiveBuySellStrengthStrategy: {self.last_bid_price}, {self.last_ask_price}, {k.price}')
        # self.active_buy_size += k.size / 2
        # self.active_sell_size += k.size / 2

        df1 = self.df_bar["Close"].dropna()

        if df1.shape[0] < self.n_rsi:
            _logger.info(
                f"ActiveBuySellStrengthStrategy wait for enough bars, {df1.shape[0]} / {self.n_rsi}"
            )
            return

        if (
            abs(self.active_sell_size - self.active_buy_size)
            < self.strength_abs_threshold
        ):
            _logger.info(
                f"ActiveBuySellStrengthStrategy not enough strength divergence, {self.active_buy_size}, {self.active_sell_size}"
            )
            return

        rsi = ta.momentum.rsi(df1, self.n_rsi).iloc[
            -1
        ]  # talib actually calculates rolling SMA; not as efficient
        ratio = self.active_buy_size / self.active_sell_size

        if (ratio > (1 + self.stength_threshold1)) & (rsi < 0.7):
            if self.current_pos <= 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = 1 - self.current_pos
                _logger.info(
                    f"ActiveBuySellStrengthStrategy long order placed, on tick time {k.timestamp}, current size {self.current_pos}, order size {o.order_size}, {self.active_buy_size}, {self.active_sell_size}, {rsi}"
                )
                self.current_pos = 1
                self.place_order(o)
        elif (ratio < (1 - self.stength_threshold1)) & (rsi > 0.3):
            if self.current_pos >= 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = -1 - self.current_pos
                _logger.info(
                    f"ActiveBuySellStrengthStrategy short order placed, on tick time {k.timestamp}, current size {self.current_pos}, order size {o.order_size}, {self.active_buy_size}, {self.active_sell_size}, {rsi}"
                )
                self.current_pos = -1
                self.place_order(o)
