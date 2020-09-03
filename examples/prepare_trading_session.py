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
import logging


def run(args):
    target_path = args.path

    # DualThrustStrategy
    sname = 'dual_thrust'
    index = pd.date_range('1/1/2020', periods=100, freq='T')
    s1 = pd.Series(range(100), index=index)
    s1.name = 'price'
    s2 = pd.Series(range(100), index=index)
    s2.name = 'volume'
    df = pd.concat([s1, s2], axis=1)
    df.to_csv(f'{target_path}{sname}.csv', header=True, index=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Trading session preparation')
    parser.add_argument('--date', help='today')
    parser.add_argument('--path', help='today', default='./strategy/')

    args = parser.parse_args()
    run(args)

    print('Dene session preparation. Ready to trade')