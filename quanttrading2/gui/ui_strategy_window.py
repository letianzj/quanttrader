#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui

class StrategyWindow(QtWidgets.QTableWidget):
    '''
    Strategy Monitor
    '''
    def __init__(self , strategy_manager, parent=None):
        super(StrategyWindow, self).__init__(parent)

        self._strategy_manager = strategy_manager

        self.header = ['SID',
                       'SName',
                       'nHoldings',
                       'nTrades',
                       'Open_PnL',
                       'Closed_PnL',
                       'Status']
        self.init_table()

    def init_table(self):
        col = len(self.header)
        self.setColumnCount(col)

        self.setHorizontalHeaderLabels(self.header)
        self.setEditTriggers(self.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)

        for key, value in self._strategy_manager._strategy_dict.items():
            try:
                self.insertRow(0)
                self.setItem(0, 0, QtWidgets.QTableWidgetItem(str(key)))
                self.setItem(0, 1, QtWidgets.QTableWidgetItem(str(value.name)))
                self.setItem(0, 6, QtWidgets.QTableWidgetItem('active' if value.active else 'inactive'))
            except:
                pass

    def update_table(self, order_event):
        pass

    def add_table(self, row, string):
        pass

    def update_status(self, row, active):
        sid = int(self.item(row,0).text())
        self._strategy_manager._strategy_dict[sid].active = active
        self.setItem(row, 6, QtWidgets.QTableWidgetItem('active' if active else 'inactive'))
