#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd

from ..event.event import Event, EventType

__all__ = ["AccountEvent"]


class AccountEvent(Event):
    """
    also serve as account
    """

    def __init__(self) -> None:
        self.event_type: EventType = EventType.ACCOUNT
        self.account_id: str = ""
        self.preday_balance: float = 0.0
        self.balance: float = 0.0
        self.available: float = 0.0
        self.commission: float = 0.0
        self.margin: float = 0.0
        self.closed_pnl: float = 0.0
        self.open_pnl: float = 0.0
        self.brokerage: str = ""
        self.timestamp: pd.Timestamp | str = ""
