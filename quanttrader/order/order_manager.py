#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .order_type import *
from .order_status import *
from datetime import datetime
from copy import copy
import logging

_logger = logging.getLogger(__name__)


class OrderManager(object):
    '''
    Manage/track all the orders
    '''
    def __init__(self, name='Global'):
        self.name = name
        self.order_dict = {}              # order_id ==> order
        self.fill_dict = {}                # fill_id ==> fill
        self.standing_order_set = set()        # order_id of standing order for convenience
        self.canceled_order_set = set()  # order_id of canceled orders for convenience

    def reset(self):
        self.order_dict.clear()
        self.fill_dict.clear()
        self.standing_order_set.clear()
        self.canceled_order_set.clear()

    def on_tick(self, tick_event):
        """
        """
        pass

    def on_order_status(self, order_event):
        """
        on order status change from broker
        including canceled status
        """
        # there should be no negative order id if order is directly placed without queue.
        if order_event.order_id < 0:
            _logger.error(f'{self.name} OrderManager received negative orderid {order_event.order_id}')

        if order_event.order_id in self.order_dict:
            if (order_event.full_symbol != self.order_dict[order_event.order_id].full_symbol):
                _logger.error(f"{self.name} OrderManager Error: orders dont match")
                return False
            # only change status when it is logical
            elif self.order_dict[order_event.order_id].order_status.value <= order_event.order_status.value:
                self.order_dict[order_event.order_id].order_status = order_event.order_status
                if order_event.order_status < OrderStatus.FILLED:
                    self.standing_order_set.add(order_event.order_id)
                elif order_event.order_status == OrderStatus.CANCELED:
                    self.canceled_order_set.add(order_event.order_id)
                    self.order_dict[order_event.order_id].cancel_time = order_event.cancel_time
                    if order_event.order_id in self.standing_order_set:
                        self.standing_order_set.remove(order_event.order_id)
                return True
            else:  # no need to change status
                return False
        # order_id not yet assigned, open order at connection or placed by trader?
        else:
            self.order_dict[order_event.order_id] = copy(order_event)        # it is important to use copy
            if order_event.order_status < OrderStatus.FILLED:
                self.standing_order_set.add(order_event.order_id)
            elif order_event.order_status == OrderStatus.CANCELED:
                self.canceled_order_set.add(order_event.order_id)
                if order_event.order_id in self.standing_order_set:
                    self.standing_order_set.remove(order_event.order_id)
            return True

    def on_cancel(self, oid):
        """
        This proactively set order status to PENDING_CANCEL
        :param o:
        :return:
        """
        # Cancel will be handled in order_status
        # self.canceled_order_set.add(oid)
        # if oid in self.standing_order_set:
        #     self.standing_order_set.remove(oid)
        if oid in self.order_dict.keys():
            self.order_dict[oid].order_status = OrderStatus.PENDING_CANCEL
        else:
            _logger.error(f'{self.name} OrderManager cancel order is not registered')

    def on_fill(self, fill_event):
        """
        on receive fill_event from broker
        """
        if fill_event.fill_id in self.fill_dict.keys():
            _logger.error(f'{self.name} fill exists')
        else:
            self.fill_dict[fill_event.fill_id] = fill_event

            if fill_event.order_id in self.order_dict:
                self.order_dict[fill_event.order_id].fill_price = (fill_event.fill_price * fill_event.fill_size \
                                                                  + self.order_dict[fill_event.order_id].fill_price * self.order_dict[fill_event.order_id].fill_size) / \
                                                                  (self.order_dict[fill_event.order_id].fill_size + fill_event.fill_size)
                self.order_dict[fill_event.order_id].fill_size += fill_event.fill_size

                if self.order_dict[fill_event.order_id].order_size == self.order_dict[fill_event.order_id].fill_size:
                    self.order_dict[fill_event.order_id].order_status = OrderStatus.FILLED
                    if fill_event.order_id in self.standing_order_set:
                        self.standing_order_set.remove(fill_event.order_id)
                else:
                    self.order_dict[fill_event.order_id].order_status = OrderStatus.PARTIALLY_FILLED
            else:
                _logger.error(f'{self.name} Fill event {fill_event.fill_id} has no matching order {fill_event.order_id}')

    def retrieve_order(self, order_id):
        try:
            return self.order_dict[order_id]
        except:
            return None

    def retrieve_fill(self, fill_id):
        try:
            return self.fill_dict[fill_id]
        except:
            return None

    def retrieve_standing_orders(self):
        oids = []
        for oid in self.standing_order_set:
            if oid in self.order_dict.keys():
                if self.order_dict[oid].order_status < OrderStatus.FILLED:  # has standing order
                    oids.append(oid)
        return oids
