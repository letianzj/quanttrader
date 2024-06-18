#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd

from ..event.event import Event, EventType
from .position import Position

__all__ = ["PositionEvent"]


class PositionEvent(Event):
    """
    position event directly from live broker
    """

    def __init__(self) -> None:
        """
        Initialises order
        """
        self.event_type: EventType = EventType.POSITION
        self.full_symbol: str = ""
        self.sec_type: str = ""
        self.average_cost: float = 0.0
        self.size: int = 0
        self.pre_size: int = 0
        self.freezed_size: int = 0
        self.realized_pnl: float = 0.0
        self.unrealized_pnl: float = 0.0
        self.account: str = ""
        self.timestamp: pd.Timestamp = ""

    def to_position(self) -> Position:
        pos = Position(self.full_symbol, self.average_cost, self.size)
        pos.realized_pnl = self.realized_pnl
        pos.unrealized_pnl = self.unrealized_pnl
        pos.account = self.account

        return pos

    def __str__(self) -> str:
        return "Ticker: %s, Cost: %s, Size: %s, opl: %s, rpl: %s" % (
            str(self.full_symbol),
            str(self.average_cost),
            str(self.size),
            str(self.unrealized_pnl),
            str(self.realized_pnl),
        )
