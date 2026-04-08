#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from init import get_system_config
from twse_fetcher import initialize_fetch_runtime, request_json, resolve_target, run_fetch
from twse_importer import create_import_target, run_import


FIELD_MAPPING = {
    "出表日期": "data_date",
    "公司代號": "company_code",
    "公司名稱": "company_name",
    "公司簡稱": "company_short_name",
    "外國企業註冊地國": "foreign_registration_country",
    "產業別": "industry_category",
    "住址": "address",
    "營利事業統一編號": "business_registration_number",
    "董事長": "chairman",
    "總經理": "general_manager",
    "發言人": "spokesperson",
    "發言人職稱": "spokesperson_title",
    "代理發言人": "acting_spokesperson",
    "總機電話": "switchboard_phone",
    "成立日期": "establishment_date",
    "上市日期": "listed_date",
    "普通股每股面額": "par_value_per_share",
    "實收資本額": "paid_in_capital",
    "私募股數": "private_placement_shares",
    "特別股": "preferred_shares",
    "編制財務報表類型": "financial_statement_type",
    "股票過戶機構": "stock_transfer_agent",
    "過戶電話": "transfer_phone",
    "過戶地址": "transfer_address",
    "簽證會計師事務所": "certified_accounting_firm",
    "簽證會計師1": "certified_accountant_1",
    "簽證會計師2": "certified_accountant_2",
    "英文簡稱": "english_short_name",
    "英文通訊地址": "english_address",
    "傳真機號碼": "fax_number",
    "電子郵件信箱": "email",
    "網址": "website",
    "已發行普通股數或TDR原股發行股數": "issued_common_shares_or_tdr_shares",
}

DEFAULT_FETCH_TARGET = resolve_target(
    dataset_name="company",
    default_api_endpoint="/opendata/t187ap03_L",
    default_schema_path="database/init_company.sql",
    default_table_name="listed_company_basic",
    default_json_name="listed_company.json",
    description="抓取 TWSE 上市公司基本資料 OpenAPI",
)

DEFAULT_IMPORT_TARGET = create_import_target(
    dataset_name="company",
    field_mapping=FIELD_MAPPING,
    primary_key="company_code",
    description="初始化並匯入 TWSE 上市公司基本資料到 SQLite",
    default_api_endpoint="/opendata/t187ap03_L",
    default_schema_path="database/init_company.sql",
    default_table_name="listed_company_basic",
    default_json_name="listed_company.json",
)


def fetch_company(
    api_url: str | None = None,
    timeout: int = 30,
    config_path: Path | None = None,
    debug_enabled: bool | None = None,
) -> list[dict[str, Any]]:
    resolved_api_url = api_url or DEFAULT_FETCH_TARGET.api_url
    effective_debug = debug_enabled
    if effective_debug is None:
        effective_debug = initialize_fetch_runtime(config_path)

    data = request_json(resolved_api_url, timeout=timeout, debug_enabled=effective_debug)
    if not isinstance(data, list):
        raise ValueError("TWSE API 回傳格式不是陣列")
    return data


def build_parser() -> argparse.ArgumentParser:
    default_system_config = get_system_config()
    parser = argparse.ArgumentParser(description="TWSE 上市公司資料工具")
    parser.add_argument(
        "--config",
        type=Path,
        default=default_system_config.config_path,
        help="config.toml 路徑",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_FETCH_TARGET.api_url,
        help="OpenAPI 完整 URL",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_FETCH_TARGET.output_path,
        help="輸出 JSON 檔案路徑",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=default_system_config.db_path,
        help="SQLite 資料庫檔案路徑",
    )
    parser.add_argument(
        "--schema-path",
        type=Path,
        default=DEFAULT_IMPORT_TARGET.schema_path,
        help="初始化 SQL 檔案路徑",
    )
    parser.add_argument(
        "--input-json",
        type=Path,
        default=DEFAULT_IMPORT_TARGET.json_path,
        help="來源 JSON 檔案路徑",
    )
    parser.add_argument(
        "--fetch-json",
        action="store_true",
        help="只抓 API 並輸出 JSON，不做資料庫匯入",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="直接從 TWSE OpenAPI 抓資料並匯入 SQLite",
    )
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="只初始化 SQLite schema，不匯入資料",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout 秒數",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    debug_enabled = initialize_fetch_runtime(args.config)

    if args.fetch_json:
        target = resolve_target(
            args.config,
            dataset_name="company",
            default_api_endpoint="/opendata/t187ap03_L",
            default_schema_path="database/init_company.sql",
            default_table_name="listed_company_basic",
            default_json_name="listed_company.json",
            api_url=args.api_url,
            output_path=args.output,
            description=DEFAULT_FETCH_TARGET.description,
        )
        data, saved_path = run_fetch(
            target,
            timeout=args.timeout,
            config_path=args.config,
            debug_enabled=debug_enabled,
        )
        print(f"fetched {len(data)} rows")
        print(f"saved to {saved_path}")
        return

    imported, db_path = run_import(args, DEFAULT_IMPORT_TARGET, fetch_company)
    if args.init_schema:
        print(f"initialized schema at {db_path}")
        return

    print(f"imported {imported} rows into {db_path}")


if __name__ == "__main__":
    main()