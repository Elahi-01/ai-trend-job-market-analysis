"""Jobs listing, AJAX search, and CSV export routes.

Public jobs pages and CSV export intentionally exclude demo records.
Static demo data is only visible through Static Demo Mode (/dashboard/demo).
"""
from flask import Blueprint, render_template, request, jsonify, Response, current_app
import csv
import io
import logging
from datetime import datetime

from app.utils.json import json_safe

logger = logging.getLogger(__name__)
jobs_bp = Blueprint("jobs", __name__)

REAL_DATA_FILTER = {
    "$and": [
        {"search_mode": {"$ne": "demo"}},
        {"is_demo": {"$ne": True}},
        {"data_scope": {"$ne": "demo"}},
    ]
}


def _and_query(*parts: dict) -> dict:
    active = [part for part in parts if part]
    if not active:
        return {}
    if len(active) == 1:
        return active[0]
    return {"$and": active}


def _build_query(args) -> dict:
    """Build a real-data-only MongoDB query from filters."""
    keyword = args.get("keyword", args.get("q", "")).strip()
    location = args.get("location", "").strip()
    source = args.get("source", "").strip()
    remote_only = args.get("remote", "").lower() == "true"

    filters = []
    if keyword:
        filters.append({"$text": {"$search": keyword}})
    if location:
        filters.append({"location": {"$regex": location, "$options": "i"}})
    if source:
        filters.append({"source": source})
    if remote_only:
        filters.append({"is_remote": True})

    return _and_query(REAL_DATA_FILTER, *filters)


@jobs_bp.route("/")
def list_jobs():
    try:
        db = current_app.db_manager
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 20)), 5), 100)
        keyword = request.args.get("keyword", "").strip()
        location = request.args.get("location", "").strip()
        source = request.args.get("source", "").strip()
        remote_only = request.args.get("remote", "").lower() == "true"

        query = _build_query(request.args)
        total = db.jobs.count_documents(query)
        skip = (page - 1) * per_page
        jobs = list(db.jobs.find(query, {"_id": 0}).sort("scraped_at", -1).skip(skip).limit(per_page))
        total_pages = max(1, (total + per_page - 1) // per_page)

        return render_template(
            "jobs.html",
            jobs=json_safe(jobs),
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            keyword=keyword,
            location=location,
            source=source,
            remote_only=remote_only,
        )
    except Exception as exc:
        logger.error("Jobs listing error: %s", exc)
        return render_template(
            "jobs.html", jobs=[], page=1, total=0, total_pages=1, per_page=20,
            keyword="", location="", source="", remote_only=False,
        )


@jobs_bp.route("/search")
def search_jobs():
    """AJAX search endpoint. Demo jobs are never returned here."""
    try:
        db = current_app.db_manager
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 10)), 1), 50)
        query = _build_query(request.args)

        total = db.jobs.count_documents(query)
        skip = (page - 1) * per_page
        jobs = list(db.jobs.find(query, {"_id": 0}).sort("scraped_at", -1).skip(skip).limit(per_page))
        return jsonify(json_safe({
            "jobs": jobs,
            "total": total,
            "page": page,
            "pages": max(1, (total + per_page - 1) // per_page),
            "data_scope": "real",
        }))
    except Exception as exc:
        logger.error("Search error: %s", exc)
        return jsonify({"error": str(exc), "jobs": [], "total": 0}), 500


@jobs_bp.route("/export")
def export_csv():
    """Export real scraped jobs only. Demo/example.com rows are excluded."""
    try:
        db = current_app.db_manager
        query = _build_query(request.args)
        jobs = list(db.jobs.find(query, {"_id": 0}).sort("scraped_at", -1).limit(5000))
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "title", "company", "location", "source", "salary", "employment_type",
            "is_remote", "skills", "job_url", "posted_date", "scraped_at",
            "search_mode", "date_scraped", "week_number", "month", "year",
        ])
        writer.writeheader()
        for job in jobs:
            writer.writerow({
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "source": job.get("source", ""),
                "salary": job.get("salary", ""),
                "employment_type": job.get("employment_type", ""),
                "is_remote": job.get("is_remote", False),
                "skills": ", ".join(job.get("skills", [])),
                "job_url": job.get("job_url", ""),
                "posted_date": str(job.get("posted_date", "")),
                "scraped_at": str(job.get("scraped_at", "")),
                "search_mode": job.get("search_mode", ""),
                "date_scraped": job.get("date_scraped", ""),
                "week_number": job.get("week_number", ""),
                "month": job.get("month", ""),
                "year": job.get("year", ""),
            })
        output.seek(0)
        filename = f"real_jobs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as exc:
        logger.error("CSV export error: %s", exc)
        return jsonify({"error": "Export failed"}), 500
