#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui
from ..order.fill_event import FillEvent

class FillWindow(QtWidgets.QTableWidget):
    fill_signal = QtCore.pyqtSignal(type(FillEvent()))

    def __init__(self, order_manager, parent=None):
        super(FillWindow, self).__init__(parent)

        self.header = ['OrderID',
                       'FillID',
                       'Symbol',
                       'Name',
                       'Security_Type',
                       'Direction',
                       'Order_Flag',
                       'Fill_Price',
                       'Filled',
                       'Fill_Time',
                       'Exchange',
                       'Account',
                       'Source']

        self.init_table()
        self._order_manager = order_manager
        self._fillids = []
        self.fill_signal.connect(self.update_table)

    def init_table(self):
        col = len(self.header)
        self.setColumnCount(col)

        self.setHorizontalHeaderLabels(self.header)
        self.setEditTriggers(self.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)

    def update_table(self,fill_event):
        '''
        Only add row
        '''
        if fill_event.broker_fill_id in self._fillids:
            row = self._orderids.index(fill_event.broker_order_id)
            self.item(row, 9).setText(fill_event.fill_time)
            print('received same fill twice')
        else:  # including empty
            try:
                self._fillids.insert(0, fill_event.broker_fill_id)
                self.insertRow(0)
                self.setItem(0, 0, QtWidgets.QTableWidgetItem(str(fill_event.client_order_id)))
                self.setItem(0, 1, QtWidgets.QTableWidgetItem(str(fill_event.broker_fill_id)))
                self.setItem(0, 2, QtWidgets.QTableWidgetItem(fill_event.full_symbol))
                self.setItem(0, 3, QtWidgets.QTableWidgetItem(""))
                self.setItem(0, 4, QtWidgets.QTableWidgetItem(""))
                self.setItem(0, 5, QtWidgets.QTableWidgetItem('Long' if fill_event.fill_size > 0 else 'Short'))
                self.setItem(0, 6, QtWidgets.QTableWidgetItem(self._order_manager.retrieve_order(fill_event.client_order_id).order_flag.name))
                self.setItem(0, 7, QtWidgets.QTableWidgetItem(str(fill_event.fill_price)))
                self.setItem(0, 8, QtWidgets.QTableWidgetItem(str(fill_event.fill_size)))
                self.setItem(0, 9, QtWidgets.QTableWidgetItem(fill_event.fill_time))
                self.setItem(0, 10, QtWidgets.QTableWidgetItem(""))
                self.setItem(0, 11, QtWidgets.QTableWidgetItem(fill_event.account))
                self.setItem(0, 12, QtWidgets.QTableWidgetItem(fill_event.source))
            except:
                print('unable to find order that matches this fill')


