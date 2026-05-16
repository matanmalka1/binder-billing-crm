from __future__ import annotations

from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.notification.models.notification import NotificationTrigger
from app.notification.services.messages import (
    CONTENT_TEMPLATES,
    DEFAULT_NOTIFICATION_SUBJECT,
    FALLBACK_CLIENT_NAME,
    SUBJECTS,
)

logger = get_logger(__name__)

_TEMPLATE_ERROR_MSG = "תבנית ההודעה חסרה או שדה חסר בנתוני ההודעה"
_TEMPLATE_ERROR_CODE = "NOTIFICATION.TEMPLATE_ERROR"


class NotificationTemplateRenderer:
    def render(
        self,
        trigger: NotificationTrigger,
        template_data: dict,
        person_name: str,
    ) -> tuple[str, str]:
        """Returns (content, subject). Raises AppError before any persistence."""
        template = CONTENT_TEMPLATES.get(trigger.value)
        if template is None:
            logger.error("NotificationTemplateRenderer: no template for trigger=%s", trigger)
            raise AppError(_TEMPLATE_ERROR_MSG, _TEMPLATE_ERROR_CODE)

        try:
            content = template.format(
                name=person_name or FALLBACK_CLIENT_NAME,
                **(template_data or {}),
            )
        except KeyError as exc:
            logger.error(
                "NotificationTemplateRenderer: missing key=%s for trigger=%s", exc, trigger
            )
            raise AppError(_TEMPLATE_ERROR_MSG, _TEMPLATE_ERROR_CODE) from exc

        subject = SUBJECTS.get(trigger, DEFAULT_NOTIFICATION_SUBJECT)
        return content, subject
