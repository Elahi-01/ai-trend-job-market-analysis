"""Scraper trigger, search mode, demo mode, and logs routes."""
from flask import Blueprint, render_template, request, jsonify, current_app, Response
from datetime import datetime
import logging
import threading
import csv
import io

from app.analysis.analytics_engine import AnalyticsEngine
from app.services.demo_data import seed_demo_data
from app.services.scraping_service import ScrapingService
from app.utils.json import json_safe

logger = logging.getLogger(__name__)
scraper_bp = Blueprint("scraper", __name__)
_scraping_lock = threading.Lock()


@scraper_bp.route("/")
def scraper_page():
    try:
        db = current_app.db_manager
        logs = list(db.scraping_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(75))
        return render_template("logs.html", logs=json_safe(logs))
    except Exception as exc:
        logger.error("Scraper page error: %s", exc)
        return render_template("logs.html", logs=[])


@scraper_bp.route("/run", methods=["POST"])
def run_scraper():
    """Run selected search mode from the dashboard/search modal."""
    data = request.get_json(silent=True) or {}
    if (data.get("search_mode") or data.get("mode")) != "demo" and not _scraping_lock.acquire(blocking=False):
        return jsonify({"success": False, "error": "Scraping already in progress"}), 429

    locked = (data.get("search_mode") or data.get("mode")) != "demo"
    try:
        service = ScrapingService(current_app.db_manager, current_app.config)
        result = service.run(data)
        return jsonify(json_safe(result))
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Scraper route error")
        try:
            current_app.db_manager.scraping_logs.insert_one({
                "timestamp": datetime.utcnow(),
                "keyword": data.get("keyword", ""),
                "location": data.get("location", ""),
                "search_mode": data.get("search_mode") or data.get("mode") or "unknown",
                "sources": data.get("sources", []),
                "results": {"error": str(exc)},
                "duration_seconds": 0,
                "status": "error",
            })
        except Exception:
            pass
        return jsonify({"success": False, "error": str(exc)}), 500
    finally:
        if locked:
            _scraping_lock.release()


@scraper_bp.route("/demo", methods=["GET", "POST"])
def demo_dashboard():
    """Load existing MongoDB analytics instantly; never runs Playwright."""
    try:
        service = ScrapingService(current_app.db_manager, current_app.config)
        return jsonify(json_safe(service.load_demo_dashboard()))
    except Exception as exc:
        logger.error("Demo mode error: %s", exc)
        return jsonify({"success": False, "error": str(exc)}), 500


@scraper_bp.route("/seed-demo", methods=["POST"])
def seed_demo():
    """Optional helper to preload demo data for recruiter showcase mode."""
    try:
        count = int((request.get_json(silent=True) or {}).get("count", 80))
        result = seed_demo_data(current_app.db_manager, count=max(10, min(count, 300)))
        # Demo analytics are generated dynamically and stay isolated from real snapshots.
        analytics = AnalyticsEngine(current_app.db_manager, demo_only=True).get_all_analytics()
        return jsonify(json_safe({"success": True, "result": result, "analytics": analytics, "dashboard_url": "/dashboard/demo"}))
    except Exception as exc:
        logger.exception("Seed demo error")
        return jsonify({"success": False, "error": str(exc)}), 500


@scraper_bp.route("/status")
def scrape_status():
    return jsonify({"running": _scraping_lock.locked()})


@scraper_bp.route("/export-logs")
def export_logs_csv():
    """Export scraping logs with clear fetched/inserted/duplicate counts."""
    try:
        db = current_app.db_manager
        logs = list(db.scraping_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(5000))
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "timestamp", "search_mode", "keyword", "location",
            "linkedin_fetched", "linkedin_inserted", "linkedin_duplicates", "linkedin_failed",
            "indeed_fetched", "indeed_inserted", "indeed_duplicates", "indeed_failed",
            "total_fetched", "total_inserted", "total_duplicates", "total_failed",
            "duration_seconds", "status",
        ])
        writer.writeheader()

        def source_stats(results, source):
            src = results.get(source, {}) if isinstance(results, dict) else {}
            return {
                "fetched": src.get("fetched", src.get("scraped", 0)),
                "inserted": src.get("inserted", 0),
                "duplicates": src.get("duplicates", 0),
                "failed": src.get("failed", 0),
            }

        for log in logs:
            results = log.get("results", {}) or {}
            summary = log.get("summary", {}) or {}
            li = source_stats(results, "linkedin")
            ind = source_stats(results, "indeed")
            writer.writerow({
                "timestamp": str(log.get("timestamp", "")),
                "search_mode": log.get("search_mode", ""),
                "keyword": log.get("keyword", ""),
                "location": log.get("location", ""),
                "linkedin_fetched": li["fetched"],
                "linkedin_inserted": li["inserted"],
                "linkedin_duplicates": li["duplicates"],
                "linkedin_failed": li["failed"],
                "indeed_fetched": ind["fetched"],
                "indeed_inserted": ind["inserted"],
                "indeed_duplicates": ind["duplicates"],
                "indeed_failed": ind["failed"],
                "total_fetched": results.get("total_fetched", summary.get("total_fetched", li["fetched"] + ind["fetched"])),
                "total_inserted": results.get("total_new", summary.get("total_inserted", li["inserted"] + ind["inserted"])),
                "total_duplicates": results.get("total_duplicates", summary.get("total_duplicates", li["duplicates"] + ind["duplicates"])),
                "total_failed": results.get("total_failed", summary.get("total_failed", li["failed"] + ind["failed"])),
                "duration_seconds": log.get("duration_seconds", 0),
                "status": log.get("status", ""),
            })

        output.seek(0)
        filename = f"scraping_logs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        logger.error("Scraping logs CSV export error: %s", exc)
        return jsonify({"success": False, "error": "Export failed"}), 500
