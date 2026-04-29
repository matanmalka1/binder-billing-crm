from app.authority_contact.models.authority_contact import ContactType
from scripts.seed_fake_data_lib.authority_offices import (
    authority_contact_type,
    authority_office_name,
)


def test_authority_office_names_use_client_city():
    city = "חיפה"

    assert authority_office_name(ContactType.ASSESSING_OFFICER, city) == "פקיד שומה חיפה"
    assert authority_office_name(ContactType.VAT_BRANCH, city) == 'משרד מע"מ חיפה'
    assert authority_office_name(ContactType.NATIONAL_INSURANCE, city) == "ביטוח לאומי חיפה"


def test_authority_contact_types_prioritize_tax_vat_and_national_insurance():
    assert [authority_contact_type(index) for index in range(3)] == [
        ContactType.ASSESSING_OFFICER,
        ContactType.VAT_BRANCH,
        ContactType.NATIONAL_INSURANCE,
    ]
