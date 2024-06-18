#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ..data.data_board import DataBoard
from ..data.tick_event import TickEvent
from ..event.backtest_event_engine import BacktestEventEngine
from ..order.fill_event import FillEvent
from ..order.order_event import OrderEvent
from ..order.order_status import OrderStatus
from ..order.order_type import OrderType
from .brokerage_base import BrokerageBase

__all__ = ["BacktestBrokerage"]


class BacktestBrokerage(BrokerageBase):
    """
    Market order is immediately filled.
    Limit or stop order is saved to _active_orders for next tick
    """

    def __init__(
        self, events_engine: BacktestEventEngine, data_board: DataBoard
    ) -> None:
        """
        Initialize Backtest Brokerage.

        :param events_engine: send fill_event to event engine
        :param data_board: retrieve latest price from data_board
        """
        super().__init__()

        self._events_engine: BacktestEventEngine = events_engine
        self._data_board: DataBoard = data_board  # retrieve price against order
        self._active_orders: dict[int, OrderEvent] = {}

    # ------------------------------------ private functions -----------------------------#
    def _calculate_commission(
        self, full_symbol: str, fill_price: float, fill_size: int
    ) -> float:
        """
        Calculate commision. By default it uses IB commission charges.

        :param full_symbol: contract symbol
        :param fill_price: order fill price
        :param fill_size: order fill size
        """
        if "STK" in full_symbol:
            commission = max(0.005 * abs(fill_size), 1)  # per share
        elif "FUT" in full_symbol:
            commission = 2.01 * abs(fill_size)  # per contract
        elif "OPT" in full_symbol:
            commission = max(0.7 * abs(fill_size), 1)
        elif "CASH" in full_symbol:
            commission = max(0.000002 * abs(fill_price * fill_size), 2)
        else:
            commission = 0.0001 * abs(
                fill_price * fill_size
            )  # assume 1bps for all other types

        return commission

    def _try_cross_order(self, order_event: OrderEvent, current_price: float) -> None:
        """
        Cross standing order against current price.

        :param order_event: order to be crossed
        :param current_price: current market price
        """
        if order_event.order_type == OrderType.MARKET:
            order_event.order_status = OrderStatus.FILLED
        # stop limit, if buy, limit price < market price < stop price;
        # if sell, limti price > market price > stop price
        # cross if opposite
        # limit: if buy, limit_price >= current_price; if sell, opposite
        elif (order_event.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]) & (
            ((order_event.order_size > 0) & (order_event.limit_price >= current_price))
            | (
                (order_event.order_size < 0)
                & (order_event.limit_price <= current_price)
            )
        ):
            order_event.order_status = OrderStatus.FILLED
        # stop: if buy, stop_price <= current_price; if sell, opposite
        elif (order_event.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]) & (
            ((order_event.order_size > 0) & (order_event.stop_price <= current_price))
            | ((order_event.order_size < 0) & (order_event.stop_price >= current_price))
        ):
            order_event.order_status = OrderStatus.FILLED

    # -------------------------------- end of private functions -----------------------------#

    # -------------------------------------- public functions -------------------------------#
    def reset(self) -> None:
        """
        Reset Backtest Brokerage.
        """
        self._active_orders.clear()
        self.orderid = 1

    def on_tick(self, tick_event: TickEvent) -> None:
        """
        Cross standing orders against new tick_event

        Market order can be potentially saved and then filled here against tomorrow's open price

        :param tick_event: new tick just came in
        :return: no return; if orders are filled, they are pushed into message queue
        """
        # check standing (stop) orders
        # put trigged into queue
        # and remove from standing order list
        _remaining_active_orders_id = []
        timestamp = tick_event.timestamp
        for oid, order_event in self._active_orders.items():
            _ = oid
            # this should be after data board is updated
            # current_price = self._data_board.get_last_price(tick_event.full_symbol)      # last price is not updated yet
            current_price = self._data_board.get_current_price(
                order_event.full_symbol, timestamp
            )
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
                fill.exchange = "BACKTEST"
                fill.commission = self._calculate_commission(
                    fill.full_symbol, fill.fill_price, fill.fill_size
                )
                self._events_engine.put(fill)
            else:
                # Trailing stop; reset stop price, use limit price as trailing amount
                # if buy, stop price drops when market price drops
                # if sell, stop price increases when market price increases
                if order_event.order_type == OrderType.TRAIING_STOP:
                    if order_event.order_size > 0:
                        order_event.stop_price = min(
                            current_price + order_event.limit_price,
                            order_event.stop_price,
                        )
                    else:
                        order_event.stop_price = max(
                            current_price - order_event.limit_price,
                            order_event.stop_price,
                        )

                _remaining_active_orders_id.append(order_event.order_id)

        self._active_orders = {
            k: v
            for k, v in self._active_orders.items()
            if k in _remaining_active_orders_id
        }

    def place_order(self, order_event: OrderEvent) -> None:
        """
        Place and fill client order; return fill event.

        Market order is immediately filled, no latency or slippage
        the alternative is to save the orders and fill in on_tick function

        :param order_event: client order received
        :return: no return; fill_event is pushed into message queue
        """
        # current_price = self._data_board.get_last_price(order_event.full_symbol)      # last price is not updated yet
        timestamp = order_event.create_time
        current_price = self._data_board.get_current_price(
            order_event.full_symbol, timestamp
        )
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
            fill.exchange = "BACKTEST"
            fill.commission = self._calculate_commission(
                fill.full_symbol, fill.fill_price, fill.fill_size
            )

            order_event.order_status = OrderStatus.FILLED
            self._events_engine.put(order_event)
            self._events_engine.put(fill)
        else:
            order_event.order_status = OrderStatus.ACKNOWLEDGED
            self._active_orders[order_event.order_id] = (
                order_event  # save standing orders
            )
            self._events_engine.put(order_event)

    def cancel_order(self, order_id: int) -> None:
        """
        Handle cancel order request from client.

        :param order_id: order id of the order to be canceled
        :return: no return; cancel feedback is pushed into message queue
        """
        self._active_orders = {
            k: v for k, v in self._active_orders.items() if k != order_id
        }

    def next_order_id(self) -> int:
        """
        Return next available order id for client to use.

        :return: next available new order id
        """
        return self.orderid

    # ------------------------------- end of public functions -----------------------------#
