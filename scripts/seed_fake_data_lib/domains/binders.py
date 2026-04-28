from __future__ import annotations

from datetime import date, timedelta, UTC, datetime
from random import Random

from app.binders.models.binder import Binder, BinderStatus
from app.binders.models.binder_handover import BinderHandover, BinderHandoverBinder
from app.binders.models.binder_intake import BinderIntake
from app.binders.models.binder_intake_edit_log import BinderIntakeEditLog
from app.binders.models.binder_intake_material import BinderIntakeMaterial, MaterialType
from app.binders.models.binder_status_log import BinderStatusLog
from app.common.enums import VatType

from ..demo_catalog import BUSINESS_NOTES
from ..realistic_seed_text import MATERIAL_DESCRIPTIONS
from ..random_utils import full_name


def create_binders(db, rng: Random, cfg, businesses, users) -> list[Binder]:
    binders: list[Binder] = []
    businesses_by_client_id: dict[int, list] = {}
    client_office_number: dict[int, int] = {}
    for business in businesses:
        businesses_by_client_id.setdefault(business.client_id, []).append(business)
        if business.client_id not in client_office_number:
            client_office_number[business.client_id] = business.client.office_client_number or business.client_id

    for client_id, client_businesses in businesses_by_client_id.items():
        office_num = client_office_number.get(client_id, client_id)
        num = rng.randint(
            cfg.min_binders_per_client,
            cfg.max_binders_per_client,
        )
        # Build binders chronologically: each one starts after the previous ends.
        # Only the last binder can be IN_OFFICE / READY_FOR_PICKUP.
        cursor = date.today() - timedelta(days=rng.randint(60, 400))
        for seq in range(1, num + 1):
            period_start = cursor
            is_last = seq == num
            if is_last:
                final_status = rng.choices(
                    [BinderStatus.IN_OFFICE, BinderStatus.READY_FOR_PICKUP, BinderStatus.RETURNED],
                    weights=[50, 25, 25],
                    k=1,
                )[0]
                if final_status == BinderStatus.RETURNED:
                    returned_at = min(date.today(), period_start + timedelta(days=rng.randint(5, 30)))
                    period_end = returned_at
                else:
                    returned_at = None
                    period_end = None
                status = final_status
            else:
                # Older binders: either CLOSED_IN_OFFICE (still in office) or RETURNED.
                status = rng.choices(
                    [BinderStatus.CLOSED_IN_OFFICE, BinderStatus.RETURNED],
                    weights=[40, 60],
                    k=1,
                )[0]
                duration = rng.randint(20, 90)
                period_end = min(date.today() - timedelta(days=1), period_start + timedelta(days=duration))
                returned_at = period_end if status == BinderStatus.RETURNED else None
                cursor = period_end + timedelta(days=rng.randint(1, 14))

            binder = Binder(
                client_record_id=client_id,
                binder_number=f"{office_num}/{seq}",
                period_start=period_start,
                period_end=period_end,
                returned_at=returned_at,
                status=status,
                created_by=rng.choice(users).id,
                pickup_person_name=(full_name(rng) if status == BinderStatus.RETURNED else None),
                notes=rng.choice(BUSINESS_NOTES),
            )
            binder.client_id = client_id
            db.add(binder)
            binders.append(binder)
    db.flush()
    _ensure_binder_status_coverage(db, binders)
    db.flush()
    return binders


def _ensure_binder_status_coverage(db, binders: list) -> None:
    """Patch existing binders so every BinderStatus appears at least once."""
    all_statuses = list(BinderStatus)
    present = {b.status for b in binders}
    missing = [s for s in all_statuses if s not in present]
    if not missing:
        return
    # Find binders whose status is over-represented (count > 1), so we can
    # reassign one without losing coverage of that status.
    from collections import Counter
    counts = Counter(b.status for b in binders)
    for status in missing:
        # Pick a binder from the most over-represented status.
        donor_status = max(counts, key=lambda s: counts[s])
        if counts[donor_status] <= 1:
            # No safe donor — append a synthetic binder instead.
            source = next(b for b in binders if b.status == donor_status)
            clone_period_end = (
                min(date.today(), source.period_start + timedelta(days=30))
                if status == BinderStatus.CLOSED_IN_OFFICE
                else None
            )
            clone = Binder(
                client_record_id=source.client_record_id,
                binder_number=f"{source.binder_number.split('/')[0]}/x{len(binders)+1}",
                period_start=source.period_start,
                period_end=clone_period_end,
                returned_at=None,
                status=status,
                created_by=source.created_by,
                pickup_person_name=None,
                notes=source.notes,
            )
            clone.client_id = source.client_id
            db.add(clone)
            binders.append(clone)
            counts[status] = counts.get(status, 0) + 1
            continue
        candidate = next(b for b in binders if b.status == donor_status)
        counts[donor_status] -= 1
        candidate.status = status
        if status == BinderStatus.CLOSED_IN_OFFICE:
            candidate.returned_at = None
            candidate.period_end = min(date.today(), candidate.period_start + timedelta(days=30))
            candidate.pickup_person_name = None
        elif status != BinderStatus.RETURNED:
            candidate.returned_at = None
            candidate.period_end = None
            candidate.pickup_person_name = None
        counts[status] = counts.get(status, 0) + 1


