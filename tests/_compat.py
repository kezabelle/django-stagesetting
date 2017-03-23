# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals
from contextlib import contextmanager
import logging

@contextmanager
def patch_logger(logger_name, log_level):
    calls = []
    def replacement(msg, *args, **kwargs):
        calls.append(msg % args)
    logger = logging.getLogger(logger_name)
    orig = getattr(logger, log_level)
    setattr(logger, log_level, replacement)
    try:
        yield calls
    finally:
        setattr(logger, log_level, orig)

