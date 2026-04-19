"""Serialization helpers for VAT API responses."""

from app.vat_reports.schemas.vat_report import VatWorkItemResponse
from app.vat_reports.services.vat_report_queries import compute_deadline_fields
from app.vat_reports.services.vat_report_service import VatReportService


def serialize_enriched_work_item(
    item,
    *,
    office_client_number_map: dict,
    name_map: dict,
    id_number_map: dict,
    status_map: dict,
    user_map: dict,
) -> VatWorkItemResponse:
    data = VatWorkItemResponse.model_validate(item)
    data.office_client_number = office_client_number_map.get(item.client_id)
    data.client_name = name_map.get(item.client_id)
    data.client_id_number = id_number_map.get(item.client_id)
    data.client_status = status_map.get(item.client_id)
    deadline = compute_deadline_fields(item, submission_method=item.submission_method)
    data.submission_deadline = deadline["submission_deadline"]
    data.statutory_deadline = deadline["statutory_deadline"]
    data.extended_deadline = deadline["extended_deadline"]
    data.days_until_deadline = deadline["days_until_deadline"]
    data.is_overdue = deadline["is_overdue"]
    data.assigned_to_name = user_map.get(item.assigned_to) if item.assigned_to else None
    data.filed_by_name = user_map.get(item.filed_by) if item.filed_by else None
    return data


def serialize_work_item(service: VatReportService, item_id: int) -> VatWorkItemResponse:
    enriched = service.get_work_item_enriched(item_id)
    return serialize_enriched_work_item(
        enriched["item"],
        office_client_number_map=enriched["office_client_number_map"],
        name_map=enriched["name_map"],
        id_number_map=enriched["id_number_map"],
        status_map=enriched["status_map"],
        user_map=enriched["user_map"],
    )
