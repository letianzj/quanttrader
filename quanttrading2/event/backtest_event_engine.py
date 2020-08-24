#!/usr/bin/env python
# -*- coding: utf-8 -*-
from queue import Empty, Queue
# from multiprocessing import Queue
from ..event.event import EventType
from threading import Thread
import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)


class BacktestEventEngine(object):
    """
    Event queue + a while loop to dispatch events
    """

    def __init__(self, datafeed):
        """
        Initialize handler function list
        """
        # if the data feed is active
        self._active = True

        # event queue
        self._queue = Queue()

        # pull from backtest data feed
        self._datafeed = datafeed

        # event handlers list, dict: specific event key --> handler value
        self._handlers = defaultdict(list)

    # ------------------------------------ public functions -----------------------------#
    def run(self, nSteps=-1):
        """
        run backtest,
        if nSteps = -1, run to the end; else run nSteps
        """
        _logger.info("Running Backtest...")
        nstep = 0
        while (self._active):
            try:
                event = self._queue.get(False)
            except Empty:   # throw good exception
                if (nSteps == -1) or (nstep < nSteps):
                    try:
                        event = self._datafeed.stream_next()
                        self._queue.put(event)
                        nstep += 1
                    except:
                        # stop if not able to next event
                        self._active = False
                else:
                    break
            else:  # not empty
                try:
                    # call event handlers
                    if event.event_type in self._handlers:
                        [handler(event) for handler in self._handlers[event.event_type]]

                except Exception as e:
                    logging.error("Error {0}".format(str(e.args[0])).encode("utf-8"))


    def put(self, event):
        """
        put event in the queue; call from outside
        """
        self._queue.put(event)

    def register_handler(self, type_, handler):
        """
        register handler/subscriber
        """
        handlerList = self._handlers[type_]

        if handler not in handlerList:
            handlerList.append(handler)

    def unregister_handler(self, type_, handler):
        """
        unregister handler/subscriber
        """
        handlerList = self._handlers[type_]

        if handler in handlerList:
            handlerList.remove(handler)

        if not handlerList:
            del self._handlers[type_]

    # -------------------------------- end of public functions -----------------------------#
