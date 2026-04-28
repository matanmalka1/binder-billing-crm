from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random
from typing import Iterable

from sqlalchemy import func, select

from app.signature_requests.models.signature_request import (
    SignatureAuditEvent,
    SignatureRequest,
    SignatureRequestStatus,
    SignatureRequestType,
)

from ._business_groups import group_businesses_by_client, pick_businesses_for_client
from ..realistic_seed_text import SIGNATURE_COPY


def _pick_related_for_client(rng: Random, rows_by_client: dict[int, list], client_id: int):
    rows = rows_by_client.get(client_id, [])
    return rng.choice(rows) if rows else None


def _group_by_attr(rows, attr_name: str) -> dict[int, list]:
    grouped: dict[int, list] = {}
    for row in rows:
        key = getattr(row, attr_name, None)
        if key is None:
            continue
        grouped.setdefault(key, []).append(row)
    return grouped


def _random_between(rng: Random, start: datetime, end: datetime) -> datetime:
    if end <= start:
        return start
    seconds = max(1, int((end - start).total_seconds()))
    return start + timedelta(seconds=rng.randint(0, seconds))


def _build_timestamps(rng: Random, status: SignatureRequestStatus) -> dict[str, datetime | None]:
    now = datetime.now(UTC)
    created_at = now - timedelta(days=rng.randint(7, 90), hours=rng.randint(0, 23))
    sent_at = None
    expires_at = None
    signed_at = None
    declined_at = None
    canceled_at = None

    if status == SignatureRequestStatus.DRAFT:
        return {
            "created_at": created_at,
            "sent_at": None,
            "expires_at": None,
            "signed_at": None,
            "declined_at": None,
            "canceled_at": None,
        }

    sent_at = _random_between(rng, created_at, now - timedelta(hours=1))
    if sent_at <= created_at:
        sent_at = created_at + timedelta(minutes=1)

    if status == SignatureRequestStatus.EXPIRED:
        expires_at = _random_between(rng, sent_at + timedelta(hours=1), now - timedelta(minutes=1))
        if expires_at <= sent_at:
            expires_at = sent_at + timedelta(hours=1)
    else:
        expires_at = sent_at + timedelta(days=rng.randint(5, 30))
        if status == SignatureRequestStatus.PENDING_SIGNATURE and expires_at <= now:
            expires_at = now + timedelta(days=rng.randint(1, 14))

    event_upper = min(now, expires_at) if expires_at else now
    if event_upper <= sent_at:
        event_upper = sent_at + timedelta(hours=1)

    if status == SignatureRequestStatus.SIGNED:
        signed_at = _random_between(rng, sent_at + timedelta(minutes=1), event_upper)
    elif status == SignatureRequestStatus.DECLINED:
        declined_at = _random_between(rng, sent_at + timedelta(minutes=1), event_upper)
    elif status == SignatureRequestStatus.CANCELED:
        canceled_at = _random_between(rng, sent_at + timedelta(minutes=1), event_upper)

    return {
        "created_at": created_at,
        "sent_at": sent_at,
        "expires_at": expires_at,
        "signed_at": signed_at,
        "declined_at": declined_at,
        "canceled_at": canceled_at,
    }


def create_signature_requests(db, rng: Random, cfg, businesses, clients, users, annual_reports, documents):
    requests: list[SignatureRequest] = []
    clients_by_id = {client.id: client for client in clients}
    reports_by_client = _group_by_attr(annual_reports, "client_id")
    documents_by_client = _group_by_attr(documents, "client_id")
    existing_count = int(db.execute(select(func.count()).select_from(SignatureRequest)).scalar_one())
    type_cycle = list(SignatureRequestType)
    status_cycle = list(SignatureRequestStatus)
    type_cycle_idx = 0
    status_cycle_idx = 0

    for client_businesses in group_businesses_by_client(businesses).values():
        client = clients_by_id.get(client_businesses[0].client_id)
        if not client:
            continue
        for business in pick_businesses_for_client(
            rng,
            client_businesses,
            cfg.signature_requests_per_client,
        ):
            report = _pick_related_for_client(rng, reports_by_client, client.id)
            document = _pick_related_for_client(rng, documents_by_client, client.id)
            if status_cycle_idx < len(status_cycle):
                status = status_cycle[status_cycle_idx]
                status_cycle_idx += 1
            else:
                status = rng.choice(status_cycle)
            timestamps = _build_timestamps(rng, status)
            serial = existing_count + len(requests) + 1
            if type_cycle_idx < len(type_cycle):
                request_type = type_cycle[type_cycle_idx]
                type_cycle_idx += 1
            else:
                request_type = rng.choice(type_cycle)
            title_prefix, request_description = SIGNATURE_COPY[request_type]

            canceled_by = None
            if status == SignatureRequestStatus.CANCELED:
                canceled_by = rng.choice(users).id
            signing_token = f"seed-sign-{serial:010d}"
            if status in (
                SignatureRequestStatus.SIGNED,
                SignatureRequestStatus.DECLINED,
                SignatureRequestStatus.EXPIRED,
                SignatureRequestStatus.CANCELED,
            ):
                signing_token = None

            request = SignatureRequest(
                client_record_id=business.client_id,
                business_id=business.id,
                created_by=rng.choice(users).id,
                annual_report_id=report.id if report else None,
                document_id=document.id if document else None,
                request_type=request_type,
                title=f"{title_prefix} - {client.full_name}",
                description=request_description,
                content_hash=None,
                storage_key=document.storage_key if document else None,
                signer_name=client.full_name,
                signer_email=client.email,
                signer_phone=client.phone,
                status=status,
                signing_token=signing_token,
                created_at=timestamps["created_at"],
                sent_at=timestamps["sent_at"],
                expires_at=timestamps["expires_at"],
                signed_at=timestamps["signed_at"],
                declined_at=timestamps["declined_at"],
                canceled_at=timestamps["canceled_at"],
                canceled_by=canceled_by,
                decline_reason="הלקוח ביקש לעדכן נוסח לפני חתימה"
                if status == SignatureRequestStatus.DECLINED
                else None,
                signer_ip_address="127.0.0.1" if status == SignatureRequestStatus.SIGNED else None,
                signer_user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" if status == SignatureRequestStatus.SIGNED else None,
                signed_document_key=(
                    f"signed/signature_request_{serial}.pdf"
                    if status == SignatureRequestStatus.SIGNED
                    else None
                ),
            )
            request.client_id = business.client_id
            db.add(request)
            requests.append(request)
    db.flush()
    return requests


def create_signature_audit_events(db, rng: Random, requests: Iterable[SignatureRequest]) -> None:
    for request in requests:
        events: list[tuple[str, datetime, str]] = []
        events.append(("created", request.created_at, "advisor"))
        if request.sent_at:
            events.append(("sent", request.sent_at, "advisor"))
        if request.signed_at:
            events.append(("signed", request.signed_at, "signer"))
        if request.declined_at:
            events.append(("declined", request.declined_at, "signer"))
        if request.canceled_at:
            events.append(("canceled", request.canceled_at, "advisor"))
        if request.status == SignatureRequestStatus.EXPIRED and request.expires_at:
            events.append(("expired", request.expires_at, "system"))

        for event_type, ts, actor_type in events:
            audit = SignatureAuditEvent(
                signature_request_id=request.id,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=request.created_by if actor_type == "advisor" else None,
                actor_name="מערכת חתימות דיגיטליות",
                ip_address="127.0.0.1",
                user_agent="signature-service/2026.04",
                occurred_at=ts,
            )
            db.add(audit)
    db.flush()
