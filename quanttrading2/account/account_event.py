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
        self.api = ''
        self.timestamp = ''

    def deserialize(self, msg):
        v = msg.split('|')
        self.account_id = v[1]
        self.preday_balance = float(v[2])
        self.balance = float(v[3])
        self.available = float(v[4])
        self.commission = float(v[5])
        self.margin = float(v[6])
        self.closed_pnl = float(v[7])
        self.open_pnl = float(v[8])
        self.timestamp = v[9]
