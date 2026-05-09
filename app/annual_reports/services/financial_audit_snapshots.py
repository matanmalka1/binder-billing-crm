"""Audit payload helpers for annual report financial lines."""


def audit_scalar(value):
    return (
        value.value
        if hasattr(value, "value")
        else str(value)
        if value is not None
        else None
    )


def income_line_snapshot(line) -> dict:
    return {
        "line_id": line.id,
        "source_type": audit_scalar(line.source_type),
        "amount": str(line.amount),
        "description": line.description,
    }


def expense_line_snapshot(line) -> dict:
    return {
        "line_id": line.id,
        "category": audit_scalar(line.category),
        "amount": str(line.amount),
        "description": line.description,
    }
