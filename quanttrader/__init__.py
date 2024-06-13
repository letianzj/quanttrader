#!/usr/bin/env python
# -*- coding: utf-8 -*-
from .version import VERSION as __version__

# https://docs.python-guide.org/writing/logging/
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
