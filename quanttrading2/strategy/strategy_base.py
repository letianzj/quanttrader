#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod
from datetime import datetime
from ..order.order_event import OrderEvent
from ..order.order_type import OrderType
from ..order import OrderManager
from ..position import PositionManager

class StrategyBase(metaclass=ABCMeta):
    """
    Base strategy class
    """
    def __init__(self):
        """
        initialize trategy
        :param symbols:
        :param events_engine:backtest_event_engine or live_event engine that provides queue_.put()
        """
        self.id = -1                    # id
        self.name = ''                  # name
        self.symbols = []               # symbols interested
        self.strategy_manager = None     # to place order through strategy_manager
        self._data_board = None         # to get current data
        self._position_manager = PositionManager()     # track local positions and cash
        self._order_manager = OrderManager()        # manage lcoal (standing) orders and fills
        self.initialized = False
        self.active = False

    def set_capital(self, capital):
        self._position_manager.set_capital(capital)

    def set_symbols(self, symbols):
        self.symbols = symbols

    def set_params(self, params_dict=None):
        if params_dict is not None:
            for key, value in params_dict.items():
                try:
                    self.__setattr__(key, value)
                except:
                    pass

    def on_init(self, strategy_manager, data_board=None, multiplier_dict={}):
        self.strategy_manager = strategy_manager
        self._data_board = data_board

        self._position_manager.set_fvp(multiplier_dict)
        self._position_manager.reset()

        self.initialized = True

    def on_start(self):
        self.active = True

    def on_stop(self):
        self.active = False

    def on_tick(self, tick_event):
        """
        Respond to tick
        """
        # for live trading, turn off p&l tick
        # for back test; this is PLACEHOLDER, do not need to tick neither
        self._position_manager.mark_to_market(tick_event.timestamp, tick_event.full_symbol, tick_event.price, self._data_board)
        pass

    def on_order_status(self, order_event):
        """
        on order acknowledged
        :return:
        """
        #raise NotImplementedError("Should implement on_order_status()")
        pass

    def on_cancel(self):
        """
        on order canceled
        :return:
        """
        pass

    def on_fill(self, fill_event):
        """
        on order filled
        :return:
        """
        self._position_manager.on_fill(fill_event)

    def place_order(self, o):
        """
        :param o:
        :return:
        """
        o.source = self.id         # identify source
        o.create_time = datetime.now().strftime('%H:%M:%S.%f')
        if (self.active):
            self.strategy_manager.place_order(o)

    def adjust_position(self, sym, size_from, size_to):
        """
        :param sym:
        :param size_from:
        :param size_to:
        :return:
        """
        o = OrderEvent()
        o.full_symbol = sym
        o.order_type = OrderType.MARKET
        o.order_size = size_to - size_from
        o.source = self.id  # identify source
        o.create_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        if (self.active):
            #self.strategy_manager.place_order(o)
            self.strategy_manager.put(o)

    def cancel_order(self, oid):
        pass

    def cancel_all(self):
        """
        cancel all standing orders from this strategy id
        :return:
        """
        pass


class Strategies(StrategyBase):
    """
    Strategies is a collection of strategy
    Usage e.g.: strategy = Strategies(strategyA, DisplayStrategy())
    """
    def __init__(self, *strategies):
        self._strategies_collection = strategies

    def on_tick(self, event):
        for strategy in self._strategies_collection:
            strategy.on_tick(event)
