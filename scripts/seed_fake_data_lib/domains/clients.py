from __future__ import annotations

from datetime import date, timedelta
from random import Random

from sqlalchemy import func, select

from app.businesses.models.business import Business, BusinessStatus, BusinessType
from app.businesses.models.business_tax_profile import BusinessTaxProfile, VatType
from app.clients.models.client import Client, IdNumberType

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
        else:
            full_name_value = full_name(rng)
            id_number_type = IdNumberType.INDIVIDUAL
            id_number = generate_valid_israeli_id(serial, prefix=str(rng.choice([0, 1, 2, 3])))

        address_street = rng.choice(STREET_NAMES)
        address_building_number = str(rng.randint(1, 220))
        address_apartment = str(rng.randint(1, 30)) if rng.random() < 0.75 else None
        address_city = rng.choice(CITY_NAMES)
        address_zip_code = f"{rng.randint(1000000, 9999999)}"

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
        if client.id in multi_business_client_ids:
            business_count = rng.randint(2, 3)

        chosen_types: list[BusinessType] = []
        # Israeli VAT law: cannot mix osek_patur and osek_murshe for the same person.
        # Multiple businesses of the SAME sole-trader type are allowed.
        sole_trader_type_chosen: BusinessType | None = None
        available_types = list(BusinessType)
        _SOLE_TRADER = {BusinessType.OSEK_PATUR, BusinessType.OSEK_MURSHE}
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

            preferred_types = [BusinessType.COMPANY, BusinessType.OSEK_MURSHE] if business_index == 0 else available_types
            remaining_types = [
                bt for bt in available_types
                if bt in preferred_types
                if bt not in chosen_types
                and not (
                    bt in _SOLE_TRADER
                    and sole_trader_type_chosen is not None
                    and bt != sole_trader_type_chosen
                )
            ]
            business_type = rng.choice(remaining_types or [BusinessType.COMPANY, BusinessType.EMPLOYEE])
            if business_type in _SOLE_TRADER and sole_trader_type_chosen is None:
                sole_trader_type_chosen = business_type
            chosen_types.append(business_type)

            if business_type == BusinessType.COMPANY:
                base_name = f'{rng.choice(COMPANY_WORDS)} {rng.choice(COMPANY_WORDS)} בע"מ'
                business_name = base_name if business_index == 0 else f"{base_name} {business_index + 1}"
            elif business_type == BusinessType.EMPLOYEE:
                business_name = None
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
                business_type=business_type,
                tax_id_number=generate_valid_israeli_id(serial, prefix="5"),
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


def create_business_tax_profiles(db, rng: Random, businesses: list[Business]) -> list[BusinessTaxProfile]:
    profiles: list[BusinessTaxProfile] = []
    for business in businesses:
        if business.business_type == BusinessType.OSEK_PATUR:
            vat_type = VatType.EXEMPT
        elif business.business_type == BusinessType.COMPANY:
            vat_type = rng.choice([VatType.MONTHLY, VatType.BIMONTHLY, VatType.MONTHLY])
        elif business.business_type == BusinessType.EMPLOYEE:
            vat_type = VatType.EXEMPT
        else:
            vat_type = rng.choice([VatType.MONTHLY, VatType.BIMONTHLY])

        tax_year_start = rng.choice([1, 1, 1, 4, 7, 10])
        advance_rate = (
            None
            if business.business_type == BusinessType.EMPLOYEE
            else rng.choice([None, 2.5, 3.0, 4.0, 5.5, 7.0])
        )
        advance_rate_updated_at = (
            None
            if advance_rate is None
            else date.today() - timedelta(days=rng.randint(10, 220))
        )
        profile = BusinessTaxProfile(
            business_id=business.id,
            vat_type=vat_type,
            vat_start_date=business.opened_at,
            accountant_name=rng.choice(
                [
                    None,
                    "כהן ושות׳ רואי חשבון",
                    "חשבית פלוס",
                    "לוי הנהלת חשבונות",
                ]
            ),
            vat_exempt_ceiling=rng.choice([None, None, 120000, 132000]) if vat_type == VatType.EXEMPT else None,
            advance_rate=advance_rate,
            advance_rate_updated_at=advance_rate_updated_at,
            business_type=business.business_type.value,
            tax_year_start=tax_year_start,
            fiscal_year_start_month=tax_year_start,
        )
        db.add(profile)
        profiles.append(profile)
    db.flush()
    return profiles
