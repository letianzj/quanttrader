#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .brokerage_base import BrokerageBase
from ..event.event import EventType
from ..account import AccountEvent
from ..data import TickEvent, TickType, BarEvent
from ..order.order_type import OrderType
from ..order.fill_event import FillEvent
from ..order.order_event import OrderEvent
from ..order.order_status import OrderStatus
from ..position.position_event import PositionEvent
from datetime import datetime
from copy import copy
from threading import Thread
import logging

from ibapi.wrapper import EWrapper
from ibapi.client import EClient
from ibapi import utils

# types
from ibapi.common import * # @UnusedWildImport
from ibapi.order_condition import * # @UnusedWildImport
from ibapi.contract import * # @UnusedWildImport
from ibapi.order import * # @UnusedWildImport
from ibapi.order_state import * # @UnusedWildImport
from ibapi.execution import Execution
from ibapi.execution import ExecutionFilter
from ibapi.commission_report import CommissionReport
from ibapi.ticktype import TickTypeEnum
from ibapi.tag_value import TagValue

from ibapi.account_summary_tags import *

_logger = logging.getLogger(__name__)


class InteractiveBrokers(BrokerageBase):
    def __init__(self, events_engine, account: str):
        """
        Initialises the handler, setting the event queue
        """
        self.events_engine = events_engine          # save events to event queue
        self.api = IBApi(self)
        self.account = account
        self.contract_detail_request_contract_dict = {}
        self.contract_detail_request_symbol_dict = {}
        self.market_data_subscription_dict = {}
        self.market_data_subscription_reverse_dict = {}
        self.market_data_tick_dict = {}          # to combine tickprice and ticksize
        self.market_depth_subscription_dict = {}
        self.market_depth_subscription_reverse_dict = {}
        self.market_depth_tick_dict = {}  # to combine tickprice and ticksize
        self.hist_data_request_dict = {}
        self.order_dict = {}
        self.account_summary_reqid = -1
        self.account = AccountEvent()
        self.clientid = 0
        self.reqid = 0
        self.orderid = 0

    def connect(self, host='127.0.0.1', port=7497, clientId=0):
        self.clientid = clientId
        if self.api.connected:
            return

        self.api.connect(host, port, clientId=clientId)
        self.api.thread.start()
        self.reqCurrentTime()

        if clientId == 0:
            # associate TWS with the client
            self.api.reqAutoOpenOrders(True)

    def disconnect(self):
        self.api.connected = False
        self.api.disconnect()

    def _calculate_commission(self, full_symbol, fill_price, fill_size):
        pass

    def next_order_id(self):
        pass

    def place_order(self, order_event):
        if not self.api.connected:
            return

        ib_contract = InteractiveBrokers.symbol_to_contract(order_event.full_symbol)
        if not ib_contract:
            _logger.error(f'Failed to find contract to place order {order_event.full_symbol}')
            return

        ib_order = InteractiveBrokers.order_to_ib_order(order_event)
        if not ib_order:
            _logger.error(f'Failed to create order to place {order_event.full_symbol}')
            return

        order_event.order_id = self.orderid
        self.api.placeOrder(self.orderid, ib_contract, ib_order)
        self.order_dict[self.orderid] = order_event
        self.orderid += 1

    def cancel_order(self, order_id):
        if not self.api.connected:
            return

        if not order_id in self.order_dict.keys():
            _logger.error(f'Order to cancel not found. order id {order_id}')

        self.api.cancelOrder(order_id)

    def cancel_all_orders(self):
        self.api.reqGlobalCancel()

    def subscribe_market_data(self, sym):
        if not self.api.connected:
            return

        if sym in self.market_data_subscription_reverse_dict.keys():
            return

        contract = InteractiveBrokers.symbol_to_contract(sym)
        if not contract:
            _logger.error(f'Failed to find contract to subscribe market data: {sym}')
            return

        self.api.reqContractDetails(self.reqid, contract)
        self.contract_detail_request_contract_dict[self.reqid] = contract
        self.contract_detail_request_symbol_dict[self.reqid] = sym
        self.reqid +=1
        self.api.reqMktData(self.reqid, contract, '', False, False, [])
        tick_event = TickEvent()
        tick_event.full_symbol = sym
        self.market_data_subscription_dict[self.reqid] = sym
        self.market_data_subscription_reverse_dict[sym] = self.reqid
        self.market_data_tick_dict[self.reqid] = tick_event
        self.reqid += 1

    def unsubscribe_market_data(self, sym):
        if not self.api.connected:
            return

        if not sym in self.market_data_subscription_reverse_dict.keys():
            return

        self.api.cancelMktData(self.market_data_subscription_reverse_dict[sym])

    def subscribe_market_depth(self, sym):
        if not self.api.connected:
            return

        if sym in self.market_depth_subscription_reverse_dict.keys():
            return

        contract = InteractiveBrokers.symbol_to_contract(sym)
        if not contract:
            _logger.error(f'Failed to find contract to subscribe market depth: {sym}')
            return

        self.api.reqMktDepth(self.reqid, contract, 5, True, [])
        self.reqid += 1
        self.market_depth_subscription_dict[self.reqid] = sym
        self.market_depth_subscription_reverse_dict[sym] = self.reqid

    def unsubscribe_market_depth(self, sym):
        if not self.api.connected:
            return

        if not sym in self.market_depth_subscription_reverse_dict.keys():
            return

        self.api.cancelMktDepth(self.market_depth_subscription_reverse_dict[sym], True)

    def subscribe_account_summary(self):
        if not self.api.connected:
            return

        if self.account_summary_reqid > 0:    # subscribed
            return

        self.account_summary_reqid = self.reqid
        self.api.reqAccountSummary(self.account_summary_reqid, "All", "$LEDGER")
        self.reqid += 1

    def unsubscribe_account_summary(self):
        if not self.api.connected:
            return

        if self.account_summary_reqid == -1:
            return

        self.api.cancelAccountSummary(self.account_summary_reqid)
        self.account_summary_reqid = -1

    def subscribe_positions(self):
        self.api.reqPositions()

    def unsubscribe_positions(self):
        self.api.cancelPositions()

    def request_historical_data(self, symbol, start=None, end=None):
        ib_contract = InteractiveBrokers.symbol_to_contract(symbol)

        if end:
            end_str = end.strftime("%Y%m%d %H:%M:%S")
        else:
            end_str = ''

        self.hist_data_request_dict[self.reqid] = symbol
        self.api.reqHistoricalData(self.reqid, ib_contract, end_str, '1 D', '1 sec', 'TRADES', 1, 1, True, [])
        self.reqid += 1

    def cancel_historical_data(self, reqid):
        self.api.cancelHistoricalData(reqid)

    def reqCurrentTime(self):
        self.api.reqCurrentTime()

    def setServerLogLevel(self, level=1):
        self.api.setServerLogLevel(level)

    @staticmethod
    def symbol_to_contract(symbol):
        """
        symbol string to ib contract
        :param symbol: AMZN STK SMART; EURGBP CASH IDEALPRO; ESM9 FUT GLOBEX
        :return: ib contract
        """
        symbol_fields = symbol.split(' ')
        ib_contract = Contract()

        if symbol_fields[1] == 'STK':
            ib_contract.symbol = symbol_fields[0]
            ib_contract.secType = symbol_fields[1]
            ib_contract.currency = 'USD'
            ib_contract.exchange = symbol_fields[2]
        elif symbol_fields[1] == 'CASH':
            ib_contract.symol = symbol_fields[0][0:3]     # EUR
            ib_contract.secType = symbol_fields[1]
            ib_contract.currency = symbol_fields[0][3:]  # GBP
            ib_contract.exchange = symbol_fields[2]
        elif symbol_fields[1] == 'FUT':
            ib_contract.localSymbol = symbol_fields[0]   # ESM9
            ib_contract.secType = symbol_fields[1]
            ib_contract.exchange = symbol_fields[2]
            ib_contract.currency = 'USD'
        else:
            _logger.error(f'invalid contract {symbol}')

        return ib_contract

    @staticmethod
    def contract_to_symbol(ib_contract):
        full_symbol = ''
        if ib_contract.secType == 'STK':
            full_symbol = ' '.join([ib_contract.LocalSymbol, 'STK', 'SMART'])    # or ib_contract.exchange
        elif ib_contract.secType == 'CASH':
            full_symbol = ' '.join([ib_contract.symol+ib_contract.currency, 'CASH', ib_contract.exchange])
        elif ib_contract.secType == 'FUT':
            full_symbol = ' '.join([ib_contract.localSymbol, 'FUT', ib_contract.exchange])

        return full_symbol


    @staticmethod
    def order_to_ib_order(order_event):
        ib_order = Order()
        ib_order.action = 'BUY' if order_event.order_size > 0 else 'SELL'
        ib_order.totalQuantity = abs(order_event.order_size)
        if order_event.order_type == OrderType.MARKET:
            ib_order.orderType = 'MKT'
        elif order_event.order_type == OrderType.LIMIT:
            ib_order.orderType = 'LMT'
            ib_order.lmtPrice = order_event.limit_price
        elif order_event.order_type == OrderType.STOP:
            ib_order.orderType = 'STP'
            ib_order.auxPrice = order_event.stop_price
        elif order_event.order_type == OrderType.STOP_LIMIT:
            ib_order.orderType = 'STP LMT'
            ib_order.lmtPrice = order_event.limit_price
            ib_order.auxPrice = order_event.stop_price
        else:
            return None

        return ib_order

    @staticmethod
    def ib_order_to_order(ib_order):
        order_event = OrderEvent()
        # order_event.order_id = orderId
        # order_event.order_status = orderState.status
        direction = 1 if ib_order.action == 'BUY' else -1
        order_event.order_size = ib_order.totalQuantity * direction
        if ib_order.orderType == 'MKT':
            order_event.order_type = OrderType.MARKET
        elif ib_order.orderType == 'LMT':
            order_event.order_type = OrderType.LIMIT
            order_event.limit_price = ib_order.lmtPrice
        elif ib_order.orderType == 'STP':
            order_event.order_type = OrderType.STOP
            order_event.stop_price = ib_order.auxPrice
        elif ib_order.orderType == 'STP LMT':
            order_event.order_type = OrderType.STOP_LIMIT
            order_event.limit_price = ib_order.lmtPrice
            order_event.stop_price = ib_order.auxPrice
        else:
            order_event.order_type = OrderType.UNKNOWN
            order_event.limit_price = ib_order.lmtPrice
            order_event.stop_price = ib_order.auxPrice

        return order_event


