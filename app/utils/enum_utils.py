from sqlalchemy import Enum as SAEnum


def pg_enum(enum_class, **kwargs):
    return SAEnum(
        enum_class,
        values_callable=lambda x: [e.value for e in x],
        **kwargs,
    )
