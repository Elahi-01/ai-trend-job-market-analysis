"""Dashboard routes.

/dashboard shows real scraped jobs only.
/dashboard/demo shows demo-only analytics for Static Demo Mode.
"""
from flask import Blueprint, render_template, current_app
from app.analysis.analytics_engine import AnalyticsEngine
from app.utils.json import json_safe
import logging

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def index():
    try:
        engine = AnalyticsEngine(current_app.db_manager)
        analytics = engine.get_all_analytics()
        return render_template(
            "dashboard.html",
            analytics=json_safe(analytics),
            dashboard_mode="real",
            dashboard_notice="Real scraped jobs only. Demo records are excluded from this dashboard and CSV export.",
        )
    except Exception as exc:
        logger.error("Dashboard error: %s", exc)
        return render_template("dashboard.html", analytics={}, dashboard_mode="real", dashboard_notice="")


@dashboard_bp.route("/dashboard/demo")
def demo_dashboard():
    """Static demo dashboard. Does not expose workflow and does not run scraping."""
    try:
        engine = AnalyticsEngine(current_app.db_manager, demo_only=True)
        analytics = engine.get_all_analytics()
        return render_template(
            "dashboard.html",
            analytics=json_safe(analytics),
            dashboard_mode="demo",
            dashboard_notice="Static Demo Mode: demo data is shown here only. It is excluded from Jobs, Search, and CSV export.",
        )
    except Exception as exc:
        logger.error("Demo dashboard error: %s", exc)
        return render_template("dashboard.html", analytics={}, dashboard_mode="demo", dashboard_notice="")
