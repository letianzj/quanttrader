#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import re
import matplotlib.pyplot as plt
import empyrical as ep
import pyfolio as pf


class PerformanceManager(object):
    """
    Record equity, positions, and trades in accordance to pyfolio format
    First date will be the first data start date
    """
    def __init__(self, symbols, benchmark=None, batch_tag='0', multi=1, fvp=None):
        self._symbols = []
        self._benchmark = benchmark
        self._batch_tag = batch_tag
        self._multi = multi                      # root multiplier, for CL1, CL2
        if multi is None:
            self._multi = 1
        self._df_fvp = fvp

        if self._multi > 1:
            for sym in symbols:
                self._symbols.extend([sym+str(i+1) for i in range(multi)])           # CL1 CL2
        else:
            self._symbols.extend(symbols)

        self._slippage = 0.0
        self._commission_rate = 0.0
        self.reset()

    # ------------------------------------ public functions -----------------------------#
    #  or each sid
    def reset(self):
        self._realized_pnl = 0.0
        self._unrealized_pnl = 0.0

        self._equity = pd.Series()      # equity line
        self._equity.name = 'total'

        if self._multi > 1:
            self._df_positions = pd.DataFrame(columns=self._symbols * 2 + ['cash', 'total', 'benchmark'])  # Position + Symbol
        else:
            self._df_positions = pd.DataFrame(columns=self._symbols + ['cash', 'total', 'benchmark'])   # Position + Symbol

        self._df_trades = pd.DataFrame(columns=['amount', 'price', 'symbol'])

    def set_splippage(self, slippage):
        self._slippage = slippage

    def set_commission_rate(self, commission_rate):
        self._commission_rate = commission_rate

    def update_performance(self, current_time, position_manager, data_board):
        if self._equity.empty:
            self._equity[current_time] = 0.0
            return
        # on a new time/date, calculate the performances for the last date
        elif current_time != self._equity.index[-1]:
            performance_time = self._equity.index[-1]

            equity = 0.0
            self._df_positions.loc[performance_time] = [0] * len(self._df_positions.columns)
            for sym, pos in position_manager.positions.items():
                m = 1
                if self._df_fvp is not None:
                    try:
                        if '|' in sym:
                            ss = sym.split('|')
                            match = re.match(r"([a-z ]+)([0-9]+)?", ss[0], re.I)
                            sym2 = match.groups()[0]

                        m = self._df_fvp.loc[sym2, 'FVP']
                    except:
                        m = 1

                # data_board hasn't been updated
                equity += pos.size * data_board.get_last_price(sym) * m
                if '|' in sym:
                    ss = sym.split('|')
                    self._df_positions.loc[performance_time, ss[0]] = [pos.size * data_board.get_last_price(sym)*m, ss[1]]
                else:
                    self._df_positions.loc[performance_time, sym] = pos.size * data_board.get_last_price(sym) * m
            self._df_positions.loc[performance_time, 'cash'] = position_manager.cash
            self._equity[performance_time] = equity + position_manager.cash
            self._df_positions.loc[performance_time, 'total'] = self._equity[performance_time]
            # calculate benchmark
            if self._benchmark is not None:
                if self._df_positions.shape[0] == 1:
                    self._df_positions.at[performance_time, 'benchmark'] = self._equity[performance_time]
                else:
                    benchmark_p0 = data_board.get_hist_price(self._benchmark, performance_time)
                    periodic_ret = 0
                    try:
                        periodic_ret = benchmark_p0.iloc[-1]['Close'] / benchmark_p0.iloc[-2]['Close'] - 1
                    except:
                        periodic_ret = benchmark_p0.iloc[-1]['Price'] / benchmark_p0.iloc[-2]['Price'] - 1
                    self._df_positions.at[performance_time, 'benchmark'] = self._df_positions.iloc[-2]['benchmark'] * (
                                1 + periodic_ret)

            self._equity[current_time] = 0.0

    def on_fill(self, fill_event):
        # self._df_trades.loc[fill_event.timestamp] = [fill_event.fill_size, fill_event.fill_price, fill_event.full_symbol]
        self._df_trades = self._df_trades.append(pd.DataFrame(
            {'amount': [fill_event.fill_size], 'price': [fill_event.fill_price], 'symbol': [fill_event.full_symbol]},
            index=[fill_event.fill_time]))

    def update_final_performance(self, current_time, position_manager, data_board):
        """
        When a new data date comes in, it calcuates performances for the previous day
        This leaves the last date not updated.
        So we call the update explicitly
        """
        performance_time = current_time

        equity = 0.0
        self._df_positions.loc[performance_time] = [0] * len(self._df_positions.columns)
        for sym, pos in position_manager.positions.items():
            m = 1
            if self._df_fvp is not None:
                try:
                    if '|' in sym:
                        ss = sym.split('|')
                        match = re.match(r"([a-z ]+)([0-9]+)?", ss[0], re.I)
                        sym2 = match.groups()[0]

                    m = self._df_fvp.loc[sym2, 'FVP']
                except:
                    m = 1
            equity += pos.size * data_board.get_last_price(sym) * m
            if '|' in sym:
                ss = sym.split('|')
                self._df_positions.loc[performance_time, ss[0]] = [pos.size * data_board.get_last_price(sym) * m, ss[1]]
            else:
                self._df_positions.loc[performance_time, sym] = pos.size * data_board.get_last_price(sym) * m
        self._df_positions.loc[performance_time, 'cash'] = position_manager.cash

        self._equity[performance_time] = equity + position_manager.cash
        self._df_positions.loc[performance_time, 'total'] = self._equity[performance_time]

        # calculate benchmark
        if self._benchmark is not None:
            if self._df_positions.shape[0] == 1:
                self._df_positions.at[performance_time, 'benchmark'] = self._equity[performance_time]
            else:
                benchmark_p0 = data_board.get_hist_price(self._benchmark, performance_time)
                periodic_ret = 0
                try:
                    periodic_ret = benchmark_p0.iloc[-1]['Close'] / benchmark_p0.iloc[-2]['Close'] - 1
                except:
                    periodic_ret = benchmark_p0.iloc[-1]['Price'] / benchmark_p0.iloc[-2]['Price'] - 1

                self._df_positions.at[performance_time, 'benchmark'] = self._df_positions.iloc[-2]['benchmark'] * (
                        1 + periodic_ret)

    def caculate_performance(self, tearsheet=False):
        # to daily
        try:
            rets = self._equity.resample('D').last().dropna().pct_change()
            if self._benchmark is not None:
                b_rets = self._df_positions['benchmark'].resample('D').last().dropna().pct_change()
        except:
            rets = self._equity.pct_change()
            if self._benchmark is not None:
                b_rets = self._df_positions['benchmark'].pct_change()

        rets = rets[1:]
        if self._benchmark is not None:
            b_rets = b_rets[1:]

        #rets.index = rets.index.tz_localize('UTC')
        #self._df_positions.index = self._df_positions.index.tz_localize('UTC')
        perf_stats_all = None
        if not self._df_trades.index.empty:
            if self._benchmark is not None:
                # self._df_trades.index = self._df_trades.index.tz_localize('UTC')
                # pf.create_full_tear_sheet(rets, self._df_positions, self._df_trades)
                rets.index = pd.to_datetime(rets.index)
                b_rets.index = rets.index

                perf_stats_strat = pf.timeseries.perf_stats(rets)
                perf_stats_benchmark = pf.timeseries.perf_stats(b_rets)
                perf_stats_all = pd.concat([perf_stats_strat, perf_stats_benchmark], axis=1)
                perf_stats_all.columns = ['Strategy', 'Benchmark']
            else:
                # self._df_trades.index = self._df_trades.index.tz_localize('UTC')
                # pf.create_full_tear_sheet(rets, self._df_positions, self._df_trades)
                rets.index = pd.to_datetime(rets.index)
                perf_stats_all = pf.timeseries.perf_stats(rets)
                perf_stats_all = perf_stats_all.to_frame(name='Strategy')

            if tearsheet:            # only plot if not self._df_trades.index.empty
                pf.create_returns_tear_sheet(rets,benchmark_rets=b_rets)
                # pf.create_returns_tear_sheet(rets)
                # pf.create_simple_tear_sheet(rets, benchmark_rets=b_rets)

                # somehow the tearsheet is too crowded.
                fig, ax = plt.subplots(nrows=1, ncols=2)
                if self._benchmark is not None:
                    pf.plot_rolling_returns(rets, factor_returns=b_rets, ax=ax[0])
                    ax[0].set_title('Cumulative returns')
                    ax[1].text(5.0, 9.5, 'Strategy', fontsize=8, fontweight='bold', horizontalalignment='left')
                    ax[1].text(8.0, 9.5, 'Benchmark', fontsize=8, fontweight='bold', horizontalalignment='left')

                    ax[1].text(0.5, 8.5, 'Annual return', fontsize=8, horizontalalignment='left')
                    ax[1].text(6.0, 8.5, round(perf_stats_all.loc['Annual return', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right')
                    ax[1].text(9.5, 8.5, round(perf_stats_all.loc['Annual return', 'Benchmark'], 4), fontsize=8,
                               horizontalalignment='right')

                    ax[1].text(0.5, 7.5, 'Cumulative returns', fontsize=8, horizontalalignment='left', color='green')
                    ax[1].text(6.0, 7.5, round(perf_stats_all.loc['Cumulative returns', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right', color='green')
                    ax[1].text(9.5, 7.5, round(perf_stats_all.loc['Cumulative returns', 'Benchmark'], 4), fontsize=8,
                               horizontalalignment='right', color='green')

                    ax[1].text(0.5, 6.5, 'Annual volatility', fontsize=8, horizontalalignment='left')
                    ax[1].text(6.0, 6.5, round(perf_stats_all.loc['Annual volatility', 'Strategy'], 4), fontsize=8,
                              horizontalalignment='right')
                    ax[1].text(9.5, 6.5, round(perf_stats_all.loc['Annual volatility', 'Benchmark'], 4), fontsize=8,
                               horizontalalignment='right')

                    ax[1].text(0.5, 5.5, 'Sharpe ratio', fontsize=8, horizontalalignment='left', color='green')
                    ax[1].text(6.0, 5.5, round(perf_stats_all.loc['Sharpe ratio', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right', color='green')
                    ax[1].text(9.5, 5.5, round(perf_stats_all.loc['Sharpe ratio', 'Benchmark'], 4), fontsize=8,
                               horizontalalignment='right', color='green')

                    ax[1].text(0.5, 4.5, 'Calmar ratio', fontsize=8, horizontalalignment='left')
                    ax[1].text(6.0, 4.5, round(perf_stats_all.loc['Calmar ratio', 'Strategy'], 4), fontsize=8,
                              horizontalalignment='right')
                    ax[1].text(9.5, 4.5, round(perf_stats_all.loc['Calmar ratio', 'Benchmark'], 4), fontsize=8,
                               horizontalalignment='right')

                    ax[1].text(0.5, 3.5, 'Sortino ratio', fontsize=8, horizontalalignment='left', color='green')
                    ax[1].text(6.0, 3.5, round(perf_stats_all.loc['Sortino ratio', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right', color='green')
                    ax[1].text(9.5, 3.5, round(perf_stats_all.loc['Sortino ratio', 'Benchmark'], 4), fontsize=8,
                               horizontalalignment='right', color='green')

                    ax[1].text(0.5, 2.5, 'Max drawdown', fontsize=8, horizontalalignment='left')
                    ax[1].text(6.0, 2.5, round(perf_stats_all.loc['Max drawdown', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right')
                    ax[1].text(9.5, 2.5, round(perf_stats_all.loc['Max drawdown', 'Benchmark'], 4), fontsize=8,
                               horizontalalignment='right')

                    ax[1].text(0.5, 1.5, 'Skew', fontsize=8, horizontalalignment='left', color='green')
                    ax[1].text(6.0, 1.5, round(perf_stats_all.loc['Skew', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right', color='green')
                    ax[1].text(9.5, 1.5, round(perf_stats_all.loc['Skew', 'Benchmark'], 4), fontsize=8,
                               horizontalalignment='right', color='green')

                    ax[1].text(0.5, 0.5, 'Kurtosis', fontsize=8, horizontalalignment='left')
                    ax[1].text(6.0, 0.5, round(perf_stats_all.loc['Kurtosis', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right')
                    ax[1].text(9.5, 0.5, round(perf_stats_all.loc['Kurtosis', 'Benchmark'], 4), fontsize=8,
                               horizontalalignment='right')
                else:
                    pf.plot_rolling_returns(rets, ax=ax[0])
                    ax[0].set_title('Cumulative returns')
                    # pf.plotting.plot_monthly_returns_heatmap(rets, ax=ax[1])
                    ax[1].text(0.5, 9.0, 'Annual return', fontsize=8, horizontalalignment='left')
                    ax[1].text(9.5, 9.0, round(perf_stats_all.loc['Annual return', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right')

                    ax[1].text(0.5, 8.0, 'Cumulative returns', fontsize=8, horizontalalignment='left', color='green')
                    ax[1].text(9.5, 8.0, round(perf_stats_all.loc['Cumulative returns', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right', color='green')

                    ax[1].text(0.5, 7.0, 'Annual volatility', fontsize=8, horizontalalignment='left')
                    ax[1].text(9.5, 7.0, round(perf_stats_all.loc['Annual volatility', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right')

                    ax[1].text(0.5, 6.0, 'Sharpe ratio', fontsize=8, horizontalalignment='left', color='green')
                    ax[1].text(9.5, 6.0, round(perf_stats_all.loc['Sharpe ratio', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right', color='green')

                    ax[1].text(0.5, 5.0, 'Calmar ratio', fontsize=8, horizontalalignment='left')
                    ax[1].text(9.5, 5.0, round(perf_stats_all.loc['Calmar ratio', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right')

                    ax[1].text(0.5, 4.0, 'Sortino ratio', fontsize=8, horizontalalignment='left', color='green')
                    ax[1].text(9.5, 4.0, round(perf_stats_all.loc['Sortino ratio', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right', color='green')

                    ax[1].text(0.5, 3.0, 'Max drawdown', fontsize=8, horizontalalignment='left')
                    ax[1].text(9.5, 3.0, round(perf_stats_all.loc['Max drawdown', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right')

                    ax[1].text(0.5, 2.0, 'Skew', fontsize=8, horizontalalignment='left', color='green')
                    ax[1].text(9.5, 2.0, round(perf_stats_all.loc['Skew', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right', color='green')

                    ax[1].text(0.5, 1.0, 'Kurtosis', fontsize=8, horizontalalignment='left')
                    ax[1].text(9.5, 1.0, round(perf_stats_all.loc['Kurtosis', 'Strategy'], 4), fontsize=8,
                               horizontalalignment='right')

                ax[1].set_title('Performance', fontweight='bold')
                ax[1].grid(False)
                # ax[1].spines['top'].set_linewidth(2.0)
                # ax[1].spines['bottom'].set_linewidth(2.0)
                ax[1].spines['right'].set_visible(False)
                ax[1].spines['left'].set_visible(False)
                ax[1].get_yaxis().set_visible(False)
                ax[1].get_xaxis().set_visible(False)
                ax[1].set_ylabel('')
                ax[1].set_xlabel('')
                ax[1].axis([0, 10, 0, 10])

                plt.show()

        drawdown_df = pf.timeseries.gen_drawdown_table(rets, top=5)
        monthly_ret_table = ep.aggregate_returns(rets, 'monthly')
        monthly_ret_table = monthly_ret_table.unstack().round(3)
        ann_ret_df = pd.DataFrame(ep.aggregate_returns(rets, 'yearly'))
        ann_ret_df = ann_ret_df.unstack().round(3)
        return perf_stats_all, drawdown_df, monthly_ret_table, ann_ret_df

    def save_results(self, output_dir):
        '''
        equity and df_posiiton should have the same datetime index
        :param output_dir:
        :return:
        '''
        self._df_positions = self._df_positions[self._symbols+['cash', 'total', 'benchmark']]
        self._df_positions.to_csv('{}{}{}{}'.format(output_dir, '/positions_', self._batch_tag if self._batch_tag else '', '.csv'))
        self._df_trades.to_csv('{}{}{}{}'.format(output_dir, '/trades_', self._batch_tag if self._batch_tag else '', '.csv'))
    # ------------------------------- end of public functions -----------------------------#