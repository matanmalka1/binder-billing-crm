"""VAT Compliance Report: per-client period coverage and stale pending flags."""

from datetime import date

from sqlalchemy.orm import Session

try:
    from tax_rules.registry import get_effective_periodic_date as _get_periodic_date
    from app.vat_reports.services.constants import VAT_STATUTORY_DEADLINE_DAY as _VAT_FALLBACK_DAY
    _CALENDAR_COLUMN = "effective_vat_periodic_and_income_tax_advances"
    _CALENDAR_AVAILABLE = True
except Exception:
    _CALENDAR_AVAILABLE = False
    _VAT_FALLBACK_DAY = 15


def _vat_deadline(period_year: int, period_month: int) -> date:
    filing_year = period_year if period_month < 12 else period_year + 1
    filing_month = (period_month % 12) + 1
    calendar_period = f"{period_year}-{period_month:02d}"
    if _CALENDAR_AVAILABLE:
        try:
            raw = _get_periodic_date(filing_year, calendar_period, _CALENDAR_COLUMN)
            if raw:
                return date.fromisoformat(raw)
        except KeyError:
            pass
    return date(filing_year, filing_month, _VAT_FALLBACK_DAY)

from app.clients.models.legal_entity import LegalEntity
from app.clients.repositories.client_record_repository import ClientRecordRepository
from app.reports.constants import VAT_STALE_PENDING_DAYS
from app.utils.time_utils import utcnow
from app.vat_reports.repositories.vat_compliance_repository import VatComplianceRepository


class VatComplianceReportService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = VatComplianceRepository(db)
        self.client_repo = ClientRecordRepository(db)

    def get_vat_compliance_report(self, year: int) -> dict:
        rows = self.repo.get_compliance_aggregates(year)
        filed_items = self.repo.get_filed_items(year)
        client_name_map = self._client_name_map([r.client_record_id for r in rows])

        # ── On-time / late counts per business ───────────────────────────────
        on_time_map: dict[tuple[int, str], int] = {}
        late_map: dict[tuple[int, str], int] = {}
        for fi in filed_items:
            period_year = int(fi.period[:4])
            period_month = int(fi.period[5:7])
            deadline = _vat_deadline(period_year, period_month)
            filed_date = fi.filed_at.date() if hasattr(fi.filed_at, "date") else fi.filed_at
            is_late = filed_date > deadline
            bucket = late_map if is_late else on_time_map
            period_type = str(fi.period_type.value)
            key = (fi.client_record_id, period_type)
            bucket[key] = bucket.get(key, 0) + 1

        items = []
        for r in rows:
            client_name = client_name_map.get(r.client_record_id)
            if client_name is None:
                continue
            period_type = str(r.period_type.value)
            grouping_key = f"{r.client_record_id}:{year}:{period_type}"
            count_key = (r.client_record_id, period_type)
            expected = int(r.periods_expected)
            filed = int(r.periods_filed or 0)
            on_time = on_time_map.get(count_key, 0)
            late = late_map.get(count_key, 0)
            items.append(
                {
                    "client_record_id": r.client_record_id,
                    "client_name": client_name,
                    "year": year,
                    "period_type": period_type,
                    "reporting_frequency": period_type,
                    "grouping_key": grouping_key,
                    "periods_expected": expected,
                    "periods_filed": filed,
                    "periods_open": expected - filed,
                    "on_time_count": on_time,
                    "late_count": late,
                    "compliance_rate": round(filed / expected * 100, 2) if expected else 0.0,
                }
            )

        # ── Stale PENDING_MATERIALS ───────────────────────────────────────────
        threshold = utcnow().replace(tzinfo=None)
        stale_pending = []
        stale_rows = self.repo.get_stale_pending(year)
        stale_name_map = self._client_name_map([r.client_record_id for r in stale_rows])
        for sr in stale_rows:
            client_name = stale_name_map.get(sr.client_record_id)
            if client_name is None:
                continue
            days_pending = (threshold - sr.updated_at).days
            if days_pending >= VAT_STALE_PENDING_DAYS:
                stale_pending.append(
                    {
                        "client_record_id": sr.client_record_id,
                        "client_name": client_name,
                        "period": sr.period,
                        "days_pending": days_pending,
                    }
                )

        return {
            "year": year,
            "total_clients": len(items),
            "items": items,
            "stale_pending": stale_pending,
        }

    def _client_name_map(self, client_record_ids: list[int]) -> dict[int, str]:
        records = self.client_repo.list_by_ids(list(set(client_record_ids)))
        legal_entity_ids = list({record.legal_entity_id for record in records})
        entities = (
            self.db.query(LegalEntity)
            .filter(LegalEntity.id.in_(legal_entity_ids))
            .all()
            if legal_entity_ids
            else []
        )
        entity_map = {entity.id: entity.official_name for entity in entities}
        return {
            record.id: entity_map[record.legal_entity_id]
            for record in records
            if record.legal_entity_id in entity_map
        }
