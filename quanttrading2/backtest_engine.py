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
from .order.order_manager import OrderManager
from .performance.performance_manager import PerformanceManager
from .risk.risk_manager import PassThroughRiskManager
from .strategy import StrategyManager

_logger = logging.getLogger(__name__)


class BacktestEngine(object):
    """
    Event driven backtest engine
    """
    def __init__(self, start_date=None, end_date=None):
        self._current_time = None
        self._start_date = start_date
        self._end_date = end_date
        self.config = dict()
        self.multiplier_dict = {}              # one copy of multiplier dict shared across program
        self._data_feed = BacktestDataFeed(self._start_date, self._end_date)
        self._data_board = DataBoard()
        self._performance_manager = PerformanceManager(self.multiplier_dict) # send dict pointer
        self._position_manager = PositionManager()
        self._position_manager.set_multiplier(self.multiplier_dict)
        self._order_manager = OrderManager()
        self._events_engine = BacktestEventEngine(self._data_feed)
        self._backtest_brokerage = BacktestBrokerage(self._events_engine, self._data_board)
        self._risk_manager = PassThroughRiskManager()
        self._strategy_manager = StrategyManager(self.config, self._backtest_brokerage, self._order_manager, self._position_manager, self._risk_manager, self._data_board, self.multiplier_dict)
        self._strategy = None

    def set_multiplier(self, multiplier_dict):
        self.multiplier_dict.update(multiplier_dict)

    def set_capital(self, capital):
        """
        set capital to the global position manager
        """
        self._position_manager.set_capital(capital)

    def set_strategy(self, strategy):
        self._strategy = strategy

    def add_data(self, data_key, data_source, watch=True):
        """
        Add data for backtest
        :param data_key: AAPL or CL; if it is followed by number, assumed to be multiplier
        :param data_source:  dataframe, datetimeindex
        :param watch: track position or not
        :return:
        """
        keys = data_key.split(' ')
        if keys[-1].isdigit():       # multiplier
            data_key = ' '.join(keys[:-1])
            self.multiplier_dict[data_key] = int(keys[-1])

        self._data_feed.set_data_source(data_source)          # get iter(datetimeindex)
        self._data_board.initialize_hist_data(data_key, data_source)
        if watch:
            self._performance_manager.add_watch(data_key, data_source)

    def _setup(self):
        """
        Tis needs to be run after strategy and data are loaded
        because it subscribes to market data
        """
        ## 1. data_feed
        self._data_feed.subscribe_market_data()

        ## 4. set strategy
        self._strategy.active = True
        self._strategy_manager.load_strategy({self._strategy.name: self._strategy})

        ## 5. global performance manager and portfolio manager
        self._performance_manager.reset()
        self._position_manager.reset()

        ## 5. trade recorder
        #self._trade_recorder = ExampleTradeRecorder(output_dir)

        ## 6. wire up event handlers
        self._events_engine.register_handler(EventType.TICK, self._tick_event_handler)
        # to be consistent with current live, order is placed directly; this accepts other status like status, fill, cancel
        self._events_engine.register_handler(EventType.ORDER, self._order_event_handler)
        self._events_engine.register_handler(EventType.FILL, self._fill_event_handler)

    # ------------------------------------ private functions -----------------------------#
    def _tick_event_handler(self, tick_event):
        self._current_time = tick_event.timestamp

        # performance update goes before position and databoard updates because it updates previous day performance
        # it can't update today because orders haven't been filled yet.
        self._performance_manager.update_performance(self._current_time, self._position_manager, self._data_board)
        self._position_manager.mark_to_market(tick_event.timestamp, tick_event.full_symbol, tick_event.price, self._data_board)
        self._strategy.on_tick(tick_event)        # plus strategy.position_manager market to marekt
        # data_baord update after strategy, so it still holds price of last tick; for position MtM
        # strategy uses tick.price for current price; and use data_board.last_price for previous price
        # for backtest, this is PLACEHOLDER based on timestamp.
        # strategy pull directly from data_board hist_data for current_price; and data_board.last_price for previous price
        self._data_board.on_tick(tick_event)
        # check standing orders, after databoard is updated
        self._backtest_brokerage.on_tick(tick_event)

    def _order_event_handler(self, order_event):
        """
        acknowledge order
        """
        # self._backtest_brokerage.place_order(order_event)
        self._order_manager.on_order_status(order_event)
        self._strategy.on_order_status(order_event)
        pass

    def _fill_event_handler(self, fill_event):
        self._order_manager.on_fill(fill_event)
        self._position_manager.on_fill(fill_event)
        self._performance_manager.on_fill(fill_event)
        self._strategy.on_fill(fill_event)

    # -------------------------------- end of private functions -----------------------------#
    def run(self):
        """
        Run backtest
        """
        self._setup()

        self._events_engine.run()
        # explicitly update last day/time
        self._performance_manager.update_performance(self._current_time, self._position_manager, self._data_board)

        return self._performance_manager._equity, self._performance_manager._df_positions, self._performance_manager._df_trades
