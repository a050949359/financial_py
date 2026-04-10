from __future__ import annotations

from typing import Any

from app.query_service import get_company_detail
from app.query_service import get_company_overview
from app.query_service import get_dashboard_snapshot
from app.query_service import get_latest_day_report_leaders
from app.query_service import search_companies
from utils.config import get_web_config


def _format_twse_date(value: Any) -> str:
    if value is None:
        return "-"

    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text or "-"


def _build_home_metrics(summary: dict[str, Any], company_overview: dict[str, Any]) -> list[dict[str, str]]:
    available_tables = sum(1 for card in summary["cards"] if card["available"])
    return [
        {
            "label": "已建資料表",
            "value": str(available_tables),
            "meta": "目前可直接查詢的資料集數量",
        },
        {
            "label": "公司總數",
            "value": str(company_overview["total_companies"]),
            "meta": f"涵蓋 {company_overview['industry_count']} 個產業類別",
        },
        {
            "label": "最近公司匯入",
            "value": company_overview["latest_imported_at"] or "-",
            "meta": "companies 資料表最近一次 imported_at",
        },
    ]


def _build_profile_items(company: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"label": "公司簡稱", "value": company.get("company_short_name") or "-"},
        {"label": "產業別", "value": company.get("industry_category") or "-"},
        {"label": "上市日期", "value": _format_twse_date(company.get("listed_date"))},
        {"label": "成立日期", "value": _format_twse_date(company.get("establishment_date"))},
        {"label": "董事長", "value": company.get("chairman") or "-"},
        {"label": "總經理", "value": company.get("general_manager") or "-"},
        {"label": "發言人", "value": company.get("spokesperson") or "-"},
        {"label": "網站", "value": company.get("website") or "-"},
    ]


def _build_contact_items(company: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"label": "地址", "value": company.get("address") or "-"},
        {"label": "總機電話", "value": company.get("switchboard_phone") or "-"},
        {"label": "電子郵件", "value": company.get("email") or "-"},
        {"label": "發言人職稱", "value": company.get("spokesperson_title") or "-"},
        {"label": "過戶電話", "value": company.get("transfer_phone") or "-"},
        {"label": "過戶地址", "value": company.get("transfer_address") or "-"},
    ]


def _build_detail_highlights(company: dict[str, Any], latest_reports: dict[str, Any]) -> list[dict[str, str]]:
    available_report_count = sum(1 for report in latest_reports.values() if report is not None)
    return [
        {"label": "資料出表日期", "value": _format_twse_date(company.get("data_date"))},
        {"label": "上市日期", "value": _format_twse_date(company.get("listed_date"))},
        {"label": "實收資本額", "value": company.get("paid_in_capital") or "-"},
        {"label": "可用報表", "value": f"{available_report_count}/3"},
    ]


def _build_report_sections(latest_reports: dict[str, Any]) -> list[dict[str, Any]]:
    specs = [
        ("最新日報", "day_report", "日成交概況"),
        ("最新月報", "month_report", "月成交概況"),
        ("最新年報", "year_report", "年成交概況"),
    ]
    sections: list[dict[str, Any]] = []
    for title, key, subtitle in specs:
        report = latest_reports.get(key)
        metrics = []
        if report is not None:
            metrics = [
                {"label": "期間", "value": report.get("report_period") or "-"},
                {"label": "成交量", "value": report.get("trade_volume") or "-"},
                {"label": "成交值", "value": report.get("trade_value") or "-"},
                {"label": "筆數", "value": report.get("transaction_count") or "-"},
            ]
        sections.append(
            {
                "title": title,
                "subtitle": subtitle,
                "report": report,
                "metrics": metrics,
            }
        )
    return sections


def build_home_context(keyword: str = "", limit: int = 20) -> dict[str, Any]:
    web_config = get_web_config()
    normalized_limit = max(1, min(limit, 100))
    summary = get_dashboard_snapshot()
    company_overview = get_company_overview()
    latest_day_leaders = get_latest_day_report_leaders(5)
    featured_companies = search_companies("", 6)
    return {
        "web_config": web_config,
        "summary": summary,
        "home_metrics": _build_home_metrics(summary, company_overview),
        "company_overview": company_overview,
        "latest_day_leaders": latest_day_leaders,
        "companies": search_companies(keyword, normalized_limit),
        "featured_companies": featured_companies,
        "keyword": keyword,
        "limit": normalized_limit,
    }


def build_company_detail_context(company_code: str) -> dict[str, Any] | None:
    web_config = get_web_config()
    detail = get_company_detail(company_code)
    if detail is None:
        return None

    return {
        "web_config": web_config,
        "detail_highlights": _build_detail_highlights(detail["company"], detail["latest_reports"]),
        "profile_items": _build_profile_items(detail["company"]),
        "contact_items": _build_contact_items(detail["company"]),
        "report_sections": _build_report_sections(detail["latest_reports"]),
        **detail,
    }