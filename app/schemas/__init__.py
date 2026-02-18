"""Compatibility layer for legacy app.schemas imports.
Prefer importing from feature package schemas (e.g., app.binders.schemas).*"""
from app.binders.schemas.binder_extended import (
    BinderDetailResponse,
    BinderListResponseExtended,
    BinderHistoryEntry,
    BinderHistoryResponse,
)

__all__ = [
    'BinderDetailResponse',
    'BinderListResponseExtended',
    'BinderHistoryEntry',
    'BinderHistoryResponse',
]
