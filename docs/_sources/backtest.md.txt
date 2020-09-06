## Backtest

[This document](https://letianzj.github.io/quanttrading-backtest.html) explains quanttrader backtest framework and code structure.

[This repository](https://github.com/letianzj/QuantResearch/tree/master/backtest) contains examples of some classical strategies and their Sharpe ratios, as well as grid-search based parameter optimization. The backtest is designed to be working together with the [pyfolio](https://github.com/quantopian/pyfolio) library.

One distinctive design in backtest is that it fills market order right away instead of filling against tomorrow's open price. After all, in the daily bar setting, it is better to send out order at 15:59:59 than waiting overnight for next day' open. If you disagree, simply save the market order similar to limit or stop order in the BacktestBrokerage class and then fill it on next tick.

Currently backtest accepts three data feeds.

* Daily bar or intraday bar from Yahoo Finance. See [here](https://medium.com/@letian.zj/free-historical-market-data-download-in-python-74e8edd462cf?source=friends_link&sk=5af814910524a593353ed3146290d50e) for how to download.

* Historical intraday bar from Interactive Brokers. Use [this script](https://github.com/letianzj/quanttrader/blob/master/examples/download_historical_data_from_ib.py) to download.

* Live tick recorded from live trading session. [This video](https://t.co/rXdW8EIbWw?amp=1) demonstrates how to do it in live session.

It is possible to load your own data source by following the above examples.

