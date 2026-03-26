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
    binder_serial = 10000 + int(rng.random() * 2000)
    businesses_by_client_id: dict[int, list] = {}
    for business in businesses:
        businesses_by_client_id.setdefault(business.client_id, []).append(business)

    for client_id, client_businesses in businesses_by_client_id.items():
        num = rng.randint(
            cfg.min_binders_per_client,
            cfg.max_binders_per_client,
        )
        for _ in range(num):
            period_start = date.today() - timedelta(days=rng.randint(0, 120))

            if rng.random() < 0.4:
                status = BinderStatus.RETURNED
                returned_at = min(
                    date.today(),
                    period_start + timedelta(days=rng.randint(5, 30)),
                )
                period_end = returned_at
            else:
                status = rng.choice([BinderStatus.IN_OFFICE, BinderStatus.READY_FOR_PICKUP])
                returned_at = None
                period_end = None

            binder = Binder(
                client_id=client_id,
                binder_number=f"B-{binder_serial}",
                period_start=period_start,
                period_end=period_end,
                returned_at=returned_at,
                status=status,
                created_by=rng.choice(users).id,
                pickup_person_name=(full_name(rng) if status == BinderStatus.RETURNED else None),
                notes=rng.choice(["", "דחוף", "הלקוח ביקש שיחה חוזרת"]),
            )
            binder_serial += 1
            db.add(binder)
            binders.append(binder)
    db.flush()
    return binders


def create_binder_logs(db, rng: Random, binders, users) -> None:
    for binder in binders:
        logs = []
        logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.IN_OFFICE.value, "קבלת קלסר"))
        if binder.status == BinderStatus.READY_FOR_PICKUP:
            logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.READY_FOR_PICKUP.value, "הטיפול הושלם"))
        elif binder.status == BinderStatus.RETURNED:
            logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.READY_FOR_PICKUP.value, "מוכן לאיסוף"))
            logs.append((BinderStatus.READY_FOR_PICKUP.value, BinderStatus.RETURNED.value, "נמסר ללקוח"))

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
    businesses_by_client_id: dict[int, list] = {}
    for business in businesses:
        businesses_by_client_id.setdefault(business.client_id, []).append(business)

    reports_by_business_id: dict[int, list] = {}
    for report in reports:
        reports_by_business_id.setdefault(report.business_id, []).append(report)

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
                business_reports = reports_by_business_id.get(business.id, [])
                if business_reports:
                    report = rng.choice(business_reports)
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
                created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 120)),
            )
            db.add(item)
            materials.append(item)
    db.flush()
    return materials
