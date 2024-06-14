#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import pandas as pd

from quanttrader.data.tick_event import TickType
from quanttrader.strategy.strategy_base import StrategyBase

_logger = logging.getLogger("qtlive")


class DualThrustStrategy(StrategyBase):
    """
    Dual thrust
    """

    def __init__(self):
        super(DualThrustStrategy, self).__init__()
        self.k1 = 0.7
        self.k2 = 0.7
        df = pd.read_csv("./strategy/dual_thrust.csv", header=0, index_col=0)
        df.index = pd.to_datetime(df.index)
        df1 = df.resample("5T").agg({"price": "ohlc", "volume": "sum"})
        df1.columns = df1.columns.get_level_values(1)
        _ = df1.resample("10T").agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )

        _logger.info("DualThrustStrategy initiated")

    def on_tick(self, tick_event):
        k = tick_event
        super().on_tick(k)  # extra mtm calc

        if k.tick_type != TickType.TRADE:
            return

        print(k)
