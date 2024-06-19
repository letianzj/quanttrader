#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from copy import copy
from datetime import datetime
from threading import Thread

import pandas as pd
from ibapi import utils
from ibapi.account_summary_tags import *
from ibapi.client import EClient
from ibapi.commission_report import CommissionReport

# types
from ibapi.common import *  # @UnusedWildImport
from ibapi.contract import *  # @UnusedWildImport
from ibapi.execution import Execution, ExecutionFilter
from ibapi.order import *  # @UnusedWildImport
from ibapi.order_condition import *  # @UnusedWildImport
from ibapi.order_state import *  # @UnusedWildImport
from ibapi.ticktype import TickType, TickTypeEnum
from ibapi.wrapper import EWrapper

from ..account.account_event import AccountEvent
from ..data.bar_event import BarEvent
from ..data.tick_event import TickEvent
from ..data.tick_event import TickType as QtTickType
from ..event.event import LogEvent
from ..event.live_event_engine import LiveEventEngine
from ..order.fill_event import FillEvent
from ..order.order_event import OrderEvent
from ..order.order_status import OrderStatus
from ..order.order_type import OrderType
from ..position.position_event import PositionEvent
from .brokerage_base import BrokerageBase

_logger = logging.getLogger(__name__)


__all__ = ["InteractiveBrokers"]


