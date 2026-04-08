#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from core.fetcher import OpenDataTarget, initialize_fetch_runtime, request_json, resolve_target, run_fetch
from core.importer import ImportTarget, create_import_target, run_import, build_parser as build_import_parser


DATASET_NAME = "year_report"
REPORT_TYPE = "year"
DEFAULT_API_ENDPOINT = "/exchangeReport/FMNPTK_ALL"
DEFAULT_SCHEMA_PATH = "database/init_year_report.sql"
DEFAULT_TABLE_NAME = "year_reports"
DEFAULT_JSON_NAME = "year_report.json"
PERIOD_FIELD = "Year"
FETCH_DESCRIPTION = "抓取 TWSE 上市證券年報成交資料 OpenAPI"
IMPORT_DESCRIPTION = "初始化並匯入 TWSE 上市證券年報成交資料到 SQLite"
FIELD_MAPPING = {
    "Code": "company_code",
    "Name": "company_name",
    "Year": "report_period",
    "TradeVolume": "trade_volume",
    "TradeValue": "trade_value",
    "Transaction": "transaction_count",
    "HighestPrice": "highest_price",
    "LowestPrice": "lowest_price",
    "AvgClosingPrice": "avg_closing_price",
    "HDate": "high_date",
    "LDate": "low_date",
}
INSERT_COLUMNS = (
    "company_code",
    "company_name",
    "report_period",
    "trade_volume",
    "trade_value",
    "transaction_count",
    "highest_price",
    "lowest_price",
    "avg_closing_price",
    "high_date",
    "low_date",
    "payload_json",
)


def build_fetch_target(
    config_path: Path | None = None,
    api_url: str | None = None,
    output_path: Path | None = None,
) -> OpenDataTarget:
    return resolve_target(
        config_path,
        dataset_name=DATASET_NAME,
        default_api_endpoint=DEFAULT_API_ENDPOINT,
        default_schema_path=DEFAULT_SCHEMA_PATH,
        default_table_name=DEFAULT_TABLE_NAME,
        default_json_name=DEFAULT_JSON_NAME,
        api_url=api_url,
        output_path=output_path,
        description=FETCH_DESCRIPTION,
    )


def fetch_year_reports(
    api_url: str | None = None,
    timeout: int = 30,
    config_path: Path | None = None,
    debug_enabled: bool | None = None,
) -> list[dict[str, Any]]:
    resolved_api_url = api_url or build_fetch_target(config_path).api_url
    effective_debug = debug_enabled
    if effective_debug is None:
        effective_debug = initialize_fetch_runtime(config_path)

    data = request_json(resolved_api_url, timeout=timeout, debug_enabled=effective_debug)
    if not isinstance(data, list):
        raise ValueError("TWSE payload for year is not a list")
    return data


def transform_year_report_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        "company_code": str(row.get("Code", "")).strip(),
        "company_name": str(row.get("Name", "")).strip(),
        "report_period": str(row.get("Year", "")).strip(),
        "trade_volume": str(row.get("TradeVolume", "")).strip(),
        "trade_value": str(row.get("TradeValue", "")).strip(),
        "transaction_count": str(row.get("Transaction", "")).strip(),
        "highest_price": str(row.get("HighestPrice", "")).strip(),
        "lowest_price": str(row.get("LowestPrice", "")).strip(),
        "avg_closing_price": str(row.get("AvgClosingPrice", "")).strip(),
        "high_date": str(row.get("HDate", "")).strip(),
        "low_date": str(row.get("LDate", "")).strip(),
        "payload_json": json.dumps(row, ensure_ascii=False, separators=(",", ":")),
    }


def build_import_target(config_path: Path | None = None) -> ImportTarget:
    return create_import_target(
        dataset_name=DATASET_NAME,
        field_mapping=FIELD_MAPPING,
        primary_key="company_code",
        conflict_columns=("company_code", "report_period"),
        insert_columns=INSERT_COLUMNS,
        row_transform=transform_year_report_row,
        description=IMPORT_DESCRIPTION,
        default_api_endpoint=DEFAULT_API_ENDPOINT,
        default_schema_path=DEFAULT_SCHEMA_PATH,
        default_table_name=DEFAULT_TABLE_NAME,
        default_json_name=DEFAULT_JSON_NAME,
        config_path=config_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = build_import_parser("TWSE 上市證券年報工具")
    parser.add_argument("--api-url", default=None, help="OpenAPI 完整 URL")
    parser.add_argument("--output", type=Path, default=None, help="輸出 JSON 檔案路徑")
    parser.add_argument("--fetch-json", action="store_true", help="只抓 API 並輸出 JSON，不做資料庫匯入")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.fetch_json:
        debug_enabled = initialize_fetch_runtime(args.config)
        target = build_fetch_target(args.config, api_url=args.api_url, output_path=args.output)
        data, saved_path = run_fetch(
            target,
            timeout=args.timeout,
            config_path=args.config,
            debug_enabled=debug_enabled,
        )
        print(f"fetched {len(data)} rows")
        print(f"saved to {saved_path}")
        return

    imported, db_path = run_import(args, build_import_target(args.config), fetch_year_reports)
    if args.init_schema:
        print(f"initialized schema at {db_path}")
        return

    print(f"imported {imported} rows into {db_path}")


if __name__ == "__main__":
    main()
