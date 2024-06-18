#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ..event.event import Event, EventType

__all__ = ["ContractEvent"]


class ContractEvent(Event):
    """
    also serve as contract
    """

    def __init__(self) -> None:
        self.event_type: EventType = EventType.CONTRACT
        self.full_symbol: str = ""
        self.local_name: str = ""
        self.mininum_tick: int = 0
