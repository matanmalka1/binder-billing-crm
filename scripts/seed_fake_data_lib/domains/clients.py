from __future__ import annotations

from datetime import date, timedelta
from random import Random

from sqlalchemy import func, select

from app.clients.models.client import Client, ClientStatus, ClientType

from ..constants import COMPANY_WORDS
from ..random_utils import full_name

STREET_NAMES = [
    "הרצל",
    "בן יהודה",
    "ויצמן",
    "הנביאים",
    "אבן גבירול",
    "העצמאות",
    "ביאליק",
    "רוטשילד",
]

CITY_NAMES = [
    "תל אביב",
    "ירושלים",
    "חיפה",
    "באר שבע",
    "פתח תקווה",
    "ראשון לציון",
    "נתניה",
    "אשדוד",
]


def create_clients(db, rng: Random, cfg) -> list[Client]:
    clients: list[Client] = []
    existing_clients = int(db.execute(select(func.count()).select_from(Client)).scalar_one())
    for i in range(cfg.clients):
        serial = existing_clients + i + 1
        open_days_ago = rng.randint(20, 1100)
        opened_at = date.today() - timedelta(days=open_days_ago)
        status = rng.choices(
            [ClientStatus.ACTIVE, ClientStatus.FROZEN, ClientStatus.CLOSED],
            weights=[80, 12, 8],
            k=1,
        )[0]
        closed_at = None
        if status == ClientStatus.CLOSED:
            closed_at = opened_at + timedelta(days=rng.randint(30, 800))
            if closed_at > date.today():
                closed_at = date.today() - timedelta(days=rng.randint(1, 15))

        client_type = rng.choice(list(ClientType))
        if client_type == ClientType.COMPANY:
            full_name_value = f'{rng.choice(COMPANY_WORDS)} {rng.choice(COMPANY_WORDS)} בע"מ'
        else:
            full_name_value = full_name(rng)

        address_street = rng.choice(STREET_NAMES)
        address_building_number = str(rng.randint(1, 220))
        address_apartment = str(rng.randint(1, 30)) if rng.random() < 0.75 else None
        address_city = rng.choice(CITY_NAMES)
        address_zip_code = f"{rng.randint(1000000, 9999999)}"

        client = Client(
            full_name=full_name_value,
            id_number=f"{100000000 + serial}",
            client_type=client_type,
            status=status,
            primary_binder_number=f"PB-{50000 + serial}",
            phone=f"05{rng.randint(10000000, 99999999)}",
            email=f"client{serial}@example.com",
            notes=rng.choice(["", "לקוח VIP", "מעדיף וואטסאפ", "מעקב חודשי"]),
            address_street=address_street,
            address_building_number=address_building_number,
            address_apartment=address_apartment,
            address_city=address_city,
            address_zip_code=address_zip_code,
            opened_at=opened_at,
            closed_at=closed_at,
        )
        db.add(client)
        clients.append(client)
    db.flush()
    return clients
