# quanttrading2

Backtest and live trading in 100% pure Python, open sourced [on GitHub](https://github.com/letianzj/quanttrading2).

### Backtest

[Backtest code structure](https://letianzj.github.io/quanttrading-backtest.html)

[Backtests examples](https://github.com/letianzj/QuantResearch/tree/master/backtest)

### Live trading

[Live Trading code structure](https://letianzj.github.io/live-trading-ib-native-python.html)

__Prerequisite__: download and install IB TWS or IB Gateway; enable API connection as described [here](https://interactivebrokers.github.io/tws-api/initial_setup.html).

__Installation__

Step 1

```shell
pip install quanttrading2
```

Alternatively, download or git the source code and include unzipped path in PYTHONPATH environment variable.

step 2

download and unzip [starter_kit](https://github.com/letianzj/quanttrading2/blob/master/examples/starter_kit.zip) in examples folder.

step 3
```shell
cd runtime      # from unzip starter_kit
python live_engine.py
```

![gui](https://github.com/letianzj/quanttrading2/blob/master/examples/gui.png)

Why quantttrading2? There exists [QuantTrading(1)](https://github.com/letianzj/QuantTrading) in C#. So this one in Python gets suffix 2.

**DISCLAIMER**
Open source, free to use, free to contribute, use at own risk. No promise of future profits nor responsibility of future loses.