#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import sqlite3
import tomllib

from utils.logging_utils import cleanup_old_logs as cleanup_old_logs_impl
from utils.logging_utils import configure_daily_file_logger


CONFIG_FILE_NAME = "config.toml"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / CONFIG_FILE_NAME


@dataclass(frozen=True)
class SystemConfig:
    config_path: Path
    project_root: Path
    db_driver: str
    db_path: Path
    source_dir: Path
    log_path: Path
    log_retention_days: int
    debug: bool


def cleanup_old_logs(log_dir: Path, retention_days: int) -> int:
    return cleanup_old_logs_impl(log_dir, retention_days)


def setup_logging(
    config_path: Path | None = None,
    logger_name: str | None = None,
) -> Path:
    config = get_system_config(config_path)
    return configure_daily_file_logger(config.log_path, config.debug, logger_name)


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


@lru_cache(maxsize=16)
def _load_config_dict(resolved_config_path: Path) -> dict:
    with resolved_config_path.open("rb") as file_handle:
        return tomllib.load(file_handle)


@lru_cache(maxsize=16)
def _resolve_config_path(config_path: Path | None = None) -> Path:
    return (config_path or find_config_path()).resolve()


def get_raw_config(config_path: Path | None = None) -> dict:
    resolved_config_path = _resolve_config_path(config_path)
    return _load_config_dict(resolved_config_path)


def get_system_config(config_path: Path | None = None) -> SystemConfig:
    resolved_config_path = _resolve_config_path(config_path)
    project_root = resolved_config_path.parent
    config = get_raw_config(resolved_config_path)

    system_config = _load_system_config(config)
    db_driver = system_config.get("db_driver", "sqlite")

    return SystemConfig(
        config_path=resolved_config_path,
        project_root=project_root,
        db_driver=db_driver,
        db_path=_resolve_path(
            project_root,
            system_config.get("db_path", ""),
            "database/twse.db",
        ),
        source_dir=_resolve_path(
            project_root,
            system_config.get("source_dir", ""),
            "Source",
        ),
        log_path=_resolve_path(
            project_root,
            system_config.get("log_path", ""),
            "log",
        ),
        log_retention_days=int(system_config.get("log_retention_days", 30)),
        debug=_parse_bool(system_config.get("debug", False)),
    )


def get_dataset_config(
    dataset_name: str,
    config_path: Path | None = None,
    *,
    default_api_endpoint: str,
    default_schema_path: str,
    default_table_name: str,
    default_json_name: str,
) -> DatasetConfig:
    resolved_config_path = _resolve_config_path(config_path)
    project_root = resolved_config_path.parent
    config = get_raw_config(resolved_config_path)

    system_config = _load_system_config(config)
    dataset_config = config.get(dataset_name, {})
    api_endpoint = dataset_config.get("api_endpoint", default_api_endpoint)
    if not api_endpoint.startswith("/"):
        api_endpoint = f"/{api_endpoint}"

    json_name = dataset_config.get("json_name", default_json_name)
    source_dir = _resolve_path(
        project_root,
        system_config.get("source_dir", ""),
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
    config = get_system_config(config_path)
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
        config = get_system_config(args.config)
        config.log_path.mkdir(parents=True, exist_ok=True)
        removed_count = cleanup_old_logs(config.log_path, config.log_retention_days)
        print(f"removed {removed_count} log files from {config.log_path}")
        return

    db_path = create_sqlite_database_file(args.config)
    print(db_path)


if __name__ == "__main__":
    main()