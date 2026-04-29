from random import Random

from app.common.enums import EntityType
from scripts.seed_fake_data_lib.business_names import seed_business_name


def test_seed_business_names_do_not_reuse_client_name_variants():
    used_names: set[str] = set()
    client_name = "ישראל ישראלי"

    names = [
        seed_business_name(
            client_full_name=client_name,
            entity_type=EntityType.OSEK_MURSHE,
            business_index=index,
            serial=index + 1,
            rng=Random(42),
            used_names=used_names,
        )
        for index in range(4)
    ]

    forbidden = {client_name, f"{client_name} 1", f"{client_name} 2", f"{client_name} 3"}
    assert forbidden.isdisjoint(names)


def test_seed_business_names_are_unique_across_seed_run():
    used_names: set[str] = set()

    names = [
        seed_business_name(
            client_full_name=f"לקוח {serial}",
            entity_type=EntityType.COMPANY_LTD,
            business_index=0,
            serial=serial,
            rng=Random(42),
            used_names=used_names,
        )
        for serial in range(1, 80)
    ]

    assert len(names) == len(set(names))
