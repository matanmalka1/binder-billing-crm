from __future__ import annotations

from datetime import date, timedelta, UTC, datetime
from random import Random

from app.binders.models.binder import Binder, BinderStatus, BinderType
from app.binders.models.binder_status_log import BinderStatusLog

from ..random_utils import full_name


def create_binders(db, rng: Random, cfg, clients, users) -> list[Binder]:
    binders: list[Binder] = []
    binder_serial = 10000
    for client in clients:
        num = rng.randint(
            cfg.min_binders_per_client,
            cfg.max_binders_per_client,
        )
        for _ in range(num):
            received_days_ago = rng.randint(0, 120)
            received_at = date.today() - timedelta(days=received_days_ago)
            expected_return_at = received_at + timedelta(days=rng.randint(7, 30))

            if rng.random() < 0.4:
                status = BinderStatus.RETURNED
                returned_at = min(
                    date.today(),
                    expected_return_at + timedelta(days=rng.randint(-2, 8)),
                )
            else:
                if expected_return_at < date.today():
                    status = rng.choice([BinderStatus.OVERDUE, BinderStatus.READY_FOR_PICKUP])
                else:
                    status = rng.choice([BinderStatus.IN_OFFICE, BinderStatus.READY_FOR_PICKUP])
                returned_at = None

            binder = Binder(
                client_id=client.id,
                binder_number=f"B-{binder_serial}",
                binder_type=rng.choice(list(BinderType)),
                received_at=received_at,
                expected_return_at=expected_return_at,
                returned_at=returned_at,
                status=status,
                received_by=rng.choice(users).id,
                returned_by=rng.choice(users).id if status == BinderStatus.RETURNED else None,
                pickup_person_name=(full_name(rng) if status == BinderStatus.RETURNED else None),
                notes=rng.choice(["", "Urgent handling", "Client requested callback"]),
            )
            binder_serial += 1
            db.add(binder)
            binders.append(binder)
    db.flush()
    return binders


def create_binder_logs(db, rng: Random, binders, users) -> None:
    for binder in binders:
        logs = []
        logs.append(("none", BinderStatus.IN_OFFICE.value, "Binder intake"))
        if binder.status == BinderStatus.READY_FOR_PICKUP:
            logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.READY_FOR_PICKUP.value, "Processing complete"))
        elif binder.status == BinderStatus.OVERDUE:
            logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.OVERDUE.value, "SLA breach"))
        elif binder.status == BinderStatus.RETURNED:
            logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.READY_FOR_PICKUP.value, "Ready for pickup"))
            logs.append((BinderStatus.READY_FOR_PICKUP.value, BinderStatus.RETURNED.value, "Picked up"))

        for old_status, new_status, note in logs:
            log = BinderStatusLog(
                binder_id=binder.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=rng.choice(users).id,
                changed_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 120)),
                notes=note,
            )
            db.add(log)
    db.flush()
