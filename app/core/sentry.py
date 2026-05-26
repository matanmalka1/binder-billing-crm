from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings


def configure_sentry(settings: Settings) -> None:
    if not (settings.SENTRY_ENABLED and settings.SENTRY_DSN):
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from sentry_sdk.types import Event, Hint

    from app.core.logging_config import get_request_id

    def _before_send(event: Event, _hint: Hint) -> Event | None:
        request_id = get_request_id()
        if request_id:
            event.setdefault("tags", {})["request_id"] = request_id
        return event

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        send_default_pii=False,
        before_send=_before_send,
    )
