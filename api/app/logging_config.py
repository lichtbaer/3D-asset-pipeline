"""Strukturiertes JSON-Logging mit python-json-logger."""

import logging
import os
from logging.handlers import RotatingFileHandler

from pythonjsonlogger import jsonlogger


def setup_logging() -> None:
    """
    Konfiguriert strukturiertes JSON-Logging.
    - Console: INFO, JSON-Format
    - File: ./storage/logs/app.log, rolling max 10MB, 3 Backups
    """
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, log_level, logging.INFO)

    # JSON-Formatter
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super().add_fields(log_record, record, message_dict)
            log_record["level"] = record.levelname
            log_record["logger"] = record.name
            if not log_record.get("timestamp"):
                from datetime import datetime, timezone

                log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
            if record.exc_info:
                log_record["traceback"] = self.formatException(record.exc_info)

    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(logger)s %(message)s"
    )

    # Root-Logger
    root = logging.getLogger()
    root.setLevel(level)

    # Entferne bestehende Handler
    for h in root.handlers[:]:
        root.removeHandler(h)

    # Console-Handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # File-Handler: ./storage/logs/app.log
    from app.config.storage import LOGS_PATH

    logs_dir = LOGS_PATH
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "app.log"

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
