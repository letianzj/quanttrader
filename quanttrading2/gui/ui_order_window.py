#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui
from ..order.order_event import OrderEvent


class OrderWindow(QtWidgets.QTableWidget):
    '''
    Order Monitor
    '''
    order_status_signal = QtCore.pyqtSignal(type(OrderEvent()))

    def __init__(self, order_manager, broker, parent=None):
        super(OrderWindow, self).__init__(parent)

        self.header = ['OrderID',
                       'SID',
                       'Symbol',
                       'Type',
                       'Limit',
                       'Stop',
                       'Quantity',
                       'Filled',
                       'Status',
                       'Order_Time',
                       'Cancel_Time',
                       'Account']

        self.init_table()

        self._orderids = []
        self._order_manager = order_manager
        self._broker = broker
        self.order_status_signal.connect(self.update_table)

    def init_table(self):
        col = len(self.header)
        self.setColumnCount(col)

        self.setHorizontalHeaderLabels(self.header)
        self.setEditTriggers(self.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)

        self.itemDoubleClicked.connect(self.cancel_order)

    def update_table(self, order_event):
        '''
        If order id exist, update status
        else append one row
        '''
        update = self._order_manager.on_order_status(order_event)

        if(update):
            if order_event.order_id in self._orderids:
                row = self._orderids.index(order_event.order_id)
                self.item(row, 7).setText(str(self._order_manager.order_dict[order_event.order_id].fill_size))
                self.item(row, 8).setText(self._order_manager.order_dict[order_event.order_id].order_status.name)
                self.item(row, 10).setText(order_event.cancel_time)
            else:  # including empty
                self._orderids.insert(0, order_event.order_id)
                self.insertRow(0)
                self.setItem(0, 0, QtWidgets.QTableWidgetItem(str(order_event.order_id)))
                self.setItem(0, 1, QtWidgets.QTableWidgetItem(str(self._order_manager.order_dict[order_event.order_id].source)))
                self.setItem(0, 2, QtWidgets.QTableWidgetItem(order_event.full_symbol))
                self.setItem(0, 3, QtWidgets.QTableWidgetItem(order_event.order_type.name))
                self.setItem(0, 4, QtWidgets.QTableWidgetItem(str(self._order_manager.order_dict[order_event.order_id].limit_price)))
                self.setItem(0, 5, QtWidgets.QTableWidgetItem(str(self._order_manager.order_dict[order_event.order_id].stop_price)))
                self.setItem(0, 6, QtWidgets.QTableWidgetItem(str(self._order_manager.order_dict[order_event.order_id].order_size)))
                self.setItem(0, 7, QtWidgets.QTableWidgetItem(str(self._order_manager.order_dict[order_event.order_id].fill_size)))
                self.setItem(0, 8, QtWidgets.QTableWidgetItem(self._order_manager.order_dict[order_event.order_id].order_status.name))
                self.setItem(0, 9, QtWidgets.QTableWidgetItem(self._order_manager.order_dict[order_event.order_id].create_time))
                self.setItem(0, 10, QtWidgets.QTableWidgetItem(self._order_manager.order_dict[order_event.order_id].cancel_time))
                self.setItem(0, 11, QtWidgets.QTableWidgetItem(self._order_manager.order_dict[order_event.order_id].account))

    def update_order_status(self, order_id):
        """
        This is called by fill handler to update order status
        """

        if order_id in self._orderids:
            row = self._orderids.index(order_id)
            self.item(row, 7).setText(str(self._order_manager.order_dict[order_id].fill_size))
            self.item(row, 8).setText(self._order_manager.order_dict[order_id].order_status.name)
            self.item(row, 10).setText(self._order_manager.order_dict[order_id].create_time)

    def cancel_order(self,mi):
        row = mi.row()
        order_id = int(self.item(row, 0).text())
        self._broker.cancel_order(order_id)

