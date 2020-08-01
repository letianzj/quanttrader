#!/usr/bin/env python
# -*- coding: utf-8 -*-
from PyQt5 import QtCore, QtWidgets, QtGui
from ..event.event import LogEvent

class LogWindow(QtWidgets.QTableWidget):
    msg_signal = QtCore.pyqtSignal(type(LogEvent()))

    def __init__(self, parent=None):
        super(LogWindow, self).__init__(parent)

        self.header = ['Time',
                       'Content']

        self.init_table()
        self.msg_signal.connect(self.update_table)

    def init_table(self):
        col = len(self.header)
        self.setColumnCount(col)

        self.setHorizontalHeaderLabels(self.header)
        self.setEditTriggers(self.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)

    def update_table(self,geneal_event):
        '''
        Only add row
        '''
        self.insertRow(0)
        self.setItem(0, 0, QtWidgets.QTableWidgetItem(geneal_event.timestamp))
        self.setItem(0, 1, QtWidgets.QTableWidgetItem(geneal_event.content))


