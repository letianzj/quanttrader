#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .order_type import *
from .order_status import *
from datetime import datetime

class OrderManager(object):
    '''
    Manage/track all the orders
    '''
    def __init__(self):
        self._client_order_id = 0         # unique internal_order id
        self.order_dict = {}              # client_order_id ==> order
        self.fill_dict = {}                # broker_fill_id ==> fill
        self._standing_order_list = []  # client_order_id of stnading orders for convenience
        self._canceled_order_list = []  # client_order_id of canceled orders for convenience

    def reset(self):
        self.order_dict.clear()
        self.fill_dict.clear()

    def on_tick(self, tick_event):
        """
        check standing (stop) orders
        put trigged into queue
        and remove from standing order list
        """
        pass

    def on_order(self, o):
        """
        on order placed by trader
        """
        if o.client_order_id < 0:         # client_order_id not yet assigned
            o.client_order_id = self._client_order_id
            o.order_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
            o.order_status = OrderStatus.NEWBORN
            self._client_order_id = self._client_order_id + 1
            self.order_dict[o.client_order_id] = o

    def on_order_status(self, order_status_event):
        """
        on order status change from broker
        including canceled status
        """
        if order_status_event.client_order_id in self.order_dict:
            if (order_status_event.full_symbol != self.order_dict[order_status_event.client_order_id].full_symbol):
                print("Error: orders dont match")
                return False
            # only change status when it is logical
            elif self.order_dict[order_status_event.client_order_id].order_status.value <= order_status_event.order_status.value:
                self.order_dict[order_status_event.client_order_id].order_status = order_status_event.order_status
                return True
            else:  # no need to change status
                return False
        elif order_status_event.client_order_id < 0:   # open order at connection
            order_status_event.client_order_id = self._client_order_id
            self._client_order_id = self._client_order_id + 1

            o = order_status_event.to_order()
            o.order_status = OrderStatus.ACKNOWLEDGED
            self.order_dict[order_status_event.client_order_id] = o

            return True
        else:
            return False

    def on_cancel(self, o):
        """
        on order canceled by trader
       for stop orders, cancel here
       for
       """
        pass

    def on_fill(self, fill_event):
        """
        on receive fill_event from broker
        """
        if fill_event.broker_fill_id in self.fill_dict:
            print('fill exists')
        else:
            self.fill_dict[fill_event.broker_fill_id] = fill_event

        if fill_event.client_order_id in self.order_dict:
            self.order_dict[fill_event.client_order_id].order_size -= fill_event.fill_size         # adjust it or keep it as original?
            self.order_dict[fill_event.client_order_id].fill_size += fill_event.fill_size
            self.order_dict[fill_event.client_order_id].fill_price = fill_event.fill_price

            if (self.order_dict[fill_event.client_order_id].fill_size == 0):
                self.order_dict[fill_event.client_order_id].order_status = OrderStatus.FILLED
                self._standing_order_list.remove(fill_event.client_order_id)
            else:
                self.order_dict[fill_event.client_order_id].order_status = OrderStatus.PARTIALLY_FILLED

    def retrieve_order(self, client_order_id):
        try:
            return self.order_dict[client_order_id]
        except:
            return None

    def retrieve_fill(self, internal_fill_id):
        try:
            return self.fill_dict[internal_fill_id]
        except:
            return None

