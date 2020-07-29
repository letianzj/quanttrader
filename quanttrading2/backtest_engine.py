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
from .position.portfolio_manager import PortfolioManager
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

        self._initial_cash = 1_000.0
        self._symbols = None
        self._benchmark = None
        self._params = None
        self._strategy = None
        self._output_dir = None

        self._batch_tag = 0
        self._multiplier = 1
        self._fvp_file = None

    def set_cash(self, cash):
        self._initial_cash = cash

    def set_symbols(self, symbols):
        self._symbols = symbols

    def set_benchmark(self, benchmark):
        self._benchmark = benchmark

    def set_strategy(self, strategy):
        self._strategy = strategy

    def set_params(self, params):
        self._parmas = params

    def set_output_dir(self, output_dir):
        self._output_dir = output_dir

    def add_data(self, data_key, data_source):
        self._data_feed.set_data_source(data_source)
        self._data_board.initialize_hist_data(data_key, data_source)

    def _setup(self):
        ## 1. data_feed
        self._data_feed.subscribe_market_data()         # not symbols_all

        ## 2. event engine
        self._events_engine = BacktestEventEngine(self._data_feed)

        ## 3. brokerage
        self._backtest_brokerage = BacktestBrokerage(
            self._events_engine, self._data_board
        )

        ## 4. portfolio_manager
        self._portfolio_manager = PortfolioManager(self._initial_cash)

        ## 5. performance_manager
        self._performance_manager = PerformanceManager(self._symbols, self._benchmark)

        ## 6. risk_manager
        self._risk_manager = PassThroughRiskManager()

        ## 7. load all strategies
        self._strategy.set_symbols(self._symbols)
        self._strategy.set_capital(self._initial_cash)
        self._strategy.on_init(self._events_engine, self._data_board, self._params)
        self._strategy.on_start()

        ## 8. trade recorder
        #self._trade_recorder = ExampleTradeRecorder(output_dir)

        ## 9. wire up event handlers
        self._events_engine.register_handler(EventType.TICK, self._tick_event_handler)
        self._events_engine.register_handler(EventType.BAR, self._bar_event_handler)
        self._events_engine.register_handler(EventType.ORDER, self._order_event_handler)
        self._events_engine.register_handler(EventType.FILL, self._fill_event_handler)

    # ------------------------------------ private functions -----------------------------#
    def _tick_event_handler(self, tick_event):
        self._current_time = tick_event.timestamp

        # performance update goes before position updates because it updates previous day performance
        self._performance_manager.update_performance(self._current_time, self._portfolio_manager, self._data_board)
        self._portfolio_manager.mark_to_market(self._current_time, tick_event.full_symbol, tick_event.price, self._data_board)
        self._data_board.on_tick(tick_event)
        self._strategy.on_tick(tick_event)

    def _bar_event_handler(self, bar_event):
        self._current_time = bar_event.bar_end_time()

        # performance update goes before position updates because it updates previous day
        self._performance_manager.update_performance(self._current_time, self._portfolio_manager, self._data_board)
        self._portfolio_manager.mark_to_market(self._current_time, bar_event.full_symbol, bar_event.adj_close_price, self._data_board)
        self._data_board.on_bar(bar_event)
        self._strategy.on_bar(bar_event)

    def _order_event_handler(self, order_event):
        self._backtest_brokerage.place_order(order_event)

    def _fill_event_handler(self, fill_event):
        self._portfolio_manager.on_fill(fill_event)
        self._performance_manager.on_fill(fill_event)

    # -------------------------------- end of private functions -----------------------------#

    # -------------------------------------- public functions -------------------------------#
    def run(self, tear_sheet=True):
        """
        Run backtest
        """
        self._setup()
        self._events_engine.run()
        self._performance_manager.update_final_performance(self._current_time, self._portfolio_manager, self._data_board)
        self._performance_manager.save_results(self._output_dir)

        return self._performance_manager.caculate_performance(tear_sheet)

    # ------------------------------- end of public functions -----------------------------#
