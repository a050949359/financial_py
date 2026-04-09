#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from core.fetcher import fetch_dataset_rows
from core.importer import ImportTarget, create_import_target
from TWSE.runner import build_dataset_parser, run_dataset_cli


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


def fetch_day_reports(
    api_url: str | None = None,
    timeout: int = 30,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: Any = None,
    debug_enabled: bool | None = None,
) -> list[dict[str, object]]:
    return fetch_dataset_rows(
        dataset_name=DATASET_NAME,
        description=FETCH_DESCRIPTION,
        payload_error_message="TWSE payload for day is not a list",
        api_url=api_url,
        timeout=timeout,
        method=method,
        headers=headers,
        query_params=query_params,
        body=body,
        debug_enabled=debug_enabled,
    )


def build_import_target() -> ImportTarget:
    return create_import_target(
        dataset_name=DATASET_NAME,
        field_mapping=FIELD_MAPPING,
        conflict_columns=("company_code", "report_period"),
        description=IMPORT_DESCRIPTION,
    )


def build_parser() -> argparse.ArgumentParser:
    return build_dataset_parser("TWSE 上市證券日報工具")


def main() -> None:
    args = build_parser().parse_args()
    run_dataset_cli(
        args,
        import_target=build_import_target(),
        fetch_rows=fetch_day_reports,
        fetch_description=FETCH_DESCRIPTION,
    )


if __name__ == "__main__":
    main()
