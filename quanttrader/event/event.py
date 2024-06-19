#!/usr/bin/env python
# -*- coding: utf-8 -*-
from enum import Enum

import pandas as pd

__all__ = ["EventType", "Event", "LogEvent"]


class EventType(Enum):
    TICK = 0
    BAR = 1
    ORDER = 2
    FILL = 3
    CANCEL = 4
    ORDERSTATUS = 5
    ACCOUNT = 6
    POSITION = 7
    CONTRACT = 8
    HISTORICAL = 9
    TIMER = 10
    LOG = 11


class Event(object):
    """
    Base Event class for event-driven system
    """

    @property
    def typename(self) -> str:
        return self.__class__.__name__


class LogEvent(Event):
    """
    Log event:
    TODO seperate ErrorEvent
    """

    def __init__(self) -> None:
        self.event_type: EventType = EventType.LOG
        self.timestamp: pd.Timestamp = None
        self.content: str = ""
