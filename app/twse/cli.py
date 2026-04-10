#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any, Callable


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from app.core.fetcher import add_fetch_arguments, parse_request_options, run_fetch_command
from app.core.importer import ImportTarget, build_parser as build_import_parser, run_import, run_import_rows


FetchRows = Callable[..., list[dict[str, Any]]]


def build_dataset_parser(description: str) -> argparse.ArgumentParser:
    parser = build_import_parser(description)
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="直接從 TWSE OpenAPI 抓資料，不讀本地 JSON",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="當使用 --fetch 時的 HTTP timeout 秒數",
    )
    return add_fetch_arguments(parser, include_fetch_json=True)


def run_dataset_cli(
    args: argparse.Namespace,
    *,
    import_target: ImportTarget,
    fetch_rows: FetchRows,
    fetch_description: str,
) -> None:
    if args.fetch_json:
        data, saved_path = run_fetch_command(
            args,
            default_dataset_name=import_target.dataset_name,
            default_description=fetch_description,
        )
        print(f"fetched {len(data)} rows")
        print(f"saved to {saved_path}")
        return

    if args.fetch:
        method, headers, query_params, body = parse_request_options(args)
        rows = fetch_rows(
            api_url=args.api_url,
            timeout=args.timeout,
            method=method,
            headers=headers,
            query_params=query_params,
            body=body,
        )
        imported, db_path = run_import_rows(args, import_target, rows)
    else:
        imported, db_path = run_import(args, import_target)

    if args.init_schema:
        print(f"initialized schema at {db_path}")
        return

    print(f"imported {imported} rows into {db_path}")