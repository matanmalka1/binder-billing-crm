from app.authority_contact.models.authority_contact import (
    AuthorityContact,
    AuthorityContactLink,
    ContactType,
)


def test_authority_contact_repr_includes_key_fields():
    contact = AuthorityContact(
        id=12,
        business_id=34,
        contact_type=ContactType.ASSESSING_OFFICER,
        name="Officer Name",
    )

    rendered = repr(contact)

    assert "id=12" in rendered
    assert "business_id=34" in rendered
    assert "Officer Name" in rendered


def test_authority_contact_link_repr_includes_relation_fields():
    link = AuthorityContactLink(contact_id=7, client_id=8, business_id=9)

    rendered = repr(link)

    assert "contact_id=7" in rendered
    assert "client_id=8" in rendered
    assert "business_id=9" in rendered
