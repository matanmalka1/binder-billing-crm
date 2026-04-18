from __future__ import annotations

from datetime import date, timedelta, UTC, datetime
from random import Random

from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_intake import BinderIntake
from app.binders.models.binder_intake_material import BinderIntakeMaterial, MaterialType
from app.binders.models.binder_status_log import BinderStatusLog

from ..random_utils import full_name


def create_binders(db, rng: Random, cfg, businesses, users) -> list[Binder]:
    binders: list[Binder] = []
    businesses_by_client_id: dict[int, list] = {}
    for business in businesses:
        businesses_by_client_id.setdefault(business.client_id, []).append(business)

    for client_id, client_businesses in businesses_by_client_id.items():
        num = rng.randint(
            cfg.min_binders_per_client,
            cfg.max_binders_per_client,
        )
        for seq in range(1, num + 1):
            period_start = date.today() - timedelta(days=rng.randint(0, 120))

            if rng.random() < 0.4:
                status = BinderStatus.RETURNED
                returned_at = min(
                    date.today(),
                    period_start + timedelta(days=rng.randint(5, 30)),
                )
                period_end = returned_at
            else:
                status = rng.choice([
                    BinderStatus.IN_OFFICE,
                    BinderStatus.CLOSED_IN_OFFICE,
                    BinderStatus.READY_FOR_PICKUP,
                ])
                returned_at = None
                period_end = None

            binder = Binder(
                client_id=client_id,
                binder_number=f"{client_id}/{seq}",
                period_start=period_start,
                period_end=period_end,
                returned_at=returned_at,
                status=status,
                created_by=rng.choice(users).id,
                pickup_person_name=(full_name(rng) if status == BinderStatus.RETURNED else None),
                notes=rng.choice(["", "דחוף", "הלקוח ביקש שיחה חוזרת"]),
            )
            db.add(binder)
            binders.append(binder)
    db.flush()
    return binders


def create_binder_logs(db, rng: Random, binders, users) -> None:
    now = datetime.now(UTC)
    for binder in binders:
        logs = []
        intake_time = datetime.combine(binder.period_start, datetime.min.time(), tzinfo=UTC) + timedelta(
            hours=rng.randint(8, 16)
        )
        logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.IN_OFFICE.value, "קבלת קלסר", intake_time))
        if binder.status == BinderStatus.READY_FOR_PICKUP:
            ready_time = intake_time + timedelta(days=rng.randint(2, 14), hours=rng.randint(1, 8))
            if ready_time > now:
                ready_time = now
            logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.READY_FOR_PICKUP.value, "הטיפול הושלם", ready_time))
        elif binder.status == BinderStatus.RETURNED:
            ready_time = intake_time + timedelta(days=rng.randint(2, 14), hours=rng.randint(1, 8))
            if ready_time > now:
                ready_time = now
            returned_base = binder.returned_at or binder.period_end or binder.period_start
            returned_time = datetime.combine(returned_base, datetime.min.time(), tzinfo=UTC) + timedelta(
                hours=rng.randint(9, 18)
            )
            if returned_time < ready_time:
                returned_time = ready_time + timedelta(hours=1)
            if returned_time > now:
                returned_time = now
            logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.READY_FOR_PICKUP.value, "מוכן לאיסוף", ready_time))
            logs.append((BinderStatus.READY_FOR_PICKUP.value, BinderStatus.RETURNED.value, "נמסר ללקוח", returned_time))

        for old_status, new_status, note, changed_at in logs:
            log = BinderStatusLog(
                binder_id=binder.id,
                old_status=old_status,
                new_status=new_status,
                changed_by=rng.choice(users).id,
                changed_at=changed_at,
                notes=note,
            )
            db.add(log)
    db.flush()


def create_binder_intakes(db, binders) -> list[BinderIntake]:
    intakes: list[BinderIntake] = []
    for binder in binders:
        intake = BinderIntake(
            binder_id=binder.id,
            received_at=binder.period_start,
            received_by=binder.created_by,
            notes=binder.notes,
        )
        db.add(intake)
        intakes.append(intake)
    db.flush()
    return intakes


def create_binder_intake_materials(db, rng: Random, binders, businesses, reports, intakes) -> list[BinderIntakeMaterial]:
    materials: list[BinderIntakeMaterial] = []
    now = datetime.now(UTC)
    businesses_by_client_id: dict[int, list] = {}
    for business in businesses:
        businesses_by_client_id.setdefault(business.client_id, []).append(business)

    reports_by_client_id: dict[int, list] = {}
    for report in reports:
        reports_by_client_id.setdefault(report.client_id, []).append(report)

    intake_by_binder_id = {intake.binder_id: intake for intake in intakes}

    for binder in binders:
        intake = intake_by_binder_id.get(binder.id)
        if intake is None:
            continue
        candidate_businesses = businesses_by_client_id.get(binder.client_id, [])
        items_per_intake = rng.randint(1, 4)
        for _ in range(items_per_intake):
            business = rng.choice(candidate_businesses) if candidate_businesses else None
            report = None
            if business and rng.random() < 0.45:
                client_reports = reports_by_client_id.get(business.client_id, [])
                if client_reports:
                    report = rng.choice(client_reports)
            item = BinderIntakeMaterial(
                intake_id=intake.id,
                business_id=business.id if business else None,
                material_type=rng.choice(list(MaterialType)),
                annual_report_id=report.id if report else None,
                description=rng.choice(
                    [
                        None,
                        "חשבוניות ספקים",
                        "דפי בנק ותדפיסים",
                        "אישורי מס וניכויים",
                    ]
                ),
                created_at=min(
                    now,
                    datetime.combine(intake.received_at, datetime.min.time(), tzinfo=UTC)
                    + timedelta(days=rng.randint(0, 14), hours=rng.randint(1, 10)),
                ),
            )
            db.add(item)
            materials.append(item)
    db.flush()
    return materials
