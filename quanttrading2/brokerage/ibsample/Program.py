"""
Copyright (C) 2019 Interactive Brokers LLC. All rights reserved. This code is subject to the terms
 and conditions of the IB API Non-Commercial License or the IB API Commercial License, as applicable.
"""

import argparse
import datetime
import collections
import inspect

import logging
import time
import os.path

from ibapi import wrapper
from ibapi import utils
from ibapi.client import EClient
from ibapi.utils import iswrapper

# types
from ibapi.common import * # @UnusedWildImport
from ibapi.order_condition import * # @UnusedWildImport
from ibapi.contract import * # @UnusedWildImport
from ibapi.order import * # @UnusedWildImport
from ibapi.order_state import * # @UnusedWildImport
from ibapi.execution import Execution
from ibapi.execution import ExecutionFilter
from ibapi.commission_report import CommissionReport
from ibapi.ticktype import * # @UnusedWildImport
from ibapi.tag_value import TagValue

from ibapi.account_summary_tags import *

from ContractSamples import ContractSamples
from OrderSamples import OrderSamples
from AvailableAlgoParams import AvailableAlgoParams
from ScannerSubscriptionSamples import ScannerSubscriptionSamples
from FaAllocationSamples import FaAllocationSamples
from ibapi.scanner import ScanData


def SetupLogger():
    if not os.path.exists("log"):
        os.makedirs("log")

    time.strftime("pyibapi.%Y%m%d_%H%M%S.log")

    recfmt = '(%(threadName)s) %(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s'

    timefmt = '%y%m%d_%H:%M:%S'

    # logging.basicConfig( level=logging.DEBUG,
    #                    format=recfmt, datefmt=timefmt)
    logging.basicConfig(filename=time.strftime("log/pyibapi.%y%m%d_%H%M%S.log"),
                        filemode="w",
                        level=logging.INFO,
                        format=recfmt, datefmt=timefmt)
    logger = logging.getLogger()
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    logger.addHandler(console)


def printWhenExecuting(fn):
    def fn2(self):
        print("   doing", fn.__name__)
        fn(self)
        print("   done w/", fn.__name__)

    return fn2

def printinstance(inst:Object):
    attrs = vars(inst)
    print(', '.join("%s: %s" % item for item in attrs.items()))

class Activity(Object):
    def __init__(self, reqMsgId, ansMsgId, ansEndMsgId, reqId):
        self.reqMsdId = reqMsgId
        self.ansMsgId = ansMsgId
        self.ansEndMsgId = ansEndMsgId
        self.reqId = reqId


class RequestMgr(Object):
    def __init__(self):
        # I will keep this simple even if slower for now: only one list of
        # requests finding will be done by linear search
        self.requests = []

    def addReq(self, req):
        self.requests.append(req)

    def receivedMsg(self, msg):
        pass


# ! [socket_declare]
class TestClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)
        # ! [socket_declare]

        # how many times a method is called to see test coverage
        self.clntMeth2callCount = collections.defaultdict(int)
        self.clntMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        self.reqId2nReq = collections.defaultdict(int)
        self.setupDetectReqId()

    def countReqId(self, methName, fn):
        def countReqId_(*args, **kwargs):
            self.clntMeth2callCount[methName] += 1
            idx = self.clntMeth2reqIdIdx[methName]
            if idx >= 0:
                sign = -1 if 'cancel' in methName else 1
                self.reqId2nReq[sign * args[idx]] += 1
            return fn(*args, **kwargs)

        return countReqId_

    def setupDetectReqId(self):

        methods = inspect.getmembers(EClient, inspect.isfunction)
        for (methName, meth) in methods:
            if methName != "send_msg":
                # don't screw up the nice automated logging in the send_msg()
                self.clntMeth2callCount[methName] = 0
                # logging.debug("meth %s", name)
                sig = inspect.signature(meth)
                for (idx, pnameNparam) in enumerate(sig.parameters.items()):
                    (paramName, param) = pnameNparam # @UnusedVariable
                    if paramName == "reqId":
                        self.clntMeth2reqIdIdx[methName] = idx

                setattr(TestClient, methName, self.countReqId(methName, meth))

                # print("TestClient.clntMeth2reqIdIdx", self.clntMeth2reqIdIdx)


# ! [ewrapperimpl]
class TestWrapper(wrapper.EWrapper):
    # ! [ewrapperimpl]
    def __init__(self):
        wrapper.EWrapper.__init__(self)

        self.wrapMeth2callCount = collections.defaultdict(int)
        self.wrapMeth2reqIdIdx = collections.defaultdict(lambda: -1)
        self.reqId2nAns = collections.defaultdict(int)
        self.setupDetectWrapperReqId()

    # TODO: see how to factor this out !!

    def countWrapReqId(self, methName, fn):
        def countWrapReqId_(*args, **kwargs):
            self.wrapMeth2callCount[methName] += 1
            idx = self.wrapMeth2reqIdIdx[methName]
            if idx >= 0:
                self.reqId2nAns[args[idx]] += 1
            return fn(*args, **kwargs)

        return countWrapReqId_

    def setupDetectWrapperReqId(self):

        methods = inspect.getmembers(wrapper.EWrapper, inspect.isfunction)
        for (methName, meth) in methods:
            self.wrapMeth2callCount[methName] = 0
            # logging.debug("meth %s", name)
            sig = inspect.signature(meth)
            for (idx, pnameNparam) in enumerate(sig.parameters.items()):
                (paramName, param) = pnameNparam # @UnusedVariable
                # we want to count the errors as 'error' not 'answer'
                if 'error' not in methName and paramName == "reqId":
                    self.wrapMeth2reqIdIdx[methName] = idx

            setattr(TestWrapper, methName, self.countWrapReqId(methName, meth))

            # print("TestClient.wrapMeth2reqIdIdx", self.wrapMeth2reqIdIdx)


# this is here for documentation generation
"""
#! [ereader]
        # You don't need to run this in your code!
        self.reader = reader.EReader(self.conn, self.msg_queue)
        self.reader.start()   # start thread
#! [ereader]
"""

