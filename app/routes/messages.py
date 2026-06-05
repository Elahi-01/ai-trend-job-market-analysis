"""Public suggestion/message system."""
from datetime import datetime
import re
import logging

from flask import Blueprint, render_template, request, jsonify, current_app

from app.services.email_service import EmailService
from app.utils.json import json_safe

logger = logging.getLogger(__name__)
messages_bp = Blueprint("messages", __name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_CATEGORIES = {"Bug", "Feature", "Improvement", "General"}


def _clean(value: str, max_len: int) -> str:
    return (value or "").strip()[:max_len]


@messages_bp.route("/feedback")
def feedback_page():
    return render_template("feedback.html")


@messages_bp.route("/api/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json(silent=True) or request.form.to_dict()
    name = _clean(data.get("name"), 80)
    email = _clean(data.get("email"), 120)
    subject = _clean(data.get("subject"), 150)
    message = _clean(data.get("message"), 3000)
    category = _clean(data.get("category"), 40) or "General"

    if category not in ALLOWED_CATEGORIES:
        category = "General"
    if len(name) < 2:
        return jsonify({"success": False, "error": "Name is required."}), 400
    if not EMAIL_PATTERN.match(email):
        return jsonify({"success": False, "error": "Valid email is required."}), 400
    if len(subject) < 3:
        return jsonify({"success": False, "error": "Subject is required."}), 400
    if len(message) < 10:
        return jsonify({"success": False, "error": "Message must be at least 10 characters."}), 400

    feedback = {
        "name": name,
        "email": email,
        "subject": subject,
        "message": message,
        "category": category,
        "status": "new",
        "source": "public_feedback_form",
        "created_at": datetime.utcnow(),
        "email_notification": {"sent": False, "reason": "Pending"},
    }

    try:
        result = current_app.db_manager.messages.insert_one(feedback)
        feedback["message_id"] = str(result.inserted_id)
        email_result = EmailService(current_app.config).send_feedback_notification(feedback)
        current_app.db_manager.messages.update_one(
            {"_id": result.inserted_id},
            {"$set": {"email_notification": email_result}},
        )
        feedback["email_notification"] = email_result
        return jsonify(json_safe({
            "success": True,
            "message": "Thank you. Your suggestion has been sent to the project owner.",
            "email_notification": email_result,
        }))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Feedback submission failed")
        return jsonify({"success": False, "error": str(exc)}), 500
