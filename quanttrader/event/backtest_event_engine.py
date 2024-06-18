#!/usr/bin/env python
# -*- coding: utf-8 -*-
# from multiprocessing import Queue
import logging
from collections import defaultdict
from queue import Empty, Queue
from typing import Any, Callable

from ..data.backtest_data_feed import BacktestDataFeed
from .event import Event, EventType

_logger = logging.getLogger(__name__)


__all__ = ["BacktestEventEngine"]


class BacktestEventEngine(object):
    """
    Event queue + a while loop to dispatch events
    """

    def __init__(self, datafeed: BacktestDataFeed) -> None:
        """
        Initialize handler function list
        """
        # if the data feed is active
        self._active = True

        # event queue
        self._queue = Queue()  # type: ignore

        # pull from backtest data feed
        self._datafeed = datafeed

        # event handlers list, dict: specific event key --> Callable[Event]
        self._handlers: defaultdict[EventType, list[Callable[[Any], None]]] = (
            defaultdict(list)
        )

    # ------------------------------------ public functions -----------------------------#
    def run(self, nSteps: int = -1) -> None:
        """
        run backtest,
        if nSteps = -1, run to the end; else run nSteps
        """
        _logger.info("Running Backtest...")
        nstep = 0
        while self._active:
            try:
                event = self._queue.get(False)
            except Empty:  # throw good exception
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

    def put(self, event: Event) -> None:
        """
        put event in the queue; call from outside
        """
        self._queue.put(event)

    def register_handler(
        self, type_: EventType, handler: Callable[[Any], None]
    ) -> None:
        """
        register handler/subscriber
        """
        handler_list = self._handlers[type_]

        if handler not in handler_list:
            handler_list.append(handler)

    def unregister_handler(
        self, type_: EventType, handler: Callable[[Any], None]
    ) -> None:
        """
        unregister handler/subscriber
        """
        handler_list = self._handlers[type_]

        if handler in handler_list:
            handler_list.remove(handler)

        if not handler_list:
            del self._handlers[type_]

    # -------------------------------- end of public functions -----------------------------#
