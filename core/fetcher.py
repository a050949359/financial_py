#!/usr/bin/env python3

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
from time import perf_counter
import sys
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from init import get_dataset_config, get_system_config, setup_logging


DEFAULT_BASE_URL = "https://openapi.twse.com.tw/v1"
DEFAULT_DESCRIPTION = "抓取 TWSE OpenAPI"
DEFAULT_OUTPUT_PATH = Path("TWSE/opendata.json")
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenDataTarget:
    api_url: str
    output_path: Path
    description: str
    method: str = "GET"
    headers: dict[str, str] | None = None
    query_params: dict[str, str] | None = None
    body: Any = None


def parse_cli_kv_pairs(
    values: list[str] | None,
    *,
    separators: tuple[str, ...],
    argument_name: str,
) -> dict[str, str] | None:
    if not values:
        return None

    parsed: dict[str, str] = {}
    for raw_value in values:
        for separator in separators:
            if separator in raw_value:
                key, value = raw_value.split(separator, 1)
                normalized_key = key.strip()
                if not normalized_key:
                    raise ValueError(f"{argument_name} 格式錯誤: {raw_value}")
                parsed[normalized_key] = value.strip()
                break
        else:
            raise ValueError(f"{argument_name} 格式錯誤: {raw_value}")

    return parsed


def build_request_url(url: str, query_params: dict[str, str] | None = None) -> str:
    if not query_params:
        return url

    parts = urlsplit(url)
    merged_query = dict(parse_qsl(parts.query, keep_blank_values=True))
    merged_query.update(query_params)
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(merged_query), parts.fragment)
    )


def encode_request_body(body: Any, headers: dict[str, str]) -> bytes | None:
    if body is None:
        return None

    if isinstance(body, bytes):
        return body
    if isinstance(body, bytearray):
        return bytes(body)
    if isinstance(body, str):
        return body.encode("utf-8")

    if not any(header.lower() == "content-type" for header in headers):
        headers["Content-Type"] = "application/json; charset=utf-8"
    return json.dumps(body, ensure_ascii=False).encode("utf-8")


def add_fetch_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_dataset: bool = False,
    include_api_path: bool = False,
    include_base_url: bool = False,
    include_description: bool = False,
    include_fetch_json: bool = False,
) -> argparse.ArgumentParser:
    if include_dataset:
        parser.add_argument(
            "--dataset",
            default=None,
            help="dataset 名稱，從 config/registry 解析 API 與輸出路徑",
        )
    if include_api_path:
        parser.add_argument(
            "--api-path",
            default=None,
            help="TWSE API path，例如 /opendata/t187ap03_L",
        )
    if include_base_url:
        parser.add_argument(
            "--base-url",
            default=DEFAULT_BASE_URL,
            help="搭配 --api-path 使用的 base URL",
        )

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
        "--method",
        default="GET",
        help="HTTP method，預設 GET",
    )
    parser.add_argument(
        "--header",
        action="append",
        default=None,
        help="HTTP header，可重複，例如 --header 'Authorization: Bearer token'",
    )
    parser.add_argument(
        "--query",
        action="append",
        default=None,
        help="Query 參數，可重複，例如 --query date=20260101",
    )
    parser.add_argument(
        "--body-json",
        default=None,
        help="JSON request body 字串，例如 '{\"key\":\"value\"}'",
    )

    if include_description:
        parser.add_argument(
            "--description",
            default=parser.description or DEFAULT_DESCRIPTION,
            help="CLI 描述文字",
        )

    if include_fetch_json:
        parser.add_argument(
            "--fetch-json",
            action="store_true",
            help="只抓 API 並輸出 JSON，不做資料庫匯入",
        )

    return parser


def build_output_path(
    *,
    api_path: str | None = None,
    output_path: Path | None = None,
) -> Path:
    if output_path is not None:
        return output_path

    system_config = get_system_config()
    if api_path is None:
        return system_config.source_dir / "opendata.json"

    normalized_name = re.sub(r"[^A-Za-z0-9]+", "_", api_path.strip("/"))
    normalized_name = normalized_name.strip("_") or "opendata"
    return system_config.source_dir / f"{normalized_name}.json"


