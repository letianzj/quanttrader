#!/usr/bin/env python
# -*- coding: utf-8 -*-
from queue import Queue, Empty
from threading import Thread
from collections import defaultdict


class LiveEventEngine(object):
    """
    Event queue + a thread to dispatch events
    """
    def __init__(self):
        """
        Initialize dispatcher thread and handler function list
        """
        # if the dispatcher is active
        self._active = False

        # event queue
        self._queue = Queue()

        # dispatcher thread
        self._thread = Thread(target=self._run)

        # event handlers list, specific event --> handler dict
        self._handlers = defaultdict(list)

    #------------------------------- private functions ---------------------------#
    def _run(self):
        """
        run dispatcher
        """
        while self.__active == True:
            try:
                event = self._queue.get(block=True, timeout=1)
                # call event handlers
                if event.event_type in self._handlers:
                    [handler(event) for handler in self._handlers[event.event_type]]

            except Empty:
                pass
                #print('Empty event queue')
            except Exception as e:
                print("Error {0}".format(str(e.args[0])).encode("utf-8"))

    #----------------------------- end of private functions ---------------------------#

    #------------------------------------ public functions -----------------------------#
    def start(self, timer=True):
        """
        start the dispatcher thread
        """
        self.__active = True
        self._thread.start()

    def stop(self):
        """
        stop the dispatcher thread
        """
        self.__active = False
        self._thread.join()

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