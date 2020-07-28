#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .risk_manager_base import RiskManagerBase

class PassThroughRiskManager(RiskManagerBase):
    def order_in_compliance(self, original_order):
        """
        Pass through the order without constraints
        """
        return original_order
