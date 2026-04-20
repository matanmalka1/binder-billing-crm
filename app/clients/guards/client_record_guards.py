from app.core.exceptions import ConflictError


def assert_client_record_is_active(client_record) -> None:
    if client_record and getattr(client_record, "status", None) in ("closed", "frozen"):
        raise ConflictError("CLIENT_RECORD.CLOSED", "CLIENT_RECORD.CLOSED")
