#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Gym trading env
Unlike live engine or backtest engine, where event loops are driven by live ticks or historical ticks,
here it is driven by step function, similar to
https://github.com/openai/gym/blob/master/gym/envs/classic_control/cartpole.py
The sequence is
1. obs <- env.reset()      # env; obs = OHLCV + technical indicators + holdings
2. action <- pi(obs)       # agent; action = target weights
3. news_obs, reward, <- step(action)      # env
    3.a action to orders   # sum(holdings) * new weights
    3.b fill orders        # portfolio rotates into new holdings
repeat 2, and 3 to interact between agent and env
"""
import gym
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class TradingEnv(gym.Env):
    """
    Description:
        backtest gym engine
        it doesn't normalize; and expects a normalization layer
    Observation:
        Type: Box(lookback_window, n_assets*5+2)
        lookback_window x (n_assets*(ohlcv) + cash+npv)
        TODO: append trades, standing orders, etc
        TODO: stop/limit orders
    Actions:
        Type: Box(n_assets + 1)
        portfolio weights [w1,w2...w_k, cash_weight], add up to one
    Reward:
        pnl every day, similar to space-invaders
    Starting State:
        random timestamp between start_date and (end_date - run_window)
    Episode Termination:
        after predefined window
        If broke, no orders will send
    """

    def __init__(self, n: np.int32, df_obs_scaled: pd.DataFrame, df_exch: pd.DataFrame):
        assert n >= 2

        self._df_obs_scaled = (
            df_obs_scaled  # observation; scaled outside along with TA indicators
        )
        self._df_exch = df_exch  # exch
        self._df_positions = df_exch * 0.0  # positions plus cash plus nav
        self._df_positions["Cash"] = 0.0
        self._df_positions["NAV"] = 0.0

        self._asset_syms = df_exch.columns
        self._n_assets = len(self._asset_syms)
        self._n_features = (
            df_obs_scaled.shape[1] / self._n_assets
        )  # assume same features across assets

        self._inital_cash = 100_000.0
        self._cash = self._inital_cash
        self._commission_rate = 0.0
        self._look_back = 10  # observation lookback history
        self._warmup = (
            50  # observation ramp-up due to e.g. 10 periods are required to cacl MA(10)
        )
        self._maxsteps = 252  # max steps in one episode

        self._max_nav_scaler = 1.0
        self._lock_init_step = False
        self._init_step = 0
        self._current_step = 0

        self._n = n  # n=2: buy/sell 100% or [0, 100%]; n=3: [0, 50%, 100%]; n=4: [0, 33.3%, 66.7%, 100%]
        self._pcts = [pct / (self._n - 1) for pct in range(self._n)]

        self.action_space = gym.spaces.Discrete(n=self._n)
        # first col is open, second col is high, ..., last col is nav
        self.observation_space = gym.spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self._look_back, df_obs_scaled.shape[1] + 1),
            dtype=np.float32,
        )

    def set_cash(self, cash: np.float32 = 100_000.0):
        self._inital_cash = cash
        self._cash = self._inital_cash

    def set_commission(self, comm: np.float32 = 0.0001):
        """
        commission plus slippage
        """
        self._commission_rate = comm

    def set_steps(
        self,
        n_lookback: np.int32 = 10,
        n_warmup: np.int32 = 50,
        n_maxsteps: np.int32 = 252,
        n_init_step: np.int32 = 0,
    ):
        self._lookback = n_lookback
        self._warmup = n_warmup
        self._maxsteps = n_maxsteps
        self._init_step = n_init_step
        if n_init_step > 0:
            assert n_init_step >= n_warmup
            self._lock_init_step = True

    def set_feature_scaling(self, max_nav_scaler: np.float32 = 1.0):
        self._max_nav_scaler = max_nav_scaler

    def _get_observation(self):
        """
        return an array of size self._lookback x features.
        Each column is a feature; last feature is NAV.
        Row is in time ascending order. That is, last row is self._current_step.
        """
        obs = self._df_obs_scaled.iloc[
            self._current_step - self._look_back + 1 : self._current_step + 1
        ].values
        obs = np.append(
            obs,
            self._df_positions.iloc[
                self._current_step - self._look_back + 1 : self._current_step + 1
            ][["NAV"]].values
            / self._max_nav_scaler,
            axis=1,
        )

        return obs

    def step(self, action):
        """
        move one step to the next timestamp, accordingly to action
        assume hft condition: execution at today 15:59:59, after observing today's ohl and (almost) close.
        execution immediately using market or market on close, no slippage.
        e.g., assume on 12/31/2019, 1/2/2020, and 1/3/2020 prices are $95, $100, $110. respectively.
        The state or observation is prices of last two days.
        We start on 1/2/2020 with $100,000.
        Then
        1. on 1/2/2020, obs = [$95, $100]         # obs <- env.reset()
        2. on 1/2/2020, based on the up-trend observation, we decide to buy.
            Our allocation action w is [50%, 50%], or half in cash, half in stock.
        3. on 1/2/2020, the step function is      # news_obs, reward <- step(action)
            3.a buy order of $5,000 or 50 shares, filled at $100
            3.b stock market environment transits to 1/3/2020, new observation is [$100, $110];
                our stock is now worth $5,500, and total asset NAV is $10,500, or reward $500.
        :param action:
        :return:
        """
        done = False

        current_size = int(
            self._df_positions.iloc[self._current_step][self._asset_syms].item()
        )
        current_cash = self._df_positions.iloc[self._current_step]["Cash"]
        current_price = self._df_exch.iloc[self._current_step].item()

        # rebalance
        current_nav = (
            current_cash + current_price * current_size
        )  # should equal to the nav column
        new_size = int(
            np.floor(current_nav * self._pcts[action] / current_price)
        )  # odd size allowed; action[-1] is cash
        delta_size = new_size - current_size
        current_commission = np.abs(delta_size) * current_price * self._commission_rate
        new_cash = current_cash - delta_size * current_price - current_commission

        # move to next timestep
        self._current_step += 1
        new_price = self._df_exch.iloc[self._current_step].item()
        new_nav = new_cash + new_price * new_size
        reward = (
            new_price - current_price
        ) * new_size - current_commission  # commission is penalty
        info = {
            "step": self._current_step,
            "time": self._df_obs_scaled.index[self._current_step],
            "old_price": current_price,
            "old position": current_size,
            "old_cash": current_cash,
            "old_nav": current_nav,
            "price": new_price,
            "position": new_size,
            "cash": new_cash,
            "nav": new_nav,
            "transaction": delta_size,
            "commission": current_commission,
            "nav_diff": new_nav - current_nav,
        }  # reward = new_nav - current_nav

        # reward = reward / self._max_nav_scaler
        self._df_positions.loc[
            self._df_positions.index[self._current_step], self._asset_syms
        ] = new_size
        self._df_positions["Cash"][self._current_step] = new_cash
        self._df_positions["NAV"][self._current_step] = new_nav

        if (
            self._current_step - self._init_step >= self._maxsteps
        ):  # e.g. init=3, current=7, _maxsteps=4
            done = True
        if self._current_step == self._df_exch.shape[0] - 1:  # end of data
            done = True

        # s'
        new_state = self._get_observation()

        return new_state, reward, done, info

    def reset(self):
        """
        random start time
        """
        self._cash = self._inital_cash
        self._df_positions = self._df_exch * 0.0
        self._df_positions["Cash"] = 0.0
        self._df_positions["NAV"] = 0.0

        if not self._lock_init_step:
            self._init_step = np.random.randint(
                low=self._warmup - 1,
                high=self._df_obs_scaled.shape[0] - self._maxsteps,
            )  # low (inclusive) to high (exclusive)
        self._current_step = self._init_step

        self._df_positions["Cash"][: self._current_step + 1] = self._cash
        self._df_positions["NAV"][: self._current_step + 1] = self._cash

        # return current_step
        return self._get_observation()

    def render(self, mode="human"):
        # plt.rcParams.update({'font.size': 6})
        fig, ax = plt.subplots(
            2, 1, gridspec_kw={"height_ratios": [3, 1]}
        )  # figsize=(15, 8)
        fig.tight_layout()
        x_left = self._init_step
        x_right = self._current_step + 1
        x_end = min(self._df_exch.shape[0], self._init_step + self._maxsteps + 1)
        df_price = self._df_exch[x_left:x_right]
        df_nav = self._df_positions["NAV"][x_left:x_right]

        ax[0].tick_params(
            axis="x",  # changes apply to the x-axis
            which="both",  # both major and minor ticks are affected
            bottom=False,  # ticks along the bottom edge are off
            top=False,  # ticks along the top edge are off
            labelbottom=False,
        )  # labels along the bottom edge are off
        ax[0].set_xlim([self._df_exch.index[x_left], self._df_exch.index[x_end - 1]])
        ax[1].set_xlim([self._df_exch.index[x_left], self._df_exch.index[x_end - 1]])
        ax[0].set_ylim(
            [
                max(self._df_exch[x_left:x_end].min().item() - 5, 0),
                self._df_exch[x_left:x_end].max().item() + 5,
            ]
        )
        df_position = self._df_positions["SPY"][x_left:x_right]
        df_position_diff = df_position - df_position.shift(1)
        df_buy = df_price[df_position_diff > 0]
        df_sell = df_price[df_position_diff < 0]
        ax[0].plot(df_price, color="black", label="Price")
        ax[0].plot(df_buy, "^", markersize=5, color="r")
        ax[0].plot(df_sell, "v", markersize=5, color="g")
        ax[1].plot(df_nav, color="black", label="NAV")
        # plt.pause(0.001)

        # https://stackoverflow.com/questions/7821518/matplotlib-save-plot-to-numpy-array
        fig.canvas.draw()
        data = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        data = data.reshape(fig.canvas.get_width_height()[::-1] + (3,))
        plt.close()
        return data

    def close(self):
        pass
