#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import abstractmethod

from ..order.order_event import OrderEvent


class BrokerageBase(object):
    """
    Brokerage base class
    """

    def __init__(self) -> None:
        self.orderid: int = 0  # next/available orderid
        self.market_data_subscription_reverse_dict: dict[str, int] = {}  # sym ==> reqId

    @abstractmethod
    def place_order(self, order_event: OrderEvent) -> None:
        """
        place order
        """
        raise NotImplementedError("Implement this in your derived class")

    @abstractmethod
    def cancel_order(self, order_id: int) -> None:
        """
        cancel order
        """
        raise NotImplementedError("Implement this in your derived class")

    @abstractmethod
    def next_order_id(self) -> int:
        """
        request next order id
        """
        raise NotImplementedError("Implement this in your derived class")

    @abstractmethod
    def _calculate_commission(
        self, full_symbol: str, fill_price: float, fill_size: int
    ) -> float:
        """
        calc commission
        """
        raise NotImplementedError("Implement this in your derived class")
