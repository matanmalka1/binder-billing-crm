from app.utils.id_validation import validate_israeli_id_checksum


def test_validate_israeli_id_checksum_accepts_known_valid_ids():
    assert validate_israeli_id_checksum("100000009") is True
    assert validate_israeli_id_checksum("039337423") is True
    assert validate_israeli_id_checksum("123456782") is True


def test_validate_israeli_id_checksum_rejects_invalid_ids():
    assert validate_israeli_id_checksum("100000008") is False
    assert validate_israeli_id_checksum("123456789") is False
    assert validate_israeli_id_checksum("12345") is False
    assert validate_israeli_id_checksum("12A456789") is False
