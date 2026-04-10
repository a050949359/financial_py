from __future__ import annotations

from flask import Blueprint
from flask import abort
from flask import jsonify
from flask import render_template
from flask import request

from app.query_service import search_companies
from web.services import build_company_detail_context
from web.services import build_home_context


web_blueprint = Blueprint(
    "web",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)


def _parse_limit(raw_value: str | None, default: int = 20) -> int:
    if raw_value is None:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        return default
    return max(1, min(parsed, 100))


@web_blueprint.get("/")
def index() -> str:
    keyword = request.args.get("q", "").strip()
    limit = _parse_limit(request.args.get("limit"), default=20)
    return render_template("index.html", **build_home_context(keyword, limit))


@web_blueprint.get("/companies/<company_code>")
def company_detail(company_code: str) -> str:
    context = build_company_detail_context(company_code)
    if context is None:
        abort(404)
    return render_template("company_detail.html", **context)


@web_blueprint.get("/api/companies")
def companies_api():
    keyword = request.args.get("q", "").strip()
    limit = _parse_limit(request.args.get("limit"), default=20)
    companies = search_companies(keyword, limit)
    return jsonify(
        {
            "items": companies,
            "keyword": keyword,
            "limit": limit,
        }
    )


@web_blueprint.get("/health")
def health():
    return jsonify({"status": "ok"})