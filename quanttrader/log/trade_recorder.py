#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import os
import csv
import logging

_logger = logging.getLogger(__name__)

from .trade_recorder_base import AbstractTradeRecorder


class ExampleTradeRecorder(AbstractTradeRecorder):
    """
    A basic compliance module which writes trades to a
    CSV file in the output directory.
    """

    def __init__(self, output_dir):
        """
        Wipe the existing trade log for the day, leaving only
        the headers in an empty CSV.

        It allows for multiple backtests to be run
        in a simple way, but quite likely makes it unsuitable for
        a production environment that requires strict record-keeping.
        """
        self.output_dir = output_dir
        # Remove the previous CSV file
        today = datetime.datetime.utcnow().date()
        self.csv_filename = "tradelog_" + today.strftime("%Y-%m-%d") + ".csv"

        try:
            fname = os.path.expanduser(os.path.join(self.output_dir, self.csv_filename))
            os.remove(fname)
        except (IOError, OSError):
            _logger.error("No tradelog files to clean.")

        # Write new file header
        fieldnames = [
            "timestamp", "ticker",
            "action", "quantity",
            "exchange", "price",
            "commission"
        ]
        fname = os.path.expanduser(os.path.join(self.output_dir, self.csv_filename))
        with open(fname, 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

    def record_trade(self, fill):
        """
        Append all details about the FillEvent to the CSV trade log.
        """
        fname = os.path.expanduser(os.path.join(self.output_dir, self.csv_filename))
        with open(fname, 'a') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                fill.timestamp, fill.ticker,
                fill.action, fill.quantity,
                fill.exchange, round(fill.price, 4),
                round(fill.commission, 4)
            ])