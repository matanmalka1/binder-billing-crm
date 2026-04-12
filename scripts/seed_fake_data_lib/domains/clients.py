from __future__ import annotations

from datetime import date, timedelta
from random import Random

from sqlalchemy import func, select

from app.businesses.models.business import Business, BusinessStatus
from app.clients.models.client import Client, IdNumberType
from app.common.enums import EntityType, VatType

from ..constants import COMPANY_WORDS
from ..random_utils import full_name, generate_valid_israeli_id

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
        is_corporation = rng.random() < 0.25
        if is_corporation:
            full_name_value = f'{rng.choice(COMPANY_WORDS)} {rng.choice(COMPANY_WORDS)} בע"מ'
            id_number_type = IdNumberType.CORPORATION
            id_number = generate_valid_israeli_id(serial, prefix="5")
            entity_type = EntityType.COMPANY_LTD
            vat_reporting_frequency = rng.choice([VatType.MONTHLY, VatType.BIMONTHLY])
            vat_exempt_ceiling = None
        else:
            full_name_value = full_name(rng)
            id_number_type = IdNumberType.INDIVIDUAL
            id_number = generate_valid_israeli_id(serial, prefix=str(rng.choice([0, 1, 2, 3])))
            entity_type = rng.choices(
                population=[EntityType.OSEK_PATUR, EntityType.OSEK_MURSHE, EntityType.EMPLOYEE],
                weights=[25, 55, 20],
                k=1,
            )[0]
            if entity_type == EntityType.OSEK_PATUR:
                vat_reporting_frequency = VatType.EXEMPT
                vat_exempt_ceiling = 120000
            elif entity_type == EntityType.OSEK_MURSHE:
                vat_reporting_frequency = rng.choice([VatType.MONTHLY, VatType.BIMONTHLY])
                vat_exempt_ceiling = None
            else:
                vat_reporting_frequency = VatType.EXEMPT
                vat_exempt_ceiling = None

        address_street = rng.choice(STREET_NAMES)
        address_building_number = str(rng.randint(1, 220))
        address_apartment = str(rng.randint(1, 30)) if rng.random() < 0.75 else None
        address_city = rng.choice(CITY_NAMES)
        address_zip_code = f"{rng.randint(1000000, 9999999)}"
        advance_rate = None if entity_type == EntityType.EMPLOYEE else round(rng.uniform(2.0, 12.0), 2)
        advance_rate_updated_at = (
            date.today() - timedelta(days=rng.randint(0, 540))
            if advance_rate is not None
            else None
        )

        client = Client(
            full_name=full_name_value,
            id_number=id_number,
            id_number_type=id_number_type,
            phone=f"05{rng.randint(10000000, 99999999)}",
            email=f"client{serial}@example.com",
            notes=rng.choice(["", "לקוח VIP", "מעדיף וואטסאפ", "מעקב חודשי"]),
            address_street=address_street,
            address_building_number=address_building_number,
            address_apartment=address_apartment,
            address_city=address_city,
            address_zip_code=address_zip_code,
            entity_type=entity_type,
            vat_reporting_frequency=vat_reporting_frequency,
            vat_exempt_ceiling=vat_exempt_ceiling,
            advance_rate=advance_rate,
            advance_rate_updated_at=advance_rate_updated_at,
            accountant_name=rng.choice(["רו\"ח דנה לוי", "רו\"ח אמיר כהן", "רו\"ח נטע מזרחי"]),
        )
        db.add(client)
        clients.append(client)
    db.flush()
    return clients


def create_businesses(db, rng: Random, clients: list[Client], users=None) -> list[Business]:
    businesses: list[Business] = []
    existing_businesses = int(db.execute(select(func.count()).select_from(Business)).scalar_one())
    multi_business_target = max(1, round(len(clients) * 0.2))
    multi_business_client_ids = {
        client.id for client in rng.sample(clients, k=min(multi_business_target, len(clients)))
    }
    serial = existing_businesses
    for client in clients:
        business_count = 1
        if client.id in multi_business_client_ids and client.entity_type != EntityType.EMPLOYEE:
            business_count = rng.randint(2, 3)

        for business_index in range(business_count):
            serial += 1
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

            if client.entity_type == EntityType.COMPANY_LTD:
                default_type = EntityType.COMPANY_LTD
            elif client.entity_type == EntityType.OSEK_PATUR:
                default_type = EntityType.OSEK_PATUR
            elif client.entity_type == EntityType.OSEK_MURSHE:
                default_type = EntityType.OSEK_MURSHE
            else:
                default_type = EntityType.EMPLOYEE

            if default_type == EntityType.COMPANY_LTD:
                base_name = f'{rng.choice(COMPANY_WORDS)} {rng.choice(COMPANY_WORDS)} בע"מ'
                business_name = base_name if business_index == 0 else f"{base_name} {business_index + 1}"
            elif default_type == EntityType.EMPLOYEE:
                business_name = (
                    "הכנסת שכר"
                    if business_count == 1
                    else f"הכנסת שכר {business_index + 1}"
                )
            else:
                label = rng.choice(["עצמאי", "עסק", "פעילות"])
                business_name = (
                    f"{client.full_name} - {label}"
                    if business_count == 1
                    else f"{client.full_name} - {label} {business_index + 1}"
                )

            business = Business(
                client_id=client.id,
                business_name=business_name,
                status=status,
                opened_at=opened_at,
                closed_at=closed_at,
                phone=client.phone,
                email=client.email,
                created_by=rng.choice(users).id if users else None,
                notes=rng.choice(["", "עסק ותיק", "מעקב חודשי", "לקוח חשוב"]),
            )
            db.add(business)
            businesses.append(business)
    db.flush()
    return businesses
