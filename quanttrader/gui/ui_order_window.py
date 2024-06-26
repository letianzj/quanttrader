#!/usr/bin/env python
# -*- coding: utf-8 -*-
from typing import Any

from PyQt5 import QtCore, QtWidgets

from ..brokerage.brokerage_base import BrokerageBase
from ..order.order_event import OrderEvent
from ..order.order_manager import OrderManager

__all__ = ["OrderWindow"]


class OrderWindow(QtWidgets.QTableWidget):
    """
    Order Monitor
    """

    order_status_signal = QtCore.pyqtSignal(type(OrderEvent()))

    def __init__(
        self,
        order_manager: OrderManager,
        broker: BrokerageBase,
        parent: Any = None,
    ) -> None:
        super(OrderWindow, self).__init__(parent)

        self.header = [
            "OrderID",  # 0
            "SID",  # 1
            "Symbol",  # 2
            "Type",  # 3
            "Limit",  # 4
            "Stop",  # 5
            "Quantity",  # 6
            "Filled",  # 7
            "Status",  # 8
            "Order_Time",  # 9
            "Cancel_Time",  # 10
            "Account",  # 11
        ]

        self.init_table()

        self._orderids: list[int] = []
        self._order_manager = order_manager
        self._broker = broker
        self.order_status_signal.connect(self.update_table)

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

        self.itemDoubleClicked.connect(self.cancel_order)

    def update_table(self, order_event: OrderEvent) -> None:
        """
        If order id exist, update status
        else append one row
        """
        update = self._order_manager.on_order_status(order_event)
        if update:
            if order_event.order_id in self._orderids:
                row = self._orderids.index(order_event.order_id)
                _itm = self.item(row, 7)
                if _itm:
                    _itm.setText(
                        str(
                            self._order_manager.order_dict[
                                order_event.order_id
                            ].fill_size
                        )
                    )

                _itm = self.item(row, 8)
                if _itm:
                    _itm.setText(
                        self._order_manager.order_dict[
                            order_event.order_id
                        ].order_status.name
                    )

                _itm = self.item(row, 10)
                if _itm:
                    _itm.setText(
                        order_event.cancel_time.strftime("%H:%M:%S.%f")
                        if order_event.cancel_time
                        else ""
                    )
            else:  # including empty
                self._orderids.insert(0, order_event.order_id)
                self.insertRow(0)
                self.setItem(
                    0, 0, QtWidgets.QTableWidgetItem(str(order_event.order_id))
                )
                self.setItem(
                    0,
                    1,
                    QtWidgets.QTableWidgetItem(
                        str(self._order_manager.order_dict[order_event.order_id].source)
                    ),
                )
                self.setItem(0, 2, QtWidgets.QTableWidgetItem(order_event.full_symbol))
                self.setItem(
                    0,
                    3,
                    QtWidgets.QTableWidgetItem(order_event.order_type.name),
                )
                self.setItem(
                    0,
                    4,
                    QtWidgets.QTableWidgetItem(
                        str(
                            self._order_manager.order_dict[
                                order_event.order_id
                            ].limit_price
                        )
                    ),
                )
                self.setItem(
                    0,
                    5,
                    QtWidgets.QTableWidgetItem(
                        str(
                            self._order_manager.order_dict[
                                order_event.order_id
                            ].stop_price
                        )
                    ),
                )
                self.setItem(
                    0,
                    6,
                    QtWidgets.QTableWidgetItem(
                        str(
                            self._order_manager.order_dict[
                                order_event.order_id
                            ].order_size
                        )
                    ),
                )
                self.setItem(
                    0,
                    7,
                    QtWidgets.QTableWidgetItem(
                        str(
                            self._order_manager.order_dict[
                                order_event.order_id
                            ].fill_size
                        )
                    ),
                )
                self.setItem(
                    0,
                    8,
                    QtWidgets.QTableWidgetItem(
                        self._order_manager.order_dict[
                            order_event.order_id
                        ].order_status.name
                    ),
                )
                self.setItem(
                    0,
                    9,
                    QtWidgets.QTableWidgetItem(
                        self._order_manager.order_dict[
                            order_event.order_id
                        ].create_time.strftime("%H:%M:%S.%f")
                        if self._order_manager.order_dict[
                            order_event.order_id
                        ].create_time
                        else ""
                    ),
                )
                self.setItem(
                    0,
                    10,
                    QtWidgets.QTableWidgetItem(
                        self._order_manager.order_dict[
                            order_event.order_id
                        ].cancel_time.strftime("%H:%M:%S.%f")
                        if self._order_manager.order_dict[
                            order_event.order_id
                        ].cancel_time
                        else ""
                    ),
                )
                self.setItem(
                    0,
                    11,
                    QtWidgets.QTableWidgetItem(
                        self._order_manager.order_dict[order_event.order_id].account
                    ),
                )

    def update_order_status(self, order_id: int) -> None:
        """
        This is called by fill handler to update order status
        """
        if order_id in self._orderids:
            row = self._orderids.index(order_id)
            _itm = self.item(row, 7)
            if _itm:
                _itm.setText(str(self._order_manager.order_dict[order_id].fill_size))

            _itm = self.item(row, 8)
            if _itm:
                _itm.setText(self._order_manager.order_dict[order_id].order_status.name)

            _itm = self.item(row, 10)
            if _itm:
                _itm.setText(
                    self._order_manager.order_dict[order_id].create_time.strftime(
                        "%H:%M:%S.%f"
                    )
                    if self._order_manager.order_dict[order_id].create_time
                    else ""
                )

    def cancel_order(self, mi: QtWidgets.QTableWidgetItem) -> None:
        row = mi.row()
        _itm = self.item(row, 0)
        if _itm:
            order_id = int(_itm.text())
            self._order_manager.on_cancel(order_id)
            self._broker.cancel_order(order_id)
