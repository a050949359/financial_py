#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from utils.config import ConfigValidationError
from utils.config import get_dataset_config
from utils.config import get_dataset_json_path
from utils.config import get_raw_config
from utils.config import get_system_config
from utils.config import validate_config
from utils.logging import cleanup_old_logs as cleanup_old_logs_impl
from utils.logging import configure_daily_file_logger


def cleanup_old_logs(log_dir: Path, retention_days: int) -> int:
    return cleanup_old_logs_impl(log_dir, retention_days)


def setup_logging(
    logger_name: str | None = None,
) -> Path:
    config = get_system_config()
    return configure_daily_file_logger(config.log_path, config.debug, logger_name)


def create_sqlite_database_file() -> Path:
    config = get_system_config()
    if config.db_driver != "sqlite":
        raise ValueError(f"不支援的 db_driver: {config.db_driver}")

    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.db_path):
        pass
    return config.db_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="依 config 建立 SQLite 資料庫檔案")
    parser.add_argument(
        "--clean-log",
        action="store_true",
        help="依 log_retention_days 清理過期 log 檔案",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="驗證 config.toml 內容是否可用",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="搭配 --validate-config 使用，只驗證指定 dataset",
    )
    parser.add_argument(
        "--print-dataset-json-path",
        default=None,
        help="輸出指定 dataset 的 JSON 路徑",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.print_dataset_json_path:
        print(get_dataset_json_path(args.print_dataset_json_path))
        return

    if args.validate_config:
        validate_config(args.dataset)
        if args.dataset:
            print(f"config ok: {args.dataset}")
        else:
            print("config ok")
        return

    if args.clean_log:
        config = get_system_config()
        config.log_path.mkdir(parents=True, exist_ok=True)
        removed_count = cleanup_old_logs(config.log_path, config.log_retention_days)
        print(f"removed {removed_count} log files from {config.log_path}")
        return

    db_path = create_sqlite_database_file()
    print(db_path)


if __name__ == "__main__":
    try:
        main()
    except ConfigValidationError as exc:
        raise SystemExit(str(exc)) from exc