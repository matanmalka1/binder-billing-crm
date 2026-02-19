from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass
class SeedConfig:
    users: int
    clients: int
    min_binders_per_client: int
    max_binders_per_client: int
    min_charges_per_client: int
    max_charges_per_client: int
    annual_reports_per_client: int
    min_tax_deadlines_per_client: int
    max_tax_deadlines_per_client: int
    min_authority_contacts_per_client: int
    max_authority_contacts_per_client: int
    seed: int
    reset: bool


def parse_args() -> SeedConfig:
    parser = argparse.ArgumentParser(description="Seed local DB with fake demo data")
    parser.add_argument("--users", type=int, default=8, help="Number of users")
    parser.add_argument("--clients", type=int, default=40, help="Number of clients")
    parser.add_argument("--min-binders-per-client", type=int, default=1)
    parser.add_argument("--max-binders-per-client", type=int, default=3)
    parser.add_argument("--min-charges-per-client", type=int, default=1)
    parser.add_argument("--max-charges-per-client", type=int, default=4)
    parser.add_argument(
        "--annual-reports-per-client",
        type=int,
        default=2,
        help="How many annual reports to seed per client",
    )
    parser.add_argument(
        "--min-tax-deadlines-per-client",
        type=int,
        default=2,
        help="Minimum tax deadlines seeded per client",
    )
    parser.add_argument(
        "--max-tax-deadlines-per-client",
        type=int,
        default=5,
        help="Maximum tax deadlines seeded per client",
    )
    parser.add_argument(
        "--min-authority-contacts-per-client",
        type=int,
        default=1,
        help="Minimum authority contacts per client",
    )
    parser.add_argument(
        "--max-authority-contacts-per-client",
        type=int,
        default=3,
        help="Maximum authority contacts per client",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--reset", action="store_true", help="Delete existing rows before seeding")

    args = parser.parse_args()
    if args.min_binders_per_client > args.max_binders_per_client:
        raise ValueError("min-binders-per-client cannot be greater than max-binders-per-client")
    if args.min_charges_per_client > args.max_charges_per_client:
        raise ValueError("min-charges-per-client cannot be greater than max-charges-per-client")
    if args.min_tax_deadlines_per_client > args.max_tax_deadlines_per_client:
        raise ValueError(
            "min-tax-deadlines-per-client cannot be greater than max-tax-deadlines-per-client"
        )
    if args.min_authority_contacts_per_client > args.max_authority_contacts_per_client:
        raise ValueError(
            "min-authority-contacts-per-client cannot be greater than max-authority-contacts-per-client"
        )

    return SeedConfig(
        users=args.users,
        clients=args.clients,
        min_binders_per_client=args.min_binders_per_client,
        max_binders_per_client=args.max_binders_per_client,
        min_charges_per_client=args.min_charges_per_client,
        max_charges_per_client=args.max_charges_per_client,
        annual_reports_per_client=args.annual_reports_per_client,
        min_tax_deadlines_per_client=args.min_tax_deadlines_per_client,
        max_tax_deadlines_per_client=args.max_tax_deadlines_per_client,
        min_authority_contacts_per_client=args.min_authority_contacts_per_client,
        max_authority_contacts_per_client=args.max_authority_contacts_per_client,
        seed=args.seed,
        reset=args.reset,
    )
