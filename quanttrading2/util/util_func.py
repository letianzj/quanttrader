#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import decimal
import pandas as pd
import pyfolio as pf
from datetime import datetime


def retrieve_multiplier_from_full_symbol(full_symbol):
    return 1.0

def read_ohlcv_csv(filepath, adjust=True):
    df = pd.read_csv(filepath, header=0, parse_dates=True, sep=',', index_col=0)
    # df.index = pd.to_datetime(df.index)
    if adjust:
        df['Open'] = df['Adj Close'] / df['Close'] * df['Open']
        df['High'] = df['Adj Close'] / df['Close'] * df['High']
        df['Low'] = df['Adj Close'] / df['Close'] * df['Low']
        df['Volume'] = df['Adj Close'] / df['Close'] * df['Volume']
        df['Close'] = df['Adj Close']

    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    return df

def save_one_run_results(output_dir, df_positions, df_trades, batch_tag=None):
    df_positions.to_csv('{}{}{}{}'.format(output_dir, '/positions_', batch_tag if batch_tag else '', '.csv'))
    df_trades.to_csv('{}{}{}{}'.format(output_dir, '/trades_', batch_tag if batch_tag else '', '.csv'))


def caculate_performance(df_equity, df_trades, df_positions, df_benchmark, tearsheet=False):
    # to daily
    try:
        rets = self._equity.resample('D').last().dropna().pct_change()
    except:
        rets = self._equity.pct_change()

    rets = rets[1:]

    #rets.index = rets.index.tz_localize('UTC')
    #self._df_positions.index = self._df_positions.index.tz_localize('UTC')
    perf_stats_all = None
    if not self._df_trades.index.empty:
        if self._benchmark is not None:
            # self._df_trades.index = self._df_trades.index.tz_localize('UTC')
            # pf.create_full_tear_sheet(rets, self._df_positions, self._df_trades)
            rets.index = pd.to_datetime(rets.index)

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