#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import sqlite3
from time import perf_counter
import sys
from typing import Any, Callable, Iterable


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from init import create_sqlite_database_file, get_dataset_config, get_system_config, setup_logging


RowTransform = Callable[[dict[str, Any]], dict[str, str]]
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ImportTarget:
    dataset_name: str
    schema_path: Path
    table_name: str
    json_path: Path
    field_mapping: dict[str, str] | None
    insert_columns: tuple[str, ...]
    conflict_columns: tuple[str, ...]
    row_transform: RowTransform | None
    description: str


def create_import_target(
    *,
    dataset_name: str,
    field_mapping: dict[str, str] | None,
    conflict_columns: tuple[str, ...],
    description: str,
    insert_columns: tuple[str, ...] | None = None,
    row_transform: RowTransform | None = None,
) -> ImportTarget:
    if field_mapping is None and insert_columns is None:
        raise ValueError("field_mapping 與 insert_columns 不能同時省略")
    if not conflict_columns:
        raise ValueError("conflict_columns 不能為空")

    dataset_config = get_dataset_config(dataset_name)
    return ImportTarget(
        dataset_name=dataset_name,
        schema_path=dataset_config.schema_path,
        table_name=dataset_config.table_name,
        json_path=dataset_config.json_path,
        field_mapping=field_mapping,
        insert_columns=insert_columns or tuple(field_mapping.values()),
        conflict_columns=conflict_columns,
        row_transform=row_transform,
        description=description,
    )


def build_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="SQLite 資料庫檔案路徑",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=None,
        help="初始化 SQL 檔案路徑",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=None,
        help="來源 JSON 檔案路徑",
    )
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="只初始化 SQLite schema，不匯入資料",
    )
    return parser


def init_database(connection: sqlite3.Connection, schema_path: Path) -> None:
    sql = schema_path.read_text(encoding="utf-8")
    connection.executescript(sql)


def load_rows(input_json: Path) -> list[dict[str, Any]]:
    payload = json.loads(input_json.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("來源 JSON 格式不是陣列")
    return payload


def normalize_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def normalize_row(
    row: dict[str, Any],
    field_mapping: dict[str, str] | None,
    row_transform: RowTransform | None = None,
) -> dict[str, str]:
    if row_transform is not None:
        return row_transform(row)
    if field_mapping is None:
        raise ValueError("未提供 row_transform 時必須設定 field_mapping")

    normalized: dict[str, str] = {}
    for source_key, target_key in field_mapping.items():
        normalized[target_key] = normalize_value(row.get(source_key, ""))
    return normalized


def build_upsert_sql(table_name: str, insert_columns: list[str], conflict_columns: tuple[str, ...]) -> str:
    placeholders = ", ".join(f":{column}" for column in insert_columns)
    conflict_column_set = set(conflict_columns)
    assignments = ", ".join(
        f"{column} = excluded.{column}"
        for column in insert_columns
        if column not in conflict_column_set
    )
    columns = ", ".join(insert_columns)
    conflict_target = ", ".join(conflict_columns)
    update_clause = "imported_at = CURRENT_TIMESTAMP"
    if assignments:
        update_clause = f"{assignments}, {update_clause}"
    return (
        f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) "
        f"ON CONFLICT({conflict_target}) DO UPDATE SET {update_clause}"
    )


def upsert_rows(
    connection: sqlite3.Connection,
    rows: Iterable[dict[str, Any]],
    *,
    field_mapping: dict[str, str] | None,
    insert_columns: tuple[str, ...],
    table_name: str,
    conflict_columns: tuple[str, ...],
    row_transform: RowTransform | None = None,
) -> int:
    normalized_rows = [normalize_row(row, field_mapping, row_transform) for row in rows]
    if not normalized_rows:
        return 0

    connection.executemany(
        build_upsert_sql(table_name, list(insert_columns), conflict_columns),
        normalized_rows,
    )

    return len(normalized_rows)


