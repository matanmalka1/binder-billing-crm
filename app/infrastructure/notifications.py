"""
Infrastructure adapters for external notification channels.

WhatsApp: disabled — stub only (returns False so caller falls back to email).
Email:    SendGrid — real implementation, gated by NOTIFICATIONS_ENABLED flag.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ─── WhatsApp (disabled) ──────────────────────────────────────────────────────

class WhatsAppChannel:
    """
    WhatsApp channel — NOT implemented.

    Always returns (False, reason) so the notification service falls back
    to email automatically. Replace this class when WhatsApp is needed.
    """

    def send(self, recipient: str, content: str) -> tuple[bool, Optional[str]]:
        logger.debug("WhatsApp is disabled; skipping send to %s", recipient)
        return (False, "WhatsApp channel is not enabled")


# ─── Email via SendGrid ────────────────────────────────────────────────────────

class EmailChannel:
    """
    Email channel backed by SendGrid.

    Requires environment variables:
        SENDGRID_API_KEY   — your SendGrid API key (sg.xxx...)
        EMAIL_FROM_ADDRESS — verified sender address, e.g. crm@yourfirm.co.il
        EMAIL_FROM_NAME    — display name, e.g. "המשרד שלי"

    When NOTIFICATIONS_ENABLED=false (the default), the channel logs the
    message and returns success without actually sending — safe for dev/test.
    """

    def __init__(self) -> None:
        from app.config import config  # local import to avoid circular

        self._enabled = config.NOTIFICATIONS_ENABLED
        self._api_key = config.SENDGRID_API_KEY
        self._from_address = config.EMAIL_FROM_ADDRESS
        self._from_name = config.EMAIL_FROM_NAME

    # ------------------------------------------------------------------
    def send(self, recipient: str, content: str, subject: Optional[str] = None) -> tuple[bool, Optional[str]]:
        """
        Send an email.

        Args:
            recipient: target email address
            content:   plain-text body (also used as HTML fallback)
            subject:   optional subject line; defaults to a generic subject

        Returns:
            (True, None) on success
            (False, error_message) on failure
        """
        if not self._enabled:
            logger.info(
                "[NOTIFICATIONS_DISABLED] Would send email to %s | subject: %s",
                recipient,
                subject or "(default)",
            )
            return (True, None)

        if not self._api_key:
            logger.error("SENDGRID_API_KEY is not configured")
            return (False, "SENDGRID_API_KEY is not configured")

        if not self._from_address:
            logger.error("EMAIL_FROM_ADDRESS is not configured")
            return (False, "EMAIL_FROM_ADDRESS is not configured")

        try:
            import urllib.request
            import json

            resolved_subject = subject or "הודעה ממערכת ניהול התיקים"

            payload = {
                "personalizations": [
                    {"to": [{"email": recipient}]}
                ],
                "from": {
                    "email": self._from_address,
                    "name": self._from_name or "CRM",
                },
                "subject": resolved_subject,
                "content": [
                    {"type": "text/plain", "value": content},
                    {"type": "text/html", "value": _to_html(content)},
                ],
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=data,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.status
                # SendGrid returns 202 Accepted on success
                if status_code in (200, 202):
                    logger.info("Email sent to %s (status %s)", recipient, status_code)
                    return (True, None)
                else:
                    msg = f"Unexpected SendGrid status: {status_code}"
                    logger.warning(msg)
                    return (False, msg)

        except Exception as exc:  # noqa: BLE001
            msg = f"SendGrid error: {exc}"
            logger.error(msg)
            return (False, msg)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _to_html(text: str) -> str:
    """Convert plain-text content to minimal HTML email body."""
    lines = text.splitlines()
    paragraphs = "".join(f"<p>{line}</p>" if line.strip() else "<br>" for line in lines)
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; font-size: 15px; color: #222; direction: rtl;">
{paragraphs}
</body>
</html>"""