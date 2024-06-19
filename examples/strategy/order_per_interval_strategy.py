#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from quanttrader.data.tick_event import TickType
from quanttrader.order.order_event import OrderEvent
from quanttrader.order.order_type import OrderType
from quanttrader.strategy.strategy_base import StrategyBase

_logger = logging.getLogger("qtlive")


class OrderPerIntervalStrategy(StrategyBase):
    """
    buy on the first tick then hold to the end
    """

    def __init__(self):
        super(OrderPerIntervalStrategy, self).__init__()
        self.ticks = 0
        self.tick_trigger_threshold = 2000
        self.direction = 1
        _logger.info("OrderPerIntervalStrategy initiated")

    def on_tick(self, tick_event):
        k = tick_event
        super().on_tick(k)  # extra mtm calc

        if k.tick_type != TickType.TRADE:
            print(k, f"{self.ticks}/{self.tick_trigger_threshold}")
        if self.ticks > self.tick_trigger_threshold:
            o1 = OrderEvent()
            o1.full_symbol = self.symbols[0]
            o1.order_type = OrderType.MARKET
            o1.order_size = self.direction

            o2 = OrderEvent()
            o2.full_symbol = self.symbols[1]
            o2.order_type = OrderType.MARKET
            o2.order_size = self.direction

            self.direction = 1 if self.direction == -1 else -1
            _logger.info(f"OrderPerIntervalStrategy order placed on ticks {self.ticks}")
            self.place_order(o1)
            self.place_order(o2)
            self.ticks = 0
        else:
            self.ticks += 1
