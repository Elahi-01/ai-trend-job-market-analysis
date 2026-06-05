"""Analytics pages and JSON API routes."""
from flask import Blueprint, render_template, jsonify, current_app
import logging

from app.analysis.analytics_engine import AnalyticsEngine
from app.utils.json import json_safe

logger = logging.getLogger(__name__)
analytics_bp = Blueprint("analytics", __name__)


def _engine():
    return AnalyticsEngine(current_app.db_manager)


@analytics_bp.route("/")
def analytics_page():
    try:
        analytics = _engine().get_all_analytics()
        return render_template("analytics.html", analytics=json_safe(analytics))
    except Exception as exc:
        logger.error("Analytics page error: %s", exc)
        return render_template("analytics.html", analytics={})


@analytics_bp.route("/api/overview")
def api_overview():
    return jsonify(json_safe(_engine().get_overview_stats()))


@analytics_bp.route("/api/skills")
def api_skills():
    return jsonify(json_safe(_engine().get_top_skills()))


@analytics_bp.route("/api/companies")
def api_companies():
    return jsonify(json_safe(_engine().get_top_companies()))


@analytics_bp.route("/api/trends")
def api_trends():
    return jsonify(json_safe(_engine().get_daily_trends()))


@analytics_bp.route("/api/historical")
def api_historical():
    return jsonify(json_safe(_engine().get_historical_summary()))


@analytics_bp.route("/api/all")
def api_all():
    return jsonify(json_safe(_engine().get_all_analytics()))


@analytics_bp.route("/api/generate/daily", methods=["POST"])
def api_generate_daily():
    return jsonify(json_safe({"success": True, "snapshot": _engine().generate_daily_snapshot()}))


@analytics_bp.route("/api/generate/weekly", methods=["POST"])
def api_generate_weekly():
    return jsonify(json_safe({"success": True, "snapshot": _engine().generate_weekly_snapshot()}))


@analytics_bp.route("/api/generate/monthly", methods=["POST"])
def api_generate_monthly():
    return jsonify(json_safe({"success": True, "snapshot": _engine().generate_monthly_snapshot()}))