class IBApi(EWrapper, EClient):
    def __init__(self, broker):
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)

        self.broker = broker
        self.thread = Thread(target=self.run)

        self.nKeybInt = 0
        self.connected = False
        self.nextValidOrderId = None
        self.globalCancelOnly = False
        self.simplePlaceOid = None

    # ------------------------------------------ EClient functions --------------------------------------- #
    def keyboardInterrupt(self):
        self.nKeybInt += 1
        if self.nKeybInt == 1:
            self.stop()
        else:
            _logger.info("Finishing test")

    def nextOrderId(self):
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid

    def stop(self):
        _logger.info("Executing cancels")
        _logger.info("Executing cancels ... finished")

    # ------------------------------------------------------------------ End EClient functions -------------------------------------------------------- #

    #---------------------------------------------------------------------- EWrapper functions -------------------------------------------------------- #
    def connectAck(self):
        if self.asynchronous:
            self.startApi()
        self.connected = True
        _logger.info('IB connected')

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        _logger.info("setting nextValidOrderId: %d", orderId)
        self.broker.orderid = orderId

    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        super().error(reqId, errorCode, errorString)
        _logger.error("Error. Id:", reqId, "Code:", errorCode, "Msg:", errorString)

    def winError(self, text: str, lastError: int):
        super().winError(text, lastError)
        _logger.error("Error Id:", lastError, "Msg:", text)

    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        super().openOrder(orderId, contract, order, orderState)
        _logger.info("OpenOrder. PermId: ", order.permId, "ClientId:", order.clientId, " OrderId:", orderId,
              "Account:", order.account, "Symbol:", contract.symbol, "SecType:", contract.secType,
              "Exchange:", contract.exchange, "Action:", order.action, "OrderType:", order.orderType,
              "TotalQty:", order.totalQuantity, "CashQty:", order.cashQty,
              "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status)

        order_event = InteractiveBrokers.ib_order_to_order(order)
        order_event.order_id = orderId
        if orderState.status == 'Submitted':
            order_event.order_status = OrderStatus.SUBMITTED
        elif orderState.status == 'Filled':
            order_event.order_status = OrderStatus.FILLED
        elif orderState.status == 'PreSubmitted':
            order_event.order_status = OrderStatus.PENDING_SUBMIT
        else:
            order_event.order_status = OrderStatus.UNKNOWN

        if orderId in self.broker.order_dict.keys():
            order_event.full_symbol = self.broker.order_dict[orderId]
        else:     # not placed by algo
            order_event.full_symbol = InteractiveBrokers.contract_to_symbol(contract)
            self.broker.order_dict[orderId] = order_event.full_symbol

        self.broker.event_engine.put(copy(order_event))

    def openOrderEnd(self):
        super().openOrderEnd()
        _logger.info("OpenOrderEnd")
        _logger.info("Received %d openOrders", len(list(self.broker.order_dict.keys())))

    def orderStatus(self, orderId: OrderId, status: str, filled: float,
                    remaining: float, avgFillPrice: float, permId: int,
                    parentId: int, lastFillPrice: float, clientId: int,
                    whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining,
                            avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        _logger.info("OrderStatus. Id:", orderId, "Status:", status, "Filled:", filled,
              "Remaining:", remaining, "AvgFillPrice:", avgFillPrice,
              "PermId:", permId, "ParentId:", parentId, "LastFillPrice:",
              lastFillPrice, "ClientId:", clientId, "WhyHeld:",
              whyHeld, "MktCapPrice:", mktCapPrice)

        order_event = self.broker.order_dict.get(OrderId, None)
        if not order_event is None:
            if status == 'Submitted':
                order_event.order_status = OrderStatus.SUBMITTED
            elif status == 'Filled':
                order_event.order_status = OrderStatus.FILLED
            elif status == 'PreSubmitted':
                order_event.order_status = OrderStatus.PENDING_SUBMIT
            else:
                order_event.order_status = OrderStatus.UNKNOWN
            order_event.fill_size = filled

        self.broker.event_engine.put(copy(order_event))

    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        _logger.info("Account list:", accountsList)

        self.broker.account = accountsList.split(",")[0]
        self.broker.reqAccountUpdates(True, self.broker.account)

    def accountSummary(self, reqId: int, account: str, tag: str, value: str,
                       currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        _logger.info("AccountSummary. ReqId:", reqId, "Account:", account,
              "Tag: ", tag, "Value:", value, "Currency:", currency)

    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(reqId)
        _logger.info("AccountSummaryEnd. ReqId:", reqId)

    def updateAccountValue(self, key: str, val: str, currency: str,
                           accountName: str):
        super().updateAccountValue(key, val, currency, accountName)
        _logger.info("UpdateAccountValue. Key:", key, "Value:", val,
              "Currency:", currency, "AccountName:", accountName)

        if key == 'NetLiquidationByCurrency':
            self.broker.account.balance = float(val)
        elif key == 'NetLiquidation':
            self.broker.account.balance = float(val)
        elif key == 'AvailableFunds':
            self.broker.account.available = float(val)
        elif key == 'UnrealizedPnL':
            self.broker.account.open_pnl = float(val)
        elif key == 'MaintMarginReq':
            self.broker.account.margin = float(val)

    def updatePortfolio(self, contract: Contract, position: float,
                        marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float,
                        realizedPNL: float, accountName: str):
        super().updatePortfolio(contract, position, marketPrice, marketValue,
                                averageCost, unrealizedPNL, realizedPNL, accountName)
        _logger.info("UpdatePortfolio.", "Symbol:", contract.symbol, "SecType:", contract.secType, "Exchange:",
              contract.exchange, "Position:", position, "MarketPrice:", marketPrice,
              "MarketValue:", marketValue, "AverageCost:", averageCost,
              "UnrealizedPNL:", unrealizedPNL, "RealizedPNL:", realizedPNL,
              "AccountName:", accountName)

        position_event = PositionEvent
        position_event.full_symbol = InteractiveBrokers.contract_to_symbol(contract)
        position_event.size = position
        try:
            multiplier = int(contract.multiplier)
        except ValueError:
            multiplier = 1
        position_event.average_cost = averageCost / multiplier
        position_event.realized_pnl = realizedPNL
        position_event.unrealized_pnl = unrealizedPNL
        self.broker.event_engine.put(position_event)

    def updateAccountTime(self, timeStamp: str):
        super().updateAccountTime(timeStamp)
        _logger.info("UpdateAccountTime. Time:", timeStamp)
        self.broker.event_engine.put(self.broker.account)

    def accountDownloadEnd(self, accountName: str):
        super().accountDownloadEnd(accountName)
        _logger.info("AccountDownloadEnd. Account:", accountName)

    def position(self, account: str, contract: Contract, position: float,
                 avgCost: float):
        super().position(account, contract, position, avgCost)
        _logger.info("Position.", "Account:", account, "Symbol:", contract.symbol, "SecType:",
              contract.secType, "Currency:", contract.currency,
              "Position:", position, "Avg cost:", avgCost)

    def positionEnd(self):
        super().positionEnd()
        _logger.info("PositionEnd")

    def positionMulti(self, reqId: int, account: str, modelCode: str,
                      contract: Contract, pos: float, avgCost: float):
        super().positionMulti(reqId, account, modelCode, contract, pos, avgCost)
        _logger.info("PositionMulti. RequestId:", reqId, "Account:", account,
              "ModelCode:", modelCode, "Symbol:", contract.symbol, "SecType:",
              contract.secType, "Currency:", contract.currency, ",Position:",
              pos, "AvgCost:", avgCost)

    def positionMultiEnd(self, reqId: int):
        super().positionMultiEnd(reqId)
        _logger.info("PositionMultiEnd. RequestId:", reqId)


    def accountUpdateMulti(self, reqId: int, account: str, modelCode: str,
                           key: str, value: str, currency: str):
        super().accountUpdateMulti(reqId, account, modelCode, key, value,
                                   currency)
        _logger.info("AccountUpdateMulti. RequestId:", reqId, "Account:", account,
              "ModelCode:", modelCode, "Key:", key, "Value:", value,
              "Currency:", currency)

    def accountUpdateMultiEnd(self, reqId: int):
        super().accountUpdateMultiEnd(reqId)
        _logger.info("AccountUpdateMultiEnd. RequestId:", reqId)

    def familyCodes(self, familyCodes: ListOfFamilyCode):
        super().familyCodes(familyCodes)
        _logger.info("Family Codes:")
        for familyCode in familyCodes:
            _logger.info("FamilyCode.", familyCode)

    def pnl(self, reqId: int, dailyPnL: float,
            unrealizedPnL: float, realizedPnL: float):
        super().pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)
        _logger.info("Daily PnL. ReqId:", reqId, "DailyPnL:", dailyPnL,
              "UnrealizedPnL:", unrealizedPnL, "RealizedPnL:", realizedPnL)

    def pnlSingle(self, reqId: int, pos: int, dailyPnL: float,
                  unrealizedPnL: float, realizedPnL: float, value: float):
        super().pnlSingle(reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value)
        _logger.info("Daily PnL Single. ReqId:", reqId, "Position:", pos,
              "DailyPnL:", dailyPnL, "UnrealizedPnL:", unrealizedPnL,
              "RealizedPnL:", realizedPnL, "Value:", value)

    def marketDataType(self, reqId: TickerId, marketDataType: int):
        super().marketDataType(reqId, marketDataType)
        _logger.info("MarketDataType. ReqId:", reqId, "Type:", marketDataType)

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float,
                  attrib: TickAttrib):
        super().tickPrice(reqId, tickType, price, attrib)

        tick_event = self.broker.market_data_tick_dict[reqId]
        if tickType == TickTypeEnum.BID:
            tick_event.tick_type = TickType.BID
            tick_event.bid_price_L1 = price
        elif tickType == TickTypeEnum.ASK:
            tick_event.tick_type = TickType.ASK
            tick_event.ask_price_L1 = price
        elif tickType == TickTypeEnum.LAST:
            tick_event.tick_type = TickType.TRADE
            tick_event.price = price
        else:
            return

        self.broker.event_engine.put(copy(tick_event))

    def tickSize(self, reqId: TickerId, tickType: TickType, size: int):
        super().tickSize(reqId, tickType, size)
        tick_event = self.broker.market_data_tick_dict[reqId]
        if tickType == TickTypeEnum.BID_SIZE:
            tick_event.tick_type = TickType.BID
            tick_event.bid_size_L1 = size
        elif tickType == TickTypeEnum.ASK_SIZE:
            tick_event.tick_type = TickType.ASK
            tick_event.ask_size_L1 = size
        elif tickType == TickTypeEnum.LAST_SIZE:
            tick_event.tick_type = TickType.TRADE
            tick_event.size = size
        else:
            return

        self.broker.event_engine.put(copy(tick_event))

    def tickGeneric(self, reqId: TickerId, tickType: TickType, value: float):
        super().tickGeneric(reqId, tickType, value)
        # print("TickGeneric. TickerId:", reqId, "TickType:", tickType, "Value:", value)
        pass

    def tickString(self, reqId: TickerId, tickType: TickType, value: str):
        super().tickString(reqId, tickType, value)
        tick_event = self.broker.market_data_tick_dict[reqId]
        tick_event.timestamp = datetime.fromtimestamp(int(value))
        self.broker.event_engine.put(copy(tick_event))

    def tickSnapshotEnd(self, reqId: int):
        super().tickSnapshotEnd(reqId)
        print("TickSnapshotEnd. TickerId:", reqId)

    def rerouteMktDataReq(self, reqId: int, conId: int, exchange: str):
        super().rerouteMktDataReq(reqId, conId, exchange)
        print("Re-route market data request. ReqId:", reqId, "ConId:", conId, "Exchange:", exchange)

    def marketRule(self, marketRuleId: int, priceIncrements: ListOfPriceIncrements):
        super().marketRule(marketRuleId, priceIncrements)
        print("Market Rule ID: ", marketRuleId)
        for priceIncrement in priceIncrements:
            print("Price Increment.", priceIncrement)

    def orderBound(self, orderId: int, apiClientId: int, apiOrderId: int):
        super().orderBound(orderId, apiClientId, apiOrderId)
        print("OrderBound.", "OrderId:", orderId, "ApiClientId:", apiClientId, "ApiOrderId:", apiOrderId)

    def tickByTickAllLast(self, reqId: int, tickType: int, time: int, price: float,
                          size: int, tickAtrribLast: TickAttribLast, exchange: str,
                          specialConditions: str):
        super().tickByTickAllLast(reqId, tickType, time, price, size, tickAtrribLast,
                                  exchange, specialConditions)
        if tickType == 1:
            print("Last.", end='')
        else:
            print("AllLast.", end='')
        print(" ReqId:", reqId,
              "Time:", datetime.datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S"),
              "Price:", price, "Size:", size, "Exch:", exchange,
              "Spec Cond:", specialConditions, "PastLimit:", tickAtrribLast.pastLimit, "Unreported:",
              tickAtrribLast.unreported)

    def tickByTickBidAsk(self, reqId: int, time: int, bidPrice: float, askPrice: float,
                         bidSize: int, askSize: int, tickAttribBidAsk: TickAttribBidAsk):
        super().tickByTickBidAsk(reqId, time, bidPrice, askPrice, bidSize,
                                 askSize, tickAttribBidAsk)
        print("BidAsk. ReqId:", reqId,
              "Time:", datetime.datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S"),
              "BidPrice:", bidPrice, "AskPrice:", askPrice, "BidSize:", bidSize,
              "AskSize:", askSize, "BidPastLow:", tickAttribBidAsk.bidPastLow, "AskPastHigh:",
              tickAttribBidAsk.askPastHigh)

    def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float):
        super().tickByTickMidPoint(reqId, time, midPoint)
        print("Midpoint. ReqId:", reqId,
              "Time:", datetime.datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S"),
              "MidPoint:", midPoint)

    def updateMktDepth(self, reqId: TickerId, position: int, operation: int,
                       side: int, price: float, size: int):
        super().updateMktDepth(reqId, position, operation, side, price, size)
        print("UpdateMarketDepth. ReqId:", reqId, "Position:", position, "Operation:",
              operation, "Side:", side, "Price:", price, "Size:", size)

    def updateMktDepthL2(self, reqId: TickerId, position: int, marketMaker: str,
                         operation: int, side: int, price: float, size: int, isSmartDepth: bool):
        super().updateMktDepthL2(reqId, position, marketMaker, operation, side,
                                 price, size, isSmartDepth)
        print("UpdateMarketDepthL2. ReqId:", reqId, "Position:", position, "MarketMaker:", marketMaker,
              "Operation:",
              operation, "Side:", side, "Price:", price, "Size:", size, "isSmartDepth:", isSmartDepth)

    def rerouteMktDepthReq(self, reqId: int, conId: int, exchange: str):
        super().rerouteMktDataReq(reqId, conId, exchange)
        print("Re-route market depth request. ReqId:", reqId, "ConId:", conId, "Exchange:", exchange)

    def realtimeBar(self, reqId: TickerId, time: int, open_: float, high: float, low: float, close: float,
                    volume: int, wap: float, count: int):
        super().realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)
        print("RealTimeBar. TickerId:", reqId,
              RealTimeBar(time, -1, open_, high, low, close, volume, wap, count))

    def headTimestamp(self, reqId: int, headTimestamp: str):
        print("HeadTimestamp. ReqId:", reqId, "HeadTimeStamp:", headTimestamp)

    def histogramData(self, reqId: int, items: HistogramDataList):
        print("HistogramData. ReqId:", reqId, "HistogramDataList:", "[%s]" % "; ".join(map(str, items)))

    def historicalData(self, reqId: int, bar: BarData):
        print("HistoricalData. ReqId:", reqId, "BarData.", bar)

        bar_event = BarEvent()
        bar_event.full_symbol = self.broker.hist_data_request_dict[reqId]
        bar_event.bar_start_time = datetime.strptime(bar.date, "%Y%m%d %H:%M:%S")
        bar_event.interval = 1  # 1 second
        bar_event.open_price = bar.open
        bar_event.high_price = bar.high
        bar_event.low_price = bar.low
        bar_event.close_price = bar.close
        bar_event.volume = bar.volume

        self.broker.event_engine.put(bar_event)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)
        print("HistoricalDataEnd. ReqId:", reqId, "from", start, "to", end)

    def historicalDataUpdate(self, reqId: int, bar: BarData):
        print("HistoricalDataUpdate. ReqId:", reqId, "BarData.", bar)

    def historicalTicks(self, reqId: int, ticks: ListOfHistoricalTick, done: bool):
        for tick in ticks:
            print("HistoricalTick. ReqId:", reqId, tick)

    def historicalTicksBidAsk(self, reqId: int, ticks: ListOfHistoricalTickBidAsk,
                              done: bool):
        for tick in ticks:
            print("HistoricalTickBidAsk. ReqId:", reqId, tick)

    def historicalTicksLast(self, reqId: int, ticks: ListOfHistoricalTickLast,
                            done: bool):
        for tick in ticks:
            print("HistoricalTickLast. ReqId:", reqId, tick)

    def securityDefinitionOptionParameter(self, reqId: int, exchange: str,
                                          underlyingConId: int, tradingClass: str, multiplier: str,
                                          expirations: SetOfString, strikes: SetOfFloat):
        super().securityDefinitionOptionParameter(reqId, exchange,
                                                  underlyingConId, tradingClass, multiplier, expirations,
                                                  strikes)
        print("SecurityDefinitionOptionParameter.",
              "ReqId:", reqId, "Exchange:", exchange, "Underlying conId:", underlyingConId, "TradingClass:",
              tradingClass, "Multiplier:", multiplier,
              "Expirations:", expirations, "Strikes:", str(strikes))

    def securityDefinitionOptionParameterEnd(self, reqId: int):
        super().securityDefinitionOptionParameterEnd(reqId)
        print("SecurityDefinitionOptionParameterEnd. ReqId:", reqId)


    def tickOptionComputation(self, reqId: TickerId, tickType: TickType,
                              impliedVol: float, delta: float, optPrice: float, pvDividend: float,
                              gamma: float, vega: float, theta: float, undPrice: float):
        super().tickOptionComputation(reqId, tickType, impliedVol, delta,
                                      optPrice, pvDividend, gamma, vega, theta, undPrice)
        print("TickOptionComputation. TickerId:", reqId, "TickType:", tickType,
              "ImpliedVolatility:", impliedVol, "Delta:", delta, "OptionPrice:",
              optPrice, "pvDividend:", pvDividend, "Gamma: ", gamma, "Vega:", vega,
              "Theta:", theta, "UnderlyingPrice:", undPrice)

    def tickNews(self, tickerId: int, timeStamp: int, providerCode: str,
                 articleId: str, headline: str, extraData: str):
        print("TickNews. TickerId:", tickerId, "TimeStamp:", timeStamp,
              "ProviderCode:", providerCode, "ArticleId:", articleId,
              "Headline:", headline, "ExtraData:", extraData)

    def historicalNews(self, reqId: int, time: str, providerCode: str,
                       articleId: str, headline: str):
        print("HistoricalNews. ReqId:", reqId, "Time:", time,
              "ProviderCode:", providerCode, "ArticleId:", articleId,
              "Headline:", headline)

    def historicalNewsEnd(self, reqId: int, hasMore: bool):
        print("HistoricalNewsEnd. ReqId:", reqId, "HasMore:", hasMore)

    def newsProviders(self, newsProviders: ListOfNewsProviders):
        print("NewsProviders: ")
        for provider in newsProviders:
            print("NewsProvider.", provider)

    def newsArticle(self, reqId: int, articleType: int, articleText: str):
        print("NewsArticle. ReqId:", reqId, "ArticleType:", articleType,
              "ArticleText:", articleText)

    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)
        if reqId in self.broker.contract_detail_request_contract_dict.keys():
            self.broker.contract_detail_request_contract_dict[reqId] = contractDetails.contract

    def bondContractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().bondContractDetails(reqId, contractDetails)

    def contractDetailsEnd(self, reqId: int):
        super().contractDetailsEnd(reqId)
        print("ContractDetailsEnd. ReqId:", reqId)

    def symbolSamples(self, reqId: int,
                      contractDescriptions: ListOfContractDescription):
        super().symbolSamples(reqId, contractDescriptions)
        print("Symbol Samples. Request Id: ", reqId)

        for contractDescription in contractDescriptions:
            derivSecTypes = ""
            for derivSecType in contractDescription.derivativeSecTypes:
                derivSecTypes += derivSecType
                derivSecTypes += " "
            print("Contract: conId:%s, symbol:%s, secType:%s primExchange:%s, "
                  "currency:%s, derivativeSecTypes:%s" % (
                      contractDescription.contract.conId,
                      contractDescription.contract.symbol,
                      contractDescription.contract.secType,
                      contractDescription.contract.primaryExchange,
                      contractDescription.contract.currency, derivSecTypes))

    def scannerParameters(self, xml: str):
        super().scannerParameters(xml)
        open('log/scanner.xml', 'w').write(xml)
        print("ScannerParameters received.")


    def scannerData(self, reqId: int, rank: int, contractDetails: ContractDetails,
                    distance: str, benchmark: str, projection: str, legsStr: str):
        super().scannerData(reqId, rank, contractDetails, distance, benchmark,
                            projection, legsStr)
        pass

    def scannerDataEnd(self, reqId: int):
        super().scannerDataEnd(reqId)
        print("ScannerDataEnd. ReqId:", reqId)

    def smartComponents(self, reqId: int, smartComponentMap: SmartComponentMap):
        super().smartComponents(reqId, smartComponentMap)
        print("SmartComponents:")
        for smartComponent in smartComponentMap:
            print("SmartComponent.", smartComponent)

    def tickReqParams(self, tickerId: int, minTick: float,
                      bboExchange: str, snapshotPermissions: int):
        super().tickReqParams(tickerId, minTick, bboExchange, snapshotPermissions)
        print("TickReqParams. TickerId:", tickerId, "MinTick:", minTick,
              "BboExchange:", bboExchange, "SnapshotPermissions:", snapshotPermissions)

    def mktDepthExchanges(self, depthMktDataDescriptions: ListOfDepthExchanges):
        super().mktDepthExchanges(depthMktDataDescriptions)
        print("MktDepthExchanges:")
        for desc in depthMktDataDescriptions:
            print("DepthMktDataDescription.", desc)

    def fundamentalData(self, reqId: TickerId, data: str):
        super().fundamentalData(reqId, data)
        print("FundamentalData. ReqId:", reqId, "Data:", data)

    def updateNewsBulletin(self, msgId: int, msgType: int, newsMessage: str,
                           originExch: str):
        super().updateNewsBulletin(msgId, msgType, newsMessage, originExch)
        print("News Bulletins. MsgId:", msgId, "Type:", msgType, "Message:", newsMessage,
              "Exchange of Origin: ", originExch)

    def receiveFA(self, faData: FaDataType, cxml: str):
        super().receiveFA(faData, cxml)
        print("Receiving FA: ", faData)
        open('log/fa.xml', 'w').write(cxml)

    def softDollarTiers(self, reqId: int, tiers: list):
        super().softDollarTiers(reqId, tiers)
        print("SoftDollarTiers. ReqId:", reqId)
        for tier in tiers:
            print("SoftDollarTier.", tier)

    def currentTime(self, time: int):
        super().currentTime(time)
        _logger.info("CurrentTime:", datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S"))

    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        super().execDetails(reqId, contract, execution)
        print("ExecDetails. ReqId:", reqId, "Symbol:", contract.symbol, "SecType:", contract.secType,
              "Currency:", contract.currency, execution)

        if execution.orderId in self.broker.order_dict.keys():
            full_symbol = self.broker.order_dict[execution.orderId]
        else:      # not placed by algo
            full_symbol = InteractiveBrokers.contract_to_symbol(contract)

        fill_event = FillEvent()
        fill_event.order_id = execution.orderId
        fill_event.fill_id = execution.execId
        fill_event.fill_price = execution.price
        fill_event.fill_size=execution.shares * (1 if execution.side == 'BUY' else -1)
        fill_event.fill_time=datetime.strptime(execution.time, "%Y%m%d  %H:%M:%S")
        fill_event.exchange = contract.exchange
        fill_event.full_symbol = full_symbol

        self.broker.put(fill_event)

    def execDetailsEnd(self, reqId: int):
        super().execDetailsEnd(reqId)
        print("ExecDetailsEnd. ReqId:", reqId)

    def displayGroupList(self, reqId: int, groups: str):
        super().displayGroupList(reqId, groups)
        print("DisplayGroupList. ReqId:", reqId, "Groups", groups)

    def displayGroupUpdated(self, reqId: int, contractInfo: str):
        super().displayGroupUpdated(reqId, contractInfo)
        print("DisplayGroupUpdated. ReqId:", reqId, "ContractInfo:", contractInfo)

    def commissionReport(self, commissionReport: CommissionReport):
        super().commissionReport(commissionReport)
        print("CommissionReport.", commissionReport)

    def completedOrder(self, contract: Contract, order: Order,
                       orderState: OrderState):
        super().completedOrder(contract, order, orderState)
        print("CompletedOrder. PermId:", order.permId, "ParentPermId:", utils.longToStr(order.parentPermId),
              "Account:", order.account,
              "Symbol:", contract.symbol, "SecType:", contract.secType, "Exchange:", contract.exchange,
              "Action:", order.action, "OrderType:", order.orderType, "TotalQty:", order.totalQuantity,
              "CashQty:", order.cashQty, "FilledQty:", order.filledQuantity,
              "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status,
              "Completed time:", orderState.completedTime, "Completed Status:" + orderState.completedStatus)

    def completedOrdersEnd(self):
        super().completedOrdersEnd()
        print("CompletedOrdersEnd")
    # ---------------------------------- End EWrapper functions ---------------------------------------------- #


