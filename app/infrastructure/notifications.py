"""
Infrastructure adapters for external notification channels.

WhatsApp: 360dialog API — real implementation when WHATSAPP_API_KEY is set;
          falls back to stub (returns False) so caller can fall back to email.
Email:    SendGrid — real implementation, gated by NOTIFICATIONS_ENABLED flag.
"""
from __future__ import annotations

import html
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Email via SendGrid ────────────────────────────────────────────────────────

class EmailChannel:
    """
    Email channel backed by SendGrid.

    Callers inject configuration values (typically from app.config.config):
        api_key      — SendGrid API key (sg.xxx...)
        from_address — verified sender address, e.g. crm@yourfirm.co.il
        from_name    — display name, e.g. "המשרד שלי"
        enabled      — feature flag; when False the channel logs instead of sending

    When NOTIFICATIONS_ENABLED=false (the default), the channel logs the
    message and returns success without actually sending — safe for dev/test.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        api_key: str,
        api_url: str,
        from_address: str,
        from_name: str = "",
    ) -> None:
        self._enabled = enabled
        self._api_key = api_key
        self._api_url = api_url
        self._from_address = from_address
        self._from_name = from_name

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
                self._api_url,
                data=data,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
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


# ─── WhatsApp via 360dialog ───────────────────────────────────────────────────

class WhatsAppChannel:
    """
    WhatsApp channel backed by 360dialog API.

    When WHATSAPP_API_KEY is empty the channel is disabled and returns
    (False, "not configured") so the caller can fall back to email.
    """

    def __init__(self, *, api_key: str, api_url: str, from_number: str) -> None:
        self._api_key = api_key
        self._api_url = api_url
        self._from_number = from_number

    @property
    def enabled(self) -> bool:
        return bool(self._api_key and self._from_number)

    def send(self, recipient_phone: str, content: str) -> tuple[bool, Optional[str]]:
        """
        Send a WhatsApp text message.

        Returns (True, None) on success, (False, error_message) otherwise.
        When not configured returns (False, "not configured") immediately.
        """
        if not self.enabled:
            logger.info("[WHATSAPP_DISABLED] Would send WhatsApp to %s", recipient_phone)
            return (False, "not configured")

        try:
            import json
            import urllib.request

            # 360dialog API payload — does NOT use messaging_product (that's Meta Graph API)
            payload = {
                "to": recipient_phone,
                "type": "text",
                "text": {"body": content},
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._api_url,
                data=data,
                headers={
                    "D360-API-KEY": self._api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 201):
                    logger.info("WhatsApp sent to %s", recipient_phone)
                    return (True, None)
                msg = f"Unexpected WhatsApp status: {resp.status}"
                logger.warning(msg)
                return (False, msg)

        except Exception as exc:  # noqa: BLE001
            msg = f"WhatsApp error: {exc}"
            logger.error(msg)
            return (False, msg)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _to_html(text: str) -> str:
    """Convert plain-text content to minimal HTML email body (XSS-safe)."""
    lines = text.splitlines()
    paragraphs = "".join(
        f"<p>{html.escape(line)}</p>" if line.strip() else "<br>"
        for line in lines
    )
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; font-size: 15px; color: #222; direction: rtl;">
{paragraphs}
</body>
</html>"""
