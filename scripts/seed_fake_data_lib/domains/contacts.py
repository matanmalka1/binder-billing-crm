from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.clients.models.client_tax_profile import ClientTaxProfile, VatType
from app.correspondence.models.correspondence import Correspondence, CorrespondenceType


def create_authority_contacts(db, rng: Random, cfg, clients):
    contacts = []
    for client in clients:
        num = rng.randint(
            cfg.min_authority_contacts_per_client,
            cfg.max_authority_contacts_per_client,
        )
        for idx in range(num):
            contact = AuthorityContact(
                client_id=client.id,
                contact_type=rng.choice(list(ContactType)),
                name=rng.choice([
                    "Ayala Ben David",
                    "Ofir Zadok",
                    "Niv Rahamim",
                    "Moran Tal",
                ]),
                office=rng.choice(["Tel Aviv", "Jerusalem", "Haifa", "Beer Sheva"]),
                phone=f"07{rng.randint(10000000, 99999999)}",
                email=f"contact{client.id}-{idx}@authority.example",
                notes=rng.choice(["", "Preferred via WhatsApp", "Banking contact"]),
                created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 300)),
                updated_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 90)),
            )
            db.add(contact)
            contacts.append(contact)
    db.flush()
    return contacts


def create_client_tax_profiles(db, rng: Random, clients):
    for client in clients:
        if rng.random() > 0.7:
            continue

        profile = ClientTaxProfile(
            client_id=client.id,
            vat_type=rng.choice(list(VatType)),
            business_type=rng.choice([
                None,
                "self_employed",
                "company",
                "non_profit",
            ]),
            tax_year_start=rng.choice([1, 4, 7, 10, None]),
            accountant_name=rng.choice([
                None,
                "Green & Co.",
                "TaxWise",
                "Levi Accounting",
            ]),
            created_at=datetime.now(UTC) - timedelta(days=rng.randint(0, 200)),
        )
        db.add(profile)
    db.flush()


def create_correspondence(db, rng: Random, clients, users):
    for client in clients:
        if rng.random() > 0.5:
            continue

        num_entries = rng.randint(1, 5)
        for _ in range(num_entries):
            occurred_at = datetime.now(UTC) - timedelta(days=rng.randint(0, 120))
            entry = Correspondence(
                client_id=client.id,
                contact_id=None,
                correspondence_type=rng.choice(list(CorrespondenceType)),
                subject=rng.choice([
                    "Discussed tax payment plan",
                    "Submitted missing documents",
                    "Scheduled meeting with authority",
                    "Client requested clarification",
                ]),
                notes=rng.choice([
                    None,
                    "Follow up next week",
                    "Email summary sent",
                    "Awaiting response",
                ]),
                occurred_at=occurred_at,
                created_by=rng.choice(users).id,
                created_at=occurred_at,
            )
            db.add(entry)
    db.flush()
