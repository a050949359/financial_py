from __future__ import annotations

import sqlite3
from typing import Any

from utils.config import get_system_config


SUMMARY_TABLES = {
    "companies": "上市公司",
    "funds": "基金",
    "day_reports": "日報資料",
    "month_reports": "月報資料",
    "year_reports": "年報資料",
}


def _connect() -> sqlite3.Connection | None:
    db_path = get_system_config().db_path
    if not db_path.is_file():
        return None

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _fetch_latest_imported_at(connection: sqlite3.Connection, table_name: str) -> str | None:
    row = connection.execute(
        f"SELECT MAX(imported_at) AS latest_imported_at FROM {table_name}"
    ).fetchone()
    if row is None:
        return None
    return row["latest_imported_at"]


def get_company_overview() -> dict[str, Any]:
    connection = _connect()
    if connection is None:
        return {
            "total_companies": 0,
            "industry_count": 0,
            "latest_imported_at": None,
        }

    with connection:
        if not _table_exists(connection, "companies"):
            return {
                "total_companies": 0,
                "industry_count": 0,
                "latest_imported_at": None,
            }

        row = connection.execute(
            """
            SELECT
                COUNT(*) AS total_companies,
                COUNT(DISTINCT industry_category) AS industry_count,
                MAX(imported_at) AS latest_imported_at
            FROM companies
            """
        ).fetchone()

    return {
        "total_companies": int(row["total_companies"]),
        "industry_count": int(row["industry_count"]),
        "latest_imported_at": row["latest_imported_at"],
    }


def get_latest_day_report_leaders(limit: int = 5) -> dict[str, Any]:
    connection = _connect()
    if connection is None:
        return {"report_period": None, "leaders": []}

    normalized_limit = max(1, min(limit, 20))
    with connection:
        if not _table_exists(connection, "day_reports"):
            return {"report_period": None, "leaders": []}

        latest_row = connection.execute(
            "SELECT MAX(report_period) AS report_period FROM day_reports"
        ).fetchone()
        if latest_row is None or latest_row["report_period"] is None:
            return {"report_period": None, "leaders": []}

        report_period = latest_row["report_period"]
        rows = connection.execute(
            """
            SELECT
                company_code,
                company_name,
                report_period,
                trade_volume,
                trade_value,
                closing_price,
                price_change
            FROM day_reports
            WHERE report_period = ?
            ORDER BY CAST(REPLACE(COALESCE(trade_value, '0'), ',', '') AS REAL) DESC
            LIMIT ?
            """,
            (report_period, normalized_limit),
        ).fetchall()

    return {
        "report_period": report_period,
        "leaders": [dict(row) for row in rows],
    }


def get_dashboard_snapshot() -> dict[str, Any]:
    connection = _connect()
    if connection is None:
        return {
            "database_ready": False,
            "cards": [],
        }

    with connection:
        cards: list[dict[str, Any]] = []
        for table_name, label in SUMMARY_TABLES.items():
            available = _table_exists(connection, table_name)
            row_count = 0
            latest_imported_at = None
            if available:
                row = connection.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()
                row_count = int(row["total"])
                latest_imported_at = _fetch_latest_imported_at(connection, table_name)

            cards.append(
                {
                    "table_name": table_name,
                    "label": label,
                    "available": available,
                    "row_count": row_count,
                    "latest_imported_at": latest_imported_at,
                }
            )

    return {
        "database_ready": True,
        "cards": cards,
    }


def search_companies(keyword: str = "", limit: int = 20) -> list[dict[str, Any]]:
    connection = _connect()
    if connection is None:
        return []

    normalized_limit = max(1, min(limit, 100))
    normalized_keyword = keyword.strip()

    with connection:
        if not _table_exists(connection, "companies"):
            return []

        if normalized_keyword:
            pattern = f"%{normalized_keyword}%"
            rows = connection.execute(
                """
                SELECT
                    company_code,
                    company_name,
                    company_short_name,
                    industry_category,
                    listed_date,
                    imported_at
                FROM companies
                WHERE company_code LIKE ?
                    OR company_name LIKE ?
                    OR company_short_name LIKE ?
                ORDER BY company_code ASC
                LIMIT ?
                """,
                (pattern, pattern, pattern, normalized_limit),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT
                    company_code,
                    company_name,
                    company_short_name,
                    industry_category,
                    listed_date,
                    imported_at
                FROM companies
                ORDER BY company_code ASC
                LIMIT ?
                """,
                (normalized_limit,),
            ).fetchall()

    return [dict(row) for row in rows]


def get_company_detail(company_code: str) -> dict[str, Any] | None:
    connection = _connect()
    if connection is None:
        return None

    with connection:
        if not _table_exists(connection, "companies"):
            return None

        company = connection.execute(
            "SELECT * FROM companies WHERE company_code = ?",
            (company_code,),
        ).fetchone()
        if company is None:
            return None

        latest_reports: dict[str, dict[str, Any] | None] = {}
        report_tables = {
            "day_report": "day_reports",
            "month_report": "month_reports",
            "year_report": "year_reports",
        }
        for key, table_name in report_tables.items():
            if not _table_exists(connection, table_name):
                latest_reports[key] = None
                continue

            row = connection.execute(
                f"""
                SELECT *
                FROM {table_name}
                WHERE company_code = ?
                ORDER BY report_period DESC
                LIMIT 1
                """,
                (company_code,),
            ).fetchone()
            latest_reports[key] = dict(row) if row is not None else None

    return {
        "company": dict(company),
        "latest_reports": latest_reports,
    }