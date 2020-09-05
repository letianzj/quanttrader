#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import argparse
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from ibapi.contract import Contract
from signal import signal, SIGINT, SIG_DFL
import logging
from quanttrader.event.event import EventType
from quanttrader.event.live_event_engine import LiveEventEngine
from quanttrader.brokerage.ib_brokerage import InteractiveBrokers

signal(SIGINT, SIG_DFL)

def log_event_handler(log_event):
    print(f'{log_event.timestamp}: {log_event.content}')

def run(args):
    _logger = logging.getLogger('quanttrader')
    _logger.setLevel(logging.DEBUG)
    handler1 = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler1.setFormatter(formatter)
    _logger.addHandler(handler1)


    events_engine = LiveEventEngine()
    tick_event_engine = LiveEventEngine()
    broker = InteractiveBrokers(events_engine, tick_event_engine, 'DU0001')
    broker.reqid = 5000
    # events_engine.register_handler(EventType.LOG, log_event_handler)
    events_engine.start()
    tick_event_engine.start()

    broker.connect('127.0.0.1', 7497, 0)
    time.sleep(5)  # 5 seconds

    contract = Contract()
    contract.conId = args.conid

    broker.api.reqContractDetails(broker.reqid, contract)

    broker.disconnect()
    events_engine.stop()
    tick_event_engine.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Contract Details')
    parser.add_argument('--conid', help='conid e.g. 383974324', required=True)

    args = parser.parse_args()
    run(args)