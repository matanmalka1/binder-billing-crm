from __future__ import annotations

from datetime import UTC, datetime, timedelta
from random import Random

from app.authority_contact.models.authority_contact import AuthorityContact, ContactType
from app.correspondence.models.correspondence import Correspondence, CorrespondenceType


def create_authority_contacts(db, rng: Random, cfg, clients, businesses):
    contacts = []
    now = datetime.now(UTC)
    businesses_by_client_id: dict[int, list] = {}
    for business in businesses:
        businesses_by_client_id.setdefault(business.client_id, []).append(business)

    for client in clients:
        num = rng.randint(
            cfg.min_authority_contacts_per_client,
            cfg.max_authority_contacts_per_client,
        )
        for idx in range(num):
            if not businesses_by_client_id.get(client.id):
                continue
            created_at = now - timedelta(days=rng.randint(0, 300))
            updated_at = min(now, created_at + timedelta(days=rng.randint(0, 90)))
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
                created_at=created_at,
                updated_at=updated_at,
            )
            db.add(contact)
            contacts.append(contact)
    db.flush()
    return contacts


def create_correspondence(db, rng: Random, businesses, users, authority_contacts):
    now = datetime.now(UTC)
    contacts_by_client_id: dict[int, list] = {}
    for contact in authority_contacts:
        contacts_by_client_id.setdefault(contact.client_id, []).append(contact)

    for business in businesses:
        num_entries = rng.randint(1, 5)
        for _ in range(num_entries):
            occurred_at = now - timedelta(days=rng.randint(0, 120))
            candidate_contacts = contacts_by_client_id.get(business.client_id, [])
            contact = rng.choice(candidate_contacts) if candidate_contacts and rng.random() < 0.65 else None
            entry = Correspondence(
                client_id=business.client_id,
                business_id=business.id,
                contact_id=contact.id if contact else None,
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
