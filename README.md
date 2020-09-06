# quanttrader

Welcome to quanttrader, a pure python-based event-driven backtest and live trading package for quant traders.

The source code is completely open-sourced [here on GitHub](https://github.com/letianzj/quanttrader). The package is published [here on pypi](https://pypi.org/project/quanttrader/) and is ready to be pip installed. The document is hosted [here on readthedocs](https://quanttrader.readthedocs.io/).

In most cases, a backtest strategy can be directly used for live trade by simply switching to live brokerage. A control window is provided to monitor live trading sessions for each strategy separately and the portfolio as a whole.

### Backtest

[Backtest code structure](https://letianzj.github.io/quanttrading-backtest.html)

[Backtests examples](https://github.com/letianzj/QuantResearch/tree/master/backtest)

### Live trading

[Live Trading demo video](https://youtu.be/CrsrTxqiXNY)

[Live Trading code structure](https://letianzj.github.io/live-trading-ib-native-python.html)

__Prerequisite__: download and install IB TWS or IB Gateway; enable API connection as described [here](https://interactivebrokers.github.io/tws-api/initial_setup.html).

__Installation__

Step 1

```shell
pip install quanttrader
```

Alternatively, download or git the source code and include unzipped path in PYTHONPATH environment variable.

step 2

Download [live_engine.py](https://github.com/letianzj/quanttrader/blob/master/examples/live_engine.py), [config_live.yaml](https://github.com/letianzj/quanttrader/blob/master/examples/config_live.yaml), [order_per_interval_strategy.py](order_per_interval_strategy.py) by clicking Raw button, right clicking save as, and then change the file extension to .py or .yaml.

step 3
```shell
cd where_the_files_are_saved
python live_engine.py
```

__Instruments Supported and Example__

* __Stock__: AMZN STK SMART
* __Foreign Exchange__: EURGBP CASH IDEALPRO
* __Futures__: ESM9 FUT GLOBEX
* __Options on Stock__: AAPL OPT 20201016 128.75 C SMART
* __Options on Futures__: ES FOP 20200911 3450 C 50 GLOBEX
* __Comdty__: XAUUSD CMDTY SMART

__Order Type Supported__

Basic order types. See [IB Doc](http://interactivebrokers.github.io/tws-api/basic_orders.html) for details.
* Auction
* Auction Limit
* Market
* Market If Touched
* Market On Close
* Market On Open
* Market to Limit
* Limit Order
* Limit if Touched
* Limit on Close
* Limit on Open
* Stop
* Stop Limit
* Trailing Stop
* Trailing Stop Limit


![gui](https://github.com/letianzj/quanttrader/blob/master/examples/gui.png)


**DISCLAIMER**
Open source, free to use, free to contribute, use at own risk. No promise of future profits nor responsibility of future loses.