#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


class Position(object):
    def __init__(self, full_symbol, average_price, size, realized_pnl=0):
        """
        Position includes zero/closed security
        """
        ## TODO: add cumulative_commission, long_trades, short_trades, round_trip etc
        self.full_symbol = full_symbol
        # average price includes commission
        self.average_price = average_price
        self.size = size
        self.realized_pnl = 0
        self.unrealized_pnl = 0
        self.account = ''

    def get_current_pnl(self):
        return self.realized_pnl, self.unrealized_pnl

    def mark_to_market(self, last_price, multiplier):
        """
        given new market price, update the position
        """
        # if long or size > 0, pnl is positive if last_price > average_price
        # else if short or size < 0, pnl is positive if last_price < average_price
        self.unrealized_pnl = (last_price - self.average_price) * self.size * multiplier

    def on_fill(self, fill_event, multiplier):
        """
        adjust average_price and size according to new fill/trade/transaction
        """
        if self.full_symbol != fill_event.full_symbol:
            _logger.error(
                "Position symbol %s and fill event symbol %s do not match. "
                % (self.full_symbol, fill_event.full_symbol)
            )

        if self.size > 0:        # existing long
            if fill_event.fill_size > 0:        # long more
                self.average_price = (self.average_price * self.size + fill_event.fill_price * fill_event.fill_size
                                      + fill_event.commission / multiplier) \
                                     // (self.size + fill_event.fill_size)
            else:        # flat long
                #_logger.info(f'flat long realized_pnl {self.realized_pnl}, avg {self.average_price}, fill {fill_event.fill_price}, {fill_event.fill_size}, {multiplier}, {fill_event.commission}')
                if abs(self.size) >= abs(fill_event.fill_size):   # stay long
                    self.realized_pnl += (self.average_price - fill_event.fill_price) * fill_event.fill_size \
                                         * multiplier - fill_event.commission
                else:   # flip to short
                    self.realized_pnl += (fill_event.fill_price - self.average_price) * self.size \
                                         * multiplier - fill_event.commission
                    self.average_price = fill_event.fill_price
        elif self.size < 0:        # existing short
            if fill_event.fill_size < 0:         # short more
                self.average_price = (self.average_price * self.size + fill_event.fill_price * fill_event.fill_size
                                      + fill_event.commission / multiplier) \
                                     // (self.size + fill_event.fill_size)
            else:          # flat short
                #_logger.info(f'flat short realized_pnl {self.realized_pnl}, avg {self.average_price}, fill {fill_event.fill_price}, {fill_event.fill_size}, {multiplier}, {fill_event.commission}')
                if abs(self.size) >= abs(fill_event.fill_size):  # stay short
                    self.realized_pnl += (self.average_price - fill_event.fill_price) * fill_event.fill_size \
                                         * multiplier - fill_event.commission
                else:   # flip to long
                    self.realized_pnl += (fill_event.fill_price - self.average_price) * self.size \
                                         * multiplier - fill_event.commission
                    self.average_price = fill_event.fill_price
        else:      # no position
            self.average_price = fill_event.fill_price + fill_event.commission / multiplier /fill_event.fill_size

        self.size += fill_event.fill_size