def build_api_url(api_path: str, base_url: str = DEFAULT_BASE_URL) -> str:
    normalized_base_url = base_url.rstrip("/")
    normalized_api_path = api_path if api_path.startswith("/") else f"/{api_path}"
    return f"{normalized_base_url}{normalized_api_path}"


def request_json(
    url: str,
    timeout: int = 30,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: Any = None,
    debug_enabled: bool = False,
) -> Any:
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "py_shell-twse-opendata/1.0",
    }
    if headers:
        request_headers.update(headers)

    resolved_url = build_request_url(url, query_params)
    request_body = encode_request_body(body, request_headers)
    request = Request(resolved_url, data=request_body, headers=request_headers, method=method.upper())
    started_at = perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")

        result = json.loads(payload)
        if debug_enabled:
            elapsed_seconds = perf_counter() - started_at
            LOGGER.info(
                "TWSE API query finished: status=success method=%s url=%s timeout=%s elapsed_seconds=%.3f",
                method.upper(),
                resolved_url,
                timeout,
                elapsed_seconds,
            )
        return result
    except Exception:
        elapsed_seconds = perf_counter() - started_at
        LOGGER.exception(
            "TWSE API 呼叫失敗: method=%s url=%s timeout=%s elapsed_seconds=%.3f",
            method.upper(),
            resolved_url,
            timeout,
            elapsed_seconds,
        )
        raise


def initialize_fetch_runtime() -> bool:
    config = get_system_config()
    setup_logging(LOGGER.name)
    return config.debug


def fetch_twse_opendata(
    api_path: str,
    timeout: int = 30,
    base_url: str = DEFAULT_BASE_URL,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: Any = None,
    debug_enabled: bool | None = None,
) -> list[dict[str, Any]]:
    effective_debug = debug_enabled
    if effective_debug is None:
        effective_debug = initialize_fetch_runtime()

    data = request_json(
        build_api_url(api_path, base_url=base_url),
        timeout=timeout,
        method=method,
        headers=headers,
        query_params=query_params,
        body=body,
        debug_enabled=effective_debug,
    )
    if not isinstance(data, list):
        raise ValueError("TWSE API 回傳格式不是陣列")
    return data


def fetch_dataset_rows(
    *,
    dataset_name: str,
    description: str,
    payload_error_message: str,
    api_url: str | None = None,
    timeout: int = 30,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: Any = None,
    debug_enabled: bool | None = None,
) -> list[dict[str, Any]]:
    resolved_api_url = api_url or resolve_target(
        dataset_name=dataset_name,
        description=description,
    ).api_url
    effective_debug = debug_enabled
    if effective_debug is None:
        effective_debug = initialize_fetch_runtime()

    data = request_json(
        resolved_api_url,
        timeout=timeout,
        method=method,
        headers=headers,
        query_params=query_params,
        body=body,
        debug_enabled=effective_debug,
    )
    if not isinstance(data, list):
        raise ValueError(payload_error_message)
    return data


def create_target(
    api_url: str,
    output_path: Path,
    description: str = DEFAULT_DESCRIPTION,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: Any = None,
) -> OpenDataTarget:
    return OpenDataTarget(
        api_url=api_url,
        output_path=output_path,
        description=description,
        method=method,
        headers=headers,
        query_params=query_params,
        body=body,
    )


def resolve_target(
    *,
    dataset_name: str,
    api_url: str | None = None,
    output_path: Path | None = None,
    description: str = DEFAULT_DESCRIPTION,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: Any = None,
) -> OpenDataTarget:
    dataset = get_dataset_config(dataset_name)
    resolved_api_url = api_url or dataset.api_url
    resolved_output_path = output_path or dataset.json_path

    return OpenDataTarget(
        api_url=resolved_api_url,
        output_path=resolved_output_path,
        description=description,
        method=method,
        headers=headers,
        query_params=query_params,
        body=body,
    )


