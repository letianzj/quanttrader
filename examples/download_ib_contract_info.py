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
from ibapi.contract import Contract
from signal import signal, SIGINT, SIG_DFL
from quanttrading2.event.event import EventType
from quanttrading2.event.live_event_engine import LiveEventEngine
from quanttrading2.brokerage.ib_brokerage import InteractiveBrokers

signal(SIGINT, SIG_DFL)

def log_event_handler(log_event):
    print(f'{log_event.timestamp}: {log_event.content}')

def run(args):
    events_engine = LiveEventEngine()
    tick_event_engine = LiveEventEngine()
    broker = InteractiveBrokers(events_engine, tick_event_engine, 'DU0001')
    broker.reqid = 5000
    events_engine.register_handler(EventType.LOG, log_event_handler)
    events_engine.start()
    tick_event_engine.start()

    broker.connect('127.0.0.1', 7497, 0)
    time.sleep(5)  # 5 seconds

    contract = Contract()
    contract.conId = 383974324

    broker.api.reqContractDetails(broker.reqid, contract)

    broker.disconnect()
    events_engine.stop()
    tick_event_engine.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Contract Details')
    parser.add_argument('--conid', help='conid')

    args = parser.parse_args()
    run(args)