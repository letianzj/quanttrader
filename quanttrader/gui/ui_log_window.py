#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any

from PyQt5 import QtCore, QtWidgets

from ..event.event import LogEvent

__all__ = ["LogWindow"]


class LogWindow(QtWidgets.QTableWidget):
    msg_signal = QtCore.pyqtSignal(type(LogEvent()))

    def __init__(self, parent: Any = None) -> None:
        super(LogWindow, self).__init__(parent)

        self.header = ["Time", "Content"]

        self.init_table()
        self.msg_signal.connect(self.update_table)

    def init_table(self) -> None:
        col = len(self.header)
        self.setColumnCount(col)

        self.setHorizontalHeaderLabels(self.header)
        self.setEditTriggers(self.NoEditTriggers)
        _vh = self.verticalHeader()
        if _vh:
            _vh.setVisible(False)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)

    def update_table(self, geneal_event: LogEvent) -> None:
        """
        Only add row
        """
        self.insertRow(0)
        self.setItem(
            0,
            0,
            QtWidgets.QTableWidgetItem(
                geneal_event.timestamp.strftime("%H:%M:%S.%f")
                if geneal_event.timestamp
                else ""
            ),
        )
        self.setItem(0, 1, QtWidgets.QTableWidgetItem(geneal_event.content))
