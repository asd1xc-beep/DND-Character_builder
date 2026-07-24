from services.data_loader import FIVETOOLS_SOURCE, load_classes


def test_imported_class_labels_are_cleaned_through_shared_formatter():
    classes = load_classes(FIVETOOLS_SOURCE)
    rogue = next(record for record in classes if record.get("name") == "Rogue")
    weapon_proficiencies = rogue.get("weapon_proficiencies", [])

    assert any("Finesse Or Light" in item for item in weapon_proficiencies)
    assert not any("{@" in item for item in weapon_proficiencies)
