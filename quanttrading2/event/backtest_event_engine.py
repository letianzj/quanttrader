#!/usr/bin/env python
# -*- coding: utf-8 -*-
from queue import Queue, Empty
from ..event.event import EventType
from threading import Thread
from collections import defaultdict


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

        # handler for all events
        self._generalHandlers = []

    # ------------------------------------ public functions -----------------------------#
    def run(self):
        """
        run backtest
        """
        print("Running Backtest...")
        while (self._active):
            try:
                event = self._queue.get(False)
            except Empty:   # throw good exception
                try:
                    event = self._datafeed.stream_next()
                    self._queue.put(event)
                except:
                    # stop if not able to next event
                    self._active = False
            else:  # not empty
                try:
                    # call event handlers
                    if event.event_type in self._handlers:
                        [handler(event) for handler in self._handlers[event.event_type]]

                    if self._generalHandlers:
                        [handler(event) for handler in self._generalHandlers]
                except Exception as e:
                    print("Error {0}".format(str(e.args[0])).encode("utf-8"))


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

    def register_general_handler(self, handler):
        """
        register general handler
        """
        if handler not in self._generalHandlers:
            self._generalHandlers.append(handler)

    def unregister_general_handler(self, handler):
        """
        unregister general handler
        """
        if handler in self._generalHandlers:
            self._generalHandlers.remove(handler)

    # -------------------------------- end of public functions -----------------------------#
