from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random
from typing import Iterable

from app.signature_requests.models.signature_request import (
    SignatureAuditEvent,
    SignatureRequest,
    SignatureRequestStatus,
    SignatureRequestType,
)


def _pick_related_annual_report(rng: Random, annual_reports):
    return rng.choice(annual_reports) if annual_reports else None


def _pick_document(rng: Random, documents):
    return rng.choice(documents) if documents else None


def create_signature_requests(db, rng: Random, cfg, clients, users, annual_reports, documents):
    requests: list[SignatureRequest] = []

    for client in clients:
        for _ in range(cfg.signature_requests_per_client):
            report = _pick_related_annual_report(rng, annual_reports)
            document = _pick_document(rng, documents)
            status = rng.choice(list(SignatureRequestStatus))

            declined_at = (
                datetime.now(UTC) - timedelta(days=rng.randint(0, 10))
                if status == SignatureRequestStatus.DECLINED
                else None
            )
            canceled_at = (
                datetime.now(UTC) - timedelta(days=rng.randint(0, 10))
                if status == SignatureRequestStatus.CANCELED
                else None
            )

            request = SignatureRequest(
                client_id=client.id,
                created_by=rng.choice(users).id,
                annual_report_id=report.id if report else None,
                document_id=document.id if document else None,
                request_type=rng.choice(list(SignatureRequestType)),
                title="Signature request " + client.full_name,
                description="Please sign and return",
                content_hash=None,
                storage_key=document.storage_key if document else None,
                signer_name=client.full_name,
                signer_email=client.email,
                signer_phone=client.phone,
                status=status,
                signing_token=f"TOKEN-{rng.randint(100000, 999999)}",
                created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 60)),
                sent_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 45)) if status != SignatureRequestStatus.DRAFT else None,
                expires_at=datetime.now(UTC) + timedelta(days=rng.randint(5, 30)),
                signed_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 10))
                if status == SignatureRequestStatus.SIGNED
                else None,
                declined_at=declined_at,
                canceled_at=canceled_at,
            )
            db.add(request)
            requests.append(request)
    db.flush()
    return requests


def create_signature_audit_events(db, rng: Random, requests: Iterable[SignatureRequest]) -> None:
    for request in requests:
        events = [
            ("created", request.created_at),
        ]
        if request.sent_at:
            events.append(("sent", request.sent_at))
        if request.sent_at and not any(e[0] == "sent" for e in events):
            events.append(("sent", request.sent_at))
        if request.signed_at:
            events.append(("signed", request.signed_at))
        if request.declined_at:
            events.append(("declined", request.declined_at))
        if request.canceled_at:
            events.append(("canceled", request.canceled_at))
        if request.status == SignatureRequestStatus.EXPIRED:
            events.append(("expired", request.expires_at))

        for event_type, ts in events:
            audit = SignatureAuditEvent(
                signature_request_id=request.id,
                event_type=event_type,
                actor_type="advisor",
                actor_id=request.created_by,
                actor_name="Seeder",
                ip_address="127.0.0.1",
                user_agent="seeder/1.0",
                occurred_at=ts or request.created_at,
            )
            db.add(audit)
    db.flush()
