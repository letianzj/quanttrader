# quanttrading2

Backtest and live trading in 100% pure Python.

### Backtest

[Backtests Blog](https://letianzj.github.io/quanttrading-backtest.html)

[Backtests examples](https://github.com/letianzj/QuantResearch/tree/master/backtest)

[Param search example](https://github.com/letianzj/QuantResearch/blob/master/backtest/ma_double_cross.py)

### Live trading

```python
# install ib and ib api
download and install IB TWS or IB Gateway
download and install official IB API. https://www.interactivebrokers.com/en/index.php?f=5041
cd TWS API/source/pythonclient
pip install .
config connection https://interactivebrokers.github.io/tws-api/initial_setup.html

# launch live trading
cd examples
python live_engine.py
```

There exists [QuantTrading(1)](https://github.com/letianzj/QuantTrading) in C#. This one with suffix 2 is written in Python.

![gui](https://github.com/letianzj/quanttrading2/blob/master/examples/gui.png)

**DISCLAIMER**
Open source, free to use, free to contribute, use at own risk. No promise of future profits nor responsibility of future loses.