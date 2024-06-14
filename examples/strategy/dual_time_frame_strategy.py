#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from quanttrader.data.tick_event import TickType
from quanttrader.order.order_event import OrderEvent
from quanttrader.order.order_type import OrderType
from quanttrader.strategy.strategy_base import StrategyBase

_logger = logging.getLogger("qtlive")


class DualTimeFrameStrategy(StrategyBase):
    """
    Dual time frame: 5sec and 15 sec SMA.
    No overnight positions

    Chapter Two Multiple Time Frame Momentum Strategy
    Miner, Robert C. High probability trading strategies: Entry to exit tactics for the forex, futures, and stock markets. Vol. 328. John Wiley & Sons, 2008.
    * Trade in the direction of the larger time frame momentum.
    * Execute the trade following the smaller time frame momentum reversals.
    """

    def __init__(self) -> None:
        super(DualTimeFrameStrategy, self).__init__()
        self.bar_start_time: str = "08:30:00"  # bar starts earlier
        self.bar_end_time: str = "16:15:00"  # 16:15; instead, stocks close at 16:00
        self.start_time: str = "09:30:00"  # trading starts
        self.end_time: str = "16:14:58"  # 16:14:58
        self.current_pos: int = 0  # flat
        self.lookback_5sec: int = 20  # lookback period
        self.lookback_15sec: int = 20  # lookback period
        self.sma_5sec: float = 0.0  # sma
        self.sma_15sec: float = 0.0  # sma

        self.sidx_5sec: int = 0  # df start idx
        self.eidx_5sec: int = 0  # df end idx
        self.nbars_5sec: int = 0  # current bars
        self.sidx_15sec: int = 0  # df start idx
        self.eidx_15sec: int = 0  # df end idx
        self.nbars_15sec: int = 0  # current bars

        self.df_5sec_bar = pd.DataFrame()
        self.df_15sec_bar = pd.DataFrame()
        self.midx_5sec = 0
        self.midx_15sec = 0

        _logger.info("DualTimeFrameStrategy initiated")

    def set_params(self, params_dict=None):
        super(DualTimeFrameStrategy, self).set_params(params_dict)

        today = datetime.today()
        self.bar_start_time = today.replace(
            hour=int(self.bar_start_time[:2]),
            minute=int(self.bar_start_time[3:5]),
            second=int(self.bar_start_time[6:]),
            microsecond=0,
        )
        self.bar_end_time = today.replace(
            hour=int(self.bar_end_time[:2]),
            minute=int(self.bar_end_time[3:5]),
            second=int(self.bar_end_time[6:]),
            microsecond=0,
        )
        self.start_time = today.replace(
            hour=int(self.start_time[:2]),
            minute=int(self.start_time[3:5]),
            second=int(self.start_time[6:]),
            microsecond=0,
        )
        self.end_time = today.replace(
            hour=int(self.end_time[:2]),
            minute=int(self.end_time[3:5]),
            second=int(self.end_time[6:]),
            microsecond=0,
        )

        dt_5sec = np.arange(0, (self.bar_end_time - self.bar_start_time).seconds, 5)
        idx_5sec = self.bar_start_time + dt_5sec * timedelta(seconds=1)
        self.df_5sec_bar = pd.DataFrame(
            np.zeros_like(
                idx_5sec,
                dtype=[
                    ("Open", np.float64),
                    ("High", np.float64),
                    ("Low", np.float64),
                    ("Close", np.float64),
                    ("Volume", np.uint8),
                ],
            )
        )
        self.df_5sec_bar.index = idx_5sec

        dt_15sec = np.arange(0, (self.bar_end_time - self.bar_start_time).seconds, 15)
        idx_15sec = self.bar_start_time + dt_15sec * timedelta(seconds=1)
        self.df_15sec_bar = pd.DataFrame(
            np.zeros_like(
                idx_15sec,
                dtype=[
                    ("Open", np.float64),
                    ("High", np.float64),
                    ("Low", np.float64),
                    ("Close", np.float64),
                    ("Volume", np.uint8),
                ],
            )
        )
        self.df_15sec_bar.index = idx_15sec

        self.midx_5sec = len(idx_5sec) - 1  # max idx
        self.midx_15sec = len(idx_15sec) - 1  # max idx

    def on_tick(self, tick_event):
        """
        Essentially it does two things:
        1. Aggregate 5sec and 15 sec bars. This is more efficient than subscribing to IB real time bars
            * avoid transmitting a series of bars
            * avoid memory allocaiton of a series of bars
        2. Implement df.dropna().mean() or talib.SMA(df.dropna(), n).iloc[-1] in a more efficient way
            * avoid dropna empty bars for less traded symbols.
            * avoid averaging loop
        """
        k = tick_event
        super().on_tick(k)  # extra mtm calc

        if k.tick_type != TickType.TRADE:  # only trace trade bars
            return

        if k.timestamp < self.bar_start_time:  # bar_start_time < start_time
            return

        if k.timestamp > self.end_time:  # flat and shutdown
            if self.current_pos != 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = -self.current_pos
                _logger.info(
                    f"EOD flat position, current size {self.current_pos}, order size {o.order_size}"
                )
                self.current_pos = 0
                self.place_order(o)
            return

        # --- 5sec bar ---#
        while (self.eidx_5sec < self.midx_5sec) and (
            self.df_5sec_bar.index[self.eidx_5sec + 1] < k.timestamp
        ):
            self.eidx_5sec += 1

        if self.df_5sec_bar.Open[self.eidx_5sec] == 0.0:  # new bar
            self.df_5sec_bar.iloc[self.eidx_5sec, 0] = k.price  # O
            self.df_5sec_bar.iloc[self.eidx_5sec, 1] = k.price  # H
            self.df_5sec_bar.iloc[self.eidx_5sec, 2] = k.price  # L
            self.df_5sec_bar.iloc[self.eidx_5sec, 3] = k.price  # C
            self.df_5sec_bar.iloc[self.eidx_5sec, 4] = k.size  # V
            self.nbars_5sec += 1
            _logger.info(
                f"New 5sec bar {self.df_5sec_bar.index[self.eidx_5sec]} | {k.timestamp}"
            )

            if self.nbars_5sec <= self.lookback_5sec:  # not enough bars
                self.sma_5sec += k.price / self.lookback_5sec
            else:  # enough bars
                while self.df_5sec_bar.Close[self.sidx_5sec] == 0.0:
                    self.sidx_5sec += 1
                self.sma_5sec = (
                    self.sma_5sec
                    + (k.price - self.df_5sec_bar.Close[self.sidx_5sec])
                    / self.lookback_5sec
                )
                self.sidx_5sec += 1
        else:  # same bar
            self.df_5sec_bar.iloc[self.eidx_5sec, 1] = max(
                self.df_5sec_bar.High[self.eidx_5sec], k.price
            )
            self.df_5sec_bar.iloc[self.eidx_5sec, 2] = min(
                self.df_5sec_bar.Low[self.eidx_5sec], k.price
            )
            self.df_5sec_bar.iloc[self.eidx_5sec, 3] = k.price
            self.df_5sec_bar.iloc[self.eidx_5sec, 4] = (
                k.size + self.df_5sec_bar.Volume[self.eidx_5sec]
            )
            _logger.info(
                f"existing 5sec bar {self.df_5sec_bar.index[self.eidx_5sec]} | {k.timestamp}"
            )

        # --- 15sec bar ---#
        while (self.eidx_15sec < self.midx_15sec) and (
            self.df_15sec_bar.index[self.eidx_15sec + 1] < k.timestamp
        ):
            self.eidx_15sec += 1

        if self.df_15sec_bar.Open[self.eidx_15sec] == 0.0:  # new bar
            self.df_15sec_bar.iloc[self.eidx_15sec, 0] = k.price  # O
            self.df_15sec_bar.iloc[self.eidx_15sec, 1] = k.price  # H
            self.df_15sec_bar.iloc[self.eidx_15sec, 2] = k.price  # L
            self.df_15sec_bar.iloc[self.eidx_15sec, 3] = k.price  # C
            self.df_15sec_bar.iloc[self.eidx_15sec, 4] = k.size  # V
            self.nbars_15sec += 1
            _logger.info(
                f"New 15sec bar {self.df_15sec_bar.index[self.eidx_15sec]} | {k.timestamp}"
            )

            if self.nbars_15sec <= self.lookback_15sec:  # not enough bars
                self.sma_15sec += k.price / self.lookback_15sec
            else:  # enough bars
                while self.df_15sec_bar.Close[self.sidx_15sec] == 0.0:
                    self.sidx_15sec += 1
                self.sma_15sec = (
                    self.sma_15sec
                    + (k.price - self.df_15sec_bar.Close[self.sidx_15sec])
                    / self.lookback_15sec
                )
                self.sidx_15sec += 1

            # --- on 15sec bar ---#
            if (
                (self.nbars_5sec >= self.lookback_5sec)
                and (self.nbars_15sec >= self.lookback_15sec)
                and (k.timestamp > self.start_time)
            ):
                self.dual_time_frame_rule(k.timestamp)
            else:
                _logger.info(
                    f"DualTimeFrameStrategy wait for enough bars, { self.nbars_5sec } / { self.nbars_15sec }"
                )
        else:  # same bar
            self.df_15sec_bar.iloc[self.eidx_15sec, 1] = max(
                self.df_15sec_bar.High[self.eidx_15sec], k.price
            )
            self.df_15sec_bar.iloc[self.eidx_15sec, 2] = min(
                self.df_15sec_bar.Low[self.eidx_15sec], k.price
            )
            self.df_15sec_bar.iloc[self.eidx_15sec, 3] = k.price
            self.df_15sec_bar.iloc[self.eidx_15sec, 4] = (
                k.size + self.df_15sec_bar.Volume[self.eidx_15sec]
            )
            _logger.info(
                f"Existing 15sec bar {self.df_15sec_bar.index[self.eidx_15sec]} | {k.timestamp}"
            )

    def dual_time_frame_rule(self, t):
        if self.sma_5sec > self.sma_15sec:
            if self.current_pos <= 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = 1 - self.current_pos
                _logger.info(
                    f"DualTimeFrameStrategy long order placed, on tick time {t}, current size {self.current_pos}, order size {o.order_size}, ma_fast {self.sma_5sec}, ma_slow {self.sma_15sec}"
                )
                self.current_pos = 1
                self.place_order(o)
            else:
                _logger.info(
                    f"DualTimeFrameStrategy keeps long, on tick time {t}, current size {self.current_pos}, ma_fast {self.sma_5sec}, ma_slow {self.sma_15sec}"
                )
        elif self.sma_5sec < self.sma_15sec:
            if self.current_pos >= 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = -1 - self.current_pos
                _logger.info(
                    f"DualTimeFrameStrategy short order placed, on tick time {t}, current size {self.current_pos}, order size {o.order_size}, ma_fast {self.sma_5sec}, ma_slow {self.sma_15sec}"
                )
                self.current_pos = -1
                self.place_order(o)
            else:
                _logger.info(
                    f"DualTimeFrameStrategy keeps short, on tick time {t}, current size {self.current_pos}, ma_fast {self.sma_5sec}, ma_slow {self.sma_15sec}"
                )
