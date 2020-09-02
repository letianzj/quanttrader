#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod

class RiskManagerBase(metaclass=ABCMeta):
    """
    RiskManager base class
    """
    @abstractmethod
    def order_in_compliance(self, o, strategy_manager=None):
        raise NotImplementedError("order_in_compliance should be implemented")
