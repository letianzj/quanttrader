#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pytest

from quanttrading2.util import read_ohlcv_csv
from quanttrading2.strategy import StrategyBase
from quanttrading2 import BacktestEngine


class BuyAndHoldStrategy(StrategyBase):
    """
    buy on the first tick then hold to the end
    """

    def __init__(self):
        super(BuyAndHoldStrategy, self).__init__()
        self.invested = False

    def on_bar(self, event):
        print(event.bar_start_time)
        symbol = self.symbols[0]
        if event.full_symbol == symbol:
            if not self.invested:
                target_size = int(self.cash / event.close_price)
                self.adjust_position(symbol, size_from=0, size_to=target_size)
                self.invested = True

class TestBuyHold:
    def test_buyhold(self):
        df = read_ohlcv_csv('test_data/TEST.csv')
        strategy = BuyAndHoldStrategy()

        backtest_engine = BacktestEngine()
        backtest_engine.add_data('TTT', df)
        backtest_engine.set_strategy(strategy)
        results, results_dd, monthly_ret_table, ann_ret_df = backtest_engine.run()
        if results is None:
            print('Empty Strategy')
        else:
            print(results)
            print(results_dd)
            print(monthly_ret_table)
            print(ann_ret_df)