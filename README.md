# quanttrading2

Backtest and live trading in 100% pure Python, open sourced [on GitHub](https://github.com/letianzj/quanttrading2).

### Backtest

[Backtests Blog](https://letianzj.github.io/quanttrading-backtest.html)

[Backtests examples](https://github.com/letianzj/QuantResearch/tree/master/backtest)

[Param search example](https://github.com/letianzj/QuantResearch/blob/master/backtest/ma_double_cross.py)

### Live trading

__Prerequisite__: download and install IB TWS or IB Gateway; enable API connection as described [here](https://interactivebrokers.github.io/tws-api/initial_setup.html).

__Approach one__: using pip install

step 1.a

```shell
pip install quanttrading2
```

step 1.b

download [examples\ive_engine.py](https://github.com/letianzj/quanttrading2/blob/master/examples/live_engine.py) and [examples\config_live.yaml](https://github.com/letianzj/quanttrading2/blob/master/examples/config_live.yaml).

step 1.c
```shell
python live_engine.py
```

__Approach two__: using source code.

step 2.a. download and unzip source code.

step 2.b. include unzipped path in PYTHONPATH environment variable.

step 2.c.
```shell
cd examples
python live_engine.py
```

![gui](https://github.com/letianzj/quanttrading2/blob/master/examples/gui.png)

Why quantttrading2? There exists [QuantTrading(1)](https://github.com/letianzj/QuantTrading) in C#. So this one in Python gets suffix 2.

**DISCLAIMER**
Open source, free to use, free to contribute, use at own risk. No promise of future profits nor responsibility of future loses.