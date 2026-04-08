#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from twse_fetcher import initialize_fetch_runtime, request_json, resolve_target, run_fetch
from twse_importer import ImportTarget, create_import_target, run_import, build_parser as build_import_parser


FIELD_MAPPING = {
    "出表日期": "data_date",
    "基金代號": "fund_code",
    "基金簡稱": "fund_short_name",
    "基金類型": "fund_type",
    "基金中文名稱": "fund_name_zh",
    "基金英文名稱": "fund_name_en",
    "標的指數/追蹤指數名稱": "benchmark_index_name",
    "標的指數是否為客製化或需揭露相關資訊之指數": "benchmark_index_disclosure_flag",
    "股票及債券投資比例說明": "stock_bond_allocation_note",
    "是否設有績效指標": "has_performance_benchmark",
    "績效指標中文名稱": "performance_benchmark_name_zh",
    "績效指標英文名稱": "performance_benchmark_name_en",
    "是否包含國外成分股": "includes_foreign_constituents",
    "基金統一編號": "fund_registration_number",
    "成立日期": "establishment_date",
    "上市日期": "listed_date",
    "基金經理人": "fund_manager",
    "經理公司總機": "manager_company_phone",
    "經理公司地址": "manager_company_address",
    "經理公司董事長": "manager_company_chairman",
    "經理公司發言人": "manager_company_spokesperson",
    "經理公司總經理": "manager_company_general_manager",
    "經理公司代理發言人": "manager_company_acting_spokesperson",
    "總代理人": "master_agent",
    "發行單位數/轉換數": "issued_units_or_conversion_units",
    "保管機構": "custodian_institution",
    "保管機構電話": "custodian_phone",
    "保管機構地址": "custodian_address",
    "備註": "remarks",
}

DATASET_NAME = "fund"
DEFAULT_API_ENDPOINT = "/opendata/t187ap47_L"
DEFAULT_SCHEMA_PATH = "database/init_fund.sql"
DEFAULT_TABLE_NAME = "fund_basic"
DEFAULT_JSON_NAME = "fund.json"
FETCH_DESCRIPTION = "抓取 TWSE 基金基本資料彙總表 OpenAPI"
IMPORT_DESCRIPTION = "初始化並匯入 TWSE 基金基本資料到 SQLite"


def build_fetch_target(
    config_path: Path | None = None,
    api_url: str | None = None,
    output_path: Path | None = None,
) -> Any:
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


def build_import_target(config_path: Path | None = None) -> ImportTarget:
    return create_import_target(
        dataset_name=DATASET_NAME,
        field_mapping=FIELD_MAPPING,
        primary_key="fund_code",
        description=IMPORT_DESCRIPTION,
        default_api_endpoint=DEFAULT_API_ENDPOINT,
        default_schema_path=DEFAULT_SCHEMA_PATH,
        default_table_name=DEFAULT_TABLE_NAME,
        default_json_name=DEFAULT_JSON_NAME,
        config_path=config_path,
    )


def fetch_fund(
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
        raise ValueError("TWSE API 回傳格式不是陣列")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = build_import_parser("TWSE 基金資料工具")
    parser.add_argument(
        "--api-url",
        default=None,
        help="OpenAPI 完整 URL",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="輸出 JSON 檔案路徑",
    )
    parser.add_argument(
        "--fetch-json",
        action="store_true",
        help="只抓 API 並輸出 JSON，不做資料庫匯入",
    )
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

    imported, db_path = run_import(args, build_import_target(args.config), fetch_fund)
    if args.init_schema:
        print(f"initialized schema at {db_path}")
        return

    print(f"imported {imported} rows into {db_path}")


if __name__ == "__main__":
    main()