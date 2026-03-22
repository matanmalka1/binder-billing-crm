from __future__ import annotations

from datetime import date
from itertools import count

from app.businesses.models.business import Business, BusinessStatus
from app.clients.models.client import Client

_seq = count(1)


def create_business(test_db, *, name_prefix: str = "Tax Deadline", status: BusinessStatus = BusinessStatus.ACTIVE) -> Business:
    idx = next(_seq)
    client = Client(
        full_name=f"{name_prefix} {idx}",
        id_number=f"TD{idx:09d}",
    )
    test_db.add(client)
    test_db.commit()

    business = test_db.query(Business).filter(Business.client_id == client.id).first()
    assert business is not None

    if business.status != status:
        business.status = status
        test_db.commit()

    test_db.refresh(business)
    return business