# ! [socket_init]
class TestApp(TestWrapper, TestClient):
    def __init__(self):
        TestWrapper.__init__(self)
        TestClient.__init__(self, wrapper=self)
        # ! [socket_init]
        self.nKeybInt = 0
        self.started = False
        self.nextValidOrderId = None
        self.permId2ord = {}
        self.reqId2nErr = collections.defaultdict(int)
        self.globalCancelOnly = False
        self.simplePlaceOid = None

    def dumpTestCoverageSituation(self):
        for clntMeth in sorted(self.clntMeth2callCount.keys()):
            logging.debug("ClntMeth: %-30s %6d" % (clntMeth,
                                                   self.clntMeth2callCount[clntMeth]))

        for wrapMeth in sorted(self.wrapMeth2callCount.keys()):
            logging.debug("WrapMeth: %-30s %6d" % (wrapMeth,
                                                   self.wrapMeth2callCount[wrapMeth]))

    def dumpReqAnsErrSituation(self):
        logging.debug("%s\t%s\t%s\t%s" % ("ReqId", "#Req", "#Ans", "#Err"))
        for reqId in sorted(self.reqId2nReq.keys()):
            nReq = self.reqId2nReq.get(reqId, 0)
            nAns = self.reqId2nAns.get(reqId, 0)
            nErr = self.reqId2nErr.get(reqId, 0)
            logging.debug("%d\t%d\t%s\t%d" % (reqId, nReq, nAns, nErr))

    @iswrapper
    # ! [connectack]
    def connectAck(self):
        if self.asynchronous:
            self.startApi()

    # ! [connectack]

    @iswrapper
    # ! [nextvalidid]
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)

        logging.debug("setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId
        print("NextValidId:", orderId)
    # ! [nextvalidid]

        # we can start now
        self.start()

    def start(self):
        if self.started:
            return

        self.started = True

        if self.globalCancelOnly:
            print("Executing GlobalCancel only")
            self.reqGlobalCancel()
        else:
            print("Executing requests")
            #self.reqGlobalCancel()
            #self.marketDataTypeOperations()
            #self.accountOperations_req()
            #self.tickDataOperations_req()
            #self.marketDepthOperations_req()
            #self.realTimeBarsOperations_req()
            #self.historicalDataOperations_req()
            #self.optionsOperations_req()
            #self.marketScannersOperations_req()
            #self.fundamentalsOperations_req()
            #self.bulletinsOperations_req()
            #self.contractOperations()
            #self.newsOperations_req()
            #self.miscelaneousOperations()
            #self.linkingOperations()
            #self.financialAdvisorOperations()
            self.orderOperations_req()
            #self.rerouteCFDOperations()
            #self.marketRuleOperations()
            #self.pnlOperations_req()
            #self.histogramOperations_req()
            #self.continuousFuturesOperations_req()
            #self.historicalTicksOperations()
            #self.tickByTickOperations_req()
            #self.whatIfOrderOperations()
            
            print("Executing requests ... finished")

    def keyboardInterrupt(self):
        self.nKeybInt += 1
        if self.nKeybInt == 1:
            self.stop()
        else:
            print("Finishing test")
            self.done = True

    def stop(self):
        print("Executing cancels")
        #self.orderOperations_cancel()
        #self.accountOperations_cancel()
        #self.tickDataOperations_cancel()
        self.marketDepthOperations_cancel()
        #self.realTimeBarsOperations_cancel()
        #self.historicalDataOperations_cancel()
        #self.optionsOperations_cancel()
        #self.marketScanners_cancel()
        #self.fundamentalsOperations_cancel()
        #self.bulletinsOperations_cancel()
        #self.newsOperations_cancel()
        #self.pnlOperations_cancel()
        #self.histogramOperations_cancel()
        #self.continuousFuturesOperations_cancel()
        #self.tickByTickOperations_cancel()
        print("Executing cancels ... finished")

    def nextOrderId(self):
        oid = self.nextValidOrderId
        self.nextValidOrderId += 1
        return oid

    @iswrapper
    # ! [error]
    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        super().error(reqId, errorCode, errorString)
        print("Error. Id:", reqId, "Code:", errorCode, "Msg:", errorString)

    # ! [error] self.reqId2nErr[reqId] += 1


    @iswrapper
    def winError(self, text: str, lastError: int):
        super().winError(text, lastError)

    @iswrapper
    # ! [openorder]
    def openOrder(self, orderId: OrderId, contract: Contract, order: Order,
                  orderState: OrderState):
        super().openOrder(orderId, contract, order, orderState)
        print("OpenOrder. PermId: ", order.permId, "ClientId:", order.clientId, " OrderId:", orderId, 
              "Account:", order.account, "Symbol:", contract.symbol, "SecType:", contract.secType,
              "Exchange:", contract.exchange, "Action:", order.action, "OrderType:", order.orderType,
              "TotalQty:", order.totalQuantity, "CashQty:", order.cashQty, 
              "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status)

        order.contract = contract
        self.permId2ord[order.permId] = order
    # ! [openorder]

    @iswrapper
    # ! [openorderend]
    def openOrderEnd(self):
        super().openOrderEnd()
        print("OpenOrderEnd")

        logging.debug("Received %d openOrders", len(self.permId2ord))
    # ! [openorderend]

    @iswrapper
    # ! [orderstatus]
    def orderStatus(self, orderId: OrderId, status: str, filled: float,
                    remaining: float, avgFillPrice: float, permId: int,
                    parentId: int, lastFillPrice: float, clientId: int,
                    whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining,
                            avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        print("OrderStatus. Id:", orderId, "Status:", status, "Filled:", filled,
              "Remaining:", remaining, "AvgFillPrice:", avgFillPrice,
              "PermId:", permId, "ParentId:", parentId, "LastFillPrice:",
              lastFillPrice, "ClientId:", clientId, "WhyHeld:",
              whyHeld, "MktCapPrice:", mktCapPrice)
    # ! [orderstatus]


    @printWhenExecuting
    def accountOperations_req(self):
        # Requesting managed accounts
        # ! [reqmanagedaccts]
        self.reqManagedAccts()
        # ! [reqmanagedaccts]

        # Requesting family codes
        # ! [reqfamilycodes]
        self.reqFamilyCodes()
        # ! [reqfamilycodes]

        # Requesting accounts' summary
        # ! [reqaaccountsummary]
        self.reqAccountSummary(9001, "All", AccountSummaryTags.AllTags)
        # ! [reqaaccountsummary]

        # ! [reqaaccountsummaryledger]
        self.reqAccountSummary(9002, "All", "$LEDGER")
        # ! [reqaaccountsummaryledger]

        # ! [reqaaccountsummaryledgercurrency]
        self.reqAccountSummary(9003, "All", "$LEDGER:EUR")
        # ! [reqaaccountsummaryledgercurrency]

        # ! [reqaaccountsummaryledgerall]
        self.reqAccountSummary(9004, "All", "$LEDGER:ALL")
        # ! [reqaaccountsummaryledgerall]

        # Subscribing to an account's information. Only one at a time!
        # ! [reqaaccountupdates]
        self.reqAccountUpdates(True, self.account)
        # ! [reqaaccountupdates]

        # ! [reqaaccountupdatesmulti]
        self.reqAccountUpdatesMulti(9005, self.account, "", True)
        # ! [reqaaccountupdatesmulti]

        # Requesting all accounts' positions.
        # ! [reqpositions]
        self.reqPositions()
        # ! [reqpositions]

        # ! [reqpositionsmulti]
        self.reqPositionsMulti(9006, self.account, "")
        # ! [reqpositionsmulti]

    @printWhenExecuting
    def accountOperations_cancel(self):
        # ! [cancelaaccountsummary]
        self.cancelAccountSummary(9001)
        self.cancelAccountSummary(9002)
        self.cancelAccountSummary(9003)
        self.cancelAccountSummary(9004)
        # ! [cancelaaccountsummary]

        # ! [cancelaaccountupdates]
        self.reqAccountUpdates(False, self.account)
        # ! [cancelaaccountupdates]

        # ! [cancelaaccountupdatesmulti]
        self.cancelAccountUpdatesMulti(9005)
        # ! [cancelaaccountupdatesmulti]

        # ! [cancelpositions]
        self.cancelPositions()
        # ! [cancelpositions]

        # ! [cancelpositionsmulti]
        self.cancelPositionsMulti(9006)
        # ! [cancelpositionsmulti]

    def pnlOperations_req(self):
        # ! [reqpnl]
        self.reqPnL(17001, "DU111519", "")
        # ! [reqpnl]

        # ! [reqpnlsingle]
        self.reqPnLSingle(17002, "DU111519", "", 8314);
        # ! [reqpnlsingle]

    def pnlOperations_cancel(self):
        # ! [cancelpnl]
        self.cancelPnL(17001)
        # ! [cancelpnl]

        # ! [cancelpnlsingle]
        self.cancelPnLSingle(17002);
        # ! [cancelpnlsingle]

    def histogramOperations_req(self):
        # ! [reqhistogramdata]
        self.reqHistogramData(4002, ContractSamples.USStockAtSmart(), False, "3 days");
        # ! [reqhistogramdata]

    def histogramOperations_cancel(self):
        # ! [cancelhistogramdata]
        self.cancelHistogramData(4002);
        # ! [cancelhistogramdata]

    def continuousFuturesOperations_req(self):
        # ! [reqcontractdetailscontfut]
        self.reqContractDetails(18001, ContractSamples.ContFut())
        # ! [reqcontractdetailscontfut]

        # ! [reqhistoricaldatacontfut]
        timeStr = datetime.datetime.fromtimestamp(time.time()).strftime('%Y%m%d %H:%M:%S')
        self.reqHistoricalData(18002, ContractSamples.ContFut(), timeStr, "1 Y", "1 month", "TRADES", 0, 1, False, []);
        # ! [reqhistoricaldatacontfut]

    def continuousFuturesOperations_cancel(self):
        # ! [cancelhistoricaldatacontfut]
        self.cancelHistoricalData(18002);
        # ! [cancelhistoricaldatacontfut]

    @iswrapper
    # ! [managedaccounts]
    def managedAccounts(self, accountsList: str):
        super().managedAccounts(accountsList)
        print("Account list:", accountsList)
        # ! [managedaccounts]

        self.account = accountsList.split(",")[0]

    @iswrapper
    # ! [accountsummary]
    def accountSummary(self, reqId: int, account: str, tag: str, value: str,
                       currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        print("AccountSummary. ReqId:", reqId, "Account:", account,
              "Tag: ", tag, "Value:", value, "Currency:", currency)
    # ! [accountsummary]

    @iswrapper
    # ! [accountsummaryend]
    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(reqId)
        print("AccountSummaryEnd. ReqId:", reqId)
    # ! [accountsummaryend]

    @iswrapper
    # ! [updateaccountvalue]
    def updateAccountValue(self, key: str, val: str, currency: str,
                           accountName: str):
        super().updateAccountValue(key, val, currency, accountName)
        print("UpdateAccountValue. Key:", key, "Value:", val,
              "Currency:", currency, "AccountName:", accountName)
    # ! [updateaccountvalue]

    @iswrapper
    # ! [updateportfolio]
    def updatePortfolio(self, contract: Contract, position: float,
                        marketPrice: float, marketValue: float,
                        averageCost: float, unrealizedPNL: float,
                        realizedPNL: float, accountName: str):
        super().updatePortfolio(contract, position, marketPrice, marketValue,
                                averageCost, unrealizedPNL, realizedPNL, accountName)
        print("UpdatePortfolio.", "Symbol:", contract.symbol, "SecType:", contract.secType, "Exchange:",
              contract.exchange, "Position:", position, "MarketPrice:", marketPrice,
              "MarketValue:", marketValue, "AverageCost:", averageCost,
              "UnrealizedPNL:", unrealizedPNL, "RealizedPNL:", realizedPNL,
              "AccountName:", accountName)
    # ! [updateportfolio]

    @iswrapper
    # ! [updateaccounttime]
    def updateAccountTime(self, timeStamp: str):
        super().updateAccountTime(timeStamp)
        print("UpdateAccountTime. Time:", timeStamp)
    # ! [updateaccounttime]

    @iswrapper
    # ! [accountdownloadend]
    def accountDownloadEnd(self, accountName: str):
        super().accountDownloadEnd(accountName)
        print("AccountDownloadEnd. Account:", accountName)
    # ! [accountdownloadend]

    @iswrapper
    # ! [position]
    def position(self, account: str, contract: Contract, position: float,
                 avgCost: float):
        super().position(account, contract, position, avgCost)
        print("Position.", "Account:", account, "Symbol:", contract.symbol, "SecType:",
              contract.secType, "Currency:", contract.currency,
              "Position:", position, "Avg cost:", avgCost)
    # ! [position]

    @iswrapper
    # ! [positionend]
    def positionEnd(self):
        super().positionEnd()
        print("PositionEnd")
    # ! [positionend]

    @iswrapper
    # ! [positionmulti]
    def positionMulti(self, reqId: int, account: str, modelCode: str,
                      contract: Contract, pos: float, avgCost: float):
        super().positionMulti(reqId, account, modelCode, contract, pos, avgCost)
        print("PositionMulti. RequestId:", reqId, "Account:", account,
              "ModelCode:", modelCode, "Symbol:", contract.symbol, "SecType:",
              contract.secType, "Currency:", contract.currency, ",Position:",
              pos, "AvgCost:", avgCost)
    # ! [positionmulti]

    @iswrapper
    # ! [positionmultiend]
    def positionMultiEnd(self, reqId: int):
        super().positionMultiEnd(reqId)
        print("PositionMultiEnd. RequestId:", reqId)
    # ! [positionmultiend]

    @iswrapper
    # ! [accountupdatemulti]
    def accountUpdateMulti(self, reqId: int, account: str, modelCode: str,
                           key: str, value: str, currency: str):
        super().accountUpdateMulti(reqId, account, modelCode, key, value,
                                   currency)
        print("AccountUpdateMulti. RequestId:", reqId, "Account:", account,
              "ModelCode:", modelCode, "Key:", key, "Value:", value,
              "Currency:", currency)
    # ! [accountupdatemulti]

    @iswrapper
    # ! [accountupdatemultiend]
    def accountUpdateMultiEnd(self, reqId: int):
        super().accountUpdateMultiEnd(reqId)
        print("AccountUpdateMultiEnd. RequestId:", reqId)
    # ! [accountupdatemultiend]

    @iswrapper
    # ! [familyCodes]
    def familyCodes(self, familyCodes: ListOfFamilyCode):
        super().familyCodes(familyCodes)
        print("Family Codes:")
        for familyCode in familyCodes:
            print("FamilyCode.", familyCode)
    # ! [familyCodes]

    @iswrapper
    # ! [pnl]
    def pnl(self, reqId: int, dailyPnL: float,
            unrealizedPnL: float, realizedPnL: float):
        super().pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)
        print("Daily PnL. ReqId:", reqId, "DailyPnL:", dailyPnL,
              "UnrealizedPnL:", unrealizedPnL, "RealizedPnL:", realizedPnL)
    # ! [pnl]

    @iswrapper
    # ! [pnlsingle]
    def pnlSingle(self, reqId: int, pos: int, dailyPnL: float,
                  unrealizedPnL: float, realizedPnL: float, value: float):
        super().pnlSingle(reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value)
        print("Daily PnL Single. ReqId:", reqId, "Position:", pos,
              "DailyPnL:", dailyPnL, "UnrealizedPnL:", unrealizedPnL,
              "RealizedPnL:", realizedPnL, "Value:", value)
    # ! [pnlsingle]

    def marketDataTypeOperations(self):
        # ! [reqmarketdatatype]
        # Switch to live (1) frozen (2) delayed (3) delayed frozen (4).
        self.reqMarketDataType(MarketDataTypeEnum.DELAYED)
        # ! [reqmarketdatatype]

    @iswrapper
    # ! [marketdatatype]
    def marketDataType(self, reqId: TickerId, marketDataType: int):
        super().marketDataType(reqId, marketDataType)
        print("MarketDataType. ReqId:", reqId, "Type:", marketDataType)
    # ! [marketdatatype]

    @printWhenExecuting
    def tickDataOperations_req(self):
        self.reqMarketDataType(MarketDataTypeEnum.DELAYED_FROZEN)
        
        # Requesting real time market data

        # ! [reqmktdata]
        self.reqMktData(1000, ContractSamples.USStockAtSmart(), "", False, False, [])
        self.reqMktData(1001, ContractSamples.StockComboContract(), "", False, False, [])
        # ! [reqmktdata]

        # ! [reqmktdata_snapshot]
        self.reqMktData(1002, ContractSamples.FutureComboContract(), "", True, False, [])
        # ! [reqmktdata_snapshot]

        # ! [regulatorysnapshot]
        # Each regulatory snapshot request incurs a 0.01 USD fee
        self.reqMktData(1003, ContractSamples.USStock(), "", False, True, [])
        # ! [regulatorysnapshot]

        # ! [reqmktdata_genticks]
        # Requesting RTVolume (Time & Sales), shortable and Fundamental Ratios generic ticks
        self.reqMktData(1004, ContractSamples.USStockAtSmart(), "233,236,258", False, False, [])
        # ! [reqmktdata_genticks]

        # ! [reqmktdata_contractnews]
        # Without the API news subscription this will generate an "invalid tick type" error
        self.reqMktData(1005, ContractSamples.USStockAtSmart(), "mdoff,292:BRFG", False, False, [])
        self.reqMktData(1006, ContractSamples.USStockAtSmart(), "mdoff,292:BRFG+DJNL", False, False, [])
        self.reqMktData(1007, ContractSamples.USStockAtSmart(), "mdoff,292:BRFUPDN", False, False, [])
        self.reqMktData(1008, ContractSamples.USStockAtSmart(), "mdoff,292:DJ-RT", False, False, [])
        # ! [reqmktdata_contractnews]


        # ! [reqmktdata_broadtapenews]
        self.reqMktData(1009, ContractSamples.BRFGbroadtapeNewsFeed(), "mdoff,292", False, False, [])
        self.reqMktData(1010, ContractSamples.DJNLbroadtapeNewsFeed(), "mdoff,292", False, False, [])
        self.reqMktData(1011, ContractSamples.DJTOPbroadtapeNewsFeed(), "mdoff,292", False, False, [])
        self.reqMktData(1012, ContractSamples.BRFUPDNbroadtapeNewsFeed(), "mdoff,292", False, False, [])
        # ! [reqmktdata_broadtapenews]

        # ! [reqoptiondatagenticks]
        # Requesting data for an option contract will return the greek values
        self.reqMktData(1013, ContractSamples.OptionWithLocalSymbol(), "", False, False, [])
        self.reqMktData(1014, ContractSamples.FuturesOnOptions(), "", False, False, []);
        
        # ! [reqoptiondatagenticks]

        # ! [reqfuturesopeninterest]
        self.reqMktData(1015, ContractSamples.SimpleFuture(), "mdoff,588", False, False, [])
        # ! [reqfuturesopeninterest]

        # ! [reqmktdatapreopenbidask]
        self.reqMktData(1016, ContractSamples.SimpleFuture(), "", False, False, [])
        # ! [reqmktdatapreopenbidask]

        # ! [reqavgoptvolume]
        self.reqMktData(1017, ContractSamples.USStockAtSmart(), "mdoff,105", False, False, [])
        # ! [reqavgoptvolume]
        
        # ! [reqsmartcomponents]
        # Requests description of map of single letter exchange codes to full exchange names
        self.reqSmartComponents(1018, "a6")
        # ! [reqsmartcomponents]
        

    @printWhenExecuting
    def tickDataOperations_cancel(self):
        # Canceling the market data subscription
        # ! [cancelmktdata]
        self.cancelMktData(1000)
        self.cancelMktData(1001)
        # ! [cancelmktdata]

        self.cancelMktData(1004)
        
        self.cancelMktData(1005)
        self.cancelMktData(1006)
        self.cancelMktData(1007)
        self.cancelMktData(1008)
        
        self.cancelMktData(1009)
        self.cancelMktData(1010)
        self.cancelMktData(1011)
        self.cancelMktData(1012)
        
        self.cancelMktData(1013)
        self.cancelMktData(1014)
        
        self.cancelMktData(1015)
        
        self.cancelMktData(1016)
        
        self.cancelMktData(1017)

    @iswrapper
    # ! [tickprice]
    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float,
                  attrib: TickAttrib):
        super().tickPrice(reqId, tickType, price, attrib)
        print("TickPrice. TickerId:", reqId, "tickType:", tickType,
              "Price:", price, "CanAutoExecute:", attrib.canAutoExecute,
              "PastLimit:", attrib.pastLimit, end=' ')
        if tickType == TickTypeEnum.BID or tickType == TickTypeEnum.ASK:
            print("PreOpen:", attrib.preOpen)
        else:
            print()
    # ! [tickprice]

    @iswrapper
    # ! [ticksize]
    def tickSize(self, reqId: TickerId, tickType: TickType, size: int):
        super().tickSize(reqId, tickType, size)
        print("TickSize. TickerId:", reqId, "TickType:", tickType, "Size:", size)
    # ! [ticksize]

    @iswrapper
    # ! [tickgeneric]
    def tickGeneric(self, reqId: TickerId, tickType: TickType, value: float):
        super().tickGeneric(reqId, tickType, value)
        print("TickGeneric. TickerId:", reqId, "TickType:", tickType, "Value:", value)
    # ! [tickgeneric]

    @iswrapper
    # ! [tickstring]
    def tickString(self, reqId: TickerId, tickType: TickType, value: str):
        super().tickString(reqId, tickType, value)
        print("TickString. TickerId:", reqId, "Type:", tickType, "Value:", value)
    # ! [tickstring]

    @iswrapper
    # ! [ticksnapshotend]
    def tickSnapshotEnd(self, reqId: int):
        super().tickSnapshotEnd(reqId)
        print("TickSnapshotEnd. TickerId:", reqId)
    # ! [ticksnapshotend]

    @iswrapper
    # ! [rerouteMktDataReq]
    def rerouteMktDataReq(self, reqId: int, conId: int, exchange: str):
        super().rerouteMktDataReq(reqId, conId, exchange)
        print("Re-route market data request. ReqId:", reqId, "ConId:", conId, "Exchange:", exchange)
    # ! [rerouteMktDataReq]

    @iswrapper
    # ! [marketRule]
    def marketRule(self, marketRuleId: int, priceIncrements: ListOfPriceIncrements):
        super().marketRule(marketRuleId, priceIncrements)
        print("Market Rule ID: ", marketRuleId)
        for priceIncrement in priceIncrements:
            print("Price Increment.", priceIncrement)
    # ! [marketRule]

    @printWhenExecuting
    def tickByTickOperations_req(self):
        # Requesting tick-by-tick data (only refresh)
        # ! [reqtickbytick]
        self.reqTickByTickData(19001, ContractSamples.EuropeanStock2(), "Last", 0, True)
        self.reqTickByTickData(19002, ContractSamples.EuropeanStock2(), "AllLast", 0, False)
        self.reqTickByTickData(19003, ContractSamples.EuropeanStock2(), "BidAsk", 0, True)
        self.reqTickByTickData(19004, ContractSamples.EurGbpFx(), "MidPoint", 0, False)
        # ! [reqtickbytick]

        # Requesting tick-by-tick data (refresh + historicalticks)
        # ! [reqtickbytickwithhist]
        self.reqTickByTickData(19005, ContractSamples.EuropeanStock2(), "Last", 10, False)
        self.reqTickByTickData(19006, ContractSamples.EuropeanStock2(), "AllLast", 10, False)
        self.reqTickByTickData(19007, ContractSamples.EuropeanStock2(), "BidAsk", 10, False)
        self.reqTickByTickData(19008, ContractSamples.EurGbpFx(), "MidPoint", 10, True)
        # ! [reqtickbytickwithhist]

    @printWhenExecuting
    def tickByTickOperations_cancel(self):
        # ! [canceltickbytick]
        self.cancelTickByTickData(19001)
        self.cancelTickByTickData(19002)
        self.cancelTickByTickData(19003)
        self.cancelTickByTickData(19004)
        # ! [canceltickbytick]

        # ! [canceltickbytickwithhist]
        self.cancelTickByTickData(19005)
        self.cancelTickByTickData(19006)
        self.cancelTickByTickData(19007)
        self.cancelTickByTickData(19008)
        # ! [canceltickbytickwithhist]
        
    @iswrapper
    # ! [orderbound]
    def orderBound(self, orderId: int, apiClientId: int, apiOrderId: int):
        super().orderBound(orderId, apiClientId, apiOrderId)
        print("OrderBound.", "OrderId:", orderId, "ApiClientId:", apiClientId, "ApiOrderId:", apiOrderId)
    # ! [orderbound]

    @iswrapper
    # ! [tickbytickalllast]
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
              "Price:", price, "Size:", size, "Exch:" , exchange,
              "Spec Cond:", specialConditions, "PastLimit:", tickAtrribLast.pastLimit, "Unreported:", tickAtrribLast.unreported)
    # ! [tickbytickalllast]

    @iswrapper
    # ! [tickbytickbidask]
    def tickByTickBidAsk(self, reqId: int, time: int, bidPrice: float, askPrice: float,
                         bidSize: int, askSize: int, tickAttribBidAsk: TickAttribBidAsk):
        super().tickByTickBidAsk(reqId, time, bidPrice, askPrice, bidSize,
                                 askSize, tickAttribBidAsk)
        print("BidAsk. ReqId:", reqId,
              "Time:", datetime.datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S"),
              "BidPrice:", bidPrice, "AskPrice:", askPrice, "BidSize:", bidSize,
              "AskSize:", askSize, "BidPastLow:", tickAttribBidAsk.bidPastLow, "AskPastHigh:", tickAttribBidAsk.askPastHigh)
    # ! [tickbytickbidask]

    # ! [tickbytickmidpoint]
    @iswrapper
    def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float):
        super().tickByTickMidPoint(reqId, time, midPoint)
        print("Midpoint. ReqId:", reqId,
              "Time:", datetime.datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S"),
              "MidPoint:", midPoint)
    # ! [tickbytickmidpoint]

    @printWhenExecuting
    def marketDepthOperations_req(self):
        # Requesting the Deep Book
        # ! [reqmarketdepth]
        self.reqMktDepth(2001, ContractSamples.EurGbpFx(), 5, False, [])
        # ! [reqmarketdepth]

        # ! [reqmarketdepth]
        self.reqMktDepth(2002, ContractSamples.EuropeanStock(), 5, True, [])
        # ! [reqmarketdepth]

        # Request list of exchanges sending market depth to UpdateMktDepthL2()
        # ! [reqMktDepthExchanges]
        self.reqMktDepthExchanges()
        # ! [reqMktDepthExchanges]

    @printWhenExecuting
    def marketDepthOperations_cancel(self):
        # Canceling the Deep Book request
        # ! [cancelmktdepth]
        self.cancelMktDepth(2001, False)
        self.cancelMktDepth(2002, True)
        # ! [cancelmktdepth]

    @iswrapper
    # ! [updatemktdepth]
    def updateMktDepth(self, reqId: TickerId, position: int, operation: int,
                       side: int, price: float, size: int):
        super().updateMktDepth(reqId, position, operation, side, price, size)
        print("UpdateMarketDepth. ReqId:", reqId, "Position:", position, "Operation:",
              operation, "Side:", side, "Price:", price, "Size:", size)
    # ! [updatemktdepth]

    @iswrapper
    # ! [updatemktdepthl2]
    def updateMktDepthL2(self, reqId: TickerId, position: int, marketMaker: str,
                         operation: int, side: int, price: float, size: int, isSmartDepth: bool):
        super().updateMktDepthL2(reqId, position, marketMaker, operation, side,
                                 price, size, isSmartDepth)
        print("UpdateMarketDepthL2. ReqId:", reqId, "Position:", position, "MarketMaker:", marketMaker, "Operation:",
              operation, "Side:", side, "Price:", price, "Size:", size, "isSmartDepth:", isSmartDepth)

    # ! [updatemktdepthl2]

    @iswrapper
    # ! [rerouteMktDepthReq]
    def rerouteMktDepthReq(self, reqId: int, conId: int, exchange: str):
        super().rerouteMktDataReq(reqId, conId, exchange)
        print("Re-route market depth request. ReqId:", reqId, "ConId:", conId, "Exchange:", exchange)
    # ! [rerouteMktDepthReq]

    @printWhenExecuting
    def realTimeBarsOperations_req(self):
        # Requesting real time bars
        # ! [reqrealtimebars]
        self.reqRealTimeBars(3001, ContractSamples.EurGbpFx(), 5, "MIDPOINT", True, [])
        # ! [reqrealtimebars]

    @iswrapper
    # ! [realtimebar]
    def realtimeBar(self, reqId: TickerId, time:int, open_: float, high: float, low: float, close: float,
                        volume: int, wap: float, count: int):
        super().realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)
        print("RealTimeBar. TickerId:", reqId, RealTimeBar(time, -1, open_, high, low, close, volume, wap, count))
    # ! [realtimebar]

    @printWhenExecuting
    def realTimeBarsOperations_cancel(self):
        # Canceling real time bars
        # ! [cancelrealtimebars]
        self.cancelRealTimeBars(3001)
        # ! [cancelrealtimebars]

    @printWhenExecuting
    def historicalDataOperations_req(self):
        # Requesting historical data
        # ! [reqHeadTimeStamp]
        self.reqHeadTimeStamp(4101, ContractSamples.USStockAtSmart(), "TRADES", 0, 1)
        # ! [reqHeadTimeStamp]

        # ! [reqhistoricaldata]
        queryTime = (datetime.datetime.today() - datetime.timedelta(days=180)).strftime("%Y%m%d %H:%M:%S")
        self.reqHistoricalData(4102, ContractSamples.EurGbpFx(), queryTime,
                               "1 M", "1 day", "MIDPOINT", 1, 1, False, [])
        self.reqHistoricalData(4103, ContractSamples.EuropeanStock(), queryTime,
                               "10 D", "1 min", "TRADES", 1, 1, False, [])
        self.reqHistoricalData(4104, ContractSamples.EurGbpFx(), "",
                               "1 M", "1 day", "MIDPOINT", 1, 1, True, [])
        # ! [reqhistoricaldata]

    @printWhenExecuting
    def historicalDataOperations_cancel(self):
        # ! [cancelHeadTimestamp]
        self.cancelHeadTimeStamp(4101)
        # ! [cancelHeadTimestamp]
        
        # Canceling historical data requests
        # ! [cancelhistoricaldata]
        self.cancelHistoricalData(4102)
        self.cancelHistoricalData(4103)
        self.cancelHistoricalData(4104)
        # ! [cancelhistoricaldata]

    @printWhenExecuting
    def historicalTicksOperations(self):
        # ! [reqhistoricalticks]
        self.reqHistoricalTicks(18001, ContractSamples.USStockAtSmart(),
                                "20170712 21:39:33", "", 10, "TRADES", 1, True, [])
        self.reqHistoricalTicks(18002, ContractSamples.USStockAtSmart(),
                                "20170712 21:39:33", "", 10, "BID_ASK", 1, True, [])
        self.reqHistoricalTicks(18003, ContractSamples.USStockAtSmart(),
                                "20170712 21:39:33", "", 10, "MIDPOINT", 1, True, [])
        # ! [reqhistoricalticks]

    @iswrapper
    # ! [headTimestamp]
    def headTimestamp(self, reqId:int, headTimestamp:str):
        print("HeadTimestamp. ReqId:", reqId, "HeadTimeStamp:", headTimestamp)
    # ! [headTimestamp]

    @iswrapper
    # ! [histogramData]
    def histogramData(self, reqId:int, items:HistogramDataList):
        print("HistogramData. ReqId:", reqId, "HistogramDataList:", "[%s]" % "; ".join(map(str, items)))
    # ! [histogramData]

    @iswrapper
    # ! [historicaldata]
    def historicalData(self, reqId:int, bar: BarData):
        print("HistoricalData. ReqId:", reqId, "BarData.", bar)
    # ! [historicaldata]

    @iswrapper
    # ! [historicaldataend]
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)
        print("HistoricalDataEnd. ReqId:", reqId, "from", start, "to", end)
    # ! [historicaldataend]

    @iswrapper
    # ! [historicalDataUpdate]
    def historicalDataUpdate(self, reqId: int, bar: BarData):
        print("HistoricalDataUpdate. ReqId:", reqId, "BarData.", bar)
    # ! [historicalDataUpdate]

    @iswrapper
    # ! [historicalticks]
    def historicalTicks(self, reqId: int, ticks: ListOfHistoricalTick, done: bool):
        for tick in ticks:
            print("HistoricalTick. ReqId:", reqId, tick)
    # ! [historicalticks]

    @iswrapper
    # ! [historicalticksbidask]
    def historicalTicksBidAsk(self, reqId: int, ticks: ListOfHistoricalTickBidAsk,
                              done: bool):
        for tick in ticks:
            print("HistoricalTickBidAsk. ReqId:", reqId, tick)
    # ! [historicalticksbidask]

    @iswrapper
    # ! [historicaltickslast]
    def historicalTicksLast(self, reqId: int, ticks: ListOfHistoricalTickLast,
                            done: bool):
        for tick in ticks:
            print("HistoricalTickLast. ReqId:", reqId, tick)
    # ! [historicaltickslast]

    @printWhenExecuting
    def optionsOperations_req(self):
        # ! [reqsecdefoptparams]
        self.reqSecDefOptParams(0, "IBM", "", "STK", 8314)
        # ! [reqsecdefoptparams]

        # Calculating implied volatility
        # ! [calculateimpliedvolatility]
        self.calculateImpliedVolatility(5001, ContractSamples.OptionAtBOX(), 5, 85, [])
        # ! [calculateimpliedvolatility]

        # Calculating option's price
        # ! [calculateoptionprice]
        self.calculateOptionPrice(5002, ContractSamples.OptionAtBOX(), 0.22, 85, [])
        # ! [calculateoptionprice]

        # Exercising options
        # ! [exercise_options]
        self.exerciseOptions(5003, ContractSamples.OptionWithTradingClass(), 1,
                             1, self.account, 1)
        # ! [exercise_options]

    @printWhenExecuting
    def optionsOperations_cancel(self):
        # Canceling implied volatility
        self.cancelCalculateImpliedVolatility(5001)
        # Canceling option's price calculation
        self.cancelCalculateOptionPrice(5002)

    @iswrapper
    # ! [securityDefinitionOptionParameter]
    def securityDefinitionOptionParameter(self, reqId: int, exchange: str,
                                          underlyingConId: int, tradingClass: str, multiplier: str,
                                          expirations: SetOfString, strikes: SetOfFloat):
        super().securityDefinitionOptionParameter(reqId, exchange,
                                                  underlyingConId, tradingClass, multiplier, expirations, strikes)
        print("SecurityDefinitionOptionParameter.",
              "ReqId:", reqId, "Exchange:", exchange, "Underlying conId:", underlyingConId, "TradingClass:", tradingClass, "Multiplier:", multiplier,
              "Expirations:", expirations, "Strikes:", str(strikes))
    # ! [securityDefinitionOptionParameter]

    @iswrapper
    # ! [securityDefinitionOptionParameterEnd]
    def securityDefinitionOptionParameterEnd(self, reqId: int):
        super().securityDefinitionOptionParameterEnd(reqId)
        print("SecurityDefinitionOptionParameterEnd. ReqId:", reqId)
    # ! [securityDefinitionOptionParameterEnd]

    @iswrapper
    # ! [tickoptioncomputation]
    def tickOptionComputation(self, reqId: TickerId, tickType: TickType,
                              impliedVol: float, delta: float, optPrice: float, pvDividend: float,
                              gamma: float, vega: float, theta: float, undPrice: float):
        super().tickOptionComputation(reqId, tickType, impliedVol, delta,
                                      optPrice, pvDividend, gamma, vega, theta, undPrice)
        print("TickOptionComputation. TickerId:", reqId, "TickType:", tickType,
              "ImpliedVolatility:", impliedVol, "Delta:", delta, "OptionPrice:",
              optPrice, "pvDividend:", pvDividend, "Gamma: ", gamma, "Vega:", vega,
              "Theta:", theta, "UnderlyingPrice:", undPrice)

    # ! [tickoptioncomputation]


    @printWhenExecuting
    def contractOperations(self):
        # ! [reqcontractdetails]
        self.reqContractDetails(210, ContractSamples.OptionForQuery())
        self.reqContractDetails(211, ContractSamples.EurGbpFx())
        self.reqContractDetails(212, ContractSamples.Bond())
        self.reqContractDetails(213, ContractSamples.FuturesOnOptions())
        self.reqContractDetails(214, ContractSamples.SimpleFuture())
        # ! [reqcontractdetails]

        # ! [reqmatchingsymbols]
        self.reqMatchingSymbols(211, "IB")
        # ! [reqmatchingsymbols]

    @printWhenExecuting
    def newsOperations_req(self):
        # Requesting news ticks
        # ! [reqNewsTicks]
        self.reqMktData(10001, ContractSamples.USStockAtSmart(), "mdoff,292", False, False, []);
        # ! [reqNewsTicks]

        # Returns list of subscribed news providers
        # ! [reqNewsProviders]
        self.reqNewsProviders()
        # ! [reqNewsProviders]

        # Returns body of news article given article ID
        # ! [reqNewsArticle]
        self.reqNewsArticle(10002,"BRFG", "BRFG$04fb9da2", [])
        # ! [reqNewsArticle]

        # Returns list of historical news headlines with IDs
        # ! [reqHistoricalNews]
        self.reqHistoricalNews(10003, 8314, "BRFG", "", "", 10, [])
        # ! [reqHistoricalNews]

        # ! [reqcontractdetailsnews]
        self.reqContractDetails(10004, ContractSamples.NewsFeedForQuery())
        # ! [reqcontractdetailsnews]

    @printWhenExecuting
    def newsOperations_cancel(self):
        # Canceling news ticks
        # ! [cancelNewsTicks]
        self.cancelMktData(10001);
        # ! [cancelNewsTicks]

    @iswrapper
    #! [tickNews]
    def tickNews(self, tickerId: int, timeStamp: int, providerCode: str,
                 articleId: str, headline: str, extraData: str):
        print("TickNews. TickerId:", tickerId, "TimeStamp:", timeStamp,
              "ProviderCode:", providerCode, "ArticleId:", articleId,
              "Headline:", headline, "ExtraData:", extraData)
    #! [tickNews]

    @iswrapper
    #! [historicalNews]
    def historicalNews(self, reqId: int, time: str, providerCode: str,
                       articleId: str, headline: str):
        print("HistoricalNews. ReqId:", reqId, "Time:", time,
              "ProviderCode:", providerCode, "ArticleId:", articleId,
              "Headline:", headline)
    #! [historicalNews]

    @iswrapper
    #! [historicalNewsEnd]
    def historicalNewsEnd(self, reqId:int, hasMore:bool):
        print("HistoricalNewsEnd. ReqId:", reqId, "HasMore:", hasMore)
    #! [historicalNewsEnd]

    @iswrapper
    #! [newsProviders]
    def newsProviders(self, newsProviders: ListOfNewsProviders):
        print("NewsProviders: ")
        for provider in newsProviders:
            print("NewsProvider.", provider)
    #! [newsProviders]

    @iswrapper
    #! [newsArticle]
    def newsArticle(self, reqId: int, articleType: int, articleText: str):
        print("NewsArticle. ReqId:", reqId, "ArticleType:", articleType,
              "ArticleText:", articleText)
    #! [newsArticle]

    @iswrapper
    # ! [contractdetails]
    def contractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().contractDetails(reqId, contractDetails)
        printinstance(contractDetails)
    # ! [contractdetails]

    @iswrapper
    # ! [bondcontractdetails]
    def bondContractDetails(self, reqId: int, contractDetails: ContractDetails):
        super().bondContractDetails(reqId, contractDetails)
        printinstance(contractDetails)
    # ! [bondcontractdetails]

    @iswrapper
    # ! [contractdetailsend]
    def contractDetailsEnd(self, reqId: int):
        super().contractDetailsEnd(reqId)
        print("ContractDetailsEnd. ReqId:", reqId)
    # ! [contractdetailsend]

    @iswrapper
    # ! [symbolSamples]
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
    # ! [symbolSamples]

    @printWhenExecuting
    def marketScannersOperations_req(self):
        # Requesting list of valid scanner parameters which can be used in TWS
        # ! [reqscannerparameters]
        self.reqScannerParameters()
        # ! [reqscannerparameters]

        # Triggering a scanner subscription
        # ! [reqscannersubscription]
        self.reqScannerSubscription(7001, ScannerSubscriptionSamples.HighOptVolumePCRatioUSIndexes(), [], [])

        # Generic Filters
        tagvalues = []
        tagvalues.append(TagValue("usdMarketCapAbove", "10000"))
        tagvalues.append(TagValue("optVolumeAbove", "1000"))
        tagvalues.append(TagValue("avgVolumeAbove", "10000"));

        self.reqScannerSubscription(7002, ScannerSubscriptionSamples.HotUSStkByVolume(), [], tagvalues) # requires TWS v973+
        # ! [reqscannersubscription]

        # ! [reqcomplexscanner]
        AAPLConIDTag = [TagValue("underConID", "265598")]
        self.reqScannerSubscription(7003, ScannerSubscriptionSamples.ComplexOrdersAndTrades(), [], AAPLConIDTag) # requires TWS v975+
        
        # ! [reqcomplexscanner]


    @printWhenExecuting
    def marketScanners_cancel(self):
        # Canceling the scanner subscription
        # ! [cancelscannersubscription]
        self.cancelScannerSubscription(7001)
        self.cancelScannerSubscription(7002)
        self.cancelScannerSubscription(7003)
        # ! [cancelscannersubscription]

    @iswrapper
    # ! [scannerparameters]
    def scannerParameters(self, xml: str):
        super().scannerParameters(xml)
        open('log/scanner.xml', 'w').write(xml)
        print("ScannerParameters received.")
    # ! [scannerparameters]

    @iswrapper
    # ! [scannerdata]
    def scannerData(self, reqId: int, rank: int, contractDetails: ContractDetails,
                    distance: str, benchmark: str, projection: str, legsStr: str):
        super().scannerData(reqId, rank, contractDetails, distance, benchmark,
                            projection, legsStr)
