#!/usr/bin/env python
# -*- coding: utf-8 -*-
# https://docs.python-guide.org/writing/logging/
import logging

from .version import VERSION as __version__

logging.getLogger(__name__).addHandler(logging.NullHandler())
