"""Centralised logging configuration for FitFetch."""

from __future__ import annotations

import logging
import os


def setup_logging() -> logging.Logger:
    """Configure the root logger and return the application logger."""
    log_level = logging.DEBUG if os.environ.get("FITFETCH_DEBUG") else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("FitFetch")


logger = setup_logging()
