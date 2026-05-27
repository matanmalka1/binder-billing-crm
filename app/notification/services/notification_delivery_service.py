from __future__ import annotations

from app.core.logging_config import get_logger
from app.notification.models.notification import NotificationChannel

logger = get_logger(__name__)


class NotificationDeliveryService:
    """
    Sends a notification to a valid recipient via the appropriate channel.

    Contract:
    - Receives a resolved recipient — never decides skipped.
    - Does NOT persist any DB records. SendService owns record creation.
    - Returns (ok: bool, error: str | None).
    """

    def send(
        self,
        channel: NotificationChannel,
        recipient: str,
        subject: str,
        body: str,
        email_channel=None,
        whatsapp_channel=None,
    ) -> tuple[bool, str | None]:
        if channel == NotificationChannel.WHATSAPP:
            if whatsapp_channel is None or not whatsapp_channel.enabled:
                return False, "whatsapp not configured"
            ok, err = whatsapp_channel.send(recipient, body)
            if not ok:
                logger.warning(
                    "whatsapp delivery failed recipient=%s error=%s", recipient, err
                )
            return ok, err

        if email_channel is None:
            return False, "email channel not configured"
        ok, err = email_channel.send(recipient, body, subject=subject)
        if not ok:
            logger.error(
                "email delivery failed recipient=%s error=%s", recipient, err
            )
        return ok, err
