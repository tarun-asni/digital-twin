import os
import logging
from concurrent_log_handler import ConcurrentRotatingFileHandler 

def setup_logging():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file_path = os.path.join(log_dir, "app.log")

    log_handler = ConcurrentRotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=10,
        encoding='utf-8'
    )

    formatter = logging.Formatter(
        "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
    )
    log_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if not any(
        isinstance(h, ConcurrentRotatingFileHandler) and h.baseFilename == log_file_path
        for h in root_logger.handlers
    ):
        root_logger.addHandler(log_handler)