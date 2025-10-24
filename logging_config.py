import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(log_file: str = "logs/ripe_atlas.log"):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger("ripe_atlas")
    logger.setLevel(logging.INFO)  # or DEBUG for more detail

    # Prevent duplicate handlers if setup_logger() is called multiple times
    if logger.handlers:
        return logger

    # rotating file handler (max 5 MB per file, keep 5 backups)
    handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # also show logs in console
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger
