#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from ..order.order_status import OrderStatus

_logger = logging.getLogger(__name__)


class StrategyManager(object):
    def __init__(self, config, broker, order_manager, position_manager, data_board, multiplier_dict):
        """
        current design: oversees all strategies/traders, check with risk managers before send out orders
        let strategy manager to track strategy position for each strategy, with the help from order manager

        :param config:
        :param strat_dict:     strat name ==> stract
        :param broker:
        :param order_manager:  support OMS
        :param position_manager:    let position manager help track total positions
        :param data_board:
        """
        self._config = config
        self._broker = broker
        self._order_manager = order_manager
        self._position_manager = position_manager
        self._data_board = data_board
        self._strategy_dict = {}            # sid ==> strategy
        self._multiplier_dict = multiplier_dict          # symbol ==> multiplier
        self._tick_strategy_dict = {}  # sym -> list of strategy
        self._sid_oid_dict = {0: [], -1: []}    # sid ==> oid list; 0: manual; -1: unknown source

    def load_strategy(self, strat_dict):
        for k, v in strat_dict.items():
            self._strategy_dict[v.id ] = v
            self._sid_oid_dict[v.id] = []         # record its orders
            v.on_init(self, self._data_board, self._multiplier_dict)
            for sym in v.symbols:
                ss = sym.split(' ')
                if ss[-1].isdigit():  # multiplier
                    sym = ' '.join(ss[:-1])
                    self._multiplier_dict[sym] = int(ss[-1])

                # now sym doesn't have multiplier
                if sym in self._tick_strategy_dict:
                    self._tick_strategy_dict[sym].append(v.id)
                else:
                    self._tick_strategy_dict[sym] = [v.id]
                if sym in self._broker.market_data_subscription_reverse_dict.keys():
                    continue
                else:
                    print(f'add {sym}')
                    self._broker.market_data_subscription_reverse_dict[sym] = -1

    def start_strategy(self, sid):
        self._strategy_dict[sid].on_start()

    def stop_strategy(self, sid):
        self._strategy_dict[sid].on_stop()

    def pause_strategy(self, sid):
        self._strategy_dict[sid].active = False

    def start_all(self):
        for k, v in self._strategy_dict.items():
            v.active = True

    def stop_all(self):
        for k, v in self._strategy_dict.items():
            v.active = False

    def place_order(self, o):
        # currently it puts order directly with broker; e.g. by simplying calling ib.placeOrder method
        # Because order is placed directly; all subsequent on_order messages are order status updates
        # TODO, use an outbound queue to send orders
        # 1. check with risk manager

        # 2. if green light
        # 2.a record
        oid = self._broker.orderid
        self._broker.orderid += 1
        o.order_id = oid
        o.order_status = OrderStatus.NEWBORN
        self._sid_oid_dict[o.source].append(oid)
        self._order_manager.on_order_status(o)
        self._strategy_dict[o.source]._order_manager.on_order_status(o)

        # 2.b place order
        self._broker.place_order(o)

    def flat_strategy(self, sid):
        """
        Assume each strategy track its own positions
        """
        pass

    def cancel_straetgy(self, sid):
        if sid not in self._sid_oid_dict.keys():
            _logger.error(f'Flat strategy can not locate strategy id {sid}')
        else:
            for oid in self._sid_oid_dict[sid]:
                if self._order_manager.order_dict[oid]:
                    pass

    def flat_all(self):
        """
        flat all according to position_manager
        :return:
        """
        for k, v in self._sid_oid_dict.items():
            pass

    def cancel_all(self):
        pass

    def on_tick(self, k):
        print(k.full_symbol, k.price, k.size)
        if k.full_symbol in self._tick_strategy_dict:
            # foreach strategy that subscribes to this tick
            s_list = self._tick_strategy_dict[k.full_symbol]
            for sid in s_list:
                if self._strategy_dict[sid].active:
                    self._strategy_dict[sid].on_tick(k)

    def on_position(self, pos):
        pass

    def on_order_status(self, order_event):
        sid = order_event.source
        if sid in self._strategy_dict.keys():
            self._strategy_dict[sid].on_order_status(order_event)
        else:
            _logger.info('strategy manager doesnt hold the oid, possibly from outside of the system')

    def on_cancel(self, oid):
        pass

    def on_fill(self, fill):
        """
        assign fill ordering to order id ==> strategy id
        """
        pass