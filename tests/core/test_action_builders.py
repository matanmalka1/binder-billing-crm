from app.core.action_builders import link_action, modal_action, mutation_action


def test_mutation_action_sets_type_and_defaults():
    action = mutation_action("cancel", "ביטול", "/things/1/cancel")
    assert action.type == "mutation"
    assert action.endpoint == "/things/1/cancel"
    assert action.method == "post"
    assert action.variant == "secondary"
    assert action.payload_schema == "none"
    assert action.confirm is False


def test_link_action_sets_type_and_route():
    action = link_action("open", "פתח", "/clients/5")
    assert action.type == "link"
    assert action.route == "/clients/5"
    assert action.endpoint is None


def test_modal_action_sets_type():
    action = modal_action("edit", "ערוך", task_id=3)
    assert action.type == "modal"
    assert action.task_id == 3


def test_mutation_action_confirm_true_when_title_provided():
    action = mutation_action(
        "del", "מחק", "/x", confirm_title="אישור", confirm_message="?"
    )
    assert action.confirm is True
    assert action.confirm_title == "אישור"
    assert action.confirm_message == "?"


def test_mutation_action_confirm_false_without_title():
    action = mutation_action("go", "בצע", "/x")
    assert action.confirm is False
    assert action.confirm_title is None


def test_mutation_action_payload_schema_typed():
    action = mutation_action("freeze", "הקפא", "/businesses/1", payload_schema="simple")
    assert action.payload_schema == "simple"


def test_mutation_action_requires_input_payload_schema():
    action = mutation_action(
        "return", "החזרה", "/binders/1/return", payload_schema="requires_input"
    )
    assert action.payload_schema == "requires_input"


def test_link_action_primary_flag_sets_variant():
    action = link_action("view", "פתח", "/x", primary=True)
    assert action.variant == "primary"


def test_mutation_action_danger_variant():
    action = mutation_action("delete", "מחק", "/x", variant="danger")
    assert action.variant == "danger"


def test_modal_action_primary_flag():
    action = modal_action("open", "פתח", primary=True)
    assert action.variant == "primary"
