from app.binders.models.binder import BinderStatus
from app.common.enums import EntityType
from app.annual_reports.models.annual_report_enums import ClientTypeForReport

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_CLIENT_IMPORT_UPLOAD_SIZE = 10 * 1024 * 1024
CLIENT_STATUS_CARD_YEAR_MIN = 2000
CLIENT_STATUS_CARD_YEAR_MAX = 2100

CLIENT_EXPORT_COLUMNS = [
    ("id", "ID"),
    ("full_name", "Full Name"),
    ("id_number", "ID Number"),
    ("phone", "Phone"),
    ("email", "Email"),
    ("address_street", "Street"),
    ("address_city", "City"),
    ("notes", "Notes"),
]

CLIENT_TEMPLATE_COLUMNS = [
    ("full_name", "Full Name"),
    ("id_number", "ID Number"),
    ("phone", "Phone (optional)"),
    ("email", "Email (optional)"),
]

CLIENT_TEMPLATE_SAMPLE_ROW = ["יוסי כהן", "123456789", "0501234567", "yossi@example.com"]
CLIENT_EXCEL_SHEET_TITLE = "Clients"
CLIENT_EXCEL_FREEZE_PANES = "A2"

AUTO_BINDER_SEQUENCE = 1
AUTO_BINDER_INITIAL_STATUS = BinderStatus.IN_OFFICE.value
AUTO_BINDER_STATUS_LOG_OLD_VALUE = "null"
AUTO_BINDER_STATUS_LOG_NOTES = "קלסר נפתח אוטומטית"

CLIENT_OBLIGATION_NEXT_YEAR_START_MONTH = 10
CLIENT_OBLIGATION_TRIGGER_FIELDS = frozenset({
    "entity_type",
    "vat_reporting_frequency",
})

ENTITY_TYPE_TO_REPORT_CLIENT_TYPE: dict[EntityType | None, ClientTypeForReport] = {
    EntityType.OSEK_PATUR: ClientTypeForReport.EXEMPT_DEALER,
    EntityType.OSEK_MURSHE: ClientTypeForReport.SELF_EMPLOYED,
    EntityType.COMPANY_LTD: ClientTypeForReport.CORPORATION,
    EntityType.EMPLOYEE: ClientTypeForReport.INDIVIDUAL,
    None: ClientTypeForReport.INDIVIDUAL,
}
