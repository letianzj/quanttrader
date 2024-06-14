#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from datetime import datetime

import pytz

from quanttrader.backtest_engine import BacktestEngine
from quanttrader.strategy.strategy_base import StrategyBase
from quanttrader.util.util_func import read_ohlcv_csv


class BuyAndHoldStrategy(StrategyBase):
    """
    buy on the first tick then hold to the end
    """

    def __init__(self) -> None:
        super(BuyAndHoldStrategy, self).__init__()
        self.invested = False

    def on_tick(self, tick_event):
        print(tick_event.timestamp)
        symbol = self.symbols[0]
        if not self.invested:
            df_hist = self._data_board.get_hist_price(symbol, tick_event.timestamp)
            close = df_hist.iloc[-1]["Close"]
            timestamp = df_hist.index[-1]
            target_size = int(self._position_manager.initial_capital / close)
            self.adjust_position(
                symbol, size_from=0, size_to=target_size, timestamp=timestamp
            )
            self.invested = True


class TestBuyHold:
    def test_buyhold(self):
        df = read_ohlcv_csv(
            os.path.join(os.path.dirname(__file__), "test_data/TEST.csv")
        )
        init_capital = 100_000.0
        test_start_date = datetime(
            2008, 1, 1, 8, 30, 0, 0, pytz.timezone("America/New_York")
        )
        test_end_date = datetime(
            2008, 12, 31, 6, 0, 0, 0, pytz.timezone("America/New_York")
        )
        strategy = BuyAndHoldStrategy()
        strategy.set_capital(init_capital)
        strategy.set_symbols(["TTT"])
        # strategy.set_params(None)

        backtest_engine = BacktestEngine(test_start_date, test_end_date)
        backtest_engine.set_capital(
            init_capital
        )  # capital or portfolio >= capital for one strategy
        backtest_engine.add_data("TTT", df)
        backtest_engine.set_strategy(strategy)
        equity, df_positions, df_trades = backtest_engine.run()
        assert df_trades.shape[0] > 0
