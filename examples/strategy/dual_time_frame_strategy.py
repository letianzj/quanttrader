#!/usr/bin/env python
# -*- coding: utf-8 -*-
from quanttrader.strategy.strategy_base import StrategyBase
from quanttrader.data.tick_event import TickType
from quanttrader.order.order_event import OrderEvent
from quanttrader.order.order_status import OrderStatus
from quanttrader.order.order_type import OrderType
from datetime import datetime, timedelta
import numpy as np
import talib
import pandas as pd
import logging

_logger = logging.getLogger('qtlive')


class DualTimeFrameStrategy(StrategyBase):
    """
    Dual time frame: 5sec and 15 sec SMA.
    No overnight positions

    Chapter Two Multiple Time Frame Momentum Strategy
    Miner, Robert C. High probability trading strategies: Entry to exit tactics for the forex, futures, and stock markets. Vol. 328. John Wiley & Sons, 2008.
    * Trade in the direction of the larger time frame momentum.
    * Execute the trade following the smaller time frame momentum reversals.
    """
    def __init__(self):
        super(DualTimeFrameStrategy, self).__init__()
        today = datetime.today()
        self.start_time = today.replace(hour=9, minute=30, second=0, microsecond=0)        # 9:30
        self.end_time = today.replace(hour=16, minute=14, second=58, microsecond=0)        # shutdown at 16:14:58

        dt_5sec = np.arange(0, 6.5*60*60+15*60, 5)    # 5sec bar, instead, stocks close at 16:00, or 6.5*60*60 = 23400
        idx_5sec = self.start_time + dt_5sec * timedelta(seconds=1)
        self.df_5sec_bar = pd.DataFrame(np.zeros_like(idx_5sec, dtype=[('Open', np.float64), ('High', np.float64), ('Low', np.float64), ('Close', np.float64), ('Volume', np.uint8)]))
        self.df_5sec_bar.index = idx_5sec

        dt_15sec = np.arange(0, 6.5*60*60+15*60, 15)    # 15sec bar, instead, stocks close at 16:00, or 6.5*60*60 = 23400
        idx_15sec = self.start_time + dt_15sec * timedelta(seconds=1)
        self.df_15sec_bar = pd.DataFrame(np.zeros_like(idx_15sec, dtype=[('Open', np.float64), ('High', np.float64), ('Low', np.float64), ('Close', np.float64), ('Volume', np.uint8)]))
        self.df_15sec_bar.index = idx_15sec

        self.current_pos = 0               # flat
        self.lookback_5sec = 20            # lookback period
        self.lookback_15sec = 20           # lookback period
        self.sma_5sec = 0.0         # sma
        self.sma_15sec = 0.0        # sma

        self.sidx_5sec = 0         # df start idx
        self.eidx_5sec = 0         # df end idx
        self.midx_5sec = len(idx_5sec) - 1            # max idx
        self.nbars_5sec = 0            # current bars
        self.sidx_15sec = 0        # df start idx
        self.eidx_15sec = 0        # df end idx
        self.midx_15sec = len(idx_15sec) - 1        # max idx
        self.nbars_15sec = 0           # current bars

        _logger.info('DualTimeFrameStrategy initiated')


    def on_tick(self, k):
        """
        Essentially it does two things:
        1. Aggregate 5sec and 15 sec bars. This is more efficient than subscribing to IB real time bars
            * avoid transmitting a series of bars
            * avoid memory allocaiton of a series of bars
        2. Implement df.dropna().mean() or talib.SMA(df.dropna(), n).iloc[-1] in a more efficient way
            * avoid dropna empty bars for less traded symbols.
            * avoid average loop
        """
        super().on_tick(k)     # extra mtm calc

        if k.tick_type != TickType.TRADE:        # only trace trade bars
            return

        if k.timestamp < self.start_time:
            return

        if k.timestamp > self.end_time:          # flat and shutdown
            if self.current_pos != 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = -self.current_pos
                _logger.info(f'EOD flat position, current size {self.current_pos}, order size {o.order_size}')
                self.current_pos = 0
                self.place_order(o)
            return
        
        #--- 5sec bar ---#
        while (self.eidx_5sec < self.midx_5sec) and (self.df_5sec_bar.idx[self.eidx_5sec+1] < k.timestamp):
            self.eidx_5sec += 1
        
        if self.df_5sec_bar.Open[self.eidx_5sec] == 0.0:       # new bar
            self.df_5sec_bar.Open[self.eidx_5sec] = k.price
            self.df_5sec_bar.High[self.eidx_5sec] = k.price
            self.df_5sec_bar.Low[self.eidx_5sec] = k.price
            self.df_5sec_bar.Close[self.eidx_5sec] = k.price
            self.nbars_5sec += 1
            
            if self.nbars_5sec <= self.lookback_5sec:         # not enough bars
                self.sma_5sec += k.price/self.lookback_5sec
            else:        # enough bars
                while self.df_5sec_bar.Close[self.sidx_5sec] == 0.0:
                    self.sidx_5sec += 1
                self.sma_5sec = self.sma_5sec + (k.price - self.df_5sec_bar.Close[self.sidx_5sec]) /self.lookback_5sec
                self.sidx_5sec += 1
        else:  # same bar
            self.df_5sec_bar.High[self.eidx_5sec] = max(self.df_5sec_bar.High[self.eidx_5sec], k.price)
            self.df_5sec_bar.Low[self.eidx_5sec] = min(self.df_5sec_bar.Low[self.eidx_5sec], k.price)
            self.df_5sec_bar.Close[self.eidx_5sec] = k.price

        #--- 15sec bar ---#
        while (self.eidx_15sec < self.midx_15sec) and (self.df_15sec_bar.idx[self.eidx_15sec+1] < k.timestamp):
            self.eidx_15sec += 1
        
        if self.df_15sec_bar.Open[self.eidx_15sec] == 0.0:       # new bar
            self.df_15sec_bar.Open[self.eidx_15sec] = k.price
            self.df_15sec_bar.High[self.eidx_15sec] = k.price
            self.df_15sec_bar.Low[self.eidx_15sec] = k.price
            self.df_15sec_bar.Close[self.eidx_15sec] = k.price
            self.nbars_15sec += 1
            
            if self.nbars_15sec <= self.lookback_15sec:         # not enough bars
                self.sma_15sec += k.price/self.lookback_15sec
            else:        # enough bars
                while self.df_15sec_bar.Close[self.sidx_15sec] == 0.0:
                    self.sidx_15sec += 1
                self.sma_15sec = self.sma_15sec + (k.price - self.df_15sec_bar.Close[self.sidx_15sec]) /self.lookback_15sec
                self.sidx_15sec += 1

            #--- on 15sec bar ---#
            if (self.nbars_5sec >= self.lookback_5sec) and (self.nbars_15sec >= self.lookback_15sec):
                self.dual_time_frame_rule(k.timestamp)
            else:
                _logger.info(f'DualTimeFrameStrategy wait for enough bars, { self.nbars_5sec } / { self.nbars_15sec }')

        else:  # same bar
            self.df_15sec_bar.High[self.eidx_15sec] = max(self.df_15sec_bar.High[self.eidx_15sec], k.price)
            self.df_15sec_bar.Low[self.eidx_15sec] = min(self.df_15sec_bar.Low[self.eidx_15sec], k.price)
            self.df_15sec_bar.Close[self.eidx_15sec] = k.price

    def dual_time_frame_rule(self, t):
        if self.sma_5sec > self.sma_15sec:
            if self.current_pos <= 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = 1 - self.current_pos
                _logger.info(f'DualTimeFrameStrategy long order placed, on tick time {t}, current size {self.current_pos}, order size {o.order_size}, ma_fast {self.sma_5sec}, ma_slow {self.sma_15sec}')
                self.current_pos = 1
                self.place_order(o)
        elif self.sma_5sec < self.sma_15sec:
            if self.current_pos >= 0:
                o = OrderEvent()
                o.full_symbol = self.symbols[0]
                o.order_type = OrderType.MARKET
                o.order_size = -1 - self.current_pos
                _logger.info(f'DualTimeFrameStrategy short order placed, on tick time {t}, current size {self.current_pos}, order size {o.order_size}, ma_fast {self.sma_5sec}, ma_slow {self.sma_15sec}')
                self.current_pos = -1
                self.place_order(o)
