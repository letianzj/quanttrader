#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd

from ..event.event import Event, EventType
from ..position.position import Position

__all__ = ["FillEvent"]


class FillEvent(Event):
    """
    Fill event, with filled quantity/size and price
    """

    def __init__(self) -> None:
        """
        Initialises fill
        """
        self.event_type: EventType = EventType.FILL
        self.order_id: int = -1
        self.fill_id: int = -1
        self.full_symbol: str = ""
        self.fill_time: pd.Timestamp
        self.fill_price: float = 0.0
        self.fill_size: int = 0  # size < 0 means short order is filled
        self.exchange: str = ""
        self.commission: float = 0.0
        self.account: str = ""
        self.source: int = -1
        self.api: str = ""

    def to_position(self, multiplier: float = 1.0) -> Position:
        """
        if there is no existing position for this symbol, this fill will create a new position
        (otherwise it will be adjusted to exisitng position)
        """
        if self.fill_size > 0:
            average_price_including_commission = (
                self.fill_price + self.commission / multiplier
            )
        else:
            average_price_including_commission = (
                self.fill_price - self.commission / multiplier
            )

        new_position = Position(
            self.full_symbol, average_price_including_commission, self.fill_size
        )
        return new_position

    def __str__(self) -> str:
        return (
            "Time: %s, Source: %s, Oid: %s, Ticker: %s, Price: %s, Size %s Comm %s"
            % (
                self.fill_time,
                str(self.source),
                str(self.order_id),
                self.full_symbol,
                str(self.fill_price),
                str(self.fill_size),
                str(self.commission),
            )
        )
