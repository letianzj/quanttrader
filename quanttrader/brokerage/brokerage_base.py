#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod


class BrokerageBase(object):
    """
    Brokerage base class
    """
    @abstractmethod
    def place_order(self, order_event):
        """"""
        raise NotImplementedError("Implement this in your derived class")

    @abstractmethod
    def cancel_order(self, order_id):
        """"""
        raise NotImplementedError("Implement this in your derived class")

    @abstractmethod
    def next_order_id(self):
        """"""
        raise NotImplementedError("Implement this in your derived class")

    @abstractmethod
    def _calculate_commission(self, full_symbol, fill_price, fill_size):
        """"""
        raise NotImplementedError("Implement this in your derived class")
