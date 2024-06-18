#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod

from ..order.order_event import OrderEvent

__all__ = ["RiskManagerBase"]


class RiskManagerBase(metaclass=ABCMeta):
    """
    RiskManager base class
    """

    @abstractmethod
    def order_in_compliance(self, o: OrderEvent, strategy_manager=None) -> bool:  # type: ignore
        raise NotImplementedError("order_in_compliance should be implemented")
