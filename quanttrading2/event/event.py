#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pandas import Timestamp
from enum import Enum


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
    def typename(self):
        return self.type.name


class LogEvent(Event):
    """
    Log event:
    TODO seperate ErrorEvent
    """
    def __init__(self):
        self.event_type = EventType.LOG
        self.timestamp = ""
        self.content = ""