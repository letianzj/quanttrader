#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from datetime import datetime
from typing import Any

import pandas as pd
from PyQt5 import QtGui, QtWidgets

from ..brokerage.brokerage_base import BrokerageBase
from ..event.event import LogEvent
from ..event.live_event_engine import LiveEventEngine
from ..order.order_event import OrderEvent
from ..order.order_manager import OrderManager
from ..order.order_status import OrderStatus
from ..order.order_type import OrderType

_logger = logging.getLogger(__name__)


__all__ = ["TradeMenu"]


class TradeMenu(QtWidgets.QWidget):
    def __init__(
        self,
        broker: BrokerageBase,
        event_engine: LiveEventEngine,
        order_manager: OrderManager,
        instrument_meta: dict[str, dict[str, Any]],
    ):
        super(TradeMenu, self).__init__()

        self.broker = broker
        self.event_engine = event_engine
        self.order_manager = order_manager
        self.instrument_meta = instrument_meta

        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("Discretionary Trade")
        self.setWindowIcon(QtGui.QIcon("gui/image/logo.ico"))
        self.resize(800, 500)
        place_order_layout = QtWidgets.QFormLayout()
        self.sym = QtWidgets.QLineEdit()
        # self.sym_name = QtWidgets.QLineEdit()
        # self.sec_type = QtWidgets.QComboBox()
        # self.sec_type.addItems(
        #     ['Stock', 'Future', 'Option', 'Forex'])
        self.direction = QtWidgets.QComboBox()
        self.direction.addItems(["Long", "Short"])
        self.order_price = QtWidgets.QLineEdit()
        self.order_quantity = QtWidgets.QLineEdit()
        self.order_type = QtWidgets.QComboBox()
        self.order_type.addItems(["MKT", "LMT"])
        # self.exchange = QtWidgets.QComboBox()
        # self.exchange.addItems(['CFFEX', 'SHFE', 'DCE', 'HKFE', 'GLOBEX', 'SMART'])
        # self.account = QtWidgets.QComboBox()
        # self.account.addItems(['FROM', 'CONFIG'])
        self.btn_order = QtWidgets.QPushButton("Place_Order")
        self.btn_order.clicked.connect(self.place_order)

        place_order_layout.addRow(QtWidgets.QLabel("Discretionary"))
        place_order_layout.addRow("Symbol", self.sym)
        # place_order_layout.addRow('Name', self.sym_name)
        # place_order_layout.addRow('Security_Type', self.sec_type)
        place_order_layout.addRow("Direction", self.direction)
        place_order_layout.addRow("Price", self.order_price)
        place_order_layout.addRow("Quantity", self.order_quantity)
        place_order_layout.addRow("Order_Type", self.order_type)
        # place_order_layout.addRow('Exchange', self.exchange)
        # place_order_layout.addRow('Account', self.account)
        place_order_layout.addRow(self.btn_order)
        self.setLayout(place_order_layout)

    def place_order(self) -> None:
        """
        This is not tracked by strategy_manager; tracked by global order_manager
        :return:
        """
        s = str(self.sym.text())
        n = self.direction.currentIndex()
        p = str(self.order_price.text())
        q = str(self.order_quantity.text())
        t = self.order_type.currentIndex()

        if s not in self.instrument_meta.keys():
            ss = s.split(" ")
            for i, c in enumerate(ss[0]):
                if c.isdigit():
                    break
                if i < len(ss[0]):
                    sym_root = ss[0][: i - 1]
                    if sym_root in self.instrument_meta.keys():
                        self.instrument_meta[s] = self.instrument_meta[
                            sym_root
                        ]  # add for quick access

        # to be checked by risk manger
        try:
            o = OrderEvent()
            o.order_status = OrderStatus.NEWBORN
            o.full_symbol = s
            o.order_size = int(q) if (n == 0) else -1 * int(q)
            o.create_time = pd.Timestamp.now()
            o.source = 0  # discretionary

            self.order_manager.on_order_status(o)

            if t == 0:
                o.order_type = OrderType.MARKET
                self.broker.place_order(o)
            elif t == 1:
                o.order_type = OrderType.LIMIT
                o.limit_price = float(p)
                self.broker.place_order(o)
            else:
                pass
        except:
            _logger.error("discretionary order error")
            msg = LogEvent()
            msg.timestamp = pd.Timestamp.now()
            msg.content = "discretionary order error"
            self.event_engine.put(msg)
