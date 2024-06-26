#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from typing import Any

from PyQt5 import QtCore, QtWidgets

from ..order.fill_event import FillEvent
from ..position.position_event import PositionEvent

_logger = logging.getLogger(__name__)


__all__ = ["PositionWindow"]


class PositionWindow(QtWidgets.QTableWidget):
    position_signal = QtCore.pyqtSignal(type(PositionEvent()))

    def __init__(self, parent: Any = None) -> None:
        super(PositionWindow, self).__init__(parent)

        self.header = [
            "Symbol",
            "Security_Type",
            "Quantity",
            "Average_Price",
            "Open_PnL",
            "Closed_PnL",
            "Account",
            "Time",
        ]

        self.init_table()
        self._symbols: list[str] = []
        self.position_signal.connect(self.update_table)

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

    def update_table(self, position_event: PositionEvent) -> None:
        if position_event.full_symbol in self._symbols:
            row = self._symbols.index(position_event.full_symbol)
            self.setItem(row, 1, QtWidgets.QTableWidgetItem(position_event.sec_type))
            self.setItem(row, 2, QtWidgets.QTableWidgetItem(str(position_event.size)))
            self.setItem(
                row,
                3,
                QtWidgets.QTableWidgetItem(str(position_event.average_cost)),
            )
            self.setItem(
                row,
                4,
                QtWidgets.QTableWidgetItem(str(position_event.unrealized_pnl)),
            )
            self.setItem(
                row,
                5,
                QtWidgets.QTableWidgetItem(str(position_event.realized_pnl)),
            )
            self.setItem(row, 6, QtWidgets.QTableWidgetItem(position_event.account))
            self.setItem(row, 7, QtWidgets.QTableWidgetItem(position_event.timestamp))
        else:
            self._symbols.insert(0, str(position_event.full_symbol))
            self.insertRow(0)
            self.setItem(0, 0, QtWidgets.QTableWidgetItem(position_event.full_symbol))
            self.setItem(0, 1, QtWidgets.QTableWidgetItem(position_event.sec_type))
            self.setItem(0, 2, QtWidgets.QTableWidgetItem(str(position_event.size)))
            self.setItem(
                0,
                3,
                QtWidgets.QTableWidgetItem(str(position_event.average_cost)),
            )
            self.setItem(
                0,
                4,
                QtWidgets.QTableWidgetItem(str(position_event.unrealized_pnl)),
            )
            self.setItem(
                0,
                5,
                QtWidgets.QTableWidgetItem(str(position_event.realized_pnl)),
            )
            self.setItem(0, 6, QtWidgets.QTableWidgetItem(position_event.account))
            self.setItem(0, 7, QtWidgets.QTableWidgetItem(position_event.timestamp))

    def on_fill(self, fill_event: FillEvent) -> None:
        pass
