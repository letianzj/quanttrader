#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import decimal
import pandas as pd
import pickle
from datetime import datetime


def retrieve_multiplier_from_full_symbol(full_symbol):
    return 1.0

def read_ohlcv_csv(filepath, adjust=True, tz='America/New_York'):
    df = pd.read_csv(filepath, header=0, parse_dates=True, sep=',', index_col=0)
    df.index = df.index + pd.DateOffset(hours=16)
    df.index = df.index.tz_localize(tz)        # US/Eastern, UTC
    # df.index = pd.to_datetime(df.index)
    if adjust:
        df['Open'] = df['Adj Close'] / df['Close'] * df['Open']
        df['High'] = df['Adj Close'] / df['Close'] * df['High']
        df['Low'] = df['Adj Close'] / df['Close'] * df['Low']
        df['Volume'] = df['Adj Close'] / df['Close'] * df['Volume']
        df['Close'] = df['Adj Close']

    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    return df

def read_intraday_bar_pickle(filepath, syms, tz='America/New_York'):
    dict_hist_data = {}
    if os.path.isfile(filepath):
        with open(filepath, 'rb') as f:
            dict_hist_data = pickle.load(f)
    dict_ret = {}
    for sym in syms:
        try:
            df = dict_hist_data[sym]
            df.index = df.index.tz_localize(tz)          # # US/Eastern, UTC
            dict_ret[sym] = df
        except:
            pass
    return dict_ret

def read_tick_data_txt(filepath, remove_bo=True, tz='America/New_York'):
    """
    filename = yyyymmdd.txt
    """
    asofdate = filepath.split('/')[-1].split('.')[0]
    data = pd.read_csv(filepath, sep=',', header=None)
    data.columns = ['Time', 'ProcessTime', 'Ticker', 'Type', 'BidSize', 'Bid', 'Ask', 'AskSize', 'Price', 'Size']
    data = data[['Time', 'Ticker', 'Type', 'BidSize', 'Bid', 'Ask', 'AskSize', 'Price', 'Size']]
    if remove_bo:
        data = data[data.Type.str.contains('TickType.TRADE')]
    data.Time = data.Time.apply(lambda t: datetime.strptime(f'{asofdate} {t}', "%Y%m%d %H:%M:%S.%f"))
    data.set_index('Time', inplace=True)
    data.index = data.index.tz_localize(tz)  # # US/Eastern, UTC
    dg = data.groupby('Ticker')
    dict_ret = {}
    for sym, dgf in dg:
        dgf = dgf[~dgf.index.duplicated(keep='last')]
        dict_ret[sym] = dgf
    return dict_ret


def save_one_run_results(output_dir, equity, df_positions, df_trades, batch_tag=None):
    df_positions.to_csv('{}{}{}{}'.format(output_dir, '/positions_', batch_tag if batch_tag else '', '.csv'))
    df_trades.to_csv('{}{}{}{}'.format(output_dir, '/trades_', batch_tag if batch_tag else '', '.csv'))
    equity.to_csv('{}{}{}{}'.format(output_dir, '/equity_', batch_tag if batch_tag else '', '.csv'))

