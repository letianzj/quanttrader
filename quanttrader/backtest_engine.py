#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from typing import Any, Tuple

import pandas as pd

from .brokerage.backtest_brokerage import BacktestBrokerage
from .data.backtest_data_feed import BacktestDataFeed
from .data.data_board import DataBoard
from .data.tick_event import TickEvent
from .event.backtest_event_engine import BacktestEventEngine
from .event.event import EventType
from .order.fill_event import FillEvent
from .order.order_event import OrderEvent
from .order.order_manager import OrderManager
from .performance.performance_manager import PerformanceManager
from .position.position_manager import PositionManager
from .risk.risk_manager import PassThroughRiskManager
from .risk.risk_manager_base import RiskManagerBase
from .strategy.strategy_base import StrategyBase
from .strategy.strategy_manager import StrategyManager

_logger = logging.getLogger(__name__)


__all__ = ["BacktestEngine"]


class BacktestEngine(object):
    """
    Event driven backtest engine
    """

    def __init__(self, start_date: datetime, end_date: datetime) -> None:
        self._current_time: pd.Timestamp = pd.Timestamp(0)
        self._start_date: datetime = start_date
        self._end_date: datetime = end_date
        self.config: dict[str, Any] = dict()
        self.config["strategy"] = (
            {}
        )  # to be consistent with live; in backtest, strategy is set outside
        self.instrument_meta: dict[str, dict[str, Any]] = (
            {}
        )  # one copy of meta dict shared across program
        self._data_feed: BacktestDataFeed = BacktestDataFeed(
            self._start_date, self._end_date
        )
        self._data_board: DataBoard = DataBoard()
        self._performance_manager: PerformanceManager = PerformanceManager(
            self.instrument_meta
        )  # send dict pointer
        self._position_manager: PositionManager = PositionManager("Global")
        self._position_manager.set_instrument_meta(self.instrument_meta)
        self._order_manager: OrderManager = OrderManager("Global")
        self._events_engine: BacktestEventEngine = BacktestEventEngine(self._data_feed)
        self._backtest_brokerage: BacktestBrokerage = BacktestBrokerage(
            self._events_engine, self._data_board
        )
        self._risk_manager: RiskManagerBase = PassThroughRiskManager()
        self._strategy_manager = StrategyManager(
            self.config,
            self._backtest_brokerage,
            self._order_manager,
            self._position_manager,
            self._risk_manager,
            self._data_board,
            self.instrument_meta,
        )
        self._strategy: StrategyBase = StrategyBase()

    def set_instrument_meta(self, instrument_meta: dict[str, dict[str, Any]]) -> None:
        self.instrument_meta.update(instrument_meta)

    def set_capital(self, capital: float) -> None:
        """
        set capital to the global position manager
        """
        self._position_manager.set_capital(capital)

    def set_strategy(self, strategy: StrategyBase) -> None:
        self._strategy = strategy

    def add_data(
        self, data_key: str, data_source: pd.DataFrame, watch: bool = True
    ) -> None:
        """
        Add data for backtest
        :param data_key: AAPL or CL
        :param data_source:  dataframe, datetimeindex
        :param watch: track position or not
        :return:
        """
        if data_key not in self.instrument_meta.keys():
            keys = data_key.split(" ")
            # find first digit position
            for i, c in enumerate(keys[0]):
                if c.isdigit():
                    break
                if i < len(keys[0]):
                    sym_root = keys[0][: i - 1]
                    if sym_root in self.instrument_meta.keys():
                        self.instrument_meta[data_key] = self.instrument_meta[sym_root]

        self._data_feed.set_data_source(data_source)  # get iter(datetimeindex)
        self._data_board.initialize_hist_data(data_key, data_source)
        if watch:
            self._performance_manager.add_watch(data_key, data_source)

    def _setup(self) -> None:
        """
        Tis needs to be run after strategy and data are loaded
        because it subscribes to market data
        """
        ## 1. data_feed
        self._data_feed.subscribe_market_data("ALL")

        ## 4. set strategy
        self._strategy.active = True
        self._strategy_manager.load_strategy({self._strategy.name: self._strategy})

        ## 5. global performance manager and portfolio manager
        self._performance_manager.reset()
        self._position_manager.reset()

        ## 5. trade recorder
        # self._trade_recorder = ExampleTradeRecorder(output_dir)

        ## 6. wire up event handlers
        self._events_engine.register_handler(EventType.TICK, self._tick_event_handler)
        # to be consistent with current live, order is placed directly; this accepts other status like status, fill, cancel
        self._events_engine.register_handler(EventType.ORDER, self._order_event_handler)
        self._events_engine.register_handler(EventType.FILL, self._fill_event_handler)

    # ------------------------------------ private functions -----------------------------#
    def _tick_event_handler(self, tick_event: TickEvent) -> None:
        self._current_time = tick_event.timestamp

        # performance update goes before position and databoard updates because it updates previous day performance
        # it can't update today because orders haven't been filled yet.
        self._performance_manager.update_performance(
            self._current_time, self._position_manager, self._data_board
        )
        self._position_manager.mark_to_market(
            tick_event.timestamp,
            tick_event.full_symbol,
            tick_event.price,
            self._data_board,
        )
        self._strategy.on_tick(
            tick_event
        )  # plus strategy.position_manager market to marekt
        # data_baord update after strategy, so it still holds price of last tick; for position MtM
        # strategy uses tick.price for current price; and use data_board.last_price for previous price
        # for backtest, this is PLACEHOLDER based on timestamp.
        # strategy pull directly from data_board hist_data for current_price; and data_board.last_price for previous price
        self._data_board.on_tick(tick_event)
        # check standing orders, after databoard is updated
        self._backtest_brokerage.on_tick(tick_event)

    def _order_event_handler(self, order_event: OrderEvent) -> None:
        """
        acknowledge order
        """
        # self._backtest_brokerage.place_order(order_event)
        self._order_manager.on_order_status(order_event)
        self._strategy.on_order_status(order_event)

    def _fill_event_handler(self, fill_event: FillEvent) -> None:
        self._order_manager.on_fill(fill_event)
        self._position_manager.on_fill(fill_event)
        self._performance_manager.on_fill(fill_event)
        self._strategy.on_fill(fill_event)

    # -------------------------------- end of private functions -----------------------------#
    def run(self) -> Tuple[pd.Series, pd.DataFrame, pd.DataFrame]:
        """
        Run backtest
        """
        self._setup()

        self._events_engine.run()
        # explicitly update last day/time
        self._performance_manager.update_performance(
            self._current_time, self._position_manager, self._data_board
        )

        return (
            self._performance_manager._equity,
            self._performance_manager._df_positions,
            self._performance_manager._df_trades,
        )
