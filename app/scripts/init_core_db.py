from __future__ import annotations

from dotenv import load_dotenv


def main() -> None:
    """
    Initialize only the core (non-Alembic) tables.

    This repo uses SQLAlchemy ORM metadata for core tables (Sprint 1–2) and Alembic
    migrations for Sprint 3–4 tables. Creating all ORM tables up-front will clash
    with Alembic migrations.
    """

    load_dotenv()

    from app.database import Base, engine

    # Import ONLY core models so Base.metadata contains only core tables.
    import app.models.user  # noqa: F401
    import app.models.client  # noqa: F401
    import app.models.binder  # noqa: F401
    import app.models.binder_status_log  # noqa: F401

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    main()

