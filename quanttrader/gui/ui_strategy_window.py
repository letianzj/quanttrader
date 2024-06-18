#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any

from PyQt5 import QtWidgets

from ..order.fill_event import FillEvent
from ..order.order_event import OrderEvent
from ..strategy.strategy_manager import StrategyManager

__all__ = ["StrategyWindow"]


class StrategyWindow(QtWidgets.QTableWidget):
    """
    Strategy Monitor
    """

    def __init__(self, strategy_manager: StrategyManager, parent: Any = None) -> None:
        super(StrategyWindow, self).__init__(parent)

        self._strategy_manager = strategy_manager

        self.header = [
            "SID",
            "SName",
            "nHoldings",
            "nOrders",
            "nFilled",
            "Open_PnL",
            "Closed_PnL",
            "Status",
        ]
        self.init_table()

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

        for key, value in self._strategy_manager.strategy_dict.items():
            try:
                self.insertRow(self.rowCount())
                self.setItem(
                    self.rowCount() - 1, 0, QtWidgets.QTableWidgetItem(str(key))
                )
                self.setItem(
                    self.rowCount() - 1,
                    1,
                    QtWidgets.QTableWidgetItem(str(value.name)),
                )
                self.setItem(
                    self.rowCount() - 1,
                    7,
                    QtWidgets.QTableWidgetItem(
                        "active" if value.active else "inactive"
                    ),
                )
            except:
                pass

    def update_order(self, order_event: OrderEvent) -> None:
        sid = order_event.source
        if sid in self._strategy_manager.strategy_dict.keys():
            row = sid - 1  # sid starts from 1
            norders = len(
                self._strategy_manager.strategy_dict[sid]._order_manager.order_dict
            )
            nfilled = len(
                self._strategy_manager.strategy_dict[sid]._order_manager.fill_dict
            )
            self.setItem(row, 3, QtWidgets.QTableWidgetItem(str(norders)))
            self.setItem(row, 4, QtWidgets.QTableWidgetItem(str(nfilled)))

    def update_fill(self, fill_event: FillEvent) -> None:
        if fill_event.fill_id in self._strategy_manager._order_manager.fill_dict.keys():
            oid = self._strategy_manager._order_manager.fill_dict[
                fill_event.fill_id
            ].order_id
            if oid in self._strategy_manager._order_manager.order_dict.keys():
                sid = self._strategy_manager._order_manager.order_dict[oid].source
                if sid in self._strategy_manager.strategy_dict.keys():
                    row = sid - 1  # sid starts from 1
                    norders = len(
                        self._strategy_manager.strategy_dict[
                            sid
                        ]._order_manager.order_dict
                    )
                    nfilled = len(
                        self._strategy_manager.strategy_dict[
                            sid
                        ]._order_manager.fill_dict
                    )
                    nholdings = self._strategy_manager.strategy_dict[
                        sid
                    ]._position_manager.get_holdings_count()
                    self.setItem(row, 2, QtWidgets.QTableWidgetItem(str(nholdings)))
                    self.setItem(row, 3, QtWidgets.QTableWidgetItem(str(norders)))
                    self.setItem(row, 4, QtWidgets.QTableWidgetItem(str(nfilled)))

    def update_pnl(self) -> None:
        for sid, s in self._strategy_manager.strategy_dict.items():
            closed_pnl: float = 0
            open_pnl: float = 0
            for _, pos in s._position_manager.positions.items():
                p1, p2 = pos.get_current_pnl()
                closed_pnl += p1
                open_pnl += p2
            self.setItem(sid - 1, 5, QtWidgets.QTableWidgetItem(str(open_pnl)))
            self.setItem(sid - 1, 6, QtWidgets.QTableWidgetItem(str(closed_pnl)))

    def update_status(self, row: int, active: bool) -> None:
        _itm = self.item(row, 0)
        if _itm:
            sid = int(_itm.text())
            self._strategy_manager.strategy_dict[sid].active = active
            self.setItem(
                row,
                7,
                QtWidgets.QTableWidgetItem("active" if active else "inactive"),
            )
