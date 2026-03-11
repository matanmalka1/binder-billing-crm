"""Compatibility re-export for annual report schemas."""

from app.annual_reports.schemas.annual_report_requests import (
    AmendRequest,
    AnnualReportCreateRequest,
    DeadlineUpdateRequest,
    ScheduleAddRequest,
    ScheduleCompleteRequest,
    StageTransitionRequest,
    StatusTransitionRequest,
    SubmitRequest,
)
from app.annual_reports.schemas.annual_report_responses import (
    AnnualReportDetailResponse,
    AnnualReportListResponse,
    AnnualReportResponse,
    ScheduleEntryResponse,
    SeasonSummaryResponse,
    StatusHistoryResponse,
)

__all__ = [
    "AmendRequest",
    "AnnualReportCreateRequest",
    "AnnualReportDetailResponse",
    "AnnualReportListResponse",
    "AnnualReportResponse",
    "DeadlineUpdateRequest",
    "ScheduleAddRequest",
    "ScheduleCompleteRequest",
    "ScheduleEntryResponse",
    "SeasonSummaryResponse",
    "StageTransitionRequest",
    "StatusHistoryResponse",
    "StatusTransitionRequest",
    "SubmitRequest",
]
