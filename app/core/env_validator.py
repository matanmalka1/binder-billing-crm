"""
Environment validation for production safety.

Validates required environment variables on startup.
Application refuses to boot if validation fails.
"""
import os
import sys


class EnvValidator:
    """Environment variable validator.

    JWT_SECRET presence is already enforced by Pydantic in app/config.py.
    Add vars here only when they cannot be validated by settings parsing.
    """

    REQUIRED_VARS: list[str] = []

    @classmethod
    def validate(cls) -> None:
        """
        Validate environment configuration.

        Exits process if validation fails.
        """
        missing = []
        empty = []

        for var in cls.REQUIRED_VARS:
            value = os.getenv(var)
            if value is None:
                missing.append(var)
            elif not value.strip():
                empty.append(var)

        if missing or empty:
            cls._print_error(missing, empty)
            sys.exit(1)

    @classmethod
    def _print_error(cls, missing: list[str], empty: list[str]) -> None:
        """Print validation error message."""
        print("=" * 60, file=sys.stderr)
        print("ENVIRONMENT VALIDATION FAILED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)

        if missing:
            print("\nMissing required variables:", file=sys.stderr)
            for var in missing:
                print(f"  - {var}", file=sys.stderr)

        if empty:
            print("\nEmpty required variables:", file=sys.stderr)
            for var in empty:
                print(f"  - {var}", file=sys.stderr)

        print("\nApplication cannot start.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
