"""Shared utilities for kgout."""

from __future__ import annotations

import logging
import sys

# Default file patterns to ignore during watching
DEFAULT_IGNORE_PATTERNS = (
    "*.ipynb",
    "*.pyc",
    "*.tmp",
    "*.lock",
    "*.log",
    "*.swp",
    "*.swo",
    ".DS_Store",
    "Thumbs.db",
)


def setup_logger(level: int = logging.INFO):
    """Configure the kgout logger with a clean format for notebooks."""
    logger = logging.getLogger("kgout")

    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Compact format: just timestamp + message (no module clutter)
    fmt = logging.Formatter(
        fmt="[kgout %(asctime)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    # Don't propagate to root logger (avoids double-printing in notebooks)
    logger.propagate = False

    return logger
