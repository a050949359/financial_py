#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from core.fetcher import OpenDataTarget, initialize_fetch_runtime, request_json, resolve_target, run_fetch
from core.importer import ImportTarget, create_import_target, run_import, build_parser as build_import_parser


DATASET_NAME = "day_report"
FETCH_DESCRIPTION = "抓取 TWSE 上市證券日報成交資料 OpenAPI"
IMPORT_DESCRIPTION = "初始化並匯入 TWSE 上市證券日報成交資料到 SQLite"
FIELD_MAPPING = {
    "Code": "company_code",
    "Name": "company_name",
    "Date": "report_period",
    "TradeVolume": "trade_volume",
    "TradeValue": "trade_value",
    "Transaction": "transaction_count",
    "OpeningPrice": "opening_price",
    "HighestPrice": "highest_price",
    "LowestPrice": "lowest_price",
    "ClosingPrice": "closing_price",
    "Change": "price_change",
}


def build_fetch_target(
    config_path: Path | None = None,
    api_url: str | None = None,
    output_path: Path | None = None,
) -> OpenDataTarget:
    return resolve_target(
        config_path,
        dataset_name=DATASET_NAME,
        api_url=api_url,
        output_path=output_path,
        description=FETCH_DESCRIPTION,
    )


def fetch_day_reports(
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
        raise ValueError("TWSE payload for day is not a list")
    return data


def build_import_target(config_path: Path | None = None) -> ImportTarget:
    return create_import_target(
        dataset_name=DATASET_NAME,
        field_mapping=FIELD_MAPPING,
        conflict_columns=("company_code", "report_period"),
        description=IMPORT_DESCRIPTION,
        config_path=config_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = build_import_parser("TWSE 上市證券日報工具")
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

    imported, db_path = run_import(args, build_import_target(args.config), fetch_day_reports)
    if args.init_schema:
        print(f"initialized schema at {db_path}")
        return

    print(f"imported {imported} rows into {db_path}")


if __name__ == "__main__":
    main()
