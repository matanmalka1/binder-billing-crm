from __future__ import annotations

from dataclasses import dataclass, field

from app.clients.enums import ClientStatus
from app.clients.models.client_record import ClientRecord
from app.notification.models.notification import NotificationTrigger

# Triggers allowed even for FROZEN/CLOSED clients
_FROZEN_CLOSED_ALLOWED = {
    NotificationTrigger.CLIENT_MISSING_INFORMATION,
    NotificationTrigger.CLIENT_DOCUMENTS_REQUEST,
}


@dataclass
class PolicyResult:
    blocked: bool
    reason: str | None = None
    warnings: list[str] = field(default_factory=list)


class NotificationPolicyService:
    """
    Business rule gate for sending notifications.

    Phase 1: client status checks only.
    Domain-specific checks (VAT window, cooldowns, etc.) added in Phases 2–3.

    Contract:
    - blocked=True → caller returns NotificationResult(status=blocked), saves NO record.
    - blocked=False with warnings → caller proceeds, includes warnings in response.
    - Missing Person/email is NOT policy. Handled by contact resolver → produces skipped.
    """

    def can_send(
        self,
        client_record: ClientRecord,
        trigger: NotificationTrigger,
    ) -> PolicyResult:
        status = client_record.status

        if status in (ClientStatus.FROZEN, ClientStatus.CLOSED):
            if trigger not in _FROZEN_CLOSED_ALLOWED:
                return PolicyResult(
                    blocked=True,
                    reason="לא ניתן לשלוח הודעות ללקוח שהסטטוס שלו הוא מוקפא או סגור",
                )

        return PolicyResult(blocked=False)
