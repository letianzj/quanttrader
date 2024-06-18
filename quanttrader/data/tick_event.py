#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
from enum import Enum

import pandas as pd

from ..event.event import Event, EventType

__all__ = ["TickType", "TickEvent"]


class TickType(Enum):
    """
    Unlike IB, it does not have tick_size, e.g., TickTypeEnum.BID_SIZE
    """

    TRADE = 0
    BID = 1
    ASK = 2
    FULL = 3


class TickEvent(Event):
    """
    Tick event
    """

    def __init__(self) -> None:
        """
        Initialises Tick
        """
        self.event_type: EventType = EventType.TICK
        self.tick_type: TickType = TickType.TRADE
        self.timestamp: pd.Timestamp = pd.Timestamp("1970-01-01", tz="UTC")
        self.full_symbol: str = ""
        self.price: float = 0.0
        self.size: int = 0
        self.depth: int = 1
        self.bid_price_L1: float = 0.0
        self.bid_size_L1: int = 0
        self.ask_price_L1: float = 0.0
        self.ask_size_L1: int = 0
        self.open_interest: int = 0
        self.open: float = 0.0
        self.high: float = 0.0
        self.low: float = 0.0
        self.pre_close: float = 0.0
        self.upper_limit_price: float = 0.0
        self.lower_limit_price: float = 0.0

    def __str__(self) -> str:
        return "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s" % (
            str(self.timestamp.strftime("%H:%M:%S.%f")),
            str(datetime.now().strftime("%H:%M:%S.%f")),
            str(self.full_symbol),
            (self.tick_type),
            str(self.bid_size_L1),
            str(self.bid_price_L1),
            str(self.ask_price_L1),
            str(self.ask_size_L1),
            str(self.price),
            str(self.size),
        )
