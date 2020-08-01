#!/usr/bin/env python
# -*- coding: utf-8 -*-
from quanttrading2.strategy.strategy_base import StrategyBase
from quanttrading2.order.order_event import OrderEvent
from quanttrading2.order.order_type import OrderType


class OrderPerIntervalStrategy(StrategyBase):
    """
    buy on the first tick then hold to the end
    """
    def __init__(self):
        super(OrderPerIntervalStrategy, self).__init__()
        self.ticks = 0
        self.tick_trigger_threshold = 10
        self.sign = 1

    def on_tick(self, k):
        symbol = self.symbols[0]
        if k.full_symbol == symbol:
            print(k)
            if (self.ticks > self.tick_trigger_threshold):
                o = OrderEvent()
                o.full_symbol = symbol
                o.order_type = OrderType.MARKET
                o.order_size = 100 * self.sign
                print('place order')
                self.place_order(o)

                self.ticks = 0
                self.sign = self.sign * (-1)
            else:
                self.ticks += 1