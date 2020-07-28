#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from .position import Position


class PortfolioManager(object):
    def __init__(self, initial_cash, fvp=None):
        """
        PortfolioManager is one component of PortfolioManager
        """
        self.cash = initial_cash
        # current total value after market to market, before trades from strategy.
        # After-trades calculated in performanace manager
        self.current_total_capital = initial_cash
        self.contracts = {}            # symbol ==> contract
        self.positions = {}
        self._df_fvp = fvp

    def reset(self):
        self.contracts.clear()
        self.positions.clear()

    def on_contract(self, contract):
        if contract.full_symbol not in self.contracts:
            self.contracts[contract.full_symbol] = contract
            print("Contract %s information received. " % contract.full_symbol)
        else:
            print("Contract %s information already exists " % contract.full_symbol)

    def on_position(self, pos_event):
        """get initial position"""
        # TODO, current_total_capital accounts for initial positions
        pos = pos_event.to_position()

        if pos.full_symbol not in self.positions:
            self.positions[pos.full_symbol] = pos
        else:

            print("Symbol %s already exists in the portfolio " % pos.full_symbol)

    def on_fill(self, fill_event):
        """
        This works only on stocks.
        TODO: consider margin
        """
        # sell will get cash back
        m = 1
        if self._df_fvp is not None:
            try:
                sym = fill_event.full_symbol
                if '|' in sym:
                    ss = sym.split('|')
                    match = re.match(r"([a-z ]+)([0-9]+)?", ss[0], re.I)
                    sym = match.groups()[0]

                m = self._df_fvp.loc[sym, 'FVP']
            except:
                m = 1
        self.cash -= (fill_event.fill_size * fill_event.fill_price)*m + fill_event.commission
        self.current_total_capital -= fill_event.commission                   # commission is a cost

        if fill_event.full_symbol in self.positions:      # adjust existing position
            self.positions[fill_event.full_symbol].on_fill(fill_event, m)
        else:
            self.positions[fill_event.full_symbol] = fill_event.to_position()

    def mark_to_market(self, current_time, symbol, last_price, data_board):
        #for sym, pos in self.positions.items():
        m = 1
        sym = symbol
        if self._df_fvp is not None:
            try:
                sym = symbol
                if '|' in sym:
                    ss = sym.split('|')
                    match = re.match(r"([a-z ]+)([0-9]+)?", ss[0], re.I)
                    sym = match.groups()[0]

                m = self._df_fvp.loc[sym, 'FVP']
            except:
                m = 1
        if symbol in self.positions:
            # TODO: for place holder case, nothing updated
            self.positions[symbol].mark_to_market(last_price, m)
            # data board not updated yet
            self.current_total_capital += self.positions[symbol].size * (last_price - data_board.get_last_price(sym)) * m
