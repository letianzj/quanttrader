#!/usr/bin/env python
# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod


class AbstractTradeRecorder(object):
    """
    transaction recorder
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def record_trade(self, fill):
        """
        logs fill event
        """
        raise NotImplementedError("Should implement record_trade()")
