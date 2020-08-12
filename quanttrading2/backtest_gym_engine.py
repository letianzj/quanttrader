#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gym trading env
https://github.com/openai/gym/blob/master/gym/envs/classic_control/cartpole.py
1. obs <- reset()      # env
2. action <- pi(obs)    # agent
3. news_obs <- step(action)      # env
repeat 2, and 3 for interactions between agent and env
"""
import os
import numpy as np
import pandas as pd
import gym
from datetime import datetime, date
import logging

from .event import EventType
from .event.backtest_event_engine import BacktestEventEngine
from .data.backtest_data_feed import BacktestDataFeed
from .data.data_board import DataBoard
from .brokerage.backtest_brokerage import BacktestBrokerage
from .position.position_manager import PositionManager
from .performance.performance_manager import PerformanceManager
from .risk.risk_manager import PassThroughRiskManager

_logger = logging.getLogger(__name__)


class BacktestGymEngine(gym.Env):
    """
    Description:
        backtest gym engine
        it doesn't normalize; and expects a normalization layer
    Observation:
        Type: Box(lookback_window, n_assets*5+2)
        lookback_window x (n_assets*(ohlcv) + cash+npv)
        TODO: append trades, commissions, standing orders, etc
        TODO: stop/limit orders
    Actions:
        Type: Box(n_assets + 1)
        portfolio weights [w1,w2...w_k, cash_weight], add up to one
    Reward:
        cumulative pnl in run_window
    Starting State:
        random timestamp between start_date and (end_date - run_window)
    Episode Termination:
        after predefined window
        If broke, no orders will send
    """
    def __init__(self, n_assets, lookback_window=15, run_window=252*2, start_date=None, end_date=None):
        self._current_time = None
        self._start_date = start_date
        self._end_date = end_date
        self.multiplier_dict = {}
        self._data_feed = BacktestDataFeed(self._start_date, self._end_date)
        self._data_board = DataBoard()
        self._performance_manager = PerformanceManager(self.multiplier_dict)
        self._position_manager = PositionManager()
        self._position_manager.set_multiplier(self.multiplier_dict)
        self._risk_manager = PassThroughRiskManager()
        self._strategy = None           # no strategy; strategy is to be learned

        self._n_assets = n_assets
        self.action_space = gym.spaces.Box(low=0.0, high=1.0, shape=(n_assets + 1,), dtype=np.float32)

        self._lookback_window = lookback_window
        self._run_window = run_window
        self.observation_space = gym.spaces.Box(low=-np.inf, high=np.inf,
                                                shape=(self._lookback_window, self._n_assets*5+2), dtype=np.float32)

        self._setup()

    def set_capital(self, capital):
        self._position_manager.set_capital(capital)

    def set_multiplier(self, multiplier_dict):
        self.multiplier_dict.update(multiplier_dict)

    def add_data(self, data_key, data_source, watch=True):
        """
        Add data for backtest
        :param data_key: AAPL or CL; if it is followed by number, assumed to be multiplier
        :param data_source:  dataframe, datetimeindex
        :param watch: track position or not
        :return:
        """
        keys = data_key.split(' ')
        if keys[-1].isdigit():       # multiplier
            data_key = ' '.join(keys[:-1])
            self.multiplier_dict[data_key] = int(keys[-1])

        self._data_feed.set_data_source(data_source)          # get iter(datetimeindex)
        self._data_board.initialize_hist_data(data_key, data_source)
        if watch:
            self._performance_manager.add_watch(data_key, data_source)

    def _setup(self):
        """
        Tis can be initialzied before data is loaded
        because it doesn't subscribe
        """
        ## 2. event engine
        self._events_engine = BacktestEventEngine(self._data_feed)

        ## 3. brokerage
        self._backtest_brokerage = BacktestBrokerage(
            self._events_engine, self._data_board
        )

        ## 6. wire up event handlers
        self._events_engine.register_handler(EventType.TICK, self._tick_event_handler)
        # to be consistent with current live, order is placed directly
        # self._events_engine.register_handler(EventType.ORDER, self._order_event_handler)
        self._events_engine.register_handler(EventType.FILL, self._fill_event_handler)

    def _tick_event_handler(self, tick_event):
        self._current_time = tick_event.timestamp

        # performance updates after one step run
        self._position_manager.mark_to_market(tick_event.timestamp, tick_event.full_symbol, tick_event.price, self._data_board)
        self._data_board.on_tick(tick_event)
        self._strategy.on_tick(tick_event)

    def _order_event_handler(self, order_event):
        """
        backtest doesn't send order_event back to strategy. It fills directly and becoems fill_event
        """
        self._backtest_brokerage.place_order(order_event)

    def _fill_event_handler(self, fill_event):
        self._position_manager.on_fill(fill_event)
        self._performance_manager.on_fill(fill_event)
        self._strategy.on_fill(fill_event)

    def reset(self):
        ## reset performance manager and portfolio manager
        self._performance_manager.reset()
        self._position_manager.reset()

        ## reset iterator randomly
        self._data_feed.subscribe_market_data()

    def step(self, action):
        """
        Run backtest
        """
        self._events_engine.run(1)
        # explicitly update performance; now orders are filled
        self._performance_manager.update_performance(self._current_time, self._position_manager, self._data_board)

        done = self._current_time is None
        state = None
        return state

    def render(self, mode='human'):
        pass

    def close(self):
        pass