def _prepare_import_context(args: argparse.Namespace, dataset_name: str) -> tuple[Any, Any, Path, Path, Path]:
    setup_logging(LOGGER.name)
    system_config = get_system_config()
    dataset_config = get_dataset_config(dataset_name)

    db_path = args.db_path or system_config.db_path
    schema_path = args.schema_path or dataset_config.schema_path
    input_json = args.input_json or dataset_config.json_path

    if db_path.resolve() == system_config.db_path.resolve():
        create_sqlite_database_file()
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(db_path):
            pass

    return system_config, dataset_config, db_path, schema_path, input_json


def _run_import_rows(
    connection: sqlite3.Connection,
    rows: list[dict[str, Any]],
    *,
    target: ImportTarget,
    table_name: str,
) -> int:
    return upsert_rows(
        connection,
        rows,
        field_mapping=target.field_mapping,
        insert_columns=target.insert_columns,
        table_name=table_name,
        conflict_columns=target.conflict_columns,
        row_transform=target.row_transform,
    )


def run_import(args: argparse.Namespace, target: ImportTarget) -> tuple[int, Path]:
    system_config, dataset_config, db_path, schema_path, input_json = _prepare_import_context(args, target.dataset_name)

    stage = "open_connection"
    rows_count = 0

    try:
        with sqlite3.connect(db_path) as connection:
            stage = "init_schema"
            init_database(connection, schema_path)

            if args.init_schema:
                return 0, db_path

            stage = "load_rows"
            rows = load_rows(input_json)
            rows_count = len(rows)

            stage = "upsert_rows"
            started_at = perf_counter()
            imported = _run_import_rows(
                connection,
                rows,
                target=target,
                table_name=dataset_config.table_name,
            )

            stage = "commit"
            connection.commit()

            if system_config.debug:
                elapsed_seconds = perf_counter() - started_at
                LOGGER.info(
                    "SQLite import finished: dataset=%s table=%s rows=%s elapsed_seconds=%.3f",
                    target.dataset_name,
                    dataset_config.table_name,
                    imported,
                    elapsed_seconds,
                )
    except Exception as exc:
        LOGGER.exception(
            "匯入流程失敗: dataset=%s stage=%s error_type=%s table=%s rows_count=%s db_path=%s schema_path=%s input_json=%s",
            target.dataset_name,
            stage,
            type(exc).__name__,
            dataset_config.table_name,
            rows_count,
            db_path,
            schema_path,
            input_json,
        )
        raise

    return imported, db_path


def run_import_rows(args: argparse.Namespace, target: ImportTarget, rows: list[dict[str, Any]]) -> tuple[int, Path]:
    system_config, dataset_config, db_path, schema_path, input_json = _prepare_import_context(args, target.dataset_name)

    stage = "open_connection"
    rows_count = len(rows)

    try:
        with sqlite3.connect(db_path) as connection:
            stage = "init_schema"
            init_database(connection, schema_path)

            if args.init_schema:
                return 0, db_path

            stage = "upsert_rows"
            started_at = perf_counter()
            imported = _run_import_rows(
                connection,
                rows,
                target=target,
                table_name=dataset_config.table_name,
            )

            stage = "commit"
            connection.commit()

            if system_config.debug:
                elapsed_seconds = perf_counter() - started_at
                LOGGER.info(
                    "SQLite import finished: dataset=%s table=%s rows=%s elapsed_seconds=%.3f",
                    target.dataset_name,
                    dataset_config.table_name,
                    imported,
                    elapsed_seconds,
                )
    except Exception as exc:
        LOGGER.exception(
            "匯入流程失敗: dataset=%s stage=%s error_type=%s table=%s rows_count=%s db_path=%s schema_path=%s input_json=%s",
            target.dataset_name,
            stage,
            type(exc).__name__,
            dataset_config.table_name,
            rows_count,
            db_path,
            schema_path,
            input_json,
        )
        raise

    return imported, db_path