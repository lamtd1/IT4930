"""
Logging configuration for the book retrieval benchmark.

Provides a single ``setup_logging`` function that configures both a
console (StreamHandler) and a rotating file handler.  Call this once
at application startup before importing any other modules that log.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path | str = Path("logs"),
    log_filename: str = "benchmark.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """
    Configure root logger with a console handler and a rotating file handler.

    Args:
        log_level:     Logging level string, e.g. ``"DEBUG"``, ``"INFO"``.
        log_dir:       Directory where log files are written.  Created if needed.
        log_filename:  Name of the log file inside ``log_dir``.
        max_bytes:     Maximum size of a single log file before rotation.
        backup_count:  Number of rotated backup files to retain.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_filename

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Formatter shared by all handlers
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler – write INFO+ to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    # Rotating file handler – captures everything at DEBUG level
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # let handlers filter by their own level

    # Avoid adding duplicate handlers if called more than once (e.g., in tests)
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    else:
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a named child logger.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A ``logging.Logger`` instance.
    """
    return logging.getLogger(name)
