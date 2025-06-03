from __future__ import annotations
import logging
from typing import Optional

# Ensure central logging is initialised once this module is imported
from app.core.logging_config import init_logging  # noqa: F401


def get_logger(name: Optional[str] = None) -> logging.Logger:  # pragma: no cover
    """Return a logger that is guaranteed to be configured.

    If *name* is omitted, the root "app" logger is returned.  This helper exists so
    that modules can simply do::

        from app.core.logger import get_logger
        logger = get_logger(__name__)
    """
    if name is None:
        name = "app"
    return logging.getLogger(name) 