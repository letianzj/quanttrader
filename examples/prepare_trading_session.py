#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse

import pandas as pd
import yaml


def run(target_path, config_file):
    with open(config_file, encoding="utf8") as fd:
        config = yaml.safe_load(fd)

    # DualThrustStrategy
    # 1. config
    config["strategy"]["DualThrustStrategy"]["params"]["G"] = 20

    # 2. data
    sname = "dual_thrust"
    index = pd.date_range("1/1/2020", periods=100, freq="T")
    s1 = pd.Series(range(100), index=index)
    s1.name = "price"
    s2 = pd.Series(range(100), index=index)
    s2.name = "volume"
    df = pd.concat([s1, s2], axis=1)
    df.to_csv(f"{target_path}{sname}.csv", header=True, index=True)

    # save config
    with open(config_file, "w", encoding="utf-8") as file:
        yaml.dump(config, file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trading session preparation")
    parser.add_argument("--date", help="today")
    parser.add_argument(
        "-f",
        "--config_file",
        dest="config_file",
        default="./config_live.yaml",
        help="config yaml file",
    )
    parser.add_argument(
        "-p", "--path", dest="path", default="./strategy/", help="data path"
    )

    args = parser.parse_args()
    run(args.path, args.config_file)

    print("Dene session preparation. Ready to trade")
