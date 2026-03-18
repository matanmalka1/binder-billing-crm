from sqlalchemy import Enum as SAEnum


def pg_enum(enum_class, **kwargs):
    """
    Drop-in replacement for Column(Enum(MyEnum)) that forces SQLAlchemy
    to use the Python enum's .value (e.g. "pending_signature") instead of
    its .name (e.g. "PENDING_SIGNATURE") when communicating with PostgreSQL.

    Background
    ----------
    SQLAlchemy's native PostgreSQL enum uses member *names* by default.
    When your Python enum uses lowercase values that differ from the uppercase
    names, every INSERT/SELECT sends the wrong string and PostgreSQL raises:
        invalid input value for enum ...: "PENDING_SIGNATURE"

    The fix is values_callable, which tells SQLAlchemy which strings to use
    as the enum labels — we always want the .value.

    Usage
    -----
    # Before
    status = Column(Enum(SignatureRequestStatus), nullable=False)

    # After
    from app.utils.enum_utils import pg_enum
    status = Column(pg_enum(SignatureRequestStatus), nullable=False)
    """
    return SAEnum(
        enum_class,
        values_callable=lambda x: [e.value for e in x],
        **kwargs,
    )