#        print("ScannerData. ReqId:", reqId, "Rank:", rank, "Symbol:", contractDetails.contract.symbol,
#              "SecType:", contractDetails.contract.secType,
#              "Currency:", contractDetails.contract.currency,
#              "Distance:", distance, "Benchmark:", benchmark,
#              "Projection:", projection, "Legs String:", legsStr)
        print("ScannerData. ReqId:", reqId, ScanData(contractDetails.contract, rank, distance, benchmark, projection, legsStr))
    # ! [scannerdata]

    @iswrapper
    # ! [scannerdataend]
    def scannerDataEnd(self, reqId: int):
        super().scannerDataEnd(reqId)
        print("ScannerDataEnd. ReqId:", reqId)
        # ! [scannerdataend]

    @iswrapper
    # ! [smartcomponents]
    def smartComponents(self, reqId:int, smartComponentMap:SmartComponentMap):
        super().smartComponents(reqId, smartComponentMap)
        print("SmartComponents:")
        for smartComponent in smartComponentMap:
            print("SmartComponent.", smartComponent)
    # ! [smartcomponents]

    @iswrapper
    # ! [tickReqParams]
    def tickReqParams(self, tickerId:int, minTick:float,
                      bboExchange:str, snapshotPermissions:int):
        super().tickReqParams(tickerId, minTick, bboExchange, snapshotPermissions)
        print("TickReqParams. TickerId:", tickerId, "MinTick:", minTick,
              "BboExchange:", bboExchange, "SnapshotPermissions:", snapshotPermissions)
    # ! [tickReqParams]

    @iswrapper
    # ! [mktDepthExchanges]
    def mktDepthExchanges(self, depthMktDataDescriptions:ListOfDepthExchanges):
        super().mktDepthExchanges(depthMktDataDescriptions)
        print("MktDepthExchanges:")
        for desc in depthMktDataDescriptions:
            print("DepthMktDataDescription.", desc)
    # ! [mktDepthExchanges]

    @printWhenExecuting
    def fundamentalsOperations_req(self):
        # Requesting Fundamentals
        # ! [reqfundamentaldata]
        self.reqFundamentalData(8001, ContractSamples.USStock(), "ReportsFinSummary", [])
        # ! [reqfundamentaldata]
        
        # ! [fundamentalexamples]
        self.reqFundamentalData(8002, ContractSamples.USStock(), "ReportSnapshot", []); # for company overview
        self.reqFundamentalData(8003, ContractSamples.USStock(), "ReportRatios", []); # for financial ratios
        self.reqFundamentalData(8004, ContractSamples.USStock(), "ReportsFinStatements", []); # for financial statements
        self.reqFundamentalData(8005, ContractSamples.USStock(), "RESC", []); # for analyst estimates
        self.reqFundamentalData(8006, ContractSamples.USStock(), "CalendarReport", []); # for company calendar
        # ! [fundamentalexamples]

    @printWhenExecuting
    def fundamentalsOperations_cancel(self):
        # Canceling fundamentalsOperations_req request
        # ! [cancelfundamentaldata]
        self.cancelFundamentalData(8001)
        # ! [cancelfundamentaldata]

        # ! [cancelfundamentalexamples]
        self.cancelFundamentalData(8002)
        self.cancelFundamentalData(8003)
        self.cancelFundamentalData(8004)
        self.cancelFundamentalData(8005)
        self.cancelFundamentalData(8006)
        # ! [cancelfundamentalexamples]

    @iswrapper
    # ! [fundamentaldata]
    def fundamentalData(self, reqId: TickerId, data: str):
        super().fundamentalData(reqId, data)
        print("FundamentalData. ReqId:", reqId, "Data:", data)
    # ! [fundamentaldata]

    @printWhenExecuting
    def bulletinsOperations_req(self):
        # Requesting Interactive Broker's news bulletinsOperations_req
        # ! [reqnewsbulletins]
        self.reqNewsBulletins(True)
        # ! [reqnewsbulletins]

    @printWhenExecuting
    def bulletinsOperations_cancel(self):
        # Canceling IB's news bulletinsOperations_req
        # ! [cancelnewsbulletins]
        self.cancelNewsBulletins()
        # ! [cancelnewsbulletins]

    @iswrapper
    # ! [updatenewsbulletin]
    def updateNewsBulletin(self, msgId: int, msgType: int, newsMessage: str,
                           originExch: str):
        super().updateNewsBulletin(msgId, msgType, newsMessage, originExch)
        print("News Bulletins. MsgId:", msgId, "Type:", msgType, "Message:", newsMessage,
              "Exchange of Origin: ", originExch)
        # ! [updatenewsbulletin]

    def ocaSample(self):
        # OCA ORDER
        # ! [ocasubmit]
        ocaOrders = [OrderSamples.LimitOrder("BUY", 1, 10), OrderSamples.LimitOrder("BUY", 1, 11),
                     OrderSamples.LimitOrder("BUY", 1, 12)]
        OrderSamples.OneCancelsAll("TestOCA_" + str(self.nextValidOrderId), ocaOrders, 2)
        for o in ocaOrders:
            self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), o)
            # ! [ocasubmit]

    def conditionSamples(self):
        # ! [order_conditioning_activate]
        mkt = OrderSamples.MarketOrder("BUY", 100)
        # Order will become active if conditioning criteria is met
        mkt.conditions.append(
            OrderSamples.PriceCondition(PriceCondition.TriggerMethodEnum.Default,
                                        208813720, "SMART", 600, False, False))
        mkt.conditions.append(OrderSamples.ExecutionCondition("EUR.USD", "CASH", "IDEALPRO", True))
        mkt.conditions.append(OrderSamples.MarginCondition(30, True, False))
        mkt.conditions.append(OrderSamples.PercentageChangeCondition(15.0, 208813720, "SMART", True, True))
        mkt.conditions.append(OrderSamples.TimeCondition("20160118 23:59:59", True, False))
        mkt.conditions.append(OrderSamples.VolumeCondition(208813720, "SMART", False, 100, True))
        self.placeOrder(self.nextOrderId(), ContractSamples.EuropeanStock(), mkt)
        # ! [order_conditioning_activate]

        # Conditions can make the order active or cancel it. Only LMT orders can be conditionally canceled.
        # ! [order_conditioning_cancel]
        lmt = OrderSamples.LimitOrder("BUY", 100, 20)
        # The active order will be cancelled if conditioning criteria is met
        lmt.conditionsCancelOrder = True
        lmt.conditions.append(
            OrderSamples.PriceCondition(PriceCondition.TriggerMethodEnum.Last,
                                        208813720, "SMART", 600, False, False))
        self.placeOrder(self.nextOrderId(), ContractSamples.EuropeanStock(), lmt)
        # ! [order_conditioning_cancel]

    def bracketSample(self):
        # BRACKET ORDER
        # ! [bracketsubmit]
        bracket = OrderSamples.BracketOrder(self.nextOrderId(), "BUY", 100, 30, 40, 20)
        for o in bracket:
            self.placeOrder(o.orderId, ContractSamples.EuropeanStock(), o)
            self.nextOrderId()  # need to advance this we'll skip one extra oid, it's fine
            # ! [bracketsubmit]

    def hedgeSample(self):
        # F Hedge order
        # ! [hedgesubmit]
        # Parent order on a contract which currency differs from your base currency
        parent = OrderSamples.LimitOrder("BUY", 100, 10)
        parent.orderId = self.nextOrderId()
        parent.transmit = False
        # Hedge on the currency conversion
        hedge = OrderSamples.MarketFHedge(parent.orderId, "BUY")
        # Place the parent first...
        self.placeOrder(parent.orderId, ContractSamples.EuropeanStock(), parent)
        # Then the hedge order
        self.placeOrder(self.nextOrderId(), ContractSamples.EurGbpFx(), hedge)
        # ! [hedgesubmit]

    def algoSamples(self):
        # ! [scale_order]
        scaleOrder = OrderSamples.RelativePeggedToPrimary("BUY",  70000,  189,  0.01);
        AvailableAlgoParams.FillScaleParams(scaleOrder, 2000, 500, True, .02, 189.00, 3600, 2.00, True, 10, 40);
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), scaleOrder);
        # ! [scale_order]

        time.sleep(1)

        # ! [algo_base_order]
        baseOrder = OrderSamples.LimitOrder("BUY", 1000, 1)
        # ! [algo_base_order]

        # ! [arrivalpx]
        AvailableAlgoParams.FillArrivalPriceParams(baseOrder, 0.1, "Aggressive", "09:00:00 CET", "16:00:00 CET", True, True, 100000)
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [arrivalpx]

        # ! [darkice]
        AvailableAlgoParams.FillDarkIceParams(baseOrder, 10, "09:00:00 CET", "16:00:00 CET", True, 100000)
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [darkice]

        # ! [place_midprice]
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), OrderSamples.Midprice("BUY", 1, 150))
        # ! [place_midprice]
		
        # ! [ad]
        # The Time Zone in "startTime" and "endTime" attributes is ignored and always defaulted to GMT
        AvailableAlgoParams.FillAccumulateDistributeParams(baseOrder, 10, 60, True, True, 1, True, True, "20161010-12:00:00 GMT", "20161010-16:00:00 GMT")
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [ad]

        # ! [twap]
        AvailableAlgoParams.FillTwapParams(baseOrder, "Marketable", "09:00:00 CET", "16:00:00 CET", True, 100000)
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [twap]

        # ! [vwap]
        AvailableAlgoParams.FillVwapParams(baseOrder, 0.2, "09:00:00 CET", "16:00:00 CET", True, True, 100000)
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [vwap]

        # ! [balanceimpactrisk]
        AvailableAlgoParams.FillBalanceImpactRiskParams(baseOrder, 0.1, "Aggressive", True)
        self.placeOrder(self.nextOrderId(), ContractSamples.USOptionContract(), baseOrder)
        # ! [balanceimpactrisk]

        # ! [minimpact]
        AvailableAlgoParams.FillMinImpactParams(baseOrder, 0.3)
        self.placeOrder(self.nextOrderId(), ContractSamples.USOptionContract(), baseOrder)
        # ! [minimpact]

        # ! [adaptive]
        AvailableAlgoParams.FillAdaptiveParams(baseOrder, "Normal")
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [adaptive]

        # ! [closepx]
        AvailableAlgoParams.FillClosePriceParams(baseOrder, 0.4, "Neutral", "20180926-06:06:49", True, 100000)
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [closepx]

        # ! [pctvol]
        AvailableAlgoParams.FillPctVolParams(baseOrder, 0.5, "12:00:00 EST", "14:00:00 EST", True, 100000)
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [pctvol]

        # ! [pctvolpx]
        AvailableAlgoParams.FillPriceVariantPctVolParams(baseOrder, 0.1, 0.05, 0.01, 0.2, "12:00:00 EST", "14:00:00 EST", True, 100000)
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [pctvolpx]

        # ! [pctvolsz]
        AvailableAlgoParams.FillSizeVariantPctVolParams(baseOrder, 0.2, 0.4, "12:00:00 EST", "14:00:00 EST", True, 100000)
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [pctvolsz]

        # ! [pctvoltm]
        AvailableAlgoParams.FillTimeVariantPctVolParams(baseOrder, 0.2, 0.4, "12:00:00 EST", "14:00:00 EST", True, 100000)
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), baseOrder)
        # ! [pctvoltm]

        # ! [jeff_vwap_algo]
        AvailableAlgoParams.FillJefferiesVWAPParams(baseOrder, "10:00:00 EST", "16:00:00 EST", 10, 10, "Exclude_Both", 130, 135, 1, 10, "Patience", False, "Midpoint")
        self.placeOrder(self.nextOrderId(), ContractSamples.JefferiesContract(), baseOrder)
        # ! [jeff_vwap_algo]

        # ! [csfb_inline_algo]
        AvailableAlgoParams.FillCSFBInlineParams(baseOrder, "10:00:00 EST", "16:00:00 EST", "Patient", 10, 20, 100, "Default", False, 40, 100, 100, 35)
        self.placeOrder(self.nextOrderId(), ContractSamples.CSFBContract(), baseOrder)
        # ! [csfb_inline_algo]

        # ! [qbalgo_strobe_algo]
        AvailableAlgoParams.FillQBAlgoInLineParams(baseOrder, "10:00:00 EST", "16:00:00 EST", -99, "TWAP", 0.25, True)
        self.placeOrder(self.nextOrderId(), ContractSamples.QBAlgoContract(), baseOrder)
        # ! [qbalgo_strobe_algo]

    @printWhenExecuting
    def financialAdvisorOperations(self):
        # Requesting FA information
        # ! [requestfaaliases]
        self.requestFA(FaDataTypeEnum.ALIASES)
        # ! [requestfaaliases]

        # ! [requestfagroups]
        self.requestFA(FaDataTypeEnum.GROUPS)
        # ! [requestfagroups]

        # ! [requestfaprofiles]
        self.requestFA(FaDataTypeEnum.PROFILES)
        # ! [requestfaprofiles]

        # Replacing FA information - Fill in with the appropriate XML string.
        # ! [replacefaonegroup]
        self.replaceFA(FaDataTypeEnum.GROUPS, FaAllocationSamples.FaOneGroup)
        # ! [replacefaonegroup]

        # ! [replacefatwogroups]
        self.replaceFA(FaDataTypeEnum.GROUPS, FaAllocationSamples.FaTwoGroups)
        # ! [replacefatwogroups]

        # ! [replacefaoneprofile]
        self.replaceFA(FaDataTypeEnum.PROFILES, FaAllocationSamples.FaOneProfile)
        # ! [replacefaoneprofile]

        # ! [replacefatwoprofiles]
        self.replaceFA(FaDataTypeEnum.PROFILES, FaAllocationSamples.FaTwoProfiles)
        # ! [replacefatwoprofiles]

        # ! [reqSoftDollarTiers]
        self.reqSoftDollarTiers(14001)
        # ! [reqSoftDollarTiers]

    @iswrapper
    # ! [receivefa]
    def receiveFA(self, faData: FaDataType, cxml: str):
        super().receiveFA(faData, cxml)
        print("Receiving FA: ", faData)
        open('log/fa.xml', 'w').write(cxml)
    # ! [receivefa]

    @iswrapper
    # ! [softDollarTiers]
    def softDollarTiers(self, reqId: int, tiers: list):
        super().softDollarTiers(reqId, tiers)
        print("SoftDollarTiers. ReqId:", reqId)
        for tier in tiers:
            print("SoftDollarTier.", tier)
    # ! [softDollarTiers]

    @printWhenExecuting
    def miscelaneousOperations(self):
        # Request TWS' current time
        self.reqCurrentTime()
        # Setting TWS logging level
        self.setServerLogLevel(1)

    @printWhenExecuting
    def linkingOperations(self):
        # ! [querydisplaygroups]
        self.queryDisplayGroups(19001)
        # ! [querydisplaygroups]

        # ! [subscribetogroupevents]
        self.subscribeToGroupEvents(19002, 1)
        # ! [subscribetogroupevents]

        # ! [updatedisplaygroup]
        self.updateDisplayGroup(19002, "8314@SMART")
        # ! [updatedisplaygroup]

        # ! [subscribefromgroupevents]
        self.unsubscribeFromGroupEvents(19002)
        # ! [subscribefromgroupevents]

    @iswrapper
    # ! [displaygrouplist]
    def displayGroupList(self, reqId: int, groups: str):
        super().displayGroupList(reqId, groups)
        print("DisplayGroupList. ReqId:", reqId, "Groups", groups)
    # ! [displaygrouplist]

    @iswrapper
    # ! [displaygroupupdated]
    def displayGroupUpdated(self, reqId: int, contractInfo: str):
        super().displayGroupUpdated(reqId, contractInfo)
        print("DisplayGroupUpdated. ReqId:", reqId, "ContractInfo:", contractInfo)
    # ! [displaygroupupdated]

    @printWhenExecuting
    def whatIfOrderOperations(self):
    # ! [whatiflimitorder]
        whatIfOrder = OrderSamples.LimitOrder("SELL", 5, 70)
        whatIfOrder.whatIf = True
        self.placeOrder(self.nextOrderId(), ContractSamples.USStockAtSmart(), whatIfOrder)
    # ! [whatiflimitorder]
        time.sleep(2)

    @printWhenExecuting
    def orderOperations_req(self):
        # Requesting the next valid id
        # ! [reqids]
        # The parameter is always ignored.
        self.reqIds(-1)
        # ! [reqids]

        # Requesting all open orders
        # ! [reqallopenorders]
        self.reqAllOpenOrders()
        # ! [reqallopenorders]

        # Taking over orders to be submitted via TWS
        # ! [reqautoopenorders]
        self.reqAutoOpenOrders(True)
        # ! [reqautoopenorders]

        # Requesting this API client's orders
        # ! [reqopenorders]
        self.reqOpenOrders()
        # ! [reqopenorders]


        # Placing/modifying an order - remember to ALWAYS increment the
        # nextValidId after placing an order so it can be used for the next one!
        # Note if there are multiple clients connected to an account, the
        # order ID must also be greater than all order IDs returned for orders
        # to orderStatus and openOrder to this client.

        # ! [order_submission]
        self.simplePlaceOid = self.nextOrderId()
        self.placeOrder(self.simplePlaceOid, ContractSamples.USStock(),
                        OrderSamples.LimitOrder("SELL", 1, 50))
        # ! [order_submission]

        # ! [faorderoneaccount]
        faOrderOneAccount = OrderSamples.MarketOrder("BUY", 100)
        # Specify the Account Number directly
        faOrderOneAccount.account = "DU119915"
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(), faOrderOneAccount)
        # ! [faorderoneaccount]

        # ! [faordergroupequalquantity]
        faOrderGroupEQ = OrderSamples.LimitOrder("SELL", 200, 2000)
        faOrderGroupEQ.faGroup = "Group_Equal_Quantity"
        faOrderGroupEQ.faMethod = "EqualQuantity"
        self.placeOrder(self.nextOrderId(), ContractSamples.SimpleFuture(), faOrderGroupEQ)
        # ! [faordergroupequalquantity]

        # ! [faordergrouppctchange]
        faOrderGroupPC = OrderSamples.MarketOrder("BUY", 0)
        # You should not specify any order quantity for PctChange allocation method
        faOrderGroupPC.faGroup = "Pct_Change"
        faOrderGroupPC.faMethod = "PctChange"
        faOrderGroupPC.faPercentage = "100"
        self.placeOrder(self.nextOrderId(), ContractSamples.EurGbpFx(), faOrderGroupPC)
        # ! [faordergrouppctchange]

        # ! [faorderprofile]
        faOrderProfile = OrderSamples.LimitOrder("BUY", 200, 100)
        faOrderProfile.faProfile = "Percent_60_40"
        self.placeOrder(self.nextOrderId(), ContractSamples.EuropeanStock(), faOrderProfile)
        # ! [faorderprofile]

        # ! [modelorder]
        modelOrder = OrderSamples.LimitOrder("BUY", 200, 100)
        modelOrder.account = "DF12345"
        modelOrder.modelCode = "Technology" # model for tech stocks first created in TWS
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(), modelOrder)
        # ! [modelorder]

        self.placeOrder(self.nextOrderId(), ContractSamples.OptionAtBOX(),
                        OrderSamples.Block("BUY", 50, 20))
        self.placeOrder(self.nextOrderId(), ContractSamples.OptionAtBOX(),
                         OrderSamples.BoxTop("SELL", 10))
        self.placeOrder(self.nextOrderId(), ContractSamples.FutureComboContract(),
                         OrderSamples.ComboLimitOrder("SELL", 1, 1, False))
        self.placeOrder(self.nextOrderId(), ContractSamples.StockComboContract(),
                          OrderSamples.ComboMarketOrder("BUY", 1, True))
        self.placeOrder(self.nextOrderId(), ContractSamples.OptionComboContract(),
                          OrderSamples.ComboMarketOrder("BUY", 1, False))
        self.placeOrder(self.nextOrderId(), ContractSamples.StockComboContract(),
                          OrderSamples.LimitOrderForComboWithLegPrices("BUY", 1, [10, 5], True))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                         OrderSamples.Discretionary("SELL", 1, 45, 0.5))
        self.placeOrder(self.nextOrderId(), ContractSamples.OptionAtBOX(),
                          OrderSamples.LimitIfTouched("BUY", 1, 30, 34))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.LimitOnClose("SELL", 1, 34))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.LimitOnOpen("BUY", 1, 35))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.MarketIfTouched("BUY", 1, 30))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                         OrderSamples.MarketOnClose("SELL", 1))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.MarketOnOpen("BUY", 1))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.MarketOrder("SELL", 1))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.MarketToLimit("BUY", 1))
        self.placeOrder(self.nextOrderId(), ContractSamples.OptionAtIse(),
                          OrderSamples.MidpointMatch("BUY", 1))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.MarketToLimit("BUY", 1))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.Stop("SELL", 1, 34.4))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.StopLimit("BUY", 1, 35, 33))
        self.placeOrder(self.nextOrderId(), ContractSamples.SimpleFuture(),
                          OrderSamples.StopWithProtection("SELL", 1, 45))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.SweepToFill("BUY", 1, 35))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.TrailingStop("SELL", 1, 0.5, 30))
        self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
                          OrderSamples.TrailingStopLimit("BUY", 1, 2, 5, 50))
        self.placeOrder(self.nextOrderId(), ContractSamples.USOptionContract(),
                         OrderSamples.Volatility("SELL", 1, 5, 2))

        self.bracketSample()

        self.conditionSamples()

        self.hedgeSample()

        # NOTE: the following orders are not supported for Paper Trading
        # self.placeOrder(self.nextOrderId(), ContractSamples.USStock(), OrderSamples.AtAuction("BUY", 100, 30.0))
        # self.placeOrder(self.nextOrderId(), ContractSamples.OptionAtBOX(), OrderSamples.AuctionLimit("SELL", 10, 30.0, 2))
        # self.placeOrder(self.nextOrderId(), ContractSamples.OptionAtBOX(), OrderSamples.AuctionPeggedToStock("BUY", 10, 30, 0.5))
        # self.placeOrder(self.nextOrderId(), ContractSamples.OptionAtBOX(), OrderSamples.AuctionRelative("SELL", 10, 0.6))
        # self.placeOrder(self.nextOrderId(), ContractSamples.SimpleFuture(), OrderSamples.MarketWithProtection("BUY", 1))
        # self.placeOrder(self.nextOrderId(), ContractSamples.USStock(), OrderSamples.PassiveRelative("BUY", 1, 0.5))

        # 208813720 (GOOG)
        # self.placeOrder(self.nextOrderId(), ContractSamples.USStock(),
        #    OrderSamples.PeggedToBenchmark("SELL", 100, 33, True, 0.1, 1, 208813720, "ISLAND", 750, 650, 800))

        # STOP ADJUSTABLE ORDERS
        # Order stpParent = OrderSamples.Stop("SELL", 100, 30)
        # stpParent.OrderId = self.nextOrderId()
        # self.placeOrder(stpParent.OrderId, ContractSamples.EuropeanStock(), stpParent)
        # self.placeOrder(self.nextOrderId(), ContractSamples.EuropeanStock(), OrderSamples.AttachAdjustableToStop(stpParent, 35, 32, 33))
        # self.placeOrder(self.nextOrderId(), ContractSamples.EuropeanStock(), OrderSamples.AttachAdjustableToStopLimit(stpParent, 35, 33, 32, 33))
        # self.placeOrder(self.nextOrderId(), ContractSamples.EuropeanStock(), OrderSamples.AttachAdjustableToTrail(stpParent, 35, 32, 32, 1, 0))

        # Order lmtParent = OrderSamples.LimitOrder("BUY", 100, 30)
        # lmtParent.OrderId = self.nextOrderId()
        # self.placeOrder(lmtParent.OrderId, ContractSamples.EuropeanStock(), lmtParent)
        # Attached TRAIL adjusted can only be attached to LMT parent orders.
        # self.placeOrder(self.nextOrderId(), ContractSamples.EuropeanStock(), OrderSamples.AttachAdjustableToTrailAmount(lmtParent, 34, 32, 33, 0.008))
        self.algoSamples()
        
        self.ocaSample()

        # Request the day's executions
        # ! [reqexecutions]
        self.reqExecutions(10001, ExecutionFilter())
        # ! [reqexecutions]
        
        # Requesting completed orders
        # ! [reqcompletedorders]
        self.reqCompletedOrders(False)
        # ! [reqcompletedorders]
        

    def orderOperations_cancel(self):
        if self.simplePlaceOid is not None:
            # ! [cancelorder]
            self.cancelOrder(self.simplePlaceOid)
            # ! [cancelorder]
            
        # Cancel all orders for all accounts
        # ! [reqglobalcancel]
        self.reqGlobalCancel()
        # ! [reqglobalcancel]

    def rerouteCFDOperations(self):
        # ! [reqmktdatacfd]
        self.reqMktData(16001, ContractSamples.USStockCFD(), "", False, False, [])
        self.reqMktData(16002, ContractSamples.EuropeanStockCFD(), "", False, False, []);
        self.reqMktData(16003, ContractSamples.CashCFD(), "", False, False, []);
        # ! [reqmktdatacfd]

        # ! [reqmktdepthcfd]
        self.reqMktDepth(16004, ContractSamples.USStockCFD(), 10, False, []);
        self.reqMktDepth(16005, ContractSamples.EuropeanStockCFD(), 10, False, []);
        self.reqMktDepth(16006, ContractSamples.CashCFD(), 10, False, []);
        # ! [reqmktdepthcfd]

    def marketRuleOperations(self):
        self.reqContractDetails(17001, ContractSamples.USStock())
        self.reqContractDetails(17002, ContractSamples.Bond())

        # ! [reqmarketrule]
        self.reqMarketRule(26)
        self.reqMarketRule(239)
        # ! [reqmarketrule]

    @iswrapper
    # ! [execdetails]
    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        super().execDetails(reqId, contract, execution)
        print("ExecDetails. ReqId:", reqId, "Symbol:", contract.symbol, "SecType:", contract.secType, "Currency:", contract.currency, execution)
    # ! [execdetails]

    @iswrapper
    # ! [execdetailsend]
    def execDetailsEnd(self, reqId: int):
        super().execDetailsEnd(reqId)
        print("ExecDetailsEnd. ReqId:", reqId)
    # ! [execdetailsend]

    @iswrapper
    # ! [commissionreport]
    def commissionReport(self, commissionReport: CommissionReport):
        super().commissionReport(commissionReport)
        print("CommissionReport.", commissionReport)
    # ! [commissionreport]

    @iswrapper
    # ! [currenttime]
    def currentTime(self, time:int):
        super().currentTime(time)
        print("CurrentTime:", datetime.datetime.fromtimestamp(time).strftime("%Y%m%d %H:%M:%S"))
    # ! [currenttime]

    @iswrapper
    # ! [completedorder]
    def completedOrder(self, contract: Contract, order: Order,
                  orderState: OrderState):
        super().completedOrder(contract, order, orderState)
        print("CompletedOrder. PermId:", order.permId, "ParentPermId:", utils.longToStr(order.parentPermId), "Account:", order.account, 
              "Symbol:", contract.symbol, "SecType:", contract.secType, "Exchange:", contract.exchange, 
              "Action:", order.action, "OrderType:", order.orderType, "TotalQty:", order.totalQuantity, 
              "CashQty:", order.cashQty, "FilledQty:", order.filledQuantity, 
              "LmtPrice:", order.lmtPrice, "AuxPrice:", order.auxPrice, "Status:", orderState.status,
              "Completed time:", orderState.completedTime, "Completed Status:" + orderState.completedStatus)
    # ! [completedorder]

    @iswrapper
    # ! [completedordersend]
    def completedOrdersEnd(self):
        super().completedOrdersEnd()
        print("CompletedOrdersEnd")
    # ! [completedordersend]

