#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any


PARENT_DIR = Path(__file__).resolve().parents[2]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from app.core.fetcher import fetch_dataset_rows
from app.core.importer import ImportTarget, create_import_target
from app.twse.cli import build_dataset_parser, run_dataset_cli


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

DATASET_NAME = "company"
FETCH_DESCRIPTION = "抓取 TWSE 上市公司基本資料 OpenAPI"
IMPORT_DESCRIPTION = "初始化並匯入 TWSE 上市公司基本資料到 SQLite"


def build_import_target() -> ImportTarget:
    return create_import_target(
        dataset_name=DATASET_NAME,
        field_mapping=FIELD_MAPPING,
        conflict_columns=("company_code",),
        description=IMPORT_DESCRIPTION,
    )


def fetch_company(
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
    return build_dataset_parser("TWSE 上市公司資料工具")


def main() -> None:
    args = build_parser().parse_args()
    run_dataset_cli(
        args,
        import_target=build_import_target(),
        fetch_rows=fetch_company,
        fetch_description=FETCH_DESCRIPTION,
    )


if __name__ == "__main__":
    main()