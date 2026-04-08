#!/usr/bin/env python3

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
import logging
from pathlib import Path


def cleanup_old_logs(log_dir: Path, retention_days: int) -> int:
    if retention_days < 1:
        return 0

    cutoff = datetime.now() - timedelta(days=retention_days)
    removed_count = 0
    for log_file in log_dir.glob("*.log"):
        try:
            modified_time = datetime.fromtimestamp(log_file.stat().st_mtime)
        except FileNotFoundError:
            continue

        if modified_time >= cutoff:
            continue

        log_file.unlink(missing_ok=True)
        removed_count += 1

    return removed_count


def configure_daily_file_logger(
    log_path: Path,
    debug_enabled: bool,
    logger_name: str | None = None,
) -> Path:
    log_level = logging.INFO if debug_enabled else logging.ERROR
    log_path.mkdir(parents=True, exist_ok=True)
    log_file_name = f"{date.today():%Y%m%d}.log"
    log_file_path = log_path / log_file_name
    resolved_log_file_path = log_file_path.resolve()

    target_logger = logging.getLogger(logger_name)
    for handler in list(target_logger.handlers):
        if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename).resolve() == resolved_log_file_path:
            handler.setLevel(log_level)
            target_logger.setLevel(log_level)
            return log_file_path
        if isinstance(handler, logging.FileHandler):
            target_logger.removeHandler(handler)
            handler.close()

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    target_logger.addHandler(file_handler)
    target_logger.propagate = False

    if target_logger.level == logging.NOTSET or target_logger.level > log_level:
        target_logger.setLevel(log_level)

    return log_file_path
