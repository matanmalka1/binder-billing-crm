from types import SimpleNamespace

from app.actions.binder_actions import get_binder_actions
from app.actions.business_actions import get_business_actions
from app.actions.charge_actions import get_charge_actions
from app.actions.report_deadline_actions import get_annual_report_actions
from app.actions.vat_report_actions import get_vat_work_item_actions
from app.annual_reports.models.annual_report_enums import AnnualReportStatus
from app.binders.models.binder import BinderStatus
from app.businesses.models.business import BusinessStatus
from app.charge.models.charge import ChargeStatus
from app.core.action_serialization import dump_action_descriptor
from app.users.models.user import UserRole
from app.vat_reports.models.vat_enums import VatWorkItemStatus


def test_binder_ready_serializes_correct_frontend_shape():
    binder = SimpleNamespace(id=10, status=BinderStatus.IN_OFFICE)

    actions = get_binder_actions(binder)
    dumped = dump_action_descriptor(actions[0])

    assert dumped["key"] == "ready"
    assert dumped["method"] == "post"
    assert dumped["endpoint"] == "/binders/10/ready"
    assert dumped["confirm"] is True
    assert dumped["confirm_title"] == "אישור סימון כמוכן לאיסוף"
    assert "id" not in dumped
    assert "payload" not in dumped


def test_binder_return_signals_requires_input():
    binder = SimpleNamespace(id=11, status=BinderStatus.READY_FOR_PICKUP)

    actions = get_binder_actions(binder)
    ret = next(action for action in actions if action.key == "return")
    dumped = dump_action_descriptor(ret)

    assert dumped["payload_schema"] == "requires_input"
    assert "inputs" not in dumped


def test_charge_cancel_serializes_correct_frontend_shape():
    charge = SimpleNamespace(id=20, status=ChargeStatus.DRAFT)

    actions = get_charge_actions(charge)
    cancel = next(action for action in actions if action.key == "cancel_charge")
    dumped = dump_action_descriptor(cancel)

    assert dumped["confirm_title"] == "אישור ביטול חיוב"
    assert dumped["variant"] == "danger"
    assert "confirm_label" not in dumped


def test_business_freeze_serializes_payload_schema():
    business = SimpleNamespace(id=5, client_id=9, status=BusinessStatus.ACTIVE)

    actions = get_business_actions(business, user_role=UserRole.ADVISOR)
    freeze = next(action for action in actions if action.key == "freeze")
    dumped = dump_action_descriptor(freeze)

    assert dumped["payload_schema"] == "simple"
    assert "payload" not in dumped


def test_vat_send_back_serializes_confirm():
    item = SimpleNamespace(id=3, status=VatWorkItemStatus.READY_FOR_REVIEW)

    actions = get_vat_work_item_actions(item, user_role=UserRole.ADVISOR)
    send_back = next(action for action in actions if action.key == "send_back")
    dumped = dump_action_descriptor(send_back)

    assert dumped["confirm"] is True
    assert dumped["confirm_title"] == "החזרה לתיקון"


def test_annual_report_submit_serializes_correct_endpoint():
    actions = get_annual_report_actions(
        report_id=8,
        status=AnnualReportStatus.NOT_STARTED.value,
    )
    submit = next(action for action in actions if action.key == "submit")
    dumped = dump_action_descriptor(submit)

    assert dumped["endpoint"] == "/annual-reports/8/submit"
    assert "id" not in dumped