def create_binder_logs(db, rng: Random, binders, users) -> None:
    now = datetime.now(UTC)
    for binder in binders:
        logs = []
        intake_time = datetime.combine(binder.period_start, datetime.min.time(), tzinfo=UTC) + timedelta(
            hours=rng.randint(8, 16)
        )
        logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.IN_OFFICE.value, "קבלת קלסר", intake_time))
        if binder.status == BinderStatus.CLOSED_IN_OFFICE:
            closed_time = intake_time + timedelta(days=rng.randint(2, 14), hours=rng.randint(1, 8))
            if closed_time > now:
                closed_time = now
            logs.append((BinderStatus.IN_OFFICE.value, BinderStatus.CLOSED_IN_OFFICE.value, "הקלסר נסגר במשרד", closed_time))
        elif binder.status == BinderStatus.READY_FOR_PICKUP:
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
            material_type = rng.choice(list(MaterialType))
            if business and rng.random() < 0.45:
                client_reports = reports_by_client_id.get(business.client_id, [])
                if client_reports:
                    report = rng.choice(client_reports)
            period_year = report.tax_year if report and material_type == MaterialType.ANNUAL_REPORT else binder.period_start.year
            period_month_start = binder.period_start.month
            period_month_end = period_month_start
            if material_type == MaterialType.VAT and business:
                if getattr(business.client, "vat_reporting_frequency", None) == VatType.BIMONTHLY:
                    period_month_end = min(12, period_month_start + 1)
            item = BinderIntakeMaterial(
                intake_id=intake.id,
                business_id=business.id if business else None,
                material_type=material_type,
                annual_report_id=report.id if report else None,
                period_year=period_year,
                period_month_start=period_month_start,
                period_month_end=period_month_end,
                description=MATERIAL_DESCRIPTIONS[material_type],
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


def create_binder_handovers(db, rng: Random, binders, users) -> list[BinderHandover]:
    handovers: list[BinderHandover] = []
    returned_by_client: dict[int, list[Binder]] = {}
    for binder in binders:
        if binder.status != BinderStatus.RETURNED:
            continue
        returned_by_client.setdefault(binder.client_id, []).append(binder)

    for client_id, client_binders in returned_by_client.items():
        ordered = sorted(
            client_binders,
            key=lambda binder: (
                binder.returned_at or binder.period_end or binder.period_start,
                binder.id,
            ),
        )
        index = 0
        while index < len(ordered):
            group_size = min(rng.randint(1, 3), len(ordered) - index)
            handover_binders = ordered[index:index + group_size]
            index += group_size
            handed_over_at = max(
                (binder.returned_at or binder.period_end or binder.period_start)
                for binder in handover_binders
            )
            handover = BinderHandover(
                client_record_id=client_id,
                received_by_name=handover_binders[-1].pickup_person_name or full_name(rng),
                handed_over_at=handed_over_at,
                until_period_year=handed_over_at.year,
                until_period_month=handed_over_at.month,
                notes=rng.choice([
                    None,
                    "המסירה בוצעה במשרד הלקוח",
                    "הלקוח קיבל את כל החומר עד למועד זה",
                    "המסירה בוצעה לאחר תיאום טלפוני",
                ]),
                created_by=rng.choice(users).id,
                created_at=datetime.combine(handed_over_at, datetime.min.time(), tzinfo=UTC)
                + timedelta(hours=rng.randint(9, 18)),
            )
            handover.client_id = client_id
            db.add(handover)
            db.flush()
            handovers.append(handover)

            for binder in handover_binders:
                db.add(BinderHandoverBinder(handover_id=handover.id, binder_id=binder.id))

    db.flush()
    return handovers


def create_binder_intake_edit_logs(db, rng: Random, intakes, users) -> list[BinderIntakeEditLog]:
    logs: list[BinderIntakeEditLog] = []
    if not intakes or not users:
        return logs

    sample_size = min(len(intakes), max(1, len(intakes) // 3))
    sampled_intakes = rng.sample(intakes, sample_size)
    for intake in sampled_intakes:
        edit_time = datetime.combine(intake.received_at, datetime.min.time(), tzinfo=UTC) + timedelta(
            days=rng.randint(0, 10),
            hours=rng.randint(9, 18),
        )

        note_suffix = rng.choice([
            "הושלם לאחר שיחת הבהרה עם הלקוח",
            "עודכן לאחר קליטת החומר במשרד",
            "נוספה הערה לאחר בדיקת מסמכים",
        ])
        old_notes = intake.notes or None
        new_notes = note_suffix if not intake.notes else f"{intake.notes}. {note_suffix}"
        note_log = BinderIntakeEditLog(
            intake_id=intake.id,
            field_name="notes",
            old_value=old_notes,
            new_value=new_notes,
            changed_by=rng.choice(users).id,
            changed_at=edit_time,
        )
        intake.notes = new_notes
        db.add(note_log)
        logs.append(note_log)

        if rng.random() < 0.4:
            shifted_date = intake.received_at + timedelta(days=1)
            date_log = BinderIntakeEditLog(
                intake_id=intake.id,
                field_name="received_at",
                old_value=str(intake.received_at),
                new_value=str(shifted_date),
                changed_by=rng.choice(users).id,
                changed_at=edit_time + timedelta(minutes=15),
            )
            intake.received_at = shifted_date
            db.add(date_log)
            logs.append(date_log)

    db.flush()
    return logs
