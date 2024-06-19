#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from abc import ABCMeta
from datetime import datetime
from typing import Any

import pandas as pd

from ..data.data_board import DataBoard
from ..data.tick_event import TickEvent
from ..order.fill_event import FillEvent
from ..order.order_event import OrderEvent
from ..order.order_manager import OrderManager
from ..order.order_type import OrderType
from ..position.position_manager import PositionManager

_logger = logging.getLogger(__name__)


__all__ = ["StrategyBase"]


class StrategyBase(metaclass=ABCMeta):
    """
    Base strategy class
    """

    def __init__(self) -> None:
        """
        initialize trategy
        :param symbols:
        :param events_engine:backtest_event_engine or live_event engine that provides queue_.put()
        """
        self.id: int = -1  # id
        self.name: str = ""  # name
        self.symbols: list[str] = []  # symbols interested
        # self.strategy_manager = None  # to place order through strategy_manager
        self._data_board: DataBoard = DataBoard()  # to get current data
        self._position_manager: PositionManager = PositionManager(
            self.name
        )  # track local positions and cash
        self._order_manager: OrderManager = OrderManager(
            self.name
        )  # manage local (standing) orders and fills

        self.active: bool = False
        self.initialized: bool = False

    def set_capital(self, capital: float) -> None:
        self._position_manager.set_capital(capital)

    def set_symbols(self, symbols: list[str]) -> None:
        self.symbols = symbols

    def set_name(self, name: str) -> None:
        self.name = name
        self._position_manager.name = name
        self._order_manager.name = name

    def set_params(self, params_dict: dict[str, float]) -> None:
        if len(params_dict) > 0:
            for key, value in params_dict.items():
                try:
                    self.__setattr__(key, value)
                except:
                    pass

    def on_init(
        self,
        strategy_manager: Any,  # type: ignore
        data_board: DataBoard,
        instrument_meta: dict[str, dict[str, Any]],
    ) -> None:

        self.strategy_manager = strategy_manager
        self._data_board = data_board
        self._position_manager.set_instrument_meta(instrument_meta)
        self._position_manager.reset()
        self.initialized = True

    def on_start(self) -> None:
        self.active = True

    def on_stop(self) -> None:
        self.active = False

    def on_tick(self, tick_event: TickEvent) -> None:
        """
        Respond to tick
        """
        # for live trading, turn off p&l tick by not calling super.on_tick()
        # for backtest, call super().on_tick() if need to track positions or npv or cash
        self._position_manager.mark_to_market(
            tick_event.timestamp,
            tick_event.full_symbol,
            tick_event.price,
            self._data_board,
        )

    def on_order_status(self, order_event: OrderEvent) -> None:
        """
        on order acknowledged
        :return:
        """
        # raise NotImplementedError("Should implement on_order_status()")
        self._order_manager.on_order_status(order_event)

    def on_fill(self, fill_event: FillEvent) -> None:
        """
        on order filled
        derived class call super().on_fill first
        """
        self._position_manager.on_fill(fill_event)
        self._order_manager.on_fill(fill_event)

    def place_order(self, o: OrderEvent) -> None:
        """
        expect user to set up order type, order size and order price
        """
        o.source = self.id  # identify source
        if o.create_time is None:
            # .strftime("%Y-%m-%d %H:%M:%S.%f")
            o.create_time = pd.Timestamp.now()
        if self.active and self.strategy_manager:
            self.strategy_manager.place_order(o)

    def adjust_position(
        self,
        sym: str,
        size_from: int,
        size_to: int,
        timestamp: pd.Timestamp = None,
    ) -> None:
        """
        use market order to adjust position
        :param sym:
        :param size_from:
        :param size_to:
        :param timestamp: used by backtest broker to get price on timestamp
        :return:
        """
        if size_from == size_to:
            return
        o = OrderEvent()
        o.full_symbol = sym
        o.order_type = OrderType.MARKET
        o.order_size = size_to - size_from
        if timestamp:
            o.create_time = timestamp
        self.place_order(o)

    def cancel_order(self, oid: int) -> None:
        if oid in self._order_manager.standing_order_set:
            self._order_manager.on_cancel(oid)
            if self.strategy_manager:
                self.strategy_manager.cancel_order(oid)
        else:
            _logger.error(f"Not a standing order to be cancelled, sid {id}, oid {oid}")

    def cancel_all(self) -> None:
        """
        cancel all standing orders from this strategy id
        :return:
        """
        for oid in self._order_manager.standing_order_set:
            self._order_manager.on_cancel(oid)
            if self.strategy_manager:
                self.strategy_manager.cancel_order(oid)