def main():
    SetupLogger()
    logging.debug("now is %s", datetime.datetime.now())
    logging.getLogger().setLevel(logging.ERROR)

    cmdLineParser = argparse.ArgumentParser("api tests")
    # cmdLineParser.add_option("-c", action="store_True", dest="use_cache", default = False, help = "use the cache")
    # cmdLineParser.add_option("-f", action="store", type="string", dest="file", default="", help="the input file")
    cmdLineParser.add_argument("-p", "--port", action="store", type=int,
                               dest="port", default=7497, help="The TCP port to use")
    cmdLineParser.add_argument("-C", "--global-cancel", action="store_true",
                               dest="global_cancel", default=False,
                               help="whether to trigger a globalCancel req")
    args = cmdLineParser.parse_args()
    print("Using args", args)
    logging.debug("Using args %s", args)
    # print(args)


    # enable logging when member vars are assigned
    from ibapi import utils
    Order.__setattr__ = utils.setattr_log
    Contract.__setattr__ = utils.setattr_log
    DeltaNeutralContract.__setattr__ = utils.setattr_log
    TagValue.__setattr__ = utils.setattr_log
    TimeCondition.__setattr__ = utils.setattr_log
    ExecutionCondition.__setattr__ = utils.setattr_log
    MarginCondition.__setattr__ = utils.setattr_log
    PriceCondition.__setattr__ = utils.setattr_log
    PercentChangeCondition.__setattr__ = utils.setattr_log
    VolumeCondition.__setattr__ = utils.setattr_log

    # from inspect import signature as sig
    # import code code.interact(local=dict(globals(), **locals()))
    # sys.exit(1)

    # tc = TestClient(None)
    # tc.reqMktData(1101, ContractSamples.USStockAtSmart(), "", False, None)
    # print(tc.reqId2nReq)
    # sys.exit(1)

    try:
        app = TestApp()
        if args.global_cancel:
            app.globalCancelOnly = True
        # ! [connect]
        app.connect("127.0.0.1", args.port, clientId=0)
        # ! [connect]
        print("serverVersion:%s connectionTime:%s" % (app.serverVersion(),
                                                      app.twsConnectionTime()))

        # ! [clientrun]
        app.run()
        # ! [clientrun]
    except:
        raise
    finally:
        app.dumpTestCoverageSituation()
        app.dumpReqAnsErrSituation()


if __name__ == "__main__":
    main()
