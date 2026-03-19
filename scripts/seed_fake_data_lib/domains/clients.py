from __future__ import annotations

from datetime import date, timedelta
from random import Random

from sqlalchemy import func, select

from app.businesses.models.business import Business, BusinessStatus, BusinessType
from app.clients.models.client import Client

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
        if rng.random() < 0.25:
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
            phone=f"05{rng.randint(10000000, 99999999)}",
            email=f"client{serial}@example.com",
            notes=rng.choice(["", "לקוח VIP", "מעדיף וואטסאפ", "מעקב חודשי"]),
            address_street=address_street,
            address_building_number=address_building_number,
            address_apartment=address_apartment,
            address_city=address_city,
            address_zip_code=address_zip_code,
        )
        db.add(client)
        clients.append(client)
    db.flush()
    return clients


def create_businesses(db, rng: Random, clients: list[Client]) -> list[Business]:
    businesses: list[Business] = []
    existing_businesses = int(db.execute(select(func.count()).select_from(Business)).scalar_one())
    for i, client in enumerate(clients):
        serial = existing_businesses + i + 1
        open_days_ago = rng.randint(20, 1100)
        opened_at = date.today() - timedelta(days=open_days_ago)
        status = rng.choices(
            [BusinessStatus.ACTIVE, BusinessStatus.FROZEN, BusinessStatus.CLOSED],
            weights=[80, 12, 8],
            k=1,
        )[0]
        closed_at = None
        if status == BusinessStatus.CLOSED:
            closed_at = opened_at + timedelta(days=rng.randint(30, 800))
            if closed_at > date.today():
                closed_at = date.today() - timedelta(days=rng.randint(1, 15))

        business_type = rng.choice(list(BusinessType))
        if business_type == BusinessType.COMPANY:
            business_name = f'{rng.choice(COMPANY_WORDS)} {rng.choice(COMPANY_WORDS)} בע"מ'
        elif business_type == BusinessType.EMPLOYEE:
            business_name = None
        else:
            business_name = f"{client.full_name} - {rng.choice(['עצמאי', 'עסק'])}"

        business = Business(
            client_id=client.id,
            business_name=business_name,
            business_type=business_type,
            status=status,
            primary_binder_number=f"PB-{50000 + serial}",
            opened_at=opened_at,
            closed_at=closed_at,
            notes=rng.choice(["", "עסק ותיק", "מעקב חודשי", "לקוח חשוב"]),
        )
        db.add(business)
        businesses.append(business)
    db.flush()
    return businesses
