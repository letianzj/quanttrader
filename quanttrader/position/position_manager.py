#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from ..position import Position
import logging

_logger = logging.getLogger(__name__)


class PositionManager(object):
    def __init__(self, name):
        """
        """
        self.name = name
        self.initial_capital = 0
        self.cash = 0
        # current total value after market to market, before trades from strategy.
        # After-trades calculated in performanace manager
        self.current_total_capital = 0
        self.contracts = {}            # symbol ==> contract
        self.positions = {}        # symbol ==> positions
        self.instrument_meta = {}        # sym ==> instrument_meta

    def set_instrument_meta(self, instrument_meta_dict):
        self.instrument_meta = instrument_meta_dict

    def set_capital(self, initial_capital):
        self.initial_capital = initial_capital

    def reset(self):
        self.cash = self.initial_capital
        self.current_total_capital = self.initial_capital
        self.contracts.clear()
        self.positions.clear()

    def get_holdings_count(self):
        n = 0
        for s, p in self.positions.items():
            if p.size != 0:
                n+=1
        return n

    def get_position_size(self, symbol):
        if symbol in self.positions.keys():
            return self.positions[symbol].size
        else:
            return 0

    def get_cash(self):
        return self.cash

    def get_total_pnl(self):
        total_pnl = 0
        for s, pos in self.positions.items():
            cp, op = pos.get_current_pnl()
            total_pnl = total_pnl + cp + op
        return total_pnl


    def on_contract(self, contract):
        if contract.full_symbol not in self.contracts:
            self.contracts[contract.full_symbol] = contract
            _logger.info(f"{self.name} Contract {contract.full_symbol} information received. ")
        else:
            _logger.info(f"{self.name} Contract {contract.full_symbol} information already exists ")

    def on_position(self, pos_event):
        """respond to updatePortfolio; global position_manager only"""
        pos = pos_event.to_position()
        self.positions[pos.full_symbol] = pos

    def on_fill(self, fill_event):
        """
        This works only on stocks.
        TODO: consider margin
        """
        # sell will get cash back
        if fill_event.full_symbol in self.instrument_meta.keys():
            multiplier = self.instrument_meta[fill_event.full_symbol]['Multiplier']
        else:
            multiplier = 1

        self.cash -= (fill_event.fill_size * fill_event.fill_price)*multiplier + fill_event.commission
        self.current_total_capital -= fill_event.commission                   # commission is a cost

        if fill_event.full_symbol in self.positions:      # adjust existing position
            self.positions[fill_event.full_symbol].on_fill(fill_event, multiplier, self.name)
        else:
            self.positions[fill_event.full_symbol] = fill_event.to_position(multiplier)

    def mark_to_market(self, time_stamp, symbol, last_price, data_board):
        """
        from previous timestamp to current timestamp. Pnl from holdings
        """
        if symbol == 'PLACEHOLDER':        # backtest placeholder, update all
            for sym, pos in self.positions.items():
                if sym in self.instrument_meta.keys():
                    multiplier = self.instrument_meta[sym]['Multiplier']
                else:
                    multiplier = 1
                real_last_price = data_board.get_hist_price(sym, time_stamp).Close.iloc[-1]         # not PLACEHOLDER
                pos.mark_to_market(real_last_price, multiplier)
                # data board not updated yet; get_last_time return previous time_stamp
                self.current_total_capital += self.positions[sym].size * (real_last_price - data_board.get_last_price(sym)) * multiplier
        elif symbol in self.positions:
            # this is a quick way based on one symbol; actual pnl should sum up across positions
            if symbol in self.instrument_meta.keys():
                multiplier = self.instrument_meta[symbol]['Multiplier']
            else:
                multiplier = 1

            self.positions[symbol].mark_to_market(last_price, multiplier)
            prev_price = data_board.get_last_price(symbol)
            if prev_price is not None:    # in case data board hasn't been updated/empty
                self.current_total_capital += self.positions[symbol].size * (last_price - prev_price) * multiplier

