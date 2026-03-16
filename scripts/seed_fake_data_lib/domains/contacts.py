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
                    "אילה בן דוד",
                    "אופיר צדוק",
                    "ניב רחמים",
                    "מורן טל",
                ]),
                office=rng.choice(["תל אביב", "ירושלים", "חיפה", "באר שבע"]),
                phone=f"07{rng.randint(10000000, 99999999)}",
                email=f"person{client.id}-{idx}@rashut.example",
                notes=rng.choice(["", "מעדיף וואטסאפ", "איש קשר לבנק"]),
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
                "עצמאי",
                "חברה",
                "עמותה",
            ]),
            tax_year_start=rng.choice([1, 4, 7, 10, None]),
            accountant_name=rng.choice([
                None,
                "כהן ושות׳ רואי חשבון",
                "חשבית פלוס",
                "לוי הנהלת חשבונות",
            ]),
            advance_rate=rng.choice([None, None, 2.5, 3.0, 4.0, 5.5, 7.0]),
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
                    "דיון בתוכנית תשלום מס",
                    "הגשת מסמכים חסרים",
                    "פגישה מתוכננת עם הרשות",
                    "הלקוח ביקש הבהרה",
                ]),
                notes=rng.choice([
                    None,
                    "מעקב שבוע הבא",
                    "סיכום שנשלח במייל",
                    "ממתין לתגובה",
                ]),
                occurred_at=occurred_at,
                created_by=rng.choice(users).id,
                created_at=occurred_at,
            )
            db.add(entry)
    db.flush()
