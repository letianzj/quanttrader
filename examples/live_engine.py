#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import importlib
import logging
import os
import sys
from datetime import datetime
from signal import SIG_DFL, SIGINT, signal

import qdarkstyle
import yaml
from PyQt5 import QtGui, QtWidgets

from quanttrader.gui.ui_main_window import MainWindow

# https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co
signal(SIGINT, SIG_DFL)


def main(config_file, instrument_meta_file):
    config = {}
    today = datetime.today().strftime("%Y%m%d")
    try:
        # path = os.path.abspath(os.path.dirname(__file__))
        with open(config_file, encoding="utf8") as fd:
            config = yaml.safe_load(fd)
    except IOError:
        print("config.yaml is missing")
    config["root_path"] = os.getcwd()

    instrument_meta = {}
    try:
        with open(instrument_meta_file, encoding="utf8") as fd:
            instrument_meta = yaml.safe_load(fd)
    except IOError:
        pass

    required_dirs = ["./log/", "./tick/", "./strategy/"]
    for d in required_dirs:
        if not os.path.exists(d):
            os.makedirs(d)

    _logger = logging.getLogger("quanttrader")
    _logger.setLevel(logging.DEBUG)
    handler1 = logging.StreamHandler()
    handler2 = logging.FileHandler(f"./log/{today}.log")
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler1.setFormatter(formatter)
    handler2.setFormatter(formatter)
    _logger.addHandler(handler1)
    _logger.addHandler(handler2)

    _logger2 = logging.getLogger("qtlive")
    _logger2.setLevel(logging.DEBUG)
    _logger2.addHandler(handler1)
    _logger2.addHandler(handler2)

    _logger3 = logging.getLogger("tick_recorder")
    _logger3.setLevel(logging.INFO)
    handler3 = logging.FileHandler(f"./tick/{today}.txt")
    formatter = logging.Formatter("")
    handler3.setFormatter(formatter)
    _logger3.addHandler(handler3)

    strategy_dict = {}
    for _, _, files in os.walk("./strategy"):
        for name in files:
            if "strategy" in name and ".pyc" not in name:
                s = name.replace(".py", "")
                try:
                    module_name = f"strategy.{s}"
                    # import module
                    module = importlib.import_module(module_name)
                    for k in dir(module):
                        if (
                            ("Strategy" in k)
                            and ("Abstract" not in k)
                            and (k in config["strategy"])
                        ):
                            v = getattr(module, k)
                            _strategy = v()
                            _strategy.set_name(k)
                            strategy_dict[k] = _strategy
                except Exception as e:  # pylint: disable=broad-except
                    _logger2.error(f"Unable to load strategy {s}: {str(e)}")

    app = QtWidgets.QApplication(sys.argv)  # pylint: disable=c-extension-no-member
    app.setWindowIcon(
        QtGui.QIcon("gui/image/logo.ico")
    )  # pylint: disable=c-extension-no-member
    main_window = MainWindow(config, instrument_meta, strategy_dict)

    if config["theme"] == "dark":
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    main_window.show()  # .showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Engine")
    parser.add_argument(
        "-f",
        "--config_file",
        dest="config_file",
        default="./config_live.yaml",
        help="config yaml file",
    )
    parser.add_argument(
        "-m",
        "--instrument_meta",
        dest="instrument_meta",
        default="./instrument_meta.yaml",
        help="instrument meta file",
    )
    args = parser.parse_args()

    main(args.config_file, args.instrument_meta)
