#!/usr/bin/env python
# -*- coding: utf-8 -*-
# http://stackoverflow.com/questions/9957195/updating-gui-elements-in-multithreaded-pyqt
import sys
import os
import webbrowser
import psutil
from queue import Queue, Empty
from PyQt5 import QtCore, QtWidgets, QtGui
from datetime import datetime

from ..brokerage.ib_brokerage import InteractiveBrokers
from ..event.event import EventType
from ..order.order_flag import OrderFlag
from ..data.data_board import DataBoard
from ..order.order_manager import OrderManager
from ..strategy.strategy_manager import StrategyManager
from ..position.position_manager import PositionManager
from ..risk.risk_manager import PassThroughRiskManager
from ..account.account_manager import AccountManager
from ..event.live_event_engine import LiveEventEngine
from ..order.order_event import OrderEvent
from ..order.order_type import OrderType
from .ui_order_window import OrderWindow
from .ui_fill_window import FillWindow
from .ui_position_window import PositionWindow
from .ui_account_window import AccountWindow
from .ui_strategy_window import StrategyWindow
from .ui_log_window import LogWindow
from .ui_trade_menu import TradeMenu


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, config, strat_dict):
        super(MainWindow, self).__init__()

        ## member variables
        self._current_time = None
        self._config = config
        self.central_widget = None
        self.message_window = None
        self.order_window = None
        self.fill_window = None
        self.position_window = None
        self.account_window = None
        self.strategy_window = None

        self._ui_events_engine = LiveEventEngine()  # update ui
        self._broker = InteractiveBrokers(self._ui_events_engine, self._config['account'])
        self._position_manager = PositionManager()
        self._order_manager = OrderManager()
        self._data_board = DataBoard()
        self.risk_manager = PassThroughRiskManager()
        self.account_manager = AccountManager(self._config['account'])

        self._strategy_manager = StrategyManager(self._config, strat_dict, self._broker, self._order_manager, self._position_manager, self._data_board)

        self.widgets = dict()
        self._schedule_timer = QtCore.QTimer()                  # task scheduler; TODO produce result_packet

        # set up gui windows
        self.setGeometry(50, 50, 600, 400)
        self.setWindowTitle('QuantTrading')
        self.setWindowIcon(QtGui.QIcon("gui/image/logo.ico"))
        self.init_menu()
        self.init_status_bar()
        self.init_central_area()

        ## wire up event handlers
        self._ui_events_engine.register_handler(EventType.TICK, self._tick_event_handler)
        self._ui_events_engine.register_handler(EventType.ORDER, self.order_window.order_status_signal.emit)
        self._ui_events_engine.register_handler(EventType.FILL, self._fill_event_handler)
        self._ui_events_engine.register_handler(EventType.POSITION, self._position_event_handler)
        self._ui_events_engine.register_handler(EventType.ACCOUNT, self.account_window.account_signal.emit)
        self._ui_events_engine.register_handler(EventType.CONTRACT, self._contract_event_handler)
        self._ui_events_engine.register_handler(EventType.HISTORICAL, self._historical_event_handler)
        self._ui_events_engine.register_handler(EventType.LOG, self.log_window.msg_signal.emit)

        ## start
        self._ui_events_engine.start()

        self.connect_to_broker()

    #################################################################################################
    # -------------------------------- Event Handler   --------------------------------------------#
    #################################################################################################
    def connect_to_broker(self):
        self._broker.connect(self._config['host'], self._config['port'], self._config['client_id'])

    def disconnect_from_broker(self):
        self._broker.disconnect()

    def open_trade_widget(self):
        widget = self.widgets.get('trade_menu', None)
        if not widget:
            widget = TradeMenu(self._broker, self._ui_events_engine)
            self.widgets['trade_menu'] = widget
        widget.show()

    def update_status_bar(self, message):
        self.statusBar().showMessage(message)

    def start_strategy(self):
        self.strategy_window.update_status(self.strategy_window.currentRow(), True)

    def pause_strategy(self):
        pass

    def stop_strategy(self):
        self.strategy_window.update_status(self.strategy_window.currentRow(), False)

    def closeEvent(self, a0: QtGui.QCloseEvent):
        print('closing main window')
        self.disconnect_from_broker()
        self._ui_events_engine.stop()

    def _tick_event_handler(self, tick_event):
        self._current_time = tick_event.timestamp

        self._data_board.on_tick(tick_event)       # update databoard
        self._order_manager.on_tick(tick_event)     # check standing stop orders
        self._strategy_manager.on_tick(tick_event)  # feed strategies

    def _order_status_event_handler(self, order_status_event):  # including cancel
        # this is moved to ui_thread for consistency
        pass

    def _fill_event_handler(self, fill_event):
        # update portfolio manager for pnl
        self._order_manager.on_fill(fill_event)  # update order manager with fill
        self._strategy_manager.on_fill(fill_event)  # feed fill to strategy
        self.fill_window.fill_signal.emit(fill_event)     # display
        self.order_window.update_order_status(fill_event.client_order_id,
                                              self._order_manager.retrieve_order(fill_event.client_order_id).order_status)

    def _position_event_handler(self, position_event):
        self._position_manager.on_position(position_event)       # position received
        self.position_window.position_signal.emit(position_event)     # display

    def _account_event_handler(self, account_event):
        pass

    def _contract_event_handler(self, contract_event):
        self._position_manager.on_contract(contract_event)

    def _historical_event_handler(self, historical_event):
        print(historical_event)

    def _outgoing_order_request_handler(self, o):
        """
         process o, check against risk manager and compliance manager
        """
        self.risk_manager.order_in_compliance(o)  # order pointer; modify order directly
        self._order_manager.on_order_status(o)

        msg = o.serialize()
        print('send msg: ' + msg)
        self._outgoing_queue.put(msg)

    def _outgoing_account_request_handler(self, a):
        msg = a.serialize()
        print('send msg: ' + msg)
        self._outgoing_queue.put(msg)

    def _outgoing_position_request_handler(self, p):
        msg = p.serialize()
        print('send msg: ' + msg)
        self._outgoing_queue.put(msg)

    def _outgoing_log_msg_request_handler(self, g):
        self.log_window.update_table(g)           # append to log window
    #################################################################################################
    # ------------------------------ Event Handler Ends --------------------------------------------#
    #################################################################################################

    #################################################################################################
    # -------------------------------- User Interface  --------------------------------------------#
    #################################################################################################
    def init_menu(self):
        menubar = self.menuBar()

        sysMenu = menubar.addMenu('Menu')
        sys_tradeAction = QtWidgets.QAction('Trade', self)
        sys_tradeAction.setStatusTip('Manual Trade')
        sys_tradeAction.triggered.connect(self.open_trade_widget)
        sysMenu.addAction(sys_tradeAction)

        sysMenu.addSeparator()

        # sys|exit
        sys_exitAction = QtWidgets.QAction('Exit', self)
        sys_exitAction.setShortcut('Ctrl+Q')
        sys_exitAction.setStatusTip('Exit_App')
        sys_exitAction.triggered.connect(self.close)
        sysMenu.addAction(sys_exitAction)

    def init_status_bar(self):
        self.statusthread = StatusThread()
        self.statusthread.status_update.connect(self.update_status_bar)
        self.statusthread.start()

    def init_central_area(self):
        self.central_widget = QtWidgets.QWidget()

        hbox = QtWidgets.QHBoxLayout()

        # -------------------------------- top ------------------------------------------#
        top = QtWidgets.QFrame()
        top.setFrameShape(QtWidgets.QFrame.StyledPanel)
        control_layout = QtWidgets.QHBoxLayout()
        self.btn_strat_start = QtWidgets.QPushButton('Start_Strat')
        self.btn_strat_start.clicked.connect(self.start_strategy)
        self.btn_strat_pause = QtWidgets.QPushButton('Pause_Strat')
        self.btn_strat_pause.clicked.connect(self.pause_strategy)
        self.btn_strat_stop = QtWidgets.QPushButton('Stop_Strat')
        self.btn_strat_stop.clicked.connect(self.stop_strategy)
        self.btn_strat_liquidate = QtWidgets.QPushButton('Liquidate_Strat')
        control_layout.addWidget(self.btn_strat_start)
        control_layout.addWidget(self.btn_strat_pause)
        control_layout.addWidget(self.btn_strat_stop)
        control_layout.addWidget(self.btn_strat_liquidate)

        top.setLayout(control_layout)
        # -------------------------------- Bottom ------------------------------------------#
        bottom = QtWidgets.QTabWidget()
        tab1 = QtWidgets.QWidget()
        tab2 = QtWidgets.QWidget()
        tab3 = QtWidgets.QWidget()
        tab4 = QtWidgets.QWidget()
        tab5 = QtWidgets.QWidget()
        tab6 = QtWidgets.QWidget()
        bottom.addTab(tab1, 'Strategy')
        bottom.addTab(tab2, 'Order')
        bottom.addTab(tab3, 'Fill')
        bottom.addTab(tab4, 'Position')
        bottom.addTab(tab5, 'Account')
        bottom.addTab(tab6, 'Log')

        self.strategy_window = StrategyWindow(self._strategy_manager)
        tab1_layout = QtWidgets.QVBoxLayout()
        tab1_layout.addWidget(self.strategy_window)
        tab1.setLayout(tab1_layout)

        self.order_window = OrderWindow(self._order_manager, self._broker)       # cancel_order outgoing nessage
        tab2_layout = QtWidgets.QVBoxLayout()
        tab2_layout.addWidget(self.order_window)
        tab2.setLayout(tab2_layout)

        self.fill_window =FillWindow(self._order_manager)
        tab3_layout = QtWidgets.QVBoxLayout()
        tab3_layout.addWidget(self.fill_window)
        tab3.setLayout(tab3_layout)

        self.position_window = PositionWindow()
        tab4_layout = QtWidgets.QVBoxLayout()
        tab4_layout.addWidget(self.position_window)
        tab4.setLayout(tab4_layout)

        self.account_window = AccountWindow(self.account_manager)
        tab5_layout = QtWidgets.QVBoxLayout()
        tab5_layout.addWidget(self.account_window)
        tab5.setLayout(tab5_layout)

        self.log_window = LogWindow()
        tab6_layout = QtWidgets.QVBoxLayout()
        tab6_layout.addWidget(self.log_window)
        tab6.setLayout(tab6_layout)

        # --------------------------------------------------------------------------------------#
        splitter1 = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        splitter1.addWidget(top)
        splitter1.addWidget(bottom)
        # splitter1.setSizes([10, 100])

        hbox.addWidget(splitter1)
        self.central_widget.setLayout(hbox)
        self.setCentralWidget(self.central_widget)

    #################################################################################################
    # ------------------------------ User Interface End --------------------------------------------#
    #################################################################################################

class StatusThread(QtCore.QThread):
    status_update = QtCore.pyqtSignal(str)

    def __init__(self):
        QtCore.QThread.__init__(self)

    def run(self):
        while True:
            cpuPercent = psutil.cpu_percent()
            memoryPercent = psutil.virtual_memory().percent
            self.status_update.emit('CPU Usage: ' + str(cpuPercent) + '% Memory Usage: ' + str(memoryPercent) + '%')
            self.sleep(1)