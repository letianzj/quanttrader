#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .brokerage_base import BrokerageBase
from ..event.event import EventType
from ..order.fill_event import FillEvent
from ..order.order_event import OrderEvent
from ..order.order_status import OrderStatus


class BacktestBrokerage(BrokerageBase):
    """
    Backtest brokerage: market order will be immediately filled.
            limit/stop order will be saved to _active_orders for next tick
    """
    def __init__(self, events_engine, data_board):
        """
        Initialises the handler, setting the event queue
        as well as access to local pricing.
        """
        self._events_engine = events_engine
        self._data_board = data_board
        self._active_orders = {}

    # ------------------------------------ private functions -----------------------------#
    def _calculate_commission(self, full_symbol, fill_price, fill_size):
        # take ib commission as example
        if 'STK' in full_symbol:
            commission = max(0.005*abs(fill_size), 1)     # per share
        elif 'FUT' in full_symbol:
            commission = 2.01 * abs(fill_size)           # per contract
        elif 'OPT' in full_symbol:
            commission = max(0.7 * abs(fill_size), 1)
        elif 'CASH' in full_symbol:
            commission = max(0.000002 * abs(fill_price * fill_size), 2)
        else:
            commission = 0

        return commission

    def _cross_limit_order(self):
        pass

    def _cross_stop_order(self):
        pass

    def _cross_market_order(self):
        pass
    # -------------------------------- end of private functions -----------------------------#

    # -------------------------------------- public functions -------------------------------#
    def reset(self):
        self._active_orders.clear()

    def on_bar(self):
        pass

    def on_tick(self):
        pass

    def place_order(self, order_event):
        """
        immediate fill, no latency or slippage
        """
        # TODO: acknowledge the order
        order_event.order_status = OrderStatus.FILLED

        fill = FillEvent()
        fill.client_order_id = order_event.client_order_id
        fill.server_order_id = order_event.client_order_id
        fill.broker_order_id = order_event.client_order_id
        fill.broker_fill_id = order_event.client_order_id
        fill.fill_time = self._data_board.get_last_timestamp(order_event.full_symbol)
        fill.full_symbol = order_event.full_symbol
        fill.fill_size = order_event.order_size
        # TODO: use bid/ask to fill short/long
        fill.fill_price = self._data_board.get_last_price(order_event.full_symbol)
        fill.exchange = 'BACKTEST'
        fill.commission = self._calculate_commission(fill.full_symbol, fill.fill_price, fill.fill_size)

        self._events_engine.put(fill)

    def cancel_order(self, order_id):
        """cancel order is not supported"""
        pass

    def next_order_id(self):
        return 0
    # ------------------------------- end of public functions -----------------------------#
