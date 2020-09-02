# quanttrading2

Backtest and live trading in 100% pure Python, open sourced [on GitHub](https://github.com/letianzj/quanttrading2).

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
pip install quanttrading2
```

Alternatively, download or git the source code and include unzipped path in PYTHONPATH environment variable.

step 2

Download [live_engine.py](https://github.com/letianzj/quanttrading2/blob/master/examples/live_engine.py), [config_live.yaml](https://github.com/letianzj/quanttrading2/blob/master/examples/config_live.yaml), [order_per_interval_strategy.py](order_per_interval_strategy.py) by clicking Raw button, right clicking save as, and then change the file extension to .py or .yaml.

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


![gui](https://github.com/letianzj/quanttrading2/blob/master/examples/gui.png)

Why quantttrading2? There exists [QuantTrading(1)](https://github.com/letianzj/QuantTrading) in C#. So this one in Python gets suffix 2.

**DISCLAIMER**
Open source, free to use, free to contribute, use at own risk. No promise of future profits nor responsibility of future loses.