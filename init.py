#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timedelta
import logging
from pathlib import Path
import sqlite3
import tomllib


CONFIG_FILE_NAME = "config.toml"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / CONFIG_FILE_NAME


@dataclass(frozen=True)
class OpenDataConfig:
    config_path: Path
    project_root: Path
    db_driver: str
    db_path: Path
    source_dir: Path
    log_path: Path
    log_retention_days: int
    debug: bool


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


def setup_logging(
    config_path: Path | None = None,
    logger_name: str | None = None,
) -> Path:
    config = load_opendata_config(config_path)
    log_level = logging.INFO if config.debug else logging.ERROR
    config.log_path.mkdir(parents=True, exist_ok=True)
    log_file_name = f"{date.today():%Y%m%d}.log"
    log_file_path = config.log_path / log_file_name
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


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    config_path: Path
    project_root: Path
    api_endpoint: str
    api_url: str
    schema_path: Path
    table_name: str
    json_name: str
    json_path: Path


def find_config_path(start_path: Path | None = None) -> Path:
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH

    start = (start_path or Path(__file__)).resolve()
    search_roots = [start.parent] if start.is_file() else [start]
    search_roots.append(Path.cwd().resolve())

    for root in search_roots:
        current = root
        while True:
            candidate = current / CONFIG_FILE_NAME
            if candidate.exists():
                return candidate
            if current.parent == current:
                break
            current = current.parent

    raise FileNotFoundError(f"找不到 {CONFIG_FILE_NAME}")


def _resolve_path(project_root: Path, value: str, fallback: str) -> Path:
    raw = Path(value or fallback)
    return raw if raw.is_absolute() else project_root / raw


def _load_system_config(config: dict) -> dict:
    return config.get("system", {})


def _parse_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def load_opendata_config(config_path: Path | None = None) -> OpenDataConfig:
    resolved_config_path = (config_path or find_config_path()).resolve()
    project_root = resolved_config_path.parent

    with resolved_config_path.open("rb") as file_handle:
        config = tomllib.load(file_handle)

    open_data_config = _load_system_config(config)

    db_driver = open_data_config.get("db_driver", "sqlite")

    return OpenDataConfig(
        config_path=resolved_config_path,
        project_root=project_root,
        db_driver=db_driver,
        db_path=_resolve_path(
            project_root,
            open_data_config.get("db_path", ""),
            "OpenData/database/twse.db",
        ),
        source_dir=_resolve_path(
            project_root,
            open_data_config.get("source_dir", ""),
            "Source",
        ),
        log_path=_resolve_path(
            project_root,
            open_data_config.get("log_path", ""),
            "log",
        ),
        log_retention_days=int(open_data_config.get("log_retention_days", 30)),
        debug=_parse_bool(open_data_config.get("debug", False)),
    )


def load_dataset_config(
    dataset_name: str,
    config_path: Path | None = None,
    *,
    default_api_endpoint: str,
    default_schema_path: str,
    default_table_name: str,
    default_json_name: str,
) -> DatasetConfig:
    resolved_config_path = (config_path or find_config_path()).resolve()
    project_root = resolved_config_path.parent

    with resolved_config_path.open("rb") as file_handle:
        config = tomllib.load(file_handle)

    open_data_config = _load_system_config(config)
    dataset_config = config.get(dataset_name, {})
    api_endpoint = dataset_config.get("api_endpoint", default_api_endpoint)
    if not api_endpoint.startswith("/"):
        api_endpoint = f"/{api_endpoint}"

    json_name = dataset_config.get("json_name", default_json_name)
    source_dir = _resolve_path(
        project_root,
        open_data_config.get("source_dir", ""),
        "Source",
    )

    return DatasetConfig(
        name=dataset_name,
        config_path=resolved_config_path,
        project_root=project_root,
        api_endpoint=api_endpoint,
        api_url=f"https://openapi.twse.com.tw/v1{api_endpoint}",
        schema_path=_resolve_path(
            project_root,
            dataset_config.get("schema_path", ""),
            default_schema_path,
        ),
        table_name=dataset_config.get("table_name", default_table_name),
        json_name=json_name,
        json_path=source_dir / json_name,
    )


def create_sqlite_database_file(config_path: Path | None = None) -> Path:
    config = load_opendata_config(config_path)
    if config.db_driver != "sqlite":
        raise ValueError(f"不支援的 db_driver: {config.db_driver}")

    config.db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(config.db_path):
        pass
    return config.db_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="依 config 建立 SQLite 資料庫檔案")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="config.toml 路徑",
    )
    parser.add_argument(
        "--clean-log",
        action="store_true",
        help="依 log_retention_days 清理過期 log 檔案",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.clean_log:
        config = load_opendata_config(args.config)
        config.log_path.mkdir(parents=True, exist_ok=True)
        removed_count = cleanup_old_logs(config.log_path, config.log_retention_days)
        print(f"removed {removed_count} log files from {config.log_path}")
        return

    db_path = create_sqlite_database_file(args.config)
    print(db_path)


if __name__ == "__main__":
    main()