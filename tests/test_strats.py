#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pytest

from quanttrader.util import read_ohlcv_csv
from quanttrader.strategy import StrategyBase
from quanttrader import BacktestEngine


class BuyAndHoldStrategy(StrategyBase):
    """
    buy on the first tick then hold to the end
    """

    def __init__(self):
        super(BuyAndHoldStrategy, self).__init__()
        self.invested = False

    def on_tick(self, event):
        print(event.timestamp)
        symbol = self.symbols[0]
        if not self.invested:
            df_hist = self._data_board.get_hist_price(symbol, event.timestamp)
            close = df_hist.iloc[-1].Close
            target_size = int(self.cash / close)
            self.adjust_position(symbol, size_from=0, size_to=target_size)
            self.invested = True

class TestBuyHold:
    def test_buyhold(self):
        df = read_ohlcv_csv('test_data/TEST.csv')
        init_capital = 100_000.0
        strategy = BuyAndHoldStrategy()
        strategy.set_capital(init_capital)
        strategy.set_symbols(['TTT'])
        strategy.set_params(None)

        backtest_engine = BacktestEngine()
        backtest_engine.set_capital(init_capital)        # capital or portfolio >= capital for one strategy
        backtest_engine.add_data('TTT', df)
        backtest_engine.set_strategy(strategy)
        equity, df_positions, df_trades = backtest_engine.run()
        if df_trades is None:
            print('Empty Strategy')
        else:
            print(equity)