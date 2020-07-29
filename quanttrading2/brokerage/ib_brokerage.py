#!/usr/bin/env python
# -*- coding: utf-8 -*-
# download and install tws api
# pip install .
from .brokerage_base import BrokerageBase
from ..event.event import EventType
from ..order.fill_event import FillEvent
from ..order.order_event import OrderEvent
from ..order.order_status import OrderStatus
import logging

from ibapi import wrapper
from ibapi import utils
from ibapi.client import EClient
from ibapi.utils import iswrapper

# types
from ibapi.common import * # @UnusedWildImport
from ibapi.order_condition import * # @UnusedWildImport
from ibapi.contract import * # @UnusedWildImport
from ibapi.order import * # @UnusedWildImport
from ibapi.order_state import * # @UnusedWildImport
from ibapi.execution import Execution
from ibapi.execution import ExecutionFilter
from ibapi.commission_report import CommissionReport
from ibapi.ticktype import * # @UnusedWildImport
from ibapi.tag_value import TagValue

from ibapi.account_summary_tags import *


_logger = logging.getLogger(__name__)


class InteractiveBrokers(BrokerageBase):
    def __init__(self, events_engine, data_board):
        """
        Initialises the handler, setting the event queue
        as well as access to local pricing.
        """
        self._events_engine = events_engine
        self._data_board = data_board
        self._active_orders = {}