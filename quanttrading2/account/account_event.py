#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..event.event import *


class AccountEvent(Event):
    """
    also serve as account
    """
    def __init__(self):
        self.event_type = EventType.ACCOUNT
        self.account_id = ''
        self.preday_balance = 0.0
        self.balance = 0.0
        self.available = 0.0
        self.commission = 0.0
        self.margin = 0.0
        self.closed_pnl = 0.0
        self.open_pnl = 0.0
        self.brokerage = ''
        self.timestamp = ''
