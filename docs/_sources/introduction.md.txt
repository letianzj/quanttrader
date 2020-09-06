## Introduction

Welcome to quanttrader, a pure python-based event-driven backtest and live trading package for quant traders.

In most cases, a backtest strategy can be directly used for live trade by simply switching to live brokerage. A control window is provided to monitor live trading sessions for each strategy separately and the portfolio as a whole.

The source code is completely open-sourced [here on GitHub](https://github.com/letianzj/quanttrader). The package is published [here on pypi](https://pypi.org/project/quanttrader/) and is ready to be pip installed. The document is hosted [here on readthedocs](https://quanttrader.readthedocs.io/).

This is NOT an ultra-low latency framework that can provide nano-second level executions. The response time, for example, between receiving data from the broker and sending out orders for a pairs-trading strategy that is subscribed to two stock feeds, is in the neighbourhood of milli-seconds. This package is designed mainly for quant traders who do not rely on market-making strategies.

__Disclaimer: This is an open-source library that is free to use, free to contribute but use at OWN risk. It does NOT promise any future profits nor is responsible for any future loses.__

