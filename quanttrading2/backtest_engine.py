#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
from datetime import datetime, date
import logging

from .event import EventType
from .event.backtest_event_engine import BacktestEventEngine
from .data.backtest_data_feed import BacktestDataFeed
from .data.data_board import DataBoard
from .brokerage.backtest_brokerage import BacktestBrokerage
from .position.position_manager import PositionManager
from .performance.performance_manager import PerformanceManager
from .risk.risk_manager import PassThroughRiskManager
from .strategy import StrategyBase


_logger = logging.getLogger(__name__)


class BacktestEngine(object):
    """
    Event driven backtest engine
    """
    def __init__(self, start_date=None, end_date=None):
        self._current_time = None
        self._start_date = start_date
        self._end_date = end_date
        self._data_feed = BacktestDataFeed(self._start_date, self._end_date)
        self._data_board = DataBoard()
        self._performance_manager = PerformanceManager()
        self._position_manager = PositionManager()
        self._risk_manager = PassThroughRiskManager()
        self._strategy = None

    def set_capital(self, capital):
        self._position_manager.set_capital(capital)

    def set_strategy(self, strategy):
        self._strategy = strategy

    def set_dvp(self, df_dvp):
        self._performance_manager.set_dvp(df_dvp)
        self._position_manager.set_dvp(df_dvp)

    def add_data(self, data_key, data_source, watch=True):
        """
        Add data for backtest
        :param data_key: AAPL or CL
        :param data_source:  dataframe, datetimeindex
        :param watch: track position or not
        :return:
        """
        self._data_feed.set_data_source(data_source)
        self._data_board.initialize_hist_data(data_key, data_source)
        if watch:
            self._performance_manager.add_watch(data_key, data_source)

    def _setup(self):
        ## 1. data_feed
        self._data_feed.subscribe_market_data()

        ## 2. event engine
        self._events_engine = BacktestEventEngine(self._data_feed)

        ## 3. brokerage
        self._backtest_brokerage = BacktestBrokerage(
            self._events_engine, self._data_board
        )

        ## 4. set strategy
        self._strategy.on_init(self._events_engine, self._data_board)
        self._strategy.on_start()

        ## 5. performance manager and portfolio manager
        self._performance_manager.reset()
        self._position_manager.reset()

        ## 5. trade recorder
        #self._trade_recorder = ExampleTradeRecorder(output_dir)

        ## 6. wire up event handlers
        self._events_engine.register_handler(EventType.TICK, self._tick_event_handler)
        self._events_engine.register_handler(EventType.ORDER, self._order_event_handler)
        self._events_engine.register_handler(EventType.FILL, self._fill_event_handler)

    # ------------------------------------ private functions -----------------------------#
    def _tick_event_handler(self, tick_event):
        self._current_time = tick_event.timestamp

        # performance update goes before position updates because it updates previous day performance
        self._performance_manager.update_performance(self._current_time, self._position_manager, self._data_board)
        self._position_manager.mark_to_market(self._current_time, tick_event.full_symbol, tick_event.price, self._data_board)
        self._data_board.on_tick(tick_event)
        self._strategy.on_tick(tick_event)

    def _order_event_handler(self, order_event):
        self._backtest_brokerage.place_order(order_event)

    def _fill_event_handler(self, fill_event):
        self._position_manager.on_fill(fill_event)
        self._performance_manager.on_fill(fill_event)

    # -------------------------------- end of private functions -----------------------------#

    # -------------------------------------- public functions -------------------------------#
    def run(self, tear_sheet=True):
        """
        Run backtest
        """
        self._setup()
        self._events_engine.run()
        # explicitly update last day/time
        self._performance_manager.update_performance(self._current_time, self._position_manager, self._data_board)

        return self._performance_manager._equity, self._performance_manager._df_positions, self._performance_manager._df_trades

    # ------------------------------- end of public functions -----------------------------#
