#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .brokerage_base import BrokerageBase
from ..event.event import EventType
from ..order.fill_event import FillEvent
from ..order.order_event import OrderEvent
from ..order.order_type import OrderType
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
        self._data_board = data_board              # retrieve price against order
        self.orderid = 1
        self.market_data_subscription_reverse_dict = {}      # market data subscription, to be consistent with live
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
            commission = 0.0001 * abs(fill_price * fill_size)       # assume 1bps for all other types

        return commission

    def _try_cross_order(self, order_event, current_price):
        if order_event.order_type == OrderType.MARKET:
            order_event.order_status = OrderStatus.FILLED
        # stop limit, if buy, limit price < market price < stop price;
        # if sell, limti price > market price > stop price
        # cross if opposite
        # limit: if buy, limit_price >= current_price; if sell, opposite
        elif (order_event.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]) & \
                (((order_event.order_size > 0) & (order_event.limit_price >= current_price)) |
                 ((order_event.order_size < 0)&(order_event.limit_price <= current_price))):
            order_event.order_status = OrderStatus.FILLED
        # stop: if buy, stop_price <= current_price; if sell, opposite
        elif (order_event.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]) & \
                (((order_event.order_size > 0) & (order_event.stop_price <= current_price)) |
                 ((order_event.order_size < 0) & (order_event.stop_price >= current_price))):
            order_event.order_status = OrderStatus.FILLED

    # -------------------------------- end of private functions -----------------------------#

    # -------------------------------------- public functions -------------------------------#
    def reset(self):
        self._active_orders.clear()
        self.orderid = 1

    def on_tick(self, tick_event):
        # check standing (stop) orders
        # put trigged into queue
        # and remove from standing order list
        _remaining_active_orders_id = []
        timestamp = tick_event.timestamp
        for oid, order_event in self._active_orders.items():
            # this should be after data board is updated
            # current_price = self._data_board.get_last_price(tick_event.full_symbol)      # last price is not updated yet
            current_price = self._data_board.get_hist_price(order_event.full_symbol, timestamp).iloc[-1].Close
            self._try_cross_order(order_event, current_price)

            if order_event.order_status == OrderStatus.FILLED:
                fill = FillEvent()
                fill.order_id = order_event.order_id
                fill.fill_id = order_event.order_id
                fill.fill_time = timestamp
                fill.full_symbol = order_event.full_symbol
                fill.fill_size = order_event.order_size
                # TODO: use bid/ask to fill short/long
                fill.fill_price = current_price
                fill.exchange = 'BACKTEST'
                fill.commission = self._calculate_commission(fill.full_symbol, fill.fill_price, fill.fill_size)
                self._events_engine.put(fill)
            else:
                # Trailing stop; reset stop price, use limit price as trailing amount
                # if buy, stop price drops when market price drops
                # if sell, stop price increases when market price increases
                if order_event.order_type == OrderType.TRAIING_STOP:
                    if order_event.order_size > 0:
                        order_event.stop_price = min(current_price+order_event.limit_price, order_event.stop_price)
                    else:
                        order_event.stop_price = max(current_price - order_event.limit_price, order_event.stop_price)

                _remaining_active_orders_id.append(order_event)

        self._active_orders = {k : v for k, v in self._active_orders if k in _remaining_active_orders_id}


    def place_order(self, order_event):
        """
        try immediate fill, no latency or slippage
        the alternative is to save the orders and fill on_tick
        """
        # current_price = self._data_board.get_last_price(order_event.full_symbol)      # last price is not updated yet
        timestamp = order_event.create_time
        current_price = self._data_board.get_hist_price(order_event.full_symbol, timestamp).iloc[-1].Close
        self._try_cross_order(order_event, current_price)

        if order_event.order_status == OrderStatus.FILLED:
            fill = FillEvent()
            fill.order_id = order_event.order_id
            fill.fill_id = order_event.order_id
            # fill.fill_time = self._data_board.get_last_timestamp(order_event.full_symbol)
            fill.fill_time = timestamp
            fill.full_symbol = order_event.full_symbol
            fill.fill_size = order_event.order_size
            # TODO: use bid/ask to fill short/long
            fill.fill_price = current_price
            fill.exchange = 'BACKTEST'
            fill.commission = self._calculate_commission(fill.full_symbol, fill.fill_price, fill.fill_size)

            order_event.order_status = OrderStatus.FILLED
            self._events_engine.put(order_event)
            self._events_engine.put(fill)
        else:
            order_event.order_status = OrderStatus.ACKNOWLEDGED
            self._active_orders[order_event.order_id] = order_event      # save standing orders
            self._events_engine.put(order_event)


    def cancel_order(self, order_id):
        self._active_orders = {k: v for k, v in self._active_orders if k != order_id}

    def next_order_id(self):
        return self.orderid
    # ------------------------------- end of public functions -----------------------------#
