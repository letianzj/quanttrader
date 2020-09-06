## Live Trading

[This youtube video](https://t.co/rXdW8EIbWw?amp=1) and [accompanying document](https://letianzj.github.io/live-trading-ib-native-python.html) demonstrates step-by-step how to set up quanttrader for live trading. Currently quanttrader only supports Interactive Brokers.

__Files used for live Trading are__

* [live_engine.py](https://github.com/letianzj/quanttrader/blob/master/examples/live_engine.py) - the main entry point

* [config_live.yaml](https://github.com/letianzj/quanttrader/blob/master/examples/config_live.yaml) - config file for live session

* [instrument_meta.yaml](https://github.com/letianzj/quanttrader/blob/master/examples/instrument_meta.yaml) - meta data for instruments to be traded

* [prepare_trading_session.yaml](https://github.com/letianzj/quanttrader/blob/master/examples/prepare_trading_session.py) - an example to demonstrate how to prepare data and strategy parameters before today's live session
