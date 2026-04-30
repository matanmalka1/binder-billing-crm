from app.actions.action_contracts import (
    build_action,
    get_annual_report_actions,
    get_tax_deadline_actions,
)
from app.actions.action_helpers import build_confirm
import pytest


def test_build_action_omits_optional_keys_when_none():
    action = build_action(
        key="k",
        label="l",
        method="post",
        endpoint="/e",
        action_id="id-1",
    )

    assert action == {
        "id": "id-1",
        "key": "k",
        "label": "l",
        "method": "post",
        "endpoint": "/e",
    }


def test_action_contracts_exports_report_deadline_actions():
    assert callable(get_tax_deadline_actions)
    assert callable(get_annual_report_actions)


def test_build_confirm_adds_optional_inputs():
    confirm = build_confirm(
        "כותרת",
        "הודעה",
        inputs=[
            {
                "name": "field_name",
                "label": "שדה",
                "type": "text",
                "required": True,
            }
        ],
    )

    assert confirm["title"] == "כותרת"
    assert confirm["inputs"][0]["type"] == "text"


def test_build_action_rejects_unsupported_method():
    with pytest.raises(ValueError, match="Action method is not supported"):
        build_action(
            key="k",
            label="l",
            method="trace",  # type: ignore[arg-type]
            endpoint="/e",
            action_id="id-1",
        )


def test_build_action_rejects_unsupported_confirm_input_type():
    with pytest.raises(ValueError, match="Action confirm input type is not supported"):
        build_action(
            key="k",
            label="l",
            method="post",
            endpoint="/e",
            action_id="id-1",
            confirm=build_confirm(
                "כותרת",
                "הודעה",
                inputs=[
                    {
                        "name": "field_name",
                        "label": "שדה",
                        "type": "number",  # type: ignore[typeddict-item]
                        "required": True,
                    }
                ],
            ),
        )
