#!/usr/bin/env python3

from __future__ import annotations

from app.cli import ConfigValidationError
from app.cli import cleanup_old_logs
from app.cli import create_sqlite_database_file
from app.cli import get_dataset_config
from app.cli import get_dataset_json_path
from app.cli import get_raw_config
from app.cli import get_system_config
from app.cli import main
from app.cli import setup_logging
from app.cli import validate_config


if __name__ == "__main__":
    try:
        main()
    except ConfigValidationError as exc:
        raise SystemExit(str(exc)) from exc