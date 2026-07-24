from rules.invocations import invocation_support
from tests.test_level_one_builds import app_data


def test_invocation_support_classifies_nested_choice_invocations_as_partial():
    agonizing = invocation_support("Agonizing Blast")
    tome = invocation_support("Pact of the Tome")
    shadows = invocation_support("Armor of Shadows")

    assert agonizing["selection"] == "supported"
    assert agonizing["prerequisites"] == "supported"
    assert agonizing["permanent_choices"] == "partial"
    assert agonizing["sheet_grants"] == "partial"
    assert tome["permanent_choices"] == "partial"
    assert tome["sheet_grants"] == "partial"
    assert shadows["permanent_choices"] == "supported"
    assert shadows["active_play"] == "description_only"


def test_imported_warlock_invocations_include_support_metadata():
    data = app_data()
    invocation_rule = data["classes_by_name"]["Warlock"]["class_options"]["eldritch_invocations"]
    support_by_name = {
        option["name"]: option["support"]
        for option in invocation_rule["options"]
    }

    assert support_by_name["Agonizing Blast"]["permanent_choices"] == "partial"
    assert support_by_name["Pact of the Tome"]["sheet_grants"] == "partial"
    assert support_by_name["Armor of Shadows"]["selection"] == "supported"


def test_imported_warlock_invocations_include_rules_descriptions():
    data = app_data()
    invocation_rule = data["classes_by_name"]["Warlock"]["class_options"]["eldritch_invocations"]
    by_name = {
        option["name"]: option
        for option in invocation_rule["options"]
    }

    assert len(by_name) == 28
    assert "Charisma modifier" in by_name["Agonizing Blast"]["description"]
    assert "Mage Armor" in by_name["Armor of Shadows"]["description"]
    assert by_name["Agonizing Blast"]["prerequisite_labels"] == [
        "Level 2 Warlock",
        "Warlock Cantrip That Deals Damage",
    ]
    assert "{@" not in by_name["Pact of the Tome"]["description"]
