#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import logging
import time
from signal import SIG_DFL, SIGINT, signal

from ibapi.contract import Contract

from quanttrader.brokerage.ib_brokerage import InteractiveBrokers
from quanttrader.event.live_event_engine import LiveEventEngine

signal(SIGINT, SIG_DFL)


def log_event_handler(log_event):
    print(f"{log_event.timestamp}: {log_event.content}")


def run(conid):
    _logger = logging.getLogger("quanttrader")
    _logger.setLevel(logging.DEBUG)
    handler1 = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler1.setFormatter(formatter)
    _logger.addHandler(handler1)

    events_engine = LiveEventEngine()
    tick_event_engine = LiveEventEngine()
    broker = InteractiveBrokers(events_engine, tick_event_engine, "DU0001")
    broker.reqid = 5000
    # events_engine.register_handler(EventType.LOG, log_event_handler)
    events_engine.start()
    tick_event_engine.start()

    broker.connect("127.0.0.1", 7497, 0)
    time.sleep(5)  # 5 seconds

    contract = Contract()
    contract.conId = conid

    broker.api.reqContractDetails(broker.reqid, contract)

    time.sleep(5)  # 5 seconds
    broker.disconnect()
    events_engine.stop()
    tick_event_engine.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Contract Details")
    parser.add_argument("--conid", help="conid e.g. 383974324", required=True)

    args = parser.parse_args()
    run(args.conid)
