#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from typing import Any

from PyQt5 import QtCore, QtWidgets

from ..order.fill_event import FillEvent

_logger = logging.getLogger(__name__)

__all__ = ["FillWindow"]


class FillWindow(QtWidgets.QTableWidget):
    """
    present fills
    """

    fill_signal = QtCore.pyqtSignal(type(FillEvent()))

    def __init__(self, parent: Any = None) -> None:
        super(FillWindow, self).__init__(parent)

        self.header = [
            "OrderID",
            "FillID",
            "SID",
            "Symbol",
            "Fill_Price",
            "Filled",
            "Fill_Time",
            "Exchange",
            "Account",
        ]

        self.init_table()
        self._fillids: list[int] = []
        self.fill_signal.connect(self.update_table)

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

    def update_table(self, fill_event: FillEvent) -> None:
        """
        Only add row
        """
        if fill_event.fill_id in self._fillids:
            row = self._fillids.index(fill_event.fill_id)
            _itm = self.item(row, 6)
            if _itm:
                _itm.setText(
                    fill_event.fill_time.strftime("%H:%M:%S.%f")
                    if fill_event.fill_time
                    else ""
                )
            _logger.error("received same fill twice")
        else:  # including empty
            try:
                self._fillids.insert(0, fill_event.fill_id)
                self.insertRow(0)
                self.setItem(0, 0, QtWidgets.QTableWidgetItem(str(fill_event.order_id)))
                self.setItem(0, 1, QtWidgets.QTableWidgetItem(str(fill_event.fill_id)))
                self.setItem(0, 2, QtWidgets.QTableWidgetItem(str(fill_event.source)))
                self.setItem(0, 3, QtWidgets.QTableWidgetItem(fill_event.full_symbol))
                self.setItem(
                    0, 4, QtWidgets.QTableWidgetItem(str(fill_event.fill_price))
                )
                self.setItem(
                    0, 5, QtWidgets.QTableWidgetItem(str(fill_event.fill_size))
                )
                self.setItem(
                    0,
                    6,
                    QtWidgets.QTableWidgetItem(
                        fill_event.fill_time.strftime("%H:%M:%S.%f")
                        if fill_event.fill_time
                        else ""
                    ),
                )
                self.setItem(0, 7, QtWidgets.QTableWidgetItem(fill_event.exchange))
                self.setItem(0, 8, QtWidgets.QTableWidgetItem(fill_event.account))
            except:
                _logger.error("unable to insert fill to fill window")
