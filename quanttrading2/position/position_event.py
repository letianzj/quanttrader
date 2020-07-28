#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ..event.event import *
from .position import Position

class PositionEvent(Event):
    """
    position event
    """
    def __init__(self):
        """
        Initialises order
        """
        self.event_type = EventType.POSITION
        self.full_symbol = ''
        self.average_cost = 0.0
        self.size = 0
        self.pre_size = 0
        self.freezed_size = 0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        self.account = ''
        self.api = ''
        self.timestamp = ''

    def deserialize(self, msg):
        v = msg.split('|')
        self.full_symbol = v[1]
        self.average_cost = float(v[2])
        self.size = int(v[3])
        self.pre_size = int(v[4])
        self.freezed_size = int(v[5])
        self.realized_pnl = float(v[6])
        self.unrealized_pnl = float(v[7])
        self.account = v[8]
        self.api = v[9]
        self.timestamp = v[10]

    def to_position(self):
        pos = Position(self.full_symbol, self.average_cost, self.size)
        pos.realized_pnl = self.realized_pnl
        pos.unrealized_pnl = self.unrealized_pnl
        pos.account = self.account
        pos.api = self.api

        return pos
