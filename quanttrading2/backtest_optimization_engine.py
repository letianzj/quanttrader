#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
from datetime import datetime, date
import multiprocessing
import yaml
from .backtest_engine import BacktestEngine

def output(content):
    print(str(datetime.now()) + "\t" + content)


def optimize(config, target_name):
    backtest = BacktestEngine(config)
    results = backtest.run(tear_sheet=False)

    try:
        #target_value = results[target_name]
        target_value = results[0].loc[target_name][0]   # first table in tuple
    except KeyError:
        target_value = 0
    return (config, target_value, results)

if __name__ == '__main__':
    # ------------------------ Set up config in code ---------------------------#
    config = {}
    config['cash'] = 500000.00
    config['benchmark'] = None
    config['root_multiplier'] = None
    config['fvp_file'] = None
    config['start_date'] = date(2010, 1, 1)
    config['end_date'] = datetime.today().date()
    config['end_date'] = date(2017, 5, 1)
    config['datasource'] = 'local'
    config['hist_dir'] = 'd:/workspace/privatefund/backtest/hist/'
    config['batch_tag'] = '0'           # used to tag first backtest; second backtest; etc
    config['output_dir'] = 'd:/workspace/privatefund/backtest/out/'

    # strategy specific
    config['strategy'] = 'MovingAverageCrossStrategy'
    config['symbols'] = ['SPX Index']

    # you can use for loop to construct params list in code
    params_list = []
    for sw in [10, 20, 30, 40, 50]:
        for lw in [10, 20, 30, 40, 50]:
            if lw <= sw:
                continue
            params_list.append({'short_window':sw, 'long_window': lw})

    config['params_list'] = params_list

    params_list = [{'short_window':10, 'long_window': 20},
                   {'short_window': 10, 'long_window': 30},
                   {'short_window': 10, 'long_window': 50},
                   {'short_window': 20, 'long_window': 30},
                   {'short_window': 20, 'long_window': 50}]
    # ------------------------ End of set up config in code ---------------------------#

    # ------------------------ Or read from config file -----------------------------------#
    config = None
    try:
        path = os.path.abspath(os.path.dirname(__file__))
        config_file = os.path.join(path, 'config_backtest_moving_average_cross.yaml')
        # config_file = os.path.join(path, 'config_backtest_mean_reversion_spread.yaml')
        with open(os.path.expanduser(config_file)) as fd:
            config = yaml.load(fd)
    except IOError:
        print("config.yaml is missing")
    # ----------------------- End of reading from config file ------------------------------#

    target_name = 'Sharpe ratio'
    pool = multiprocessing.Pool(multiprocessing.cpu_count())

    res_list = []
    batch_token = 0
    for param in config['params_list']:
        config_local = config.copy()
        config_local['params'] = param
        config_local['batch_tag'] = str(batch_token)
        res_list.append(pool.apply_async(optimize, (config_local, target_name)))
        batch_token = batch_token + 1
    pool.close()
    pool.join()

    res_list = [res.get() for res in res_list]
    res_list.sort(reverse=True, key=lambda res:res[1])

    output('-' * 50)
    output(u'optimization results：')
    for res in res_list:
        output(u'Params：%s，%s：%s' % (res[0]['params'], target_name, res[1]))