class InteractiveBrokers(BrokerageBase):
    def __init__(
        self,
        msg_event_engine: LiveEventEngine,
        tick_event_engine: LiveEventEngine,
        account: str,
    ) -> None:
        """
        Initialize InteractiveBrokers brokerage.

        Currently, the client is strongly coupled to broker without an incoming queue,
        e.g. client calls broker.place_order to place order directly.

        :param msg_event_engine:  used to broadcast messages the broker generates back to client
        :param tick_event_engine:  used to broadcast market data back to client
        :param account: the IB account
        """
        super().__init__()

        self.event_engine = msg_event_engine  # save events to event queue
        self.tick_event_engine = tick_event_engine
        self.api = IBApi(self)  # type: ignore
        self.account = account
        self.contract_detail_request_contract_dict: dict[int, Contract] = (  # type: ignore
            {}
        )  # reqid ==> contract
        self.contract_detail_request_symbol_dict: dict[int, str] = (
            {}
        )  # reqid ==> symbol
        self.sym_contract_dict: dict[str, Contract] = {}  # type: ignore
        self.contract_symbol_dict: dict[int, str] = {}  # conId ==> symbol
        self.market_data_subscription_dict: dict[int, str] = {}  # reqId ==> sym
        self.market_data_tick_dict: dict[int, TickEvent] = (
            {}
        )  # reqid ==> tick_event; to combine tickprice and ticksize
        self.market_depth_subscription_dict: dict[int, str] = {}
        self.market_depth_subscription_reverse_dict: dict[str, int] = {}
        self.market_depth_tick_dict: dict[int, TickEvent] = (
            {}
        )  # to combine tickprice and ticksize
        self.hist_data_request_dict: dict[int, str] = {}
        self.order_dict: dict[int, OrderEvent] = {}  # order id ==> order_event
        self.account_summary_reqid = -1
        self.account_summary = AccountEvent()
        self.account_summary.brokerage = "IB"
        self.clientid = 0
        self.reqid = 0  # next/available reqid

    def connect(
        self, host: str = "127.0.0.1", port: int = 7497, clientId: int = 0
    ) -> None:
        """
        Connect to IB. Request open orders under clientid upon successful connection.

        :param host: host address
        :param port: socket port
        :param clientId: client id
        """
        self.clientid = clientId
        if self.api.connected:
            return

        self.api.connect(host, port, clientId=clientId)
        self.api.thread.start()
        self.reqCurrentTime()

        if clientId == 0:
            # associate TWS with the client
            _logger.info(f"connected {self.api.isConnected()}... request open orders")
            self.api.reqAutoOpenOrders(True)

    def disconnect(self) -> None:
        """
        Disconnect from IB
        """
        if not self.api.isConnected():
            return

        self.api.connected = False
        # self.api.conn.disconnect()
        self.api.conn.socket = None
        self.api.disconnect()
        _logger.info(f"disconnected {self.api.isConnected()}")

    def _calculate_commission(
        self, full_symbol: str, fill_price: float, fill_size: int
    ) -> float:
        """"""
        raise NotImplementedError("Implement this in your derived class")

    def next_order_id(self) -> int:
        """
        Return next available order id

        :return: next order id available for next orders
        """
        return self.orderid

    def place_order(self, order_event: OrderEvent) -> None:
        """
        Place order to IB

        :param order_event: client order to be placed
        :return: no return. An order event is pushed to message queue with order status Acknowledged
        """
        if not self.api.connected:
            return

        ib_contract = InteractiveBrokers.symbol_to_contract(order_event.full_symbol)
        if not ib_contract:
            _logger.error(
                f"Failed to find contract to place order {order_event.full_symbol}"
            )
            return

        ib_order = InteractiveBrokers.order_to_ib_order(order_event)
        if not ib_order:
            _logger.error(f"Failed to create order to place {order_event.full_symbol}")
            return

        ib_order.eTradeOnly = False  # The EtradeOnly IBApi.Order attribute is no longer supported. Error received with TWS versions 983+
        ib_order.firmQuoteOnly = False  # The firmQuoteOnly IBApi.Order attribute is no longer supported. Error received with TWS versions 983+
        if order_event.order_id < 0:
            order_event.order_id = self.orderid
            self.orderid += 1
        order_event.account = self.account
        order_event.timestamp = pd.Timestamp.now()
        order_event.order_status = OrderStatus.ACKNOWLEDGED  # acknowledged
        self.order_dict[order_event.order_id] = order_event
        _logger.info(
            f"Order acknowledged {order_event.order_id}, {order_event.full_symbol}"
        )
        self.event_engine.put(copy(order_event))
        self.api.placeOrder(order_event.order_id, ib_contract, ib_order)

    def cancel_order(self, order_id: int) -> None:
        """
        Cancel client order.

        :param order_id: order id of the order to be canceled
        :return: no return. If order is successfully canceled, IB will return an orderstatus message.
        """
        if not self.api.connected:
            return

        if not order_id in self.order_dict.keys():
            _logger.error(f"Order to cancel not found. order id {order_id}")
            return

        self.order_dict[order_id].cancel_time = pd.Timestamp.now()

        self.api.cancelOrder(order_id)

    def cancel_all_orders(self) -> None:
        """
        Cancel all standing orders, for example, before one wants to shut down completely for some reasons.

        """
        self.api.reqGlobalCancel()

    def subscribe_market_data(self, sym: str) -> None:
        """
        Subscribe market L1 data. Market data for this symbol will then be streamed to client.

        :param sym: the symbol to be subscribed.
        """
        if not self.api.connected:
            return

        # it's not going to re-subscribe, because we only call subscribe_market_datas
        # if sym in self.market_data_subscription_reverse_dict.keys():
        #     return

        contract = InteractiveBrokers.symbol_to_contract(sym)
        if not contract:
            _logger.error(f"Failed to find contract to subscribe market data: {sym}")
            return

        self.api.reqContractDetails(self.reqid, contract)
        _logger.info(f"Requesting market data {self.reqid} {sym}")
        self.contract_detail_request_contract_dict[self.reqid] = contract
        self.contract_detail_request_symbol_dict[self.reqid] = sym
        self.reqid += 1
        self.api.reqMktData(self.reqid, contract, "", False, False, [])
        tick_event = TickEvent()
        tick_event.full_symbol = sym
        self.market_data_subscription_dict[self.reqid] = sym
        self.market_data_subscription_reverse_dict[sym] = self.reqid
        self.market_data_tick_dict[self.reqid] = tick_event
        self.reqid += 1

    def subscribe_market_datas(self) -> None:
        """
        Subscribe market L1 data for all symbols used in strategies. Market data for this symbol will then be streamed to client.

        """
        syms = list(self.market_data_subscription_reverse_dict.keys())
        for sym in syms:
            self.subscribe_market_data(sym)

    def unsubscribe_market_data(self, sym: str) -> None:
        """
        Unsubscribe market L1 data. Market data for this symbol will stop streaming to client.

        :param sym: the symbol to be subscribed.
        """
        if not self.api.connected:
            return

        if not sym in self.market_data_subscription_reverse_dict.keys():
            return

        self.api.cancelMktData(self.market_data_subscription_reverse_dict[sym])

    def subscribe_market_depth(self, sym: str) -> None:
        """
        Subscribe market L2 data. Market data for this symbol will then be streamed to client.

        :param sym: the symbol to be subscribed.
        """
        if not self.api.connected:
            return

        if sym in self.market_depth_subscription_reverse_dict.keys():
            return

        contract = InteractiveBrokers.symbol_to_contract(sym)
        if not contract:
            _logger.error(f"Failed to find contract to subscribe market depth: {sym}")
            return

        self.api.reqMktDepth(self.reqid, contract, 5, True, [])
        self.reqid += 1
        self.market_depth_subscription_dict[self.reqid] = sym
        self.market_depth_subscription_reverse_dict[sym] = self.reqid

    def unsubscribe_market_depth(self, sym: str) -> None:
        """
        Unsubscribe market L2 data. Market data for this symbol will stop streaming to client.

        :param sym: the symbol to be subscribed.
        """
        if not self.api.connected:
            return

        if not sym in self.market_depth_subscription_reverse_dict.keys():
            return

        self.api.cancelMktDepth(self.market_depth_subscription_reverse_dict[sym], True)

    def subscribe_account_summary(self) -> None:
        """
        Request account summary from broker
        """
        if not self.api.connected:
            return

        if self.account_summary_reqid > 0:  # subscribed
            return

        self.account_summary_reqid = self.reqid
        self.api.reqAccountSummary(self.account_summary_reqid, "All", "$LEDGER")
        self.reqid += 1

    def unsubscribe_account_summary(self) -> None:
        """
        Stop receiving account summary from broker
        """
        if not self.api.connected:
            return

        if self.account_summary_reqid == -1:
            return

        self.api.cancelAccountSummary(self.account_summary_reqid)
        self.account_summary_reqid = -1

    def subscribe_positions(self) -> None:
        """
        Request existing positions from broker
        """
        self.api.reqPositions()

    def unsubscribe_positions(self) -> None:
        """
        Stop receiving existing position message from broker.
        """
        self.api.cancelPositions()

    def request_historical_data(self, symbol: str, end: datetime | None = None) -> None:
        """
        Request 1800 S (30 mins) historical bar data from Interactive Brokers.

        :param symbol: the contract whose historical data is requested
        :param end: the end time of the historical data
        :return: no returns; data is broadcasted through message queue
        """
        ib_contract = InteractiveBrokers.symbol_to_contract(symbol)

        if end:
            end_str = end.strftime("%Y%m%d %H:%M:%S")
        else:
            end_str = ""

        self.hist_data_request_dict[self.reqid] = symbol
        self.api.reqHistoricalData(
            self.reqid,
            ib_contract,
            end_str,
            "1800 S",
            "1 secs",
            "TRADES",
            1,
            1,
            False,
            [],
        )  # first 1 is useRTH
        self.reqid += 1

    def cancel_historical_data(self, reqid: int) -> None:
        """
        Cancel historical data request. Usually not necessary.

        :param reqid: the historical data request id
        """
        self.api.cancelHistoricalData(reqid)

    def request_historical_ticks(
        self, symbol: str, start_time: str, reqtype: str = "TICKS"
    ) -> None:
        """
        Request historical time and sales data from Interactive Brokers.
        See here https://interactivebrokers.github.io/tws-api/historical_time_and_sales.html

        :param symbol: the contract whose historical data is requested
        :param start_time:  i.e. "20170701 12:01:00". Uses TWS timezone specified at login
        :param reqtype: TRADES, BID_ASK, or MIDPOINT
        :return: no returns; data is broadcasted through message queue
        """
        ib_contract = InteractiveBrokers.symbol_to_contract(symbol)
        useRth = 1
        self.hist_data_request_dict[self.reqid] = symbol
        self.api.reqHistoricalTicks(
            self.reqid,
            ib_contract,
            start_time,
            "",
            1000,
            reqtype,
            useRth,
            True,
            [],
        )
        self.reqid += 1

    def reqCurrentTime(self) -> None:
        """
        Request server time on broker side
        """
        self.api.reqCurrentTime()

    def setServerLogLevel(self, level: int = 1) -> None:
        """
        Set server side log level or the log messages received from server.

        :param level: log level
        """
        self.api.setServerLogLevel(level)

    def heartbeat(self) -> None:
        """
        Request server time as heartbeat
        """
        if self.api.isConnected():
            _logger.info("reqPositions")
            # self.api.reqPositions()
            self.reqCurrentTime()  # EWrapper::currentTime

    def log(self, msg: str) -> None:
        """
        Broadcast server log message through message queue

        :param msg: message to be broadcast
        :return: no return; log meesage is placed into message queue
        """

        log_event = LogEvent()
        log_event.timestamp = pd.Timestamp.now()
        log_event.content = msg
        self.event_engine.put(log_event)

    @staticmethod
    def symbol_to_contract(symbol: str) -> Contract:  # type: ignore
        """
        Convert fulll symbol string to IB contract

        TODO
        CL.HO BAG 174230608 1 NYMEX 257430162 1 NYMEX NYMEX     # Inter-comdty
        ES.NQ BAG 371749798 1 GLOBEX 371749745 1 GLOBEX GLOBEX     # Inter-comdty
        CL.HO BAG 257430162 1 NYMEX 174230608 1 NYMEX NYMEX

        :param symbol: full symbol, e.g. AMZN STK SMART
        :return: IB contract
        """
        symbol_fields = symbol.split(" ")
        ib_contract = Contract()  # type: ignore

        if symbol_fields[1] == "STK":
            ib_contract.localSymbol = symbol_fields[0]
            ib_contract.secType = symbol_fields[1]
            ib_contract.currency = "USD"
            ib_contract.exchange = symbol_fields[2]
        elif symbol_fields[1] == "CASH":
            ib_contract.symbol = symbol_fields[0][0:3]  # EUR
            ib_contract.secType = symbol_fields[1]  # CASH
            ib_contract.currency = symbol_fields[0][3:]  # GBP
            ib_contract.exchange = symbol_fields[2]  # IDEALPRO
        elif symbol_fields[1] == "FUT":
            ib_contract.localSymbol = symbol_fields[0].replace(
                "_", " "
            )  # ESM9, in case YM___SEP_20
            ib_contract.secType = symbol_fields[1]  # FUT
            ib_contract.exchange = symbol_fields[2]  # GLOBEX
            ib_contract.currency = "USD"
        elif symbol_fields[1] == "OPT":  # AAPL OPT 20201016 128.75 C SMART
            ib_contract.symbol = symbol_fields[0]  # AAPL
            ib_contract.secType = symbol_fields[1]  # OPT
            ib_contract.lastTradeDateOrContractMonth = symbol_fields[2]  # 20201016
            ib_contract.strike = (
                float(symbol_fields[3])
                if "." in symbol_fields[3]
                else int(symbol_fields[3])
            )  # 128.75
            ib_contract.right = symbol_fields[4]  # C
            ib_contract.exchange = symbol_fields[5]  # SMART
            ib_contract.currency = "USD"
            ib_contract.multiplier = "100"
        elif symbol_fields[1] == "FOP":  # ES FOP 20200911 3450 C 50 GLOBEX
            ib_contract.symbol = symbol_fields[0]  # ES
            ib_contract.secType = symbol_fields[1]  # FOP
            ib_contract.lastTradeDateOrContractMonth = symbol_fields[2]  # 20200911
            ib_contract.strike = (
                float(symbol_fields[3])
                if "." in symbol_fields[3]
                else int(symbol_fields[3])
            )  # 128.75
            ib_contract.right = symbol_fields[4]  # C
            ib_contract.multiplier = symbol_fields[5]  # 50
            ib_contract.exchange = symbol_fields[6]  # GLOBEX
            ib_contract.currency = "USD"
        elif symbol_fields[1] == "CMDTY":  # XAUUSD CMDTY SMART
            ib_contract.symbol = symbol_fields[0]  # XAUUSD
            ib_contract.secType = symbol_fields[1]  # COMDTY
            ib_contract.currency = "USD"
            ib_contract.exchange = symbol_fields[2]  # SMART
        elif symbol_fields[1] == "BAG":
            ib_contract.symbol = symbol_fields[0]  # CL.BZ
            ib_contract.secType = symbol_fields[1]  # BAG

            leg1 = ComboLeg()  # type: ignore
            leg1.conId = int(symbol_fields[2])  # 174230608
            leg1.ratio = int(symbol_fields[3])  # 1
            leg1.action = "BUY"
            leg1.exchange = symbol_fields[4]  # NYMEX

            leg2 = ComboLeg()  # type: ignore
            leg2.conId = int(symbol_fields[5])  # 162929662
            leg2.ratio = int(symbol_fields[6])  # 1
            leg2.action = "SELL"
            leg2.exchange = symbol_fields[7]  # NYMEX

            ib_contract.comboLegs = []
            ib_contract.comboLegs.append(leg1)
            ib_contract.comboLegs.append(leg2)

            ib_contract.exchange = symbol_fields[8]  # NYMEX
            ib_contract.currency = "USD"
        else:
            _logger.error(f"invalid contract {symbol}")

        return ib_contract

    @staticmethod
    def contract_to_symbol(ib_contract: Contract) -> str:  # type: ignore
        """
        Convert IB contract to full symbol

        :param ib_contract: IB contract
        :return: full symbol
        """
        full_symbol = ""
        if ib_contract.secType == "STK":
            full_symbol = " ".join(
                [ib_contract.localSymbol, "STK", "SMART"]
            )  # or ib_contract.primaryExchange?
        elif ib_contract.secType == "CASH":
            full_symbol = " ".join(
                [
                    ib_contract.symbol + ib_contract.currency,
                    "CASH",
                    ib_contract.exchange,
                ]
            )
        elif ib_contract.secType == "FUT":
            full_symbol = " ".join(
                [
                    ib_contract.localSymbol.replace(" ", "_"),
                    "FUT",
                    (
                        ib_contract.primaryExchange
                        if ib_contract.primaryExchange != ""
                        else ib_contract.exchange
                    ),
                ]
            )
        elif ib_contract.secType == "OPT":
            full_symbol = " ".join(
                [
                    ib_contract.symbol,
                    "OPT",
                    ib_contract.lastTradeDateOrContractMonth,
                    str(ib_contract.strike),
                    ib_contract.right,
                    "SMART",
                ]
            )
        elif ib_contract.secType == "FOP":
            full_symbol = " ".join(
                [
                    ib_contract.symbol,
                    "FOP",
                    ib_contract.lastTradeDateOrContractMonth,
                    str(ib_contract.strike),
                    ib_contract.right,
                    ib_contract.multiplier,
                    ib_contract.exchange,
                ]
            )
        elif ib_contract.secType == "COMDTY":
            full_symbol = " ".join([ib_contract.symbol, "COMDTY", "SMART"])
        elif ib_contract.secType == "BAG":
            full_symbol = " ".join([ib_contract.symbol, "COMDTY", "SMART"])

        return full_symbol

    @staticmethod
    def order_to_ib_order(order_event: OrderEvent) -> Order:  # type: ignore
        """
        Convert order event to IB order

        :param order_event: internal representation of order
        :return:  IB representation of order
        """
        ib_order = Order()  # type: ignore
        ib_order.action = "BUY" if order_event.order_size > 0 else "SELL"
        ib_order.totalQuantity = abs(order_event.order_size)
        if order_event.order_type == OrderType.MARKET:
            ib_order.orderType = "MKT"
        elif order_event.order_type == OrderType.LIMIT:
            ib_order.orderType = "LMT"
            ib_order.lmtPrice = order_event.limit_price
        elif order_event.order_type == OrderType.STOP:
            ib_order.orderType = "STP"
            ib_order.auxPrice = order_event.stop_price
        elif order_event.order_type == OrderType.STOP_LIMIT:
            ib_order.orderType = "STP LMT"
            ib_order.lmtPrice = order_event.limit_price
            ib_order.auxPrice = order_event.stop_price
        else:
            return None

        return ib_order

    @staticmethod
    def ib_order_to_order(ib_order: Order) -> OrderEvent:  # type: ignore
        """
        Convert IB order to order event

        :param ib_order: IB representation of order
        :return: internal representation of order
        """
        order_event = OrderEvent()
        # order_event.order_id = orderId
        # order_event.order_status = orderState.status
        direction = 1 if ib_order.action == "BUY" else -1
        order_event.order_size = ib_order.totalQuantity * direction
        if ib_order.orderType == "MKT":
            order_event.order_type = OrderType.MARKET
        elif ib_order.orderType == "LMT":
            order_event.order_type = OrderType.LIMIT
            order_event.limit_price = ib_order.lmtPrice
        elif ib_order.orderType == "STP":
            order_event.order_type = OrderType.STOP
            order_event.stop_price = ib_order.auxPrice
        elif ib_order.orderType == "STP LMT":
            order_event.order_type = OrderType.STOP_LIMIT
            order_event.limit_price = ib_order.lmtPrice
            order_event.stop_price = ib_order.auxPrice
        else:
            order_event.order_type = OrderType.UNKNOWN
            order_event.limit_price = ib_order.lmtPrice
            order_event.stop_price = ib_order.auxPrice

        return order_event


