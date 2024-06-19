#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from ..brokerage.brokerage_base import BrokerageBase
from ..data.data_board import DataBoard
from ..data.tick_event import TickEvent
from ..order.fill_event import FillEvent
from ..order.order_event import OrderEvent
from ..order.order_manager import OrderManager
from ..order.order_status import OrderStatus
from ..position.position_event import PositionEvent
from ..position.position_manager import PositionManager
from ..risk.risk_manager_base import RiskManagerBase
from ..strategy.strategy_base import StrategyBase

_logger = logging.getLogger(__name__)


__all__ = ["StrategyManager"]


class StrategyManager(object):
    def __init__(
        self,
        config: dict[str, Any],
        broker: BrokerageBase,
        order_manager: OrderManager,
        position_manager: PositionManager,
        risk_manager: RiskManagerBase,
        data_board: DataBoard,
        instrument_meta: dict[str, dict[str, Any]],
    ) -> None:
        """
        current design: oversees all strategies/traders, check with risk managers before send out orders
        let strategy manager to track strategy position for each strategy, with the help from order manager

        :param config:
        :param strat_dict:     strat name ==> stract
        :param broker: to place order directly without message queue
        :param order_manager:  this order manager support total/global orders
        :param position_manager:    this position manager help track total/global positions
        :param risk_manager: chck order witth
        :param data_board: for strategy
        """
        self.config: dict[str, Any] = config
        self._broker: BrokerageBase = broker
        self._order_manager: OrderManager = order_manager
        self._position_manager: PositionManager = position_manager
        self._risk_manager: RiskManagerBase = risk_manager
        self._data_board: DataBoard = data_board
        self.strategy_dict: dict[int, StrategyBase] = {}  # sid ==> strategy
        self._instrument_meta: dict[str, dict[str, Any]] = (
            instrument_meta  # symbol ==> instrument_meta
        )
        self._tickstrategy_dict: dict[str, list[int]] = (
            {}
        )  # sym -> list of strategy ids
        self._sid_oid_dict: dict[int, list[int]] = {
            0: [],
            -1: [],
        }  # sid ==> oid list; 0: manual; -1: unknown source

    def load_strategy(self, strat_dict: dict[str, StrategyBase]) -> None:
        sid = 1  # 0 is mannual discretionary trade, or not found
        # similar to backtest; strategy sets capital, params, and symbols
        for k, v in strat_dict.items():
            v.id = sid
            sid += 1
            v.name = k
            if v.name in self.config["strategy"].keys():
                v.active = self.config["strategy"][v.name]["active"]
                v.set_capital(self.config["strategy"][v.name]["capital"])  # float
                v.set_params(self.config["strategy"][v.name]["params"])  # dict
                v.set_symbols(self.config["strategy"][v.name]["symbols"])  # list

                # yaml converts to seconds
                if "order_start_time" in self.config["strategy"][v.name].keys():
                    if isinstance(
                        self.config["strategy"][v.name]["order_start_time"],
                        int,
                    ):
                        self.config["strategy"][v.name]["order_start_time"] = str(
                            timedelta(
                                seconds=self.config["strategy"][v.name][
                                    "order_start_time"
                                ]
                            )
                        )
                if "order_end_time" in self.config["strategy"][v.name].keys():
                    if isinstance(
                        self.config["strategy"][v.name]["order_end_time"], int
                    ):
                        self.config["strategy"][v.name]["order_end_time"] = str(
                            timedelta(
                                seconds=self.config["strategy"][v.name][
                                    "order_end_time"
                                ]
                            )
                        )

            self.strategy_dict[v.id] = v
            self._sid_oid_dict[v.id] = []  # record its orders
            for sym in v.symbols:
                if sym not in self._instrument_meta.keys():
                    # find first digit position
                    ss = sym.split(" ")
                    for i, c in enumerate(ss[0]):
                        if c.isdigit():
                            break
                    if i < len(ss[0]):
                        sym_root = ss[0][: i - 1]
                        if sym_root in self._instrument_meta.keys():
                            self._instrument_meta[sym] = self._instrument_meta[
                                sym_root
                            ]  # add for quick access

                if sym in self._tickstrategy_dict:
                    self._tickstrategy_dict[sym].append(v.id)
                else:
                    self._tickstrategy_dict[sym] = [v.id]
                if sym in self._broker.market_data_subscription_reverse_dict.keys():
                    continue
                else:
                    _logger.info(f"add {sym}")
                    self._broker.market_data_subscription_reverse_dict[sym] = -1

            v.on_init(self, self._data_board, self._instrument_meta)

    def start_strategy(self, sid: int) -> None:
        self.strategy_dict[sid].active = True

    def stop_strategy(self, sid: int) -> None:
        self.strategy_dict[sid].active = False

    def pause_strategy(self, sid: int) -> None:
        self.strategy_dict[sid].active = False

    def start_all(self) -> None:
        for k, v in self.strategy_dict.items():
            v.active = True

    def stop_all(self) -> None:
        for k, v in self.strategy_dict.items():
            v.active = False

    def place_order(self, o: OrderEvent, check_risk: bool = True) -> None:
        # currently it puts order directly with broker; e.g. by simplying calling ib.placeOrder method
        # Because order is placed directly; all subsequent on_order messages are order status updates
        # TODO, use an outbound queue to send orders
        # 1. check with risk manager
        order_check = True
        if check_risk:
            order_check = self._risk_manager.order_in_compliance(o, self)

        # 2. if green light
        if not order_check:
            return

        # 2.a record
        oid = self._broker.orderid
        self._broker.orderid += 1
        o.order_id = oid
        o.order_status = OrderStatus.NEWBORN
        self._sid_oid_dict[o.source].append(oid)
        # feedback newborn status
        self._order_manager.on_order_status(o)
        if (
            o.source in self.strategy_dict.keys()
        ):  # in case it is not placed by strategy
            self.strategy_dict[o.source].on_order_status(o)

        # 2.b place order
        self._broker.place_order(o)

    def cancel_order(self, oid: int) -> None:
        self._order_manager.on_cancel(oid)
        # self.strategy_dict[sid].on_cancel(oid)  # This is moved to strategy_base
        self._broker.cancel_order(oid)

    def cancel_strategy(self, sid: int) -> None:
        """
        call strategy cancel to take care of strategy order_manager
        """
        if sid not in self.strategy_dict.keys():
            _logger.error(f"Cancel strategy can not locate strategy id {sid}")
        else:
            self.strategy_dict[sid].cancel_all()

    def cancel_all(self) -> None:
        for sid, s in self.strategy_dict.items():
            s.cancel_all()

    def flat_strategy(self, sid: int) -> None:
        """
        flat with MARKET order (default)
        Assume each strategy track its own positions
        TODO: should turn off strategy?
        """
        if sid not in self.strategy_dict.keys():
            _logger.error(f"Flat strategy can not locate strategy id {sid}")

        for sym, pos in self.strategy_dict[sid]._position_manager.positions.items():
            if pos.size != 0:
                o = OrderEvent()
                o.full_symbol = sym
                o.order_size = -pos.size
                o.source = 0  # mannual flat
                o.create_time = pd.Timestamp.now()
                self.place_order(
                    o, check_risk=False
                )  # flat strategy doesnot cehck risk

    def flat_all(self) -> None:
        """
        flat all according to position_manager
        TODO: should turn off all strategies?
        :return:
        """
        for sym, pos in self._position_manager.positions.items():
            if pos.size != 0:
                o = OrderEvent()
                o.full_symbol = sym
                o.order_size = -pos.size
                o.source = 0
                o.create_time = pd.Timestamp.now()
                self.place_order(
                    o, check_risk=False
                )  # flat strategy doesnot cehck risk

    def on_tick(self, k: TickEvent) -> None:
        # print(k.full_symbol, k.price, k.size)
        if k.full_symbol in self._tickstrategy_dict.keys():
            # foreach strategy that subscribes to this tick
            s_list = self._tickstrategy_dict[k.full_symbol]
            for sid in s_list:
                if self.strategy_dict[sid].active:
                    self.strategy_dict[sid].on_tick(k)

    def on_position(self, pos: PositionEvent) -> None:
        """
        get initial position
        read from config file instead
        :param pos:
        :return:
        """
        pass

    def on_order_status(self, order_event: OrderEvent) -> None:
        """
        TODO: check if source is working
        :param order_event:
        :return:
        """
        sid = order_event.source
        if sid in self.strategy_dict.keys():
            self.strategy_dict[sid].on_order_status(order_event)
        else:
            _logger.info(
                f"strategy manager doesnt hold the oid {order_event.order_id} to set status {order_event.order_status}, possibly from outside of the system"
            )

    def on_cancel(self, order_event: OrderEvent) -> None:
        """
        TODO no need for this
        """
        sid = order_event.source
        if sid in self.strategy_dict.keys():
            self.strategy_dict[sid].on_order_status(order_event)
        else:
            _logger.info(
                f"strategy manager doesnt hold the oid {order_event.order_id} to cancel, possibly from outside of the system"
            )

    def on_fill(self, fill_event: FillEvent) -> None:
        """
        assign fill ordering to order id ==> strategy id
        TODO: check fill_event source; if not, fix it or use fill_event.order_id
        """
        sid = fill_event.source
        if sid in self.strategy_dict.keys():
            self.strategy_dict[sid].on_fill(fill_event)
        else:
            _logger.info(
                f"strategy manager doesnt hold the oid {fill_event.order_id} to fill, possibly from outside of the system"
            )
