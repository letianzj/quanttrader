#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Making identical historical data requests within 15 seconds.
Making six or more historical data requests for the same Contract, Exchange and Tick Type within two seconds.
Making more than 60 requests within any ten minute period.
"""
import os
import argparse
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from signal import signal, SIGINT, SIG_DFL
import pickle
from quanttrader.event.event import EventType
from quanttrader.event.live_event_engine import LiveEventEngine
from quanttrader.brokerage.ib_brokerage import InteractiveBrokers

signal(SIGINT, SIG_DFL)
df = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

def log_event_handler(log_event):
    print(f'{log_event.timestamp}: {log_event.content}')

def historical_event_handler(bar_event):
    """
    local timezone based on tws setting
    """
    global df
    row_dict = {}
    row_dict['Open'] = bar_event.open_price
    row_dict['High'] = bar_event.high_price
    row_dict['Low'] = bar_event.low_price
    row_dict['Close'] = bar_event.close_price
    row_dict['Volume'] = bar_event.volume
    df1 = pd.DataFrame(row_dict, index=[bar_event.bar_start_time])
    df = pd.concat([df, df1], axis=0)

def run(args):
    global  df
    dfd = pd.DataFrame()
    dict_all = dict()
    events_engine = LiveEventEngine()
    tick_event_engine = LiveEventEngine()
    broker = InteractiveBrokers(events_engine, tick_event_engine, 'DU0001')
    broker.reqid = 5000
    events_engine.register_handler(EventType.LOG, log_event_handler)
    tick_event_engine.register_handler(EventType.BAR, historical_event_handler)
    events_engine.start()
    tick_event_engine.start()

    broker.connect('127.0.0.1', 7497, 0)
    time.sleep(5)  # 5 seconds

    # RTH stock 9:30~16:00; FUT 9:30~17:00, ES halt 16:15~16:30
    # 7.5h x 2 = 15 requests = 15*15 ~ 4min
    symbols = [
        'ESU0 FUT GLOBEX',          # 9:30 a.m. ET on the 3rd Friday of the contract month; 15:14:30 – 15:15:00 CT; final 9:30am opening prices
        # 'NQU0 FUT GLOBEX',          # 9:30 a.m. ET on the 3rd Friday of the contract month
        # 'CLU0 FUT NYNEX',           # 3 business day prior to the 25th calendar day of the month prior to the contract month, if not business day; active -2D; 4:28:00 to 14:30:00 ET; 14:00:00 and 14:30:00 ET
        # 'CLV0 FUT NYNEX',
        # 'HOU0 FUT NYMEX',           # last business day of the month prior to the contract month; active -2D CL; 14:28:00 to 14:30:00 ET, 14:00:00 and 14:30:00 ET.
        # 'HOV0 FUT NYMEX',
        # 'RBU0 FUT NYMEX',           # last business day of the month prior to the contract month.; active -2D CL; 14:28:00 to 14:30:00 ET, 14:00:00 and 14:30:00 ET.
        # 'RBV0 FUT NYMEX',
        # 'NGU0 FUT NYMEX',         # 3rd last business days of the month prior to the contract month; active -2D. 14:28:00 to 14:30:00 ET; 14:00:00 and 14:30:00 ET
        # 'NGV0 FUT NYMEX',
        # # 'SPY STK SMART',
        # 'QQQ STK SMART',
        # 'XLE STK SMART',
        # 'XLF STK SMART',
        # 'XLU STK SMART',
        # 'XLK STK SMART',
        # 'XLP STK SMART',
        # 'XLI STK SMART',
        # 'XLV STK SMART',
        # 'XLB STK SMART',
        # 'XLY STK SMART',
        # 'XLRE STK SMART',
        # 'XLC STK SMART'
    ]
    date = args.date
    path = args.path

    for sym in symbols:
        end_date = datetime.strptime(date, '%Y%m%d')
        if 'STK' in sym:
            end_date = end_date + timedelta(hours=16)       # 16:00
        else:  # FUT
            end_date = end_date + timedelta(hours=17)       # 17:00

        while end_date.hour >= 10:       # last one is (9:30am, 10am)
            print(sym, end_date)
            broker.request_historical_data(sym, end_date)
            end_date = end_date - timedelta(minutes=30)
            time.sleep(15)       # 15 seconds

            # daily combine and remove duplicates
            dfd = df.combine_first(dfd)
            # ready for the next 30min
            df = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

        dfd.sort_index(inplace=True)
        dict_all[sym] = dfd

    dict_stats = {}
    for k, v in dict_all.items():
        dict_stats[k] = v.shape[0]

    df_stats = pd.DataFrame.from_dict(dict_stats, orient='index')
    print('-----------------------------------------------')
    print(df_stats)

    outfile = f'{path}{date}.pkl'
    with open(outfile, 'wb') as f:
        pickle.dump(dict_all, f, pickle.HIGHEST_PROTOCOL)

    broker.disconnect()
    events_engine.stop()
    tick_event_engine.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Historical Downloader')
    parser.add_argument('--date', help='yyyymmdd')
    parser.add_argument('--path', default='d:/workspace/quantresearch/data/tick/', help='hist data folder')

    args = parser.parse_args()
    run(args)
