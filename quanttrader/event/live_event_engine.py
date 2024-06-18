#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from collections import defaultdict
from queue import Empty, Queue
from threading import Thread
from typing import Any, Callable

from ..event.event import Event, EventType

_logger = logging.getLogger(__name__)


__all__ = ["LiveEventEngine"]


class LiveEventEngine(object):
    """
    Event queue + a thread to dispatch events
    """

    def __init__(self) -> None:
        """
        Initialize dispatcher thread and handler function list
        """
        # if the dispatcher is active
        self._active = False

        # event queue
        self._queue = Queue()  # type: ignore

        # dispatcher thread
        self._thread = Thread(target=self._run)

        # event handlers list, dict: specific event key --> Callable[Event]
        self._handlers: defaultdict[EventType, list[Callable[[Any], None]]] = (
            defaultdict(list)
        )

    # ------------------------------- private functions ---------------------------#
    def _run(self) -> None:
        """
        run dispatcher
        """
        while self._active:
            try:
                event = self._queue.get(block=True, timeout=1)
                # call event handlers
                if event.event_type in self._handlers:
                    [handler(event) for handler in self._handlers[event.event_type]]
            except Empty:
                pass
            except Exception as e:
                _logger.error(f"Event {event.event_type}, Error {str(e)}")

    # ----------------------------- end of private functions ---------------------------#

    # ------------------------------------ public functions -----------------------------#
    def start(self, timer: bool = True) -> None:
        """
        start the dispatcher thread
        """
        self._active = True
        self._thread.start()

    def stop(self) -> None:
        """
        stop the dispatcher thread
        """
        self._active = False
        self._thread.join()

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