def create_path_target(
    *,
    api_path: str,
    base_url: str = DEFAULT_BASE_URL,
    output_path: Path | None = None,
    description: str = DEFAULT_DESCRIPTION,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    body: Any = None,
) -> OpenDataTarget:
    return OpenDataTarget(
        api_url=build_api_url(api_path, base_url=base_url),
        output_path=build_output_path(
            api_path=api_path,
            output_path=output_path,
        ),
        description=description,
        method=method,
        headers=headers,
        query_params=query_params,
        body=body,
    )


def parse_request_options(args: argparse.Namespace) -> tuple[str, dict[str, str] | None, dict[str, str] | None, Any]:
    method = getattr(args, "method", "GET").upper()
    headers = parse_cli_kv_pairs(getattr(args, "header", None), separators=(":",), argument_name="--header")
    query_params = parse_cli_kv_pairs(getattr(args, "query", None), separators=("=",), argument_name="--query")

    body_json = getattr(args, "body_json", None)
    body = None
    if body_json is not None:
        body = json.loads(body_json)

    return method, headers, query_params, body


def resolve_cli_target(
    args: argparse.Namespace,
    *,
    default_dataset_name: str | None = None,
    default_description: str = DEFAULT_DESCRIPTION,
) -> OpenDataTarget:
    dataset_name = getattr(args, "dataset", None) or default_dataset_name
    api_url = getattr(args, "api_url", None)
    api_path = getattr(args, "api_path", None)
    output_path = getattr(args, "output", None)
    base_url = getattr(args, "base_url", DEFAULT_BASE_URL)
    method, headers, query_params, body = parse_request_options(args)

    if dataset_name is not None:
        return resolve_target(
            dataset_name=dataset_name,
            api_url=api_url,
            output_path=output_path,
            description=default_description,
            method=method,
            headers=headers,
            query_params=query_params,
            body=body,
        )

    if api_url:
        return create_target(
            api_url,
            build_output_path(output_path=output_path),
            default_description,
            method=method,
            headers=headers,
            query_params=query_params,
            body=body,
        )

    if api_path:
        return create_path_target(
            api_path=api_path,
            base_url=base_url,
            output_path=output_path,
            description=default_description,
            method=method,
            headers=headers,
            query_params=query_params,
            body=body,
        )

    raise ValueError("必須提供 dataset、api-url 或 api-path")


def run_fetch_command(
    args: argparse.Namespace,
    *,
    default_dataset_name: str | None = None,
    default_description: str = DEFAULT_DESCRIPTION,
) -> tuple[Any, Path]:
    debug_enabled = initialize_fetch_runtime()
    target = resolve_cli_target(
        args,
        default_dataset_name=default_dataset_name,
        default_description=default_description,
    )
    return run_fetch(
        target,
        timeout=args.timeout,
        debug_enabled=debug_enabled,
    )


def fetch_target(target: OpenDataTarget, timeout: int = 30, debug_enabled: bool = False) -> Any:
    return request_json(
        target.api_url,
        timeout=timeout,
        method=target.method,
        headers=target.headers,
        query_params=target.query_params,
        body=target.body,
        debug_enabled=debug_enabled,
    )


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
    debug_enabled: bool | None = None,
) -> tuple[Any, Path]:
    effective_debug = debug_enabled
    if effective_debug is None:
        effective_debug = initialize_fetch_runtime()

    resolved_output_path = output_path or target.output_path
    data = fetch_target(target, timeout=timeout, debug_enabled=effective_debug)
    save_json(data, resolved_output_path)
    return data, resolved_output_path


def build_parser(default_target: OpenDataTarget | None = None) -> argparse.ArgumentParser:
    target = default_target or create_target(
        DEFAULT_BASE_URL,
        DEFAULT_OUTPUT_PATH,
        DEFAULT_DESCRIPTION,
    )
    parser = argparse.ArgumentParser(description=target.description)
    add_fetch_arguments(
        parser,
        include_dataset=True,
        include_api_path=True,
        include_base_url=True,
        include_description=True,
    )
    parser.set_defaults(description=target.description)
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
    data, saved_path = run_fetch_command(
        args,
        default_description=args.description,
    )

    print(f"fetched {len(data)} rows")
    print(f"saved to {saved_path}")


if __name__ == "__main__":
    main()