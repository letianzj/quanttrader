#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
import argparse
import yaml
from PyQt5 import QtCore, QtWidgets, QtGui
from quanttrading2.gui.ui_main_window import MainWindow
import atexit
from signal import signal, SIGINT, SIG_DFL
from os import kill
from multiprocessing import Process
import logging

# https://stackoverflow.com/questions/4938723/what-is-the-correct-way-to-make-my-pyqt-application-quit-when-killed-from-the-co
signal(SIGINT, SIG_DFL)


def main(config_file):
    config = None
    strategy_dict = {}
    try:
        # path = os.path.abspath(os.path.dirname(__file__))
        # config_file = os.path.join(path, 'config.yaml')
        with open(config_file, encoding='utf8') as fd:
            config = yaml.safe_load(fd)
    except IOError:
        print("config.yaml is missing")

    _logger = logging.getLogger('quanttrading2')
    _logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    _logger.addHandler(handler)

    i = 1
    for s, v in config['strategy'].items():
        try:
            exec(open(v['path']).read(), locals())
            exec(f'strat_{i}=locals()["{s}"]()')
            exec(f'strategy_dict["{s}"]=strat_{i}')
            i += 1
        except:
            pass

    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow(config, strategy_dict)

    if config['theme'] == 'dark':
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    mainWindow.show()      # .showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Live Engine')
    parser.add_argument('-f', '--config_file', dest = 'config_file', default='./config_live.yaml', help='config yaml file')
    args = parser.parse_args()

    main(args.config_file)