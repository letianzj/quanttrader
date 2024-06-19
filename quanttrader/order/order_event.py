#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd

from ..event.event import Event, EventType
from .order_flag import OrderFlag
from .order_status import OrderStatus
from .order_type import OrderType

__all__ = ["OrderEvent"]


class OrderEvent(Event):
    """
    Order event
    """

    def __init__(self) -> None:
        """
        order and order status
        """
        self.event_type: EventType = EventType.ORDER
        self.order_id: int = -1
        self.order_type: OrderType = OrderType.MARKET
        self.order_flag: OrderFlag = OrderFlag.OPEN
        self.order_status: OrderStatus = OrderStatus.UNKNOWN
        self.full_symbol: str = ""
        self.order_size: int = 0  # short < 0, long > 0
        self.limit_price: float = 0.0
        self.stop_price: float = 0.0
        self.fill_size: int = 0
        self.fill_price: float = 0.0
        self.create_time: pd.Timestamp = None
        self.fill_time: pd.Timestamp = None
        self.cancel_time: pd.Timestamp = None
        self.account: str = ""
        self.source: int = -1  # sid, -1: unknown, 0: discretionary

    def __str__(self) -> str:
        return "Time: %s, Source: %s, Type: %s, LMT: %s, STP %s Size %s" % (
            self.create_time,
            str(self.source),
            str(self.order_type),
            str(self.limit_price),
            str(self.stop_price),
            str(self.order_size),
        )
