#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..event.event import *


class ContractEvent(Event):
    """
    also serve as contract
    """
    def __init__(self):
        self.event_type = EventType.CONTRACT
        self.full_symbol = ''
        self.local_name = ''
        self.mininum_tick = ''
