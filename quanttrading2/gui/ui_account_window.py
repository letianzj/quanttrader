#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui
import logging
from ..account.account_event import AccountEvent

_logger = logging.getLogger(__name__)


class AccountWindow(QtWidgets.QTableWidget):
    account_signal = QtCore.pyqtSignal(type(AccountEvent()))

    def __init__(self, account_manager, parent=None):
        super(AccountWindow, self).__init__(parent)

        self.header = ['AccountID',
                       'Net',
                       'Available',
                       'Margin',
                       'Closed_PnL',
                       'Open_PnL',
                       'Brokerage',
                       'Time']

        self.init_table()
        self._account_manager = account_manager
        self._account_ids = []
        self.account_signal.connect(self.update_table)

    def init_table(self):
        col = len(self.header)
        self.setColumnCount(col)

        self.setHorizontalHeaderLabels(self.header)
        self.setEditTriggers(self.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)

    def update_table(self,account_event):
        '''
        Only add row
        '''
        self._account_manager.on_account(account_event)
        _logger.info(f'account id recorded: {account_event.account_id}')

        if account_event.account_id in self._account_ids:
            row = self._account_ids.index(account_event.account_id)
            self.setItem(row, 1, QtWidgets.QTableWidgetItem(str(account_event.balance)))
            self.setItem(row, 2, QtWidgets.QTableWidgetItem(str(account_event.available)))
            self.setItem(row, 3, QtWidgets.QTableWidgetItem(str(account_event.margin)))
            self.setItem(row, 4, QtWidgets.QTableWidgetItem(str(account_event.closed_pnl)))
            self.setItem(row, 5, QtWidgets.QTableWidgetItem(str(account_event.open_pnl)))
            self.setItem(row, 6, QtWidgets.QTableWidgetItem(account_event.brokerage))
            self.setItem(row, 7, QtWidgets.QTableWidgetItem(account_event.timestamp))

        else:
            self._account_ids.insert(0, account_event.account_id)
            self.insertRow(0)
            self.setItem(0, 0, QtWidgets.QTableWidgetItem(account_event.account_id))
            self.setItem(0, 1, QtWidgets.QTableWidgetItem(str(account_event.balance)))
            self.setItem(0, 2, QtWidgets.QTableWidgetItem(str(account_event.available)))
            self.setItem(0, 3, QtWidgets.QTableWidgetItem(str(account_event.margin)))
            self.setItem(0, 4, QtWidgets.QTableWidgetItem(str(account_event.closed_pnl)))
            self.setItem(0, 5, QtWidgets.QTableWidgetItem(str(account_event.open_pnl)))
            self.setItem(0, 6, QtWidgets.QTableWidgetItem(account_event.brokerage))
            self.setItem(0, 7, QtWidgets.QTableWidgetItem(account_event.timestamp))

