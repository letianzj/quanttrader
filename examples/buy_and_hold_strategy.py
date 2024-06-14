"""
buy and hold strategy example
"""

import os
from datetime import datetime

import pytz

from quanttrader.backtest_engine import BacktestEngine
from quanttrader.data.tick_event import TickEvent
from quanttrader.strategy.strategy_base import StrategyBase
from quanttrader.util.util_func import read_ohlcv_csv


class BuyAndHoldStrategy(StrategyBase):
    """
    buy on the first tick then hold to the end
    """

    def __init__(self) -> None:
        super().__init__()
        self.invested: bool = False

    def on_tick(self, tick_event: TickEvent) -> None:
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


if __name__ == "__main__":
    df = read_ohlcv_csv(
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "TEST.csv")
    )
    INIT_CAPITAL = 100_000.0
    test_start_date = datetime(
        2008, 1, 1, 8, 30, 0, 0, pytz.timezone("America/New_York")
    )
    test_end_date = datetime(
        2008, 12, 31, 6, 0, 0, 0, pytz.timezone("America/New_York")
    )
    strategy = BuyAndHoldStrategy()
    strategy.set_capital(INIT_CAPITAL)
    strategy.set_symbols(["TTT"])
    # strategy.set_params(None)     # no params to set

    backtest_engine = BacktestEngine(test_start_date, test_end_date)
    backtest_engine.set_capital(
        INIT_CAPITAL
    )  # capital or portfolio >= capital for one strategy
    backtest_engine.add_data("TTT", df)
    backtest_engine.set_strategy(strategy)
    equity, df_positions, df_trades = backtest_engine.run()
    if df_trades is None:
        print("Empty Strategy")
    else:
        print(equity)
