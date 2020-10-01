#!/usr/bin/env python
# -*- coding: utf-8 -*-
from quanttrader.strategy.strategy_base import StrategyBase
from quanttrader.data.tick_event import TickType
from quanttrader.order.order_event import OrderEvent
from quanttrader.order.order_status import OrderStatus
from quanttrader.order.order_type import OrderType
import numpy as np
import logging

_logger = logging.getLogger('qtlive')


class MovingAverageCrossStrategy(StrategyBase):
    """
    EMA
    """
    def __init__(self):
        super(MovingAverageCrossStrategy, self).__init__()
        self.last_bid = -1
        self.last_ask = -1
        self.last_trade = -1
        self.ema = -1
        self.last_time = -1
        self.G = 20
        _logger.info('MovingAverageCrossStrategy initiated')

    def on_fill(self, fill_event):
        super().on_fill(fill_event)

        _logger.info(f'MovingAverageCrossStrategy order filled. oid {fill_event.order_id}, filled price {fill_event.fill_price} size {fill_event.fill_size}')

    def on_tick(self, k):
        super().on_tick(k)     # extra mtm calc

        symbol = self.symbols[0]
        print(k)
        if k.tick_type == TickType.BID:
            self.last_bid = k.bid_price_L1
        if k.tick_type == TickType.ASK:
            self.last_ask = k.ask_price_L1
        elif k.tick_type == TickType.TRADE:     # only place on trade
            self.last_trade = k.price
            if self.ema == -1:          # intialize ema; alternative is to use yesterday close in __init__
                self.ema = self.last_trade
                self.last_time = k.timestamp
            else:
                time_elapsed = (k.timestamp - self.last_time).total_seconds()
                alpha = 1- np.exp(-time_elapsed/self.G)
                self.ema += alpha * (self.last_trade - self.ema)
                self.last_time = k.timestamp

            print(f'MovingAverageCrossStrategy: {self.last_trade} {self.ema}')
            if k.price > self.ema:    # (flip to) long
                # check standing orders; if it is also a buy order, do nothing
                # elif it is a sell order; cancel the order
                # TODO it's possible that order fails to be placed due to connection issue; and order status is kept as acknowledged
                # TODO it's possible that IB side failed to recoginize the order:  Error. id: 14071, Code: 200, Msg: No security definition has been found for the request (valid security, later another order accepted)
                # TODO it's also possible to cancel a partially filled order
                # TODO: also see cancel placed on 10:07:21.771; openorder pending cancel on 10:07:21.918; execDetails filled on 10:07:21.958; orderstatus filled on 10:07:21.992; error message cancel rejected on 10:07:22.112
                standing_oids = self._order_manager.retrieve_standing_orders()
                if len(standing_oids) > 0:
                    _logger.info(f"MovingAverageCrossStrategy standing orders: {','.join(map(str, standing_oids))}")
                # it is possible having more than one standing orders:
                #       one to be cancelled
                #       the other to be filled
                for oid in standing_oids:
                    if self._order_manager.retrieve_order(oid).order_size > 0:
                        _logger.info(f'MovingAverageCrossStrategy long order already in place. ema {self.ema}, last {k.price}, bid {self.last_bid}')
                        return
                    elif self._order_manager.retrieve_order(oid).order_size < 0:
                        _logger.info(f'MovingAverageCrossStrategy cancel existing short. ema {self.ema}, last {k.price}, bid {self.last_bid}')
                        self.cancel_order(oid)
                if self.last_bid < 0:     # bid not initiated yet
                    return

                current_pos = int(self._position_manager.get_position_size(symbol))
                if current_pos not in [-1, 0]:
                    # _logger.error(f'MovingAverageCrossStrategy current size exceeds. {current_pos}')
                    return
                o = OrderEvent()
                o.full_symbol = symbol
                o.order_type = OrderType.LIMIT
                o.limit_price = self.last_bid
                o.order_size = 1 - current_pos
                _logger.info(f'MovingAverageCrossStrategy long order placed, current size {current_pos}, order size {o.order_size}. ema {self.ema}, last {k.price}, bid {self.last_bid}')
                self.place_order(o)
            else:   # (flip to) short
                # check standing orders; if it is also a short order, do nothing
                # elif it is a long order; cancel the order
                standing_oids = self._order_manager.retrieve_standing_orders()
                if len(standing_oids) > 0:
                    _logger.info(f"MovingAverageCrossStrategy standing orders: {','.join(map(str, standing_oids))}")
                # it is possible having more than one standing orders:
                #       one to be cancelled
                #       the other to be filled
                for oid in standing_oids:
                    if self._order_manager.retrieve_order(oid).order_size < 0:
                        _logger.info(f'MovingAverageCrossStrategy short order already in place. ema {self.ema}, last {k.price}, bid {self.last_bid}')
                        return
                    elif self._order_manager.retrieve_order(oid).order_size > 0:
                        _logger.info(f'MovingAverageCrossStrategy cancel existing long. ema {self.ema}, last {k.price}, bid {self.last_bid}')
                        self.cancel_order(oid)
                if self.last_ask < 0:     # ask not initiated yet
                    return

                current_pos = int(self._position_manager.get_position_size(symbol))
                if current_pos not in [0, 1]:
                    # _logger.error(f'MovingAverageCrossStrategy current size exceeds. {current_pos}')
                    return
                o = OrderEvent()
                o.full_symbol = symbol
                o.order_type = OrderType.LIMIT
                o.limit_price = self.last_ask
                o.order_size = -1 - current_pos
                _logger.info(f'MovingAverageCrossStrategy short order placed, current size {current_pos}, order size {o.order_size}, ema {self.ema}, last {k.price}, ask {self.last_ask}')
                self.place_order(o)
