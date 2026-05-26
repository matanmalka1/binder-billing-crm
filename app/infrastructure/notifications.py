"""
Infrastructure adapters for external notification channels.

WhatsApp: 360dialog API — real implementation when WHATSAPP_API_KEY is set;
          falls back to stub (returns False) so caller can fall back to email.
Email:    SendGrid — real implementation, gated by NOTIFICATIONS_ENABLED flag.
"""

from __future__ import annotations

import html
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

EMAIL_PROVIDER_TIMEOUT_SECONDS = 10
MAX_PROVIDER_ERROR_BODY_LENGTH = 1000


# ─── Email via SendGrid ────────────────────────────────────────────────────────


class EmailDeliveryError(RuntimeError):
    """Raised when the configured email provider cannot accept the message."""


class EmailChannel:
    """
    Email channel backed by SendGrid.

    Callers inject configuration values (typically from app.config.settings):
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
    def send(
        self, recipient: str, content: str, subject: str | None = None
    ) -> tuple[bool, str | None]:
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
        resolved_subject = subject or "הודעה ממערכת ניהול התיקים"
        payload = {
            "personalizations": [{"to": [{"email": recipient}]}],
            "from": self._sender_payload(),
            "subject": resolved_subject,
            "content": [
                {"type": "text/plain", "value": content},
                {"type": "text/html", "value": _to_html(content)},
            ],
        }
        return self._send_payload(payload, success_log_recipient=recipient)

    def send_template(
        self,
        recipient: str,
        template_id: str,
        dynamic_template_data: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Send an email using a SendGrid dynamic template.

        Returns:
            (True, None) on success
            (False, error_message) on failure
        """
        if not template_id:
            return (False, "SendGrid template_id is not configured")

        payload = {
            "personalizations": [
                {
                    "to": [{"email": recipient}],
                    "dynamic_template_data": dynamic_template_data,
                }
            ],
            "from": self._sender_payload(),
            "template_id": template_id,
        }
        return self._send_payload(payload, success_log_recipient=recipient)

    def _send_payload(
        self,
        payload: dict[str, Any],
        *,
        success_log_recipient: str,
    ) -> tuple[bool, str | None]:
        if not self._enabled:
            logger.info(
                "[NOTIFICATIONS_DISABLED] Would send email to %s",
                success_log_recipient,
            )
            return (True, None)

        config_error = self._configuration_error()
        if config_error:
            logger.error(config_error)
            return (False, config_error)

        try:
            status_code = self._post_sendgrid(payload)
        except EmailDeliveryError as exc:
            msg = str(exc)
            logger.error(msg)
            return (False, msg)

        logger.info("Email sent to %s (status %s)", success_log_recipient, status_code)
        return (True, None)

    def _post_sendgrid(self, payload: dict[str, Any]) -> int:
        try:
            response = httpx.post(
                self._api_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=EMAIL_PROVIDER_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:
            raise EmailDeliveryError(f"SendGrid email request failed: {exc}") from exc

        if response.status_code not in (200, 202):
            body = response.text[:MAX_PROVIDER_ERROR_BODY_LENGTH]
            raise EmailDeliveryError(
                f"SendGrid rejected email: status={response.status_code} body={body}"
            )
        return response.status_code

    def _configuration_error(self) -> str | None:
        if not self._api_key:
            return "SENDGRID_API_KEY is not configured"
        if not self._from_address:
            return "EMAIL_FROM_ADDRESS is not configured"
        return None

    def _sender_payload(self) -> dict[str, str]:
        return {
            "email": self._from_address,
            "name": self._from_name or "CRM",
        }


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

    def send(self, recipient_phone: str, content: str) -> tuple[bool, str | None]:
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
        f"<p>{html.escape(line)}</p>" if line.strip() else "<br>" for line in lines
    )
    return f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; font-size: 15px; color: #222; direction: rtl;">
{paragraphs}
</body>
</html>"""
