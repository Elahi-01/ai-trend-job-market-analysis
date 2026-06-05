"""SMTP email service for feedback notifications."""
import logging
import smtplib
from email.message import EmailMessage
from typing import Dict, Any

logger = logging.getLogger(__name__)


class EmailService:
    """Sends admin notifications without adding extra dependencies."""

    def __init__(self, config):
        self.enabled = bool(config.get("MAIL_ENABLED"))
        self.server = config.get("MAIL_SERVER", "smtp.gmail.com")
        self.port = int(config.get("MAIL_PORT", 587))
        self.use_tls = bool(config.get("MAIL_USE_TLS", True))
        self.username = config.get("MAIL_USERNAME", "")
        self.password = config.get("MAIL_PASSWORD", "")
        self.receiver = config.get("MAIL_RECEIVER", "")
        self.project_name = config.get("PROJECT_NAME", "AI Trend Job Market Analysis")

    def can_send(self) -> bool:
        return self.enabled and bool(self.username and self.password and self.receiver)

    def send_feedback_notification(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Send suggestion notification email to the project owner/admin."""
        if not self.can_send():
            return {
                "sent": False,
                "reason": "Mail is disabled or SMTP environment variables are incomplete.",
            }

        subject = f"[{self.project_name}] New {feedback.get('category', 'Suggestion')} Message"
        body = f"""New suggestion/message received for {self.project_name}.

Name: {feedback.get('name', 'N/A')}
Email: {feedback.get('email', 'N/A')}
Category: {feedback.get('category', 'General')}
Subject: {feedback.get('subject', 'No subject')}

Message:
{feedback.get('message', '')}

Stored in MongoDB messages collection.
"""
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.username
        msg["To"] = self.receiver
        reply_to = feedback.get("email")
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.set_content(body)

        try:
            with smtplib.SMTP(self.server, self.port, timeout=20) as smtp:
                if self.use_tls:
                    smtp.starttls()
                smtp.login(self.username, self.password)
                smtp.send_message(msg)
            return {"sent": True, "reason": "Email notification sent."}
        except Exception as exc:  # noqa: BLE001 - log and preserve app flow
            logger.exception("Feedback email failed")
            return {"sent": False, "reason": str(exc)}
