#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import decimal
import pandas as pd
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

def save_one_run_results(output_dir, equity, df_positions, df_trades, batch_tag=None):
    df_positions.to_csv('{}{}{}{}'.format(output_dir, '/positions_', batch_tag if batch_tag else '', '.csv'))
    df_trades.to_csv('{}{}{}{}'.format(output_dir, '/trades_', batch_tag if batch_tag else '', '.csv'))
    equity.to_csv('{}{}{}{}'.format(output_dir, '/equity_', batch_tag if batch_tag else '', '.csv'))

