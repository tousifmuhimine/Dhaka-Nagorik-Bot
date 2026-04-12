"""Email automation service for complaint lifecycle notifications."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosmtplib
import jinja2
from app.core.config import get_settings
from app.schemas.complaint import ComplaintRecord

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending automated emails via SMTP."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.template_dir = Path(__file__).parent.parent / "templates" / "email"
        self._envelope = jinja2.Environment(loader=jinja2.FileSystemLoader(self.template_dir))

    @property
    def enabled(self) -> bool:
        """Check if email service is configured."""
        return self.settings.has_email_config

    def _get_template(self, template_name: str) -> jinja2.Template:
        """Load email template by name."""
        try:
            return self._envelope.get_template(template_name)
        except jinja2.TemplateNotFound:
            logger.error(f"Email template not found: {template_name}")
            raise

    async def send_complaint_confirmation(self, complaint: ComplaintRecord, citizen_email: str) -> bool:
        """Send complaint submission confirmation email to citizen."""
        if not self.enabled:
            logger.warning("Email service disabled. Skipping complaint confirmation.")
            return False

        try:
            template = self._get_template("complaint_confirmation.html")
            body = template.render(
                complaint_id=complaint.id,
                complaint_summary=complaint.summary,
                category=complaint.category,
                thana=complaint.thana,
                created_at=complaint.created_at.isoformat(),
                urgency=complaint.urgency,
                bot_name=self.settings.email_from_name,
            )

            subject = f"Complaint Received - Ref: {complaint.id[:8].upper()}"
            await self._send_email(citizen_email, subject, body)
            logger.info(f"Complaint confirmation sent to {citizen_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send complaint confirmation: {e}")
            return False

    async def send_authority_notification(
        self, complaint: ComplaintRecord, authority_email: str, thana: str
    ) -> bool:
        """Notify authority when a complaint is assigned to their thana."""
        if not self.enabled:
            logger.warning("Email service disabled. Skipping authority notification.")
            return False

        try:
            template = self._get_template("authority_notification.html")
            body = template.render(
                complaint_id=complaint.id,
                complaint_summary=complaint.summary,
                category=complaint.category,
                thana=thana,
                created_at=complaint.created_at.isoformat(),
                urgency=complaint.urgency,
                area=complaint.area,
                duration=complaint.duration,
                bot_name=self.settings.email_from_name,
            )

            subject = f"New Complaint Assigned - {thana} Thana - Ref: {complaint.id[:8].upper()}"
            await self._send_email(authority_email, subject, body)
            logger.info(f"Authority notification sent to {authority_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send authority notification: {e}")
            return False

    async def send_resolution_notification(self, complaint: ComplaintRecord, citizen_email: str) -> bool:
        """Notify citizen that their complaint has been resolved."""
        if not self.enabled:
            logger.warning("Email service disabled. Skipping resolution notification.")
            return False

        try:
            template = self._get_template("resolution_notification.html")

            # Calculate resolution time
            if complaint.completed_at and complaint.created_at:
                resolution_hours = (complaint.completed_at - complaint.created_at).total_seconds() / 3600
            else:
                resolution_hours = 0

            body = template.render(
                complaint_id=complaint.id,
                complaint_summary=complaint.summary,
                category=complaint.category,
                thana=complaint.thana,
                completed_at=complaint.completed_at.isoformat() if complaint.completed_at else "N/A",
                created_at=complaint.created_at.isoformat(),
                resolution_hours=round(resolution_hours, 2),
                status=complaint.status,
                bot_name=self.settings.email_from_name,
            )

            subject = f"Your Complaint Resolution - Ref: {complaint.id[:8].upper()}"
            await self._send_email(citizen_email, subject, body)
            logger.info(f"Resolution notification sent to {citizen_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send resolution notification: {e}")
            return False

    async def send_confirmation_request(self, complaint: ComplaintRecord, citizen_email: str) -> bool:
        """Request citizen to confirm or reject resolution."""
        if not self.enabled:
            logger.warning("Email service disabled. Skipping confirmation request.")
            return False

        try:
            template = self._get_template("confirmation_request.html")
            body = template.render(
                complaint_id=complaint.id,
                complaint_summary=complaint.summary,
                category=complaint.category,
                thana=complaint.thana,
                completed_at=complaint.completed_at.isoformat() if complaint.completed_at else "N/A",
                bot_name=self.settings.email_from_name,
            )

            subject = f"Please Confirm Resolution - Ref: {complaint.id[:8].upper()}"
            await self._send_email(citizen_email, subject, body)
            logger.info(f"Confirmation request sent to {citizen_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send confirmation request: {e}")
            return False

    async def _send_email(self, recipient: str, subject: str, html_body: str) -> None:
        """Internal method to send email via SMTP."""
        try:
            message = (
                f"From: {self.settings.email_from_name} <{self.settings.email_sender}>\n"
                f"To: {recipient}\n"
                f"Subject: {subject}\n"
                f"MIME-Version: 1.0\n"
                f"Content-Type: text/html; charset=utf-8\n"
                f"\n{html_body}"
            )

            async with aiosmtplib.SMTP(
                hostname=self.settings.email_smtp_host, port=self.settings.email_smtp_port
            ) as smtp:
                await smtp.login(self.settings.email_user, self.settings.email_password)
                await smtp.send_message(message)

            logger.debug(f"Email sent to {recipient}: {subject}")
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            raise


# Singleton instance
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
