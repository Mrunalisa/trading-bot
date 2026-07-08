"""
Central logging configuration.

Every API request, response, and error is written to a rotating log
file so that a full audit trail of trading activity is kept, without
flooding the console during interactive use.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_file: str = "logs/trading_bot.log", level: int = logging.INFO) -> logging.Logger:
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(level)
    logger.handlers.clear()  # avoid duplicate handlers if setup_logging is called twice

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)  # keep stdout clean; CLI prints its own summaries
    logger.addHandler(console_handler)

    return logger
