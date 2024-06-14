#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod

from ..event.event import Event


class DataFeedBase(metaclass=ABCMeta):
    """
    DateFeed baae class
    """

    @abstractmethod
    def subscribe_market_data(self, symbols: str | list[str]) -> None:
        """subscribe to market data"""

    @abstractmethod
    def unsubscribe_market_data(self, symbols: str | list[str]) -> None:
        """unsubscribe market data"""

    @abstractmethod
    def stream_next(self) -> Event:
        """stream next data event"""
