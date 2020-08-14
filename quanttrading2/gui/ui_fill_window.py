#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui
from ..order.fill_event import FillEvent
import logging

_logger = logging.getLogger(__name__)

class FillWindow(QtWidgets.QTableWidget):
    """
    present fills
    """
    fill_signal = QtCore.pyqtSignal(type(FillEvent()))

    def __init__(self, parent=None):
        super(FillWindow, self).__init__(parent)

        self.header = ['OrderID',
                       'FillID',
                       'SID',
                       'Symbol',
                       'Fill_Price',
                       'Filled',
                       'Fill_Time',
                       'Exchange',
                       'Account']

        self.init_table()
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
        if fill_event.fill_id in self._fillids:
            row = self._fillids.index(fill_event.fill_id)
            self.item(row, 6).setText(fill_event.fill_time)
            _logger.error('received same fill twice')
        else:  # including empty
            try:
                self._fillids.insert(0, fill_event.fill_id)
                self.insertRow(0)
                self.setItem(0, 0, QtWidgets.QTableWidgetItem(str(fill_event.order_id)))
                self.setItem(0, 1, QtWidgets.QTableWidgetItem(str(fill_event.fill_id)))
                self.setItem(0, 2, QtWidgets.QTableWidgetItem(str(fill_event.source)))
                self.setItem(0, 3, QtWidgets.QTableWidgetItem(fill_event.full_symbol))
                self.setItem(0, 4, QtWidgets.QTableWidgetItem(str(fill_event.fill_price)))
                self.setItem(0, 5, QtWidgets.QTableWidgetItem(str(fill_event.fill_size)))
                self.setItem(0, 6, QtWidgets.QTableWidgetItem(fill_event.fill_time))
                self.setItem(0, 7, QtWidgets.QTableWidgetItem(fill_event.exchange))
                self.setItem(0, 8, QtWidgets.QTableWidgetItem(fill_event.account))
            except:
                _logger.error('unable to insert fill to fill window')


