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
FETCH_DESCRIPTION = "抓取 TWSE 基金基本資料彙總表 OpenAPI"
IMPORT_DESCRIPTION = "初始化並匯入 TWSE 基金基本資料到 SQLite"


def build_import_target() -> ImportTarget:
    return create_import_target(
        dataset_name=DATASET_NAME,
        field_mapping=FIELD_MAPPING,
        conflict_columns=("fund_code",),
        description=IMPORT_DESCRIPTION,
    )


def fetch_fund(
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
        payload_error_message="TWSE API 回傳格式不是陣列",
        api_url=api_url,
        timeout=timeout,
        method=method,
        headers=headers,
        query_params=query_params,
        body=body,
        debug_enabled=debug_enabled,
    )


def build_parser() -> argparse.ArgumentParser:
    return build_dataset_parser("TWSE 基金資料工具")


def main() -> None:
    args = build_parser().parse_args()
    run_dataset_cli(
        args,
        import_target=build_import_target(),
        fetch_rows=fetch_fund,
        fetch_description=FETCH_DESCRIPTION,
    )


if __name__ == "__main__":
    main()