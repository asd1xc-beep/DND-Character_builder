from collections.abc import Mapping

from models.character import merge_unique


def selected_package_items(options, selected_name, fallback_items=None):
    fallback_items = fallback_items or []
    if not options or not selected_name:
        return list(fallback_items)
    package = next((item for item in options if item.get("name") == selected_name), None)
    if not package:
        return list(fallback_items)
    return [str(item) for item in package.get("items", []) or [] if item]


def selected_default_equipment(character, class_data=None, background_data=None):
    if not character.get("include_default_equipment", True):
        return []
    class_data = class_data or {}
    background_data = background_data or {}
    class_options = character.get("class_options", {}) or {}
    background_options = character.get("background_options", {}) or {}
    return merge_unique(
        selected_package_items(
            class_data.get("equipment_packages", []),
            class_options.get("equipment_package"),
            class_data.get("starting_equipment", []),
        ),
        selected_package_items(
            background_data.get("equipment_packages", []),
            background_options.get("equipment_package"),
            background_data.get("equipment", []),
        ),
    )


def derive_equipment(character, class_data=None, background_data=None):
    return merge_unique(
        selected_default_equipment(character, class_data, background_data),
        character.get("custom_equipment", []),
    )


def sync_equipment_state(character, class_data=None, background_data=None):
    character.setdefault("include_default_equipment", True)
    if "custom_equipment" not in character:
        character["custom_equipment"] = merge_unique(character.get("equipment", []))
        character["equipment_migration_pending"] = True
    character["custom_equipment"] = merge_unique(character.get("custom_equipment", []))
    if character.get("equipment_migration_pending"):
        package_items = set(selected_default_equipment(character, class_data, background_data))
        character["custom_equipment"] = [
            item
            for item in character.get("custom_equipment", [])
            if item not in package_items
        ]
        character["equipment_migration_pending"] = False
    character["equipment"] = derive_equipment(character, class_data, background_data)
    return character["equipment"]


def migrate_legacy_equipment(character, saved_character: Mapping | None = None):
    saved_character = saved_character or {}
    character.setdefault("include_default_equipment", True)
    if "custom_equipment" not in saved_character:
        character["custom_equipment"] = merge_unique(saved_character.get("equipment", []))
        character["equipment_migration_pending"] = bool(character["custom_equipment"])
    else:
        character["custom_equipment"] = merge_unique(character.get("custom_equipment", []))
        character.setdefault("equipment_migration_pending", False)
    character["equipment"] = merge_unique(character.get("equipment", []))
    return character
