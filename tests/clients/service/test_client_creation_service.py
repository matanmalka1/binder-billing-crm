from app.clients.models.client_record import ClientRecord
from app.clients.models.legal_entity import LegalEntity
from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import (
    PersonLegalEntityLink,
    PersonLegalEntityRole,
)
from app.clients.services.client_creation_service import ClientCreationService
from app.common.enums import IdNumberType


def test_create_client_creates_legacy_and_identity_graph(test_db):
    service = ClientCreationService(test_db)

    client_record = service.create_client(
        full_name="Client Identity",
        id_number="123456780",
        id_number_type=IdNumberType.INDIVIDUAL,
        phone="0501234567",
        email="client@example.com",
        address_city="תל אביב",
        accountant_name="רו\"ח בדיקה",
        actor_id=7,
    )

    person = test_db.query(Person).filter(Person.id_number == "123456780").one()
    legal_entity = test_db.query(LegalEntity).filter(LegalEntity.id == client_record.legal_entity_id).one()
    link = (
        test_db.query(PersonLegalEntityLink)
        .filter(
            PersonLegalEntityLink.person_id == person.id,
            PersonLegalEntityLink.legal_entity_id == legal_entity.id,
        )
        .one()
    )
    stored_record = test_db.query(ClientRecord).filter(ClientRecord.id == client_record.id).one()

    assert stored_record.id == client_record.id
    assert stored_record.office_client_number == client_record.office_client_number
    assert stored_record.accountant_name == 'רו"ח בדיקה'
    assert legal_entity.id_number == "123456780"
    assert legal_entity.official_name == "Client Identity"
    assert person.full_name == "Client Identity"
    assert person.phone == "0501234567"
    assert person.email == "client@example.com"
    assert person.address_city == "תל אביב"
    assert link.role == PersonLegalEntityRole.OWNER