class IBApi(EWrapper, EClient):  # type: ignore
    def __init__(self, broker: InteractiveBrokers) -> None:
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)

        self.broker = broker
        self.thread = Thread(target=self.run)

        self.nKeybInt = 0
        self.connected = False
        self.globalCancelOnly = False
        self.simplePlaceOid = None

    # ------------------------------------------ EClient functions --------------------------------------- #
    def keyboardInterrupt(self) -> None:
        self.nKeybInt += 1
        if self.nKeybInt == 1:
            self.stop()
        else:
            _logger.info("Finishing test")

    def stop(self) -> None:
        _logger.info("Executing cancels")
        _logger.info("Executing cancels ... finished")

    # ------------------------------------------------------------------ End EClient functions -------------------------------------------------------- #

    # ---------------------------------------------------------------------- EWrapper functions -------------------------------------------------------- #
    def connectAck(self) -> None:
        if self.asynchronous:
            self.startApi()
        self.connected = True
        _logger.info("IB connected")

    def nextValidId(self, orderId: int) -> None:
        super().nextValidId(orderId)
        msg = f"nextValidOrderId: {orderId}"
        _logger.info(msg)
        self.broker.log(msg)
        self.broker.orderid = orderId

        # we can start now
        self.broker.subscribe_market_datas()

    def error(self, reqId: TickerId, errorCode: int, errorString: str) -> None:  # type: ignore
        super().error(reqId, errorCode, errorString)
        msg = f"Error. id: {reqId}, Code: {errorCode}, Msg: {errorString}"
        _logger.error(msg)
        self.broker.log(msg)

    def winError(self, text: str, lastError: int) -> None:
        super().winError(text, lastError)
        msg = f"Error Id: {lastError}, Msg: {text}"
        _logger.error(msg)
        self.broker.log(msg)

    def openOrder(
        self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState  # type: ignore
    ) -> None:
        """
        Currently IB sends out two openOrder and two OrderStatus; so there are four filled order_status sent out
        """
        super().openOrder(orderId, contract, order, orderState)
        msg = (
            f"OpenOrder. PermId: {order.permId}, ClientId:  {order.clientId}, OrderId: {orderId}, "
            f"Account: {order.account}, Symbol: {contract.symbol}, SecType: {contract.secType}, "
            f"Exchange: {contract.exchange}, Action: {order.action}, OrderType: {order.orderType}, "
            f"TotalQty: {order.totalQuantity}, CashQty: {order.cashQty}, LmtPrice: {order.lmtPrice}, "
            f"AuxPrice: {order.auxPrice}, Status: {orderState.status}"
        )
        _logger.info(msg)
        self.broker.log(msg)

        if orderId in self.broker.order_dict.keys():
            order_event = self.broker.order_dict[orderId]
        else:  # not placed by algo
            order_event = InteractiveBrokers.ib_order_to_order(order)
            order_event.order_id = orderId
            order_event.full_symbol = InteractiveBrokers.contract_to_symbol(contract)
            order_event.account = self.broker.account
            order_event.create_time = pd.Timestamp(datetime.now())
            order_event.source = -1  # unrecognized source
            self.broker.order_dict[orderId] = order_event

        if orderState.status == "Submitted":
            order_event.order_status = OrderStatus.SUBMITTED
        elif orderState.status == "Filled":
            order_event.order_status = OrderStatus.FILLED
        elif orderState.status == "PreSubmitted":
            order_event.order_status = OrderStatus.PENDING_SUBMIT
        elif orderState.status == "Cancelled":
            order_event.order_status = OrderStatus.CANCELED
        elif orderState.status == "Inactive":  # e.g. exchange closed
            order_event.order_status = OrderStatus.ERROR
        else:
            order_event.order_status = OrderStatus.UNKNOWN

        self.broker.event_engine.put(copy(order_event))

    def openOrderEnd(self) -> None:
        super().openOrderEnd()
        _logger.info("OpenOrderEnd")
        _logger.info(f"Received openOrders {len(list(self.broker.order_dict.keys()))}")

    def orderStatus(
        self,
        orderId: OrderId,  # type: ignore
        status: str,
        filled: float,
        remaining: float,
        avgFillPrice: float,
        permId: int,
        parentId: int,
        lastFillPrice: float,
        clientId: int,
        whyHeld: str,
        mktCapPrice: float,
    ) -> None:

        super().orderStatus(
            orderId,
            status,
            filled,
            remaining,
            avgFillPrice,
            permId,
            parentId,
            lastFillPrice,
            clientId,
            whyHeld,
            mktCapPrice,
        )
        msg = (
            f"OrderStatus. Id: {orderId}, Status: {status}, Filled: {filled}, "
            f"Remaining: {remaining}, AvgFillPrice: {avgFillPrice}, PermId: {permId}, ParentId: {parentId}, "
            f"LastFillPrice: {lastFillPrice}, ClientId: {clientId}, WhyHeld: {whyHeld}, MktCapPrice: {mktCapPrice}"
        )
        _logger.info(msg)
        self.broker.log(msg)

        order_event = self.broker.order_dict.get(orderId, None)
        if order_event is None:
            msg = f"OrderStatus: Unable to find order {orderId}"
            _logger.error(msg)
            self.broker.log(msg)
            order_event = OrderEvent()
            order_event.order_id = orderId
            order_event.account = self.broker.account
            order_event.order_size = int(filled + remaining)
            order_event.fill_size = int(filled)
            order_event.order_type = OrderType.UNKNOWN
            order_event.order_status = OrderStatus.UNKNOWN
            # order_event.order_time = datetime.now().strftime("%H:%M:%S.%f")
            order_event.create_time = pd.Timestamp.now()
            order_event.source = -1  # unrecognized source
            self.broker.order_dict[orderId] = order_event

        if status == "Submitted":
            order_event.order_status = OrderStatus.SUBMITTED
        elif status == "Filled":
            order_event.order_status = OrderStatus.FILLED
        elif status == "PreSubmitted":
            order_event.order_status = OrderStatus.PENDING_SUBMIT
        elif status == "Cancelled" or status == "ApiCancelled":
            order_event.order_status = OrderStatus.CANCELED
            order_event.fill_size = int(filled)  # remaining = order_size - fill_size
            order_event.cancel_time = pd.Timestamp.now()
        elif status == "Inactive":  # e.g. exchange closed
            order_event.order_status = OrderStatus.ERROR
        else:
            order_event.order_status = OrderStatus.UNKNOWN
        order_event.fill_size = int(filled)

        self.broker.event_engine.put(copy(order_event))

    def managedAccounts(self, accountsList: str) -> None:
        super().managedAccounts(accountsList)
        msg = f"Account list:, {accountsList}"
        _logger.info(msg)
        self.broker.log(msg)

        self.broker.account = accountsList.split(",")[0]
        self.reqAccountUpdates(True, self.broker.account)

    def accountSummary(
        self, reqId: int, account: str, tag: str, value: str, currency: str
    ) -> None:
        super().accountSummary(reqId, account, tag, value, currency)
        msg = f"AccountSummary. ReqId: {reqId}, Account: {account}, Tag: {tag}, Value: {value}, Currency: {currency}"
        _logger.info(msg)
        self.broker.log(msg)

    def accountSummaryEnd(self, reqId: int) -> None:
        super().accountSummaryEnd(reqId)
        _logger.info(f"AccountSummaryEnd. ReqId: {reqId}")

    def updateAccountValue(
        self, key: str, val: str, currency: str, accountName: str
    ) -> None:
        """
        Just as with the TWS' Account Window, unless there is a position change this information is updated at a fixed interval of three minutes.
        """
        super().updateAccountValue(key, val, currency, accountName)
        msg = f"UpdateAccountValue. Key: {key}, Value: {val},  Currency: {currency}, AccountName: {accountName}"
        _logger.info(msg)

        self.broker.account_summary.timestamp = datetime.now().strftime("%H:%M:%S.%f")

        if key == "NetLiquidationByCurrency" and currency == "USD":
            self.broker.account_summary.balance = float(val)
        elif key == "NetLiquidation" and currency == "USD":
            self.broker.account_summary.balance = float(val)
            self.broker.account_summary.account_id = accountName
        elif key == "AvailableFunds" and currency == "USD":
            self.broker.account_summary.available = float(val)
        elif key == "MaintMarginReq" and currency == "USD":
            self.broker.account_summary.margin = float(val)
        elif key == "RealizedPnL" and currency == "USD":
            self.broker.account_summary.closed_pnl = float(val)
        elif key == "UnrealizedPnL" and currency == "USD":
            self.broker.account_summary.open_pnl = float(val)
            self.broker.event_engine.put(
                self.broker.account_summary
            )  # assume alphabatic order

    def updatePortfolio(
        self,
        contract: Contract,  # type: ignore
        position: float,
        marketPrice: float,
        marketValue: float,
        averageCost: float,
        unrealizedPNL: float,
        realizedPNL: float,
        accountName: str,
    ) -> None:
        """
        Just as with the TWS' Account Window, unless there is a position change this information is updated at a fixed interval of three minutes.
        """
        super().updatePortfolio(
            contract,
            position,
            marketPrice,
            marketValue,
            averageCost,
            unrealizedPNL,
            realizedPNL,
            accountName,
        )
        msg = (
            f"UpdatePortfolio. Symbol: {contract.symbol}, SecType: {contract.secType}, Exchange: {contract.exchange}, "
            f"Position: {position}, MarketPrice: {marketPrice}, MarketValue: {marketValue}, AverageCost: {averageCost}, "
            f"UnrealizedPNL: {unrealizedPNL}, RealizedPNL: {realizedPNL}, AccountName: {accountName}"
        )
        _logger.info(msg)

        position_event = PositionEvent()
        position_event.full_symbol = InteractiveBrokers.contract_to_symbol(contract)
        position_event.sec_type = contract.secType
        position_event.account = accountName
        position_event.size = int(position)
        try:
            multiplier = int(contract.multiplier)
        except ValueError:
            multiplier = 1
        position_event.average_cost = averageCost / multiplier
        position_event.realized_pnl = realizedPNL
        position_event.unrealized_pnl = unrealizedPNL
        position_event.timestamp = datetime.now().strftime("%H:%M:%S.%f")
        self.broker.event_engine.put(position_event)

    def updateAccountTime(self, timeStamp: str) -> None:
        super().updateAccountTime(timeStamp)
        msg = f"UpdateAccountTime. Time: {timeStamp}"
        _logger.info(msg)
        self.broker.log(msg)
        # self.broker.event_engine.put(self.broker.account)

    def accountDownloadEnd(self, accountName: str) -> None:
        super().accountDownloadEnd(accountName)
        msg = f"AccountDownloadEnd. Account: {accountName}"
        _logger.info(msg)

    def position(
        self, account: str, contract: Contract, position: float, avgCost: float  # type: ignore
    ) -> None:
        super().position(account, contract, position, avgCost)
        msg = (
            f"Position. Account: {account}, Symbol: {contract.symbol}, SecType: {contract.secType}, "
            f"Currency: {contract.currency}, Position: {position}, Avg cost: {avgCost}"
        )
        _logger.info(msg)

    def positionEnd(self) -> None:
        super().positionEnd()
        _logger.info("PositionEnd")

    def positionMulti(
        self,
        reqId: int,
        account: str,
        modelCode: str,
        contract: Contract,  # type: ignore
        pos: float,
        avgCost: float,
    ) -> None:
        super().positionMulti(reqId, account, modelCode, contract, pos, avgCost)
        msg = (
            f"PositionMulti. RequestId: {reqId}, Account: {account}, ModelCode: {modelCode}, Symbol: {contract.symbol}, "
            f"SecType: {contract.secType}, Currency: {contract.currency}, Position: {pos}, AvgCost: {avgCost}"
        )
        _logger.info(msg)

    def positionMultiEnd(self, reqId: int) -> None:
        super().positionMultiEnd(reqId)
        _logger.info(f"PositionMultiEnd. RequestId: {reqId}")

    def accountUpdateMulti(
        self,
        reqId: int,
        account: str,
        modelCode: str,
        key: str,
        value: str,
        currency: str,
    ) -> None:
        super().accountUpdateMulti(reqId, account, modelCode, key, value, currency)
        msg = (
            f"AccountUpdateMulti. RequestId: {reqId}, Account: {account}, ModelCode: {modelCode}, Key: {key}, "
            f"Value: {value}, Currency: {currency}"
        )
        _logger.info(msg)

    def accountUpdateMultiEnd(self, reqId: int) -> None:
        super().accountUpdateMultiEnd(reqId)
        _logger.info(f"AccountUpdateMultiEnd. RequestId: {reqId}")

    def familyCodes(self, familyCodes: ListOfFamilyCode) -> None:  # type: ignore
        super().familyCodes(familyCodes)
        _logger.info("Family Codes:")
        for familyCode in familyCodes:
            _logger.info(f"FamilyCode. {familyCode}")

    def pnl(
        self,
        reqId: int,
        dailyPnL: float,
        unrealizedPnL: float,
        realizedPnL: float,
    ) -> None:
        super().pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)
        msg = f"Daily PnL. ReqId: {reqId}, DailyPnL: {dailyPnL}, UnrealizedPnL: {unrealizedPnL}, RealizedPnL: {realizedPnL}"
        _logger.info(msg)

    def pnlSingle(
        self,
        reqId: int,
        pos: int,
        dailyPnL: float,
        unrealizedPnL: float,
        realizedPnL: float,
        value: float,
    ) -> None:
        super().pnlSingle(reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value)
        msg = (
            f"Daily PnL Single. ReqId: {reqId}, Position: {pos}, DailyPnL: {dailyPnL}, UnrealizedPnL: {unrealizedPnL}, "
            f"RealizedPnL: {realizedPnL}, Value: {value}"
        )
        _logger.info(msg)

    def marketDataType(self, reqId: TickerId, marketDataType: int) -> None:  # type: ignore
        super().marketDataType(reqId, marketDataType)
        _logger.info(f"MarketDataType. ReqId: {reqId}, Type: {marketDataType}")

    def tickPrice(
        self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib  # type: ignore
    ) -> None:
        super().tickPrice(reqId, tickType, price, attrib)

        tick_event = self.broker.market_data_tick_dict[reqId]
        tick_event.timestamp = datetime.now()
        if TickTypeEnum.to_str(tickType) == "BID":
            tick_event.tick_type = QtTickType.BID
            tick_event.bid_price_L1 = price
        elif TickTypeEnum.to_str(tickType) == "ASK":
            tick_event.tick_type = QtTickType.ASK
            tick_event.ask_price_L1 = price
        elif TickTypeEnum.to_str(tickType) == "LAST":
            tick_event.tick_type = QtTickType.TRADE
            tick_event.price = price
        else:
            return

        self.broker.tick_event_engine.put(copy(tick_event))

    def tickSize(self, reqId: TickerId, tickType: TickType, size: int) -> None:  # type: ignore
        super().tickSize(reqId, tickType, size)

        tick_event = self.broker.market_data_tick_dict[reqId]
        tick_event.timestamp = datetime.now()
        if TickTypeEnum.to_str(tickType) == "BID_SIZE":
            tick_event.tick_type = QtTickType.BID
            tick_event.bid_size_L1 = size
        elif TickTypeEnum.to_str(tickType) == "ASK_SIZE":
            tick_event.tick_type = QtTickType.ASK
            tick_event.ask_size_L1 = size
        elif TickTypeEnum.to_str(tickType) == "LAST_SIZE":
            tick_event.tick_type = QtTickType.TRADE
            tick_event.size = size
        else:
            return

        self.broker.tick_event_engine.put(copy(tick_event))

    def tickGeneric(self, reqId: TickerId, tickType: TickType, value: float) -> None:  # type: ignore
        super().tickGeneric(reqId, tickType, value)
        # _logger.info(f"TickGeneric. TickerId: {reqId}, TickType: {tickType}, Value: {value}")
        pass

    def tickString(self, reqId: TickerId, tickType: TickType, value: str) -> None:  # type: ignore
        super().tickString(reqId, tickType, value)
        pass
        # tick_event = self.broker.market_data_tick_dict[reqId]
        # tick_event.timestamp = datetime.fromtimestamp(int(value))
        # self.broker.tick_event_engine.put(copy(tick_event))

    def tickSnapshotEnd(self, reqId: int) -> None:
        super().tickSnapshotEnd(reqId)
        msg = f"TickSnapshotEnd. TickerId: {reqId}"
        _logger.info(msg)

    def rerouteMktDataReq(self, reqId: int, conId: int, exchange: str) -> None:
        super().rerouteMktDataReq(reqId, conId, exchange)
        msg = f"Re-route market data request. ReqId: {reqId}, ConId: {conId}, Exchange: {exchange}"
        _logger.info(msg)

    def marketRule(self, marketRuleId: int, priceIncrements: ListOfPriceIncrements) -> None:  # type: ignore
        super().marketRule(marketRuleId, priceIncrements)
        msg = f"Market Rule ID: {marketRuleId}"
        _logger.info(msg)
        for priceIncrement in priceIncrements:
            msg = f"Price Increment. {priceIncrement}"
            _logger.info(msg)

    def orderBound(self, reqId: int, apiClientId: int, apiOrderId: int) -> None:

        super().orderBound(reqId, apiClientId, apiOrderId)
        msg = f"OrderBound. OrderId: {reqId}, ApiClientId: {apiClientId}, ApiOrderId: {apiOrderId}"
        _logger.info(msg)

    def tickByTickAllLast(
        self,
        reqId: int,
        tickType: int,
        time: int,
        price: float,
        size: int,
        tickAttribLast: TickAttribLast,  # type: ignore
        exchange: str,
        specialConditions: str,
    ) -> None:

        super().tickByTickAllLast(
            reqId,
            tickType,
            time,
            price,
            size,
            tickAttribLast,
            exchange,
            specialConditions,
        )
        if tickType == 1:
            _logger.info("Last.")
        else:
            _logger.info("AllLast.")
        msg = (
            f'ReqId: {reqId}, Time: {datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S")}, '
            f"Price: {price}, Size: {size}, Exch: {exchange}, Spec Cond: {specialConditions}, "
            f"PastLimit: {tickAttribLast.pastLimit}, Unreported: {tickAttribLast.unreported}"
        )
        _logger.info(msg)

    def tickByTickBidAsk(
        self,
        reqId: int,
        time: int,
        bidPrice: float,
        askPrice: float,
        bidSize: int,
        askSize: int,
        tickAttribBidAsk: TickAttribBidAsk,  # type: ignore
    ) -> None:
        super().tickByTickBidAsk(
            reqId, time, bidPrice, askPrice, bidSize, askSize, tickAttribBidAsk
        )
        msg = (
            f'BidAsk. ReqId: {reqId}, Time: {datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S")}, '
            f"BidPrice: {bidPrice}, AskPrice: {askPrice}, BidSize: {bidSize}, AskSize: {askSize}, "
            f"BidPastLow: {tickAttribBidAsk.bidPastLow}, AskPastHigh: {tickAttribBidAsk.askPastHigh}"
        )
        _logger.info(msg)

    def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float) -> None:
        super().tickByTickMidPoint(reqId, time, midPoint)
        msg = 'Midpoint. ReqId: {reqId}, Time: {datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S")}, MidPoint: {midPoint}'
        _logger.info(msg)

    def updateMktDepth(
        self,
        reqId: TickerId,  # type: ignore
        position: int,
        operation: int,
        side: int,
        price: float,
        size: int,
    ) -> None:
        super().updateMktDepth(reqId, position, operation, side, price, size)
        msg = f"UpdateMarketDepth. ReqId: {reqId}, Position: {position}, Operation: {operation}, Side: {side}, Price: {price}, Size: {size}"
        _logger.info(msg)

    def updateMktDepthL2(
        self,
        reqId: TickerId,  # type: ignore
        position: int,
        marketMaker: str,
        operation: int,
        side: int,
        price: float,
        size: int,
        isSmartDepth: bool,
    ) -> None:
        super().updateMktDepthL2(
            reqId,
            position,
            marketMaker,
            operation,
            side,
            price,
            size,
            isSmartDepth,
        )
        msg = (
            f"UpdateMarketDepthL2. ReqId: {reqId}, Position: {position}, MarketMaker: {marketMaker}, "
            f"Operation: {operation}, Side: {side}, Price: {price}, Size: {size}, isSmartDepth: {isSmartDepth}"
        )
        _logger.info(msg)

    def rerouteMktDepthReq(self, reqId: int, conId: int, exchange: str) -> None:
        super().rerouteMktDataReq(reqId, conId, exchange)
        msg = f"Re-route market depth request. ReqId: {reqId}, ConId: {conId}, Exchange: {exchange}"
        _logger.info(msg)

    def realtimeBar(
        self,
        reqId: TickerId,  # type: ignore
        time: int,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        wap: float,
        count: int,
    ) -> None:
        super().realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)
        msg = f"RealTimeBar. TickerId: {reqId}, time: {time}, close: {close}, count {count}"
        # bar = RealTimeBar(time, -1, open_, high, low, close, volume, wap, count)
        _logger.info(msg)

    def headTimestamp(self, reqId: int, headTimestamp: str) -> None:
        msg = f"HeadTimestamp. ReqId: {reqId}, HeadTimeStamp: {headTimestamp}"
        _logger.info(msg)

    def histogramData(self, reqId: int, items: HistogramDataList) -> None:  # type: ignore
        msg = f"HistogramData. ReqId: {reqId}, HistogramDataList: items[0]"
        _logger.info(msg)

    def historicalData(self, reqId: int, bar: BarData) -> None:  # type: ignore
        _logger.info(f"HistoricalData. ReqId: {reqId}, BarData. {bar}")

        bar_event = BarEvent()
        bar_event.full_symbol = self.broker.hist_data_request_dict[reqId]
        bar_event.bar_start_time = datetime.strptime(bar.date, "%Y%m%d %H:%M:%S")
        bar_event.interval = 1  # 1 second
        bar_event.open_price = bar.open
        bar_event.high_price = bar.high
        bar_event.low_price = bar.low
        bar_event.close_price = bar.close
        bar_event.volume = bar.volume

        self.broker.tick_event_engine.put(bar_event)

    def historicalDataEnd(self, reqId: int, start: str, end: str) -> None:
        super().historicalDataEnd(reqId, start, end)
        msg = f"HistoricalDataEnd. ReqId: {reqId}, from {start}, to {end}"
        _logger.info(msg)

    def historicalDataUpdate(self, reqId: int, bar: BarData) -> None:  # type: ignore
        msg = f"HistoricalDataUpdate. ReqId: {reqId}, BarData. {bar}"
        _logger.info(msg)

    def historicalTicks(self, reqId: int, ticks: ListOfHistoricalTick, done: bool) -> None:  # type: ignore
        for tick in ticks:
            _logger.info(f"HistoricalTick. ReqId: {reqId}, {tick}")

    def historicalTicksBidAsk(
        self, reqId: int, ticks: ListOfHistoricalTickBidAsk, done: bool  # type: ignore
    ) -> None:
        for tick in ticks:
            _logger.info(f"HistoricalTickBidAsk. ReqId: {reqId}, {tick}")

    def historicalTicksLast(
        self, reqId: int, ticks: ListOfHistoricalTickLast, done: bool  # type: ignore
    ) -> None:
        for tick in ticks:
            _logger.info(f"HistoricalTickLast. ReqId: {reqId}, {tick}")

    def securityDefinitionOptionParameter(
        self,
        reqId: int,
        exchange: str,
        underlyingConId: int,
        tradingClass: str,
        multiplier: str,
        expirations: SetOfString,  # type: ignore
        strikes: SetOfFloat,  # type: ignore
    ) -> None:
        super().securityDefinitionOptionParameter(
            reqId,
            exchange,
            underlyingConId,
            tradingClass,
            multiplier,
            expirations,
            strikes,
        )
        msg = (
            f"SecurityDefinitionOptionParameter. ReqId: {reqId}, Exchange: {exchange}, Underlying conId: {underlyingConId}, "
            f"TradingClass: {tradingClass}, Multiplier: {multiplier}, Expirations: {expirations}, Strikes: {str(strikes)}"
        )
        _logger.info(msg)

    def securityDefinitionOptionParameterEnd(self, reqId: int) -> None:
        super().securityDefinitionOptionParameterEnd(reqId)
        _logger.info("SecurityDefinitionOptionParameterEnd. ReqId: {reqId}")

    def tickOptionComputation(
        self,
        reqId: TickerId,  # type: ignore
        tickType: TickType,  # type: ignore
        tickAttrib: int,
        impliedVol: float,
        delta: float,
        optPrice: float,
        pvDividend: float,
        gamma: float,
        vega: float,
        theta: float,
        undPrice: float,
    ) -> None:
        super().tickOptionComputation(
            reqId,
            tickType,
            tickAttrib,
            impliedVol,
            delta,
            optPrice,
            pvDividend,
            gamma,
            vega,
            theta,
            undPrice,
        )
        msg = (
            f"TickOptionComputation. TickerId: {reqId}, TickType: {tickType}, ImpliedVolatility: {impliedVol}, "
            f"Delta: {delta}, OptionPrice: {optPrice}, pvDividend: {pvDividend}, Gamma: {gamma}, "
            f"Vega: {vega}, Theta: {theta}, UnderlyingPrice: {undPrice}"
        )
        _logger.info(msg)

    def tickNews(
        self,
        tickerId: int,
        timeStamp: int,
        providerCode: str,
        articleId: str,
        headline: str,
        extraData: str,
    ) -> None:
        msg = (
            f"TickNews. TickerId: {tickerId}, TimeStamp: {timeStamp}, ProviderCode: {providerCode}, "
            f"ArticleId: {articleId}, Headline: {headline}, ExtraData: {extraData}"
        )
        _logger.info(msg)

    def historicalNews(
        self,
        requestId: int,
        time: str,
        providerCode: str,
        articleId: str,
        headline: str,
    ) -> None:
        msg = (
            f"HistoricalNews. ReqId: {requestId}, Time: {time}, ProviderCode: {providerCode}, "
            f"ArticleId: {articleId}, Headline: {headline}"
        )
        _logger.info(msg)

    def historicalNewsEnd(self, requestId: int, hasMore: bool) -> None:
        _logger.info(f"HistoricalNewsEnd. ReqId: {requestId}, HasMore: {hasMore}")

    def newsProviders(self, newsProviders: ListOfNewsProviders) -> None:  # type: ignore
        _logger.info("NewsProviders: ")
        for provider in newsProviders:
            _logger.info(f"NewsProvider. {provider}")

    def newsArticle(self, requestId: int, articleType: int, articleText: str) -> None:
        msg = f"NewsArticle. ReqId: {requestId}, ArticleType: {articleType}, ArticleText: {articleText}"
        _logger.info(msg)

    def contractDetails(self, reqId: int, contractDetails: ContractDetails) -> None:  # type: ignore
        super().contractDetails(reqId, contractDetails)
        _logger.info(
            f"Contract Detail: {contractDetails.contract.symbol}, {contractDetails.contract.localSymbol}, {contractDetails.contract.primaryExchange}, {contractDetails.contract.exchange}, {contractDetails.contract.multiplier}"
        )
        if reqId in self.broker.contract_detail_request_contract_dict.keys():
            self.broker.contract_detail_request_contract_dict[reqId] = (
                contractDetails.contract
            )
            self.broker.sym_contract_dict[
                self.broker.contract_detail_request_symbol_dict[reqId]
            ] = contractDetails.contract
            self.broker.contract_symbol_dict[contractDetails.contract.conId] = (
                self.broker.contract_detail_request_symbol_dict[reqId]
            )
        else:
            _logger.error(
                f"Orphaned contract details request {reqId}, {contractDetails.underSymbol}"
            )

    def bondContractDetails(self, reqId: int, contractDetails: ContractDetails) -> None:  # type: ignore
        super().bondContractDetails(reqId, contractDetails)

    def contractDetailsEnd(self, reqId: int) -> None:
        super().contractDetailsEnd(reqId)
        _logger.info(f"ContractDetailsEnd. ReqId: {reqId}")

    def symbolSamples(
        self, reqId: int, contractDescriptions: ListOfContractDescription  # type: ignore
    ) -> None:
        super().symbolSamples(reqId, contractDescriptions)
        _logger.info(f"Symbol Samples. Request Id: {reqId}")

        for contractDescription in contractDescriptions:
            derivSecTypes = ""
            for derivSecType in contractDescription.derivativeSecTypes:
                derivSecTypes += derivSecType
                derivSecTypes += " "
            _logger.info(
                "Contract: conId:%s, symbol:%s, secType:%s primExchange:%s, "
                "currency:%s, derivativeSecTypes:%s"
                % (
                    contractDescription.contract.conId,
                    contractDescription.contract.symbol,
                    contractDescription.contract.secType,
                    contractDescription.contract.primaryExchange,
                    contractDescription.contract.currency,
                    derivSecTypes,
                )
            )

    def scannerParameters(self, xml: str) -> None:
        super().scannerParameters(xml)
        open("log/scanner.xml", "w").write(xml)
        _logger.info("ScannerParameters received.")

    def scannerData(
        self,
        reqId: int,
        rank: int,
        contractDetails: ContractDetails,  # type: ignore
        distance: str,
        benchmark: str,
        projection: str,
        legsStr: str,
    ) -> None:

        super().scannerData(
            reqId,
            rank,
            contractDetails,
            distance,
            benchmark,
            projection,
            legsStr,
        )

    def scannerDataEnd(self, reqId: int) -> None:
        super().scannerDataEnd(reqId)
        _logger.info(f"ScannerDataEnd. ReqId: {reqId}")

    def smartComponents(self, reqId: int, smartComponentMap: SmartComponentMap) -> None:  # type: ignore
        super().smartComponents(reqId, smartComponentMap)
        _logger.info("SmartComponents:")
        for smartComponent in smartComponentMap:
            _logger.info(f"SmartComponent. {smartComponent}")

    def tickReqParams(
        self,
        tickerId: int,
        minTick: float,
        bboExchange: str,
        snapshotPermissions: int,
    ) -> None:
        super().tickReqParams(tickerId, minTick, bboExchange, snapshotPermissions)
        msg = (
            f"TickReqParams. TickerId: {tickerId}, MinTick: {minTick}, BboExchange: {bboExchange}, "
            f"SnapshotPermissions: {snapshotPermissions}"
        )
        _logger.info(msg)

    def mktDepthExchanges(self, depthMktDataDescriptions: ListOfDepthExchanges) -> None:  # type: ignore
        super().mktDepthExchanges(depthMktDataDescriptions)
        _logger.info("MktDepthExchanges:")
        for desc in depthMktDataDescriptions:
            _logger.info(f"DepthMktDataDescription. {desc}")

    def fundamentalData(self, reqId: TickerId, data: str) -> None:  # type: ignore
        super().fundamentalData(reqId, data)
        _logger.info(f"FundamentalData. ReqId: {reqId}, Data: {data}")

    def updateNewsBulletin(
        self, msgId: int, msgType: int, newsMessage: str, originExch: str
    ) -> None:
        super().updateNewsBulletin(msgId, msgType, newsMessage, originExch)
        msg = f"News Bulletins. MsgId: {msgId}, Type: {msgType}, Message: {newsMessage}, Exchange of Origin: {originExch}"
        _logger.info(msg)

    def receiveFA(self, faData: FaDataType, cxml: str) -> None:  # type: ignore
        super().receiveFA(faData, cxml)
        _logger.info(f"Receiving FA: {faData}")
        open("log/fa.xml", "w").write(cxml)

    def softDollarTiers(self, reqId: int, tiers: list) -> None:  # type: ignore
        super().softDollarTiers(reqId, tiers)
        _logger.info(f"SoftDollarTiers. ReqId: {reqId}")
        for tier in tiers:
            _logger.info(f"SoftDollarTier. {tier}")

    def currentTime(self, time: int) -> None:
        super().currentTime(time)
        msg = f'CurrentTime: {datetime.fromtimestamp(time).strftime("%H:%M:%S.%f")}'
        _logger.info(msg)
        self.broker.log(msg)

    def execDetails(self, reqId: int, contract: Contract, execution: Execution) -> None:  # type: ignore
        super().execDetails(reqId, contract, execution)
        msg = (
            f"ExecDetails. ReqId: {reqId}, Symbol: {contract.symbol}, SecType: {contract.secType}, "
            f"Currency: {contract.currency}, oid: {execution.orderId}, {execution.price}, {execution.shares}"
        )
        _logger.info(msg)

        fill_event = FillEvent()
        fill_event.order_id = execution.orderId
        fill_event.fill_id = execution.execId
        fill_event.fill_price = execution.price
        fill_event.fill_size = execution.shares * (
            1 if execution.side == "BOT" else -1
        )  # BOT SLD
        fill_event.fill_time = pd.Timestamp(
            datetime.strptime(execution.time, "%Y%m%d  %H:%M:%S")
        )
        fill_event.exchange = (
            contract.exchange
            if contract.primaryExchange == ""
            else contract.primaryExchange
        )
        fill_event.account = self.broker.account

        if execution.orderId in self.broker.order_dict.keys():
            fill_event.full_symbol = self.broker.order_dict[
                execution.orderId
            ].full_symbol
            fill_event.source = self.broker.order_dict[execution.orderId].source
        else:  # not placed by algo
            fill_event.full_symbol = InteractiveBrokers.contract_to_symbol(contract)

        self.broker.event_engine.put(fill_event)

    def execDetailsEnd(self, reqId: int) -> None:
        super().execDetailsEnd(reqId)
        _logger.info(f"ExecDetailsEnd. ReqId: {reqId}")

    def displayGroupList(self, reqId: int, groups: str) -> None:
        super().displayGroupList(reqId, groups)
        _logger.info(f"DisplayGroupList. ReqId: {reqId}, Groups: {groups}")

    def displayGroupUpdated(self, reqId: int, contractInfo: str) -> None:
        super().displayGroupUpdated(reqId, contractInfo)
        _logger.info(
            f"DisplayGroupUpdated. ReqId: {reqId}, ContractInfo: {contractInfo}"
        )

    def commissionReport(self, commissionReport: CommissionReport) -> None:
        super().commissionReport(commissionReport)
        _logger.info(f"CommissionReport. {commissionReport}")

    def completedOrder(
        self, contract: Contract, order: Order, orderState: OrderState  # type: ignore
    ) -> None:
        super().completedOrder(contract, order, orderState)
        msg = (
            f"CompletedOrder. PermId: {order.permId}, ParentPermId: {utils.longToStr(order.parentPermId)}, "
            f"Account: {order.account}, Symbol: {contract.symbol}, SecType: {contract.secType}, Exchange: {contract.exchange}, "
            f"Action: {order.action}, OrderType: {order.orderType}, TotalQty: {order.totalQuantity}, "
            f"CashQty: {order.cashQty}, FilledQty: {order.filledQuantity}, LmtPrice: {order.lmtPrice}, "
            f"AuxPrice: {order.auxPrice}, Status: {orderState.status}, Completed time: {orderState.completedTime}, "
            f"Completed Status: {orderState.completedStatus}"
        )
        _logger.info(msg)

    def completedOrdersEnd(self) -> None:
        super().completedOrdersEnd()
        _logger.info("CompletedOrdersEnd")

    # ---------------------------------- End EWrapper functions ---------------------------------------------- #
