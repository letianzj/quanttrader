#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .order_status import OrderStatus
from ..event.event import *
from .order_event import OrderEvent
from .order_type import OrderType
from .order_flag import OrderFlag


class OrderStatusEvent(Event):
    """
    Order status event
    """
    def __init__(self):
        """
        order status contains order information because of open orders
        upon reconnect, open order event info will be received to recreate an order
        """
        self.event_type = EventType.ORDERSTATUS
        self.order_id = -1
        self.order_flag = OrderFlag.OPEN
        self.order_status = OrderStatus.UNKNOWN
        self.full_symbol = ''
        self.order_size = 0
        self.limit_price = 0.0
        self.stop_price = 0.0
        self.fill_size = 0
        self.fill_price = 0.0
        self.create_time = None
        self.fill_time = None
        self.cancel_time = None
        self.account = ''
        self.api = ''
        self.timestamp = ''

    def to_order(self):
        o = OrderEvent()
        o.order_id = self.order_id
        o.full_symbol = self.full_symbol
        o.order_type = OrderType.LIMIT
        o.order_flag = self.order_flag
        o.order_status = self.order_status
        o.limit_price = self.limit_price
        o.stop_price = self.stop_price
        o.order_size = self.order_size
        o.fill_price = self.fill_price
        o.fill_size = self.fill_size
        o.create_time = self.create_time
        o.fill_time = self.fill_time
        o.cancel_time = self.cancel_time
        o.account =  self.account
        o.source = -1  # sid

        return o