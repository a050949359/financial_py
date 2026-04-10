#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PARENT_DIR = Path(__file__).resolve().parents[1]
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from utils.config import get_web_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="啟動 Flask Web 介面")
    parser.add_argument("--host", default=None, help="Web host，預設讀取 config.toml")
    parser.add_argument("--port", type=int, default=None, help="Web port，預設讀取 config.toml")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="以 debug 模式啟動 Flask，未提供時使用 config.toml 設定",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = get_web_config()
    from web import create_app

    app = create_app()
    app.run(
        host=args.host or config.host,
        port=args.port or config.port,
        debug=args.debug or config.debug,
    )


if __name__ == "__main__":
    main()