from __future__ import annotations

from datetime import date, timedelta
from random import Random

from sqlalchemy import func, select

from app.businesses.models.business import Business, BusinessStatus
from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.common.enums import EntityType, IdNumberType, VatType
from app.notes.models.entity_note import EntityNote

from ..business_names import seed_business_name
from ..demo_catalog import (
    BUSINESS_CATALOG,
    BUSINESS_NOTES,
    CLIENT_NOTES,
    ENTITY_NOTE_TEXTS,
    REALISTIC_ADDRESSES,
    demo_email,
    mobile_phone,
)
from ..random_utils import full_name, generate_valid_israeli_id
from .client_graph import SeedClient


def create_clients(db, rng: Random, cfg, users=None) -> list[SeedClient]:
    clients: list[SeedClient] = []
    existing_clients = int(db.execute(select(func.count()).select_from(ClientRecord)).scalar_one())
    existing_max_office_number = db.execute(select(func.max(ClientRecord.office_client_number))).scalar_one()
    next_office_client_number = (existing_max_office_number or 0) + 1
    for i in range(cfg.clients):
        serial = existing_clients + i + 1
        is_corporation = rng.random() < 0.25
        address = rng.choice(REALISTIC_ADDRESSES)
        if is_corporation:
            full_name_value = BUSINESS_CATALOG[(serial - 1) % len(BUSINESS_CATALOG)]
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

        address_street = address["street"]
        address_building_number = str(rng.randint(1, 220))
        address_apartment = str(rng.randint(1, 30)) if rng.random() < 0.75 else None
        address_city = address["city"]
        address_zip_code = address["zip_code"]
        advance_rate = None if entity_type == EntityType.EMPLOYEE else round(rng.uniform(2.0, 12.0), 2)
        advance_rate_updated_at = (
            date.today() - timedelta(days=rng.randint(0, 540))
            if advance_rate is not None
            else None
        )
        phone = mobile_phone(rng)
        email = demo_email("client", serial)
        legal_entity = LegalEntity(
            official_name=full_name_value,
            id_number=id_number,
            id_number_type=id_number_type,
            entity_type=entity_type,
            vat_reporting_frequency=vat_reporting_frequency,
            vat_exempt_ceiling=vat_exempt_ceiling,
            advance_rate=advance_rate,
            advance_rate_updated_at=advance_rate_updated_at,
        )
        db.add(legal_entity)
        db.flush()
        person = Person(
            full_name=full_name_value,
            id_number=id_number,
            id_number_type=IdNumberType.OTHER if id_number_type == IdNumberType.CORPORATION else id_number_type,
            phone=phone,
            email=email,
            address_street=address_street,
            address_building_number=address_building_number,
            address_apartment=address_apartment,
            address_city=address_city,
            address_zip_code=address_zip_code,
        )
        db.add(person)
        db.flush()
        db.add(
            PersonLegalEntityLink(
                person_id=person.id,
                legal_entity_id=legal_entity.id,
                role=PersonLegalEntityRole.OWNER,
            )
        )
        db.flush()
        client_record = ClientRecord(
            legal_entity_id=legal_entity.id,
            office_client_number=next_office_client_number,
            notes=rng.choice(CLIENT_NOTES),
            accountant_id=rng.choice(users).id if users else None,
        )
        db.add(client_record)
        db.flush()
        client = SeedClient(
            id=client_record.id,
            legal_entity_id=legal_entity.id,
            office_client_number=client_record.office_client_number,
            full_name=full_name_value,
            email=email,
            phone=phone,
            city=address_city,
            entity_type=entity_type,
            vat_reporting_frequency=vat_reporting_frequency,
        )
        clients.append(client)
        next_office_client_number += 1
    db.flush()
    return clients


def create_businesses(db, rng: Random, clients: list[SeedClient], users=None) -> list[Business]:
    businesses: list[Business] = []
    existing_businesses = int(db.execute(select(func.count()).select_from(Business)).scalar_one())
    used_names = set(db.execute(select(Business.business_name)).scalars().all())
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

            business_name = seed_business_name(
                client_full_name=client.full_name,
                entity_type=default_type,
                business_index=business_index,
                serial=serial,
                rng=rng,
                used_names=used_names,
            )

            business = Business(
                legal_entity_id=client.legal_entity_id,
                business_name=business_name,
                status=status,
                opened_at=opened_at,
                closed_at=closed_at,
                phone_override=client.phone,
                email_override=client.email,
                created_by=rng.choice(users).id if users else None,
                notes=rng.choice(BUSINESS_NOTES),
            )
            # Seed helpers still group businesses through the owning client record.
            # Keep that linkage in-memory without reintroducing a DB column.
            business.client_id = client.id
            business.client = client
            db.add(business)
            businesses.append(business)
    db.flush()
    return businesses


def create_entity_notes(db, rng: Random, clients: list[SeedClient], users) -> None:
    for client in rng.sample(clients, min(len(clients), max(1, len(clients) // 2))):
        note = EntityNote(
            entity_type="client",
            entity_id=client.id,
            note=rng.choice(ENTITY_NOTE_TEXTS),
            created_by=rng.choice(users).id if users else None,
        )
        db.add(note)
    db.flush()
