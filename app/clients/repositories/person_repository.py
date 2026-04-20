from typing import Optional

from sqlalchemy.orm import Session

from app.clients.models.person import Person
from app.clients.models.person_legal_entity_link import PersonLegalEntityLink, PersonLegalEntityRole
from app.common.enums import IdNumberType


class PersonRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        full_name: str,
        id_number: str,
        id_number_type: IdNumberType,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address_street: Optional[str] = None,
        address_building_number: Optional[str] = None,
        address_apartment: Optional[str] = None,
        address_city: Optional[str] = None,
        address_zip_code: Optional[str] = None,
    ) -> Person:
        person = Person(
            full_name=full_name,
            id_number=id_number,
            id_number_type=id_number_type,
            phone=phone,
            email=email,
            address_street=address_street,
            address_building_number=address_building_number,
            address_apartment=address_apartment,
            address_city=address_city,
            address_zip_code=address_zip_code,
        )
        self.db.add(person)
        self.db.flush()
        return person

    def get_by_id_number(
        self, id_number_type: IdNumberType, id_number: str
    ) -> Optional[Person]:
        return (
            self.db.query(Person)
            .filter(
                Person.id_number_type == id_number_type,
                Person.id_number == id_number,
            )
            .first()
        )

    def create_link(
        self,
        *,
        person_id: int,
        legal_entity_id: int,
        role: PersonLegalEntityRole = PersonLegalEntityRole.OWNER,
    ) -> PersonLegalEntityLink:
        link = PersonLegalEntityLink(
            person_id=person_id,
            legal_entity_id=legal_entity_id,
            role=role,
        )
        self.db.add(link)
        self.db.flush()
        return link

    def get_owner_for_legal_entity(self, legal_entity_id: int) -> Optional[Person]:
        return (
            self.db.query(Person)
            .join(
                PersonLegalEntityLink,
                PersonLegalEntityLink.person_id == Person.id,
            )
            .filter(
                PersonLegalEntityLink.legal_entity_id == legal_entity_id,
                PersonLegalEntityLink.role == PersonLegalEntityRole.OWNER,
            )
            .first()
        )

    def ensure_owner(
        self, *, legal_entity_id: int, full_name: str, id_number: str,
        id_number_type: IdNumberType, **fields,
    ) -> None:
        # ck_persons_id_number_type_not_corporation — skip for CORPORATION.
        if id_number_type == IdNumberType.CORPORATION:
            return
        person = self.get_by_id_number(id_number_type, id_number)
        if not person:
            person = self.create(
                full_name=full_name, id_number=id_number,
                id_number_type=id_number_type, **fields,
            )
        if not self.get_owner_for_legal_entity(legal_entity_id):
            self.create_link(person_id=person.id, legal_entity_id=legal_entity_id)
