#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .order_status import OrderStatus
from .order_flag import OrderFlag
from .order_type import OrderType
from ..event.event import *

class OrderEvent(Event):
    """
    Order event
    """
    def __init__(self):
        """
        Initialises order
        """
        self.event_type = EventType.ORDER
        self.server_order_id = -1
        self.client_order_id = -1
        self.broker_order_id = -1
        self.order_type = OrderType.MARKET
        self.order_flag = OrderFlag.OPEN
        self.order_status = OrderStatus.UNKNOWN
        self.full_symbol =  ''
        self.order_size = 0         # short < 0, long > 0
        self.limit_price = 0.0
        self.stop_price = 0.0
        self.fill_size = 0
        self.fill_price = 0.0
        self.create_time = None
        self.fill_time = None
        self.cancel_time = None
        self.account = ''
        self.source = -1              # sid
        self.timestamp = ''

    def serialize(self):
        msg = ''
        if self.order_type == OrderType.MARKET:
            msg = 'o' + '|' + self.account + '|'+ str(self.source) + '|' + str(self.client_order_id) + '|' \
                  + 'MKT' + '|' + self.full_symbol + '|' + str(self.order_size) + '|' + str(self.order_flag.value)
        else:
            msg = 'o' + '|' + self.account + '|' + str(self.source) + '|' + str(self.client_order_id) + '|' \
                  + 'LMT'+ '|' + self.full_symbol + '|' + str(self.order_size) + '|' + str(self.limit_price) + '|' \
                  + str(self.order_flag.value)
        return msg