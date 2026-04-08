#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import sys
from typing import Any
from urllib.request import Request, urlopen


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from init import load_dataset_config, load_opendata_config, setup_logging


DEFAULT_CONFIG = load_opendata_config()
DEFAULT_BASE_URL = "https://openapi.twse.com.tw/v1"
DEFAULT_DESCRIPTION = "抓取 TWSE OpenAPI"
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenDataTarget:
    api_url: str
    output_path: Path
    description: str


def build_api_url(api_path: str, base_url: str = DEFAULT_BASE_URL) -> str:
    normalized_base_url = base_url.rstrip("/")
    normalized_api_path = api_path if api_path.startswith("/") else f"/{api_path}"
    return f"{normalized_base_url}{normalized_api_path}"


def request_json(
    url: str,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
    config_path: Path | None = None,
) -> Any:
    setup_logging(config_path, LOGGER.name)
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "py_shell-twse-opendata/1.0",
    }
    if headers:
        request_headers.update(headers)

    request = Request(url, headers=request_headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")

        return json.loads(payload)
    except Exception:
        LOGGER.exception("TWSE API 呼叫失敗: url=%s timeout=%s", url, timeout)
        raise


def fetch_twse_opendata(
    api_path: str,
    timeout: int = 30,
    base_url: str = DEFAULT_BASE_URL,
    config_path: Path | None = None,
) -> list[dict[str, Any]]:
    data = request_json(
        build_api_url(api_path, base_url=base_url),
        timeout=timeout,
        config_path=config_path,
    )
    if not isinstance(data, list):
        raise ValueError("TWSE API 回傳格式不是陣列")
    return data


def create_target(api_url: str, output_path: Path, description: str = DEFAULT_DESCRIPTION) -> OpenDataTarget:
    return OpenDataTarget(
        api_url=api_url,
        output_path=output_path,
        description=description,
    )


def resolve_target(
    config_path: Path | None = None,
    *,
    dataset_name: str | None = None,
    default_api_endpoint: str = "/opendata/t187ap03_L",
    default_schema_path: str = "database/init_company.sql",
    default_table_name: str = "listed_company_basic",
    default_json_name: str = "listed_company.json",
    api_url: str | None = None,
    output_path: Path | None = None,
    description: str = DEFAULT_DESCRIPTION,
) -> OpenDataTarget:
    if dataset_name:
        dataset = load_dataset_config(
            dataset_name,
            config_path,
            default_api_endpoint=default_api_endpoint,
            default_schema_path=default_schema_path,
            default_table_name=default_table_name,
            default_json_name=default_json_name,
        )
        resolved_api_url = api_url or dataset.api_url
        resolved_output_path = output_path or dataset.json_path
    else:
        config = load_opendata_config(config_path)
        resolved_api_url = api_url or DEFAULT_BASE_URL
        resolved_output_path = output_path or config.project_root / "OpenData" / "opendata.json"

    return OpenDataTarget(
        api_url=resolved_api_url,
        output_path=resolved_output_path,
        description=description,
    )


def fetch_target(target: OpenDataTarget, timeout: int = 30, config_path: Path | None = None) -> Any:
    return request_json(target.api_url, timeout=timeout, config_path=config_path)


def save_json(data: Any, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def run_fetch(
    target: OpenDataTarget,
    timeout: int = 30,
    output_path: Path | None = None,
    config_path: Path | None = None,
) -> tuple[Any, Path]:
    resolved_output_path = output_path or target.output_path
    data = fetch_target(target, timeout=timeout, config_path=config_path)
    save_json(data, resolved_output_path)
    return data, resolved_output_path


def build_parser(default_target: OpenDataTarget | None = None) -> argparse.ArgumentParser:
    target = default_target or resolve_target(description=DEFAULT_DESCRIPTION)
    parser = argparse.ArgumentParser(description=target.description)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG.config_path,
        help="config.toml 路徑",
    )
    parser.add_argument(
        "--api-url",
        default=target.api_url,
        help="OpenAPI 完整 URL",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=target.output_path,
        help="輸出 JSON 檔案路徑",
    )
    parser.add_argument(
        "--description",
        default=target.description,
        help="CLI 描述文字",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout 秒數",
    )
    return parser


def main(default_target: OpenDataTarget | None = None) -> None:
    parser = build_parser(default_target)
    args = parser.parse_args()

    target = resolve_target(
        args.config,
        api_url=args.api_url,
        output_path=args.output,
        description=args.description,
    )
    data, saved_path = run_fetch(target, timeout=args.timeout, config_path=args.config)

    print(f"fetched {len(data)} rows")
    print(f"saved to {saved_path}")


if __name__ == "__main__":
    main()