#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod


class DataFeedBase(metaclass=ABCMeta):
    """
    DateFeed baae class
    """

    @abstractmethod
    def subscribe_market_data(self, symbols):
        """subscribe to market data"""

    @abstractmethod
    def unsubscribe_market_data(self, symbols):
        """unsubscribe market data"""

    @abstractmethod
    def stream_next(self):
        """stream next data event"""