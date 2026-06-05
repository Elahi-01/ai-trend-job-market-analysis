"""Owner/admin-only pages: private workflow, messages, and system overview."""
from datetime import datetime, timedelta
import logging

from flask import Blueprint, render_template, request, redirect, url_for, session, current_app, flash, jsonify

from app.analysis.analytics_engine import AnalyticsEngine
from app.utils.admin_auth import admin_required
from app.utils.json import json_safe

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if username == current_app.config["ADMIN_USERNAME"] and password == current_app.config["ADMIN_PASSWORD"]:
            session["admin_authenticated"] = True
            session["admin_username"] = username
            session.permanent = True
            flash("Admin login successful.", "success")
            return redirect(request.args.get("next") or url_for("admin.panel"))
        flash("Invalid admin credentials.", "danger")
    return render_template("admin_login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin_authenticated", None)
    session.pop("admin_username", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("dashboard.index"))


@admin_bp.route("/")
@admin_required
def panel():
    try:
        db = current_app.db_manager
        overview = AnalyticsEngine(db).get_overview_stats()
        total_messages = db.messages.count_documents({})
        new_messages = db.messages.count_documents({"status": "new"})
        last_24h = datetime.utcnow() - timedelta(hours=24)
        recent_messages = db.messages.count_documents({"created_at": {"$gte": last_24h}})
        latest_logs = list(db.scraping_logs.find({}, {"_id": 0}).sort("timestamp", -1).limit(6))
        return render_template(
            "admin_panel.html",
            overview=json_safe(overview),
            total_messages=total_messages,
            new_messages=new_messages,
            recent_messages=recent_messages,
            latest_logs=json_safe(latest_logs),
        )
    except Exception as exc:
        logger.exception("Admin panel failed")
        flash(str(exc), "danger")
        return render_template("admin_panel.html", overview={}, total_messages=0, new_messages=0, recent_messages=0, latest_logs=[])


@admin_bp.route("/workflow")
@admin_required
def workflow():
    return render_template("admin_workflow.html")


@admin_bp.route("/messages")
@admin_required
def messages():
    page = max(int(request.args.get("page", 1)), 1)
    per_page = 20
    status = (request.args.get("status") or "").strip()
    query = {"status": status} if status else {}
    total = current_app.db_manager.messages.count_documents(query)
    records = list(
        current_app.db_manager.messages.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    return render_template(
        "admin_messages.html",
        messages=json_safe(records),
        page=page,
        total=total,
        pages=max(1, (total + per_page - 1) // per_page),
        status=status,
    )


@admin_bp.route("/messages/<message_id>/status", methods=["POST"])
@admin_required
def update_message_status(message_id):
    from bson import ObjectId

    status = (request.get_json(silent=True) or {}).get("status", "read")
    if status not in {"new", "read", "archived"}:
        return jsonify({"success": False, "error": "Invalid status"}), 400
    try:
        current_app.db_manager.messages.update_one({"_id": ObjectId(message_id)}, {"$set": {"status": status}})
        return jsonify({"success": True})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500
