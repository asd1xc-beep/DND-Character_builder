from rules.class_choice_rules import (
    ASPECT_OF_THE_WILDS_OPTIONS,
    DEFENSIVE_TACTICS_OPTIONS,
    selected_subclass_name,
)
from rules.leveling import selected_subclass_data, selected_subclass_options, slug
from rules.wizard_spellbook import wizard_spellbook_spells


CONFIGURABLE_CLASS_OPTION_KEYS = {
    "aspect_of_the_wilds",
    "fiendish_resilience_damage_type",
    "hunters_prey",
    "defensive_tactics",
    "structured_spell_choice",
    "third_eye_mode",
}

DAMAGE_TYPE_OPTIONS = [
    "Acid",
    "Cold",
    "Fire",
    "Lightning",
    "Necrotic",
    "Poison",
    "Psychic",
    "Radiant",
    "Thunder",
]

THIRD_EYE_OPTIONS = [
    "Darkvision",
    "Greater Comprehension",
    "See Invisibility",
]


def refresh_feature_configurations(character, class_data, data=None):
    existing = {
        config.get("feature_id"): config
        for config in character.get("feature_configurations", [])
        if isinstance(config, dict) and config.get("feature_id")
    }
    refreshed = []
    for definition in active_configuration_definitions(character, class_data, data or {}):
        current = existing.get(definition["feature_id"], {})
        current_value = current.get("current_value") or definition.get("initial_value", "")
        if current_value not in definition.get("eligible_options", []):
            current_value = definition.get("initial_value", "")
        if current_value not in definition.get("eligible_options", []):
            continue
        refreshed.append({
            **definition,
            "current_value": current_value,
        })
    character["feature_configurations"] = refreshed
    return refreshed


def active_configuration_definitions(character, class_data, data=None):
    class_name = class_data.get("name", character.get("class", ""))
    level = int(character.get("level", 1) or 1)
    class_options = character.get("class_options", {})
    subclass_data = selected_subclass_data(class_data, character.get("subclass", ""))
    subclass_name = subclass_data.get("short_name") or selected_subclass_name(character)
    definitions = []
    data = data or {}

    if class_name == "Barbarian" and subclass_name == "Wild Heart" and level >= 6:
        definitions.extend(configuration_from_class_option(
            character,
            key="aspect_of_the_wilds",
            feature_name="Aspect of the Wilds",
            options=ASPECT_OF_THE_WILDS_OPTIONS,
            level_gained=6,
            change_timing="long_rest",
        ))

    if class_name == "Ranger" and subclass_name == "Hunter" and level >= 3:
        subclass_options = selected_subclass_options(class_data, character.get("subclass", ""))
        definitions.extend(configuration_from_class_option(
            character,
            key="hunters_prey",
            feature_name="Hunter's Prey",
            options=subclass_options.get("hunters_prey", {}).get("from", []),
            level_gained=3,
            change_timing="long_rest",
        ))
        if level >= 7:
            definitions.extend(configuration_from_class_option(
                character,
                key="defensive_tactics",
                feature_name="Defensive Tactics",
                options=DEFENSIVE_TACTICS_OPTIONS,
                level_gained=7,
                change_timing="long_rest",
            ))

    if class_name == "Druid" and subclass_name == "Land" and level >= 3:
        subclass_options = selected_subclass_options(class_data, character.get("subclass", ""))
        spell_rule = subclass_options.get("structured_spell_choice", {})
        definitions.extend(configuration_from_class_option(
            character,
            key="structured_spell_choice",
            feature_name="Circle of the Land terrain",
            options=[option.get("name", "") for option in spell_rule.get("options", [])],
            level_gained=3,
            change_timing="long_rest",
        ))

    if class_name == "Warlock" and subclass_name == "Fiend" and level >= 10:
        definitions.append(configuration_definition(
            character,
            key="fiendish_resilience_damage_type",
            feature_name="Fiendish Resilience damage type",
            options=DAMAGE_TYPE_OPTIONS,
            level_gained=10,
            change_timing="short_or_long_rest",
            initial_value=character.get("class_options", {}).get("fiendish_resilience_damage_type", "Fire"),
        ))

    if class_name == "Wizard" and subclass_name == "Diviner" and level >= 10:
        definitions.append(configuration_definition(
            character,
            key="third_eye_mode",
            feature_name="The Third Eye",
            options=THIRD_EYE_OPTIONS,
            level_gained=10,
            change_timing="short_or_long_rest",
            initial_value=character.get("class_options", {}).get("third_eye_mode", "Darkvision"),
        ))

    if class_name == "Wizard" and level >= 18:
        definitions.extend(spell_mastery_configuration_definitions(character, data.get("spells", [])))

    return definitions


def configuration_from_class_option(character, key, feature_name, options, level_gained, change_timing):
    initial_value = character.get("class_options", {}).get(key, "")
    if not initial_value:
        return []
    return [configuration_definition(character, key, feature_name, options, level_gained, change_timing, initial_value)]


def configuration_definition(character, key, feature_name, options, level_gained, change_timing, initial_value):
    option_values = [option for option in options or [] if option]
    return {
        "feature_id": key,
        "feature_name": feature_name,
        "source": {
            "type": "class_option",
            "class_name": character.get("class", ""),
            "subclass_name": character.get("subclass", ""),
            "level_gained": level_gained,
            "class_option_key": key,
        },
        "initial_value": initial_value,
        "current_value": initial_value,
        "change_timing": change_timing,
        "eligible_options": option_values,
    }


def spell_mastery_configuration_definitions(character, spells):
    return [
        definition
        for definition in [
            spell_mastery_configuration_definition(character, spells, "spell_mastery_level_1", 1),
            spell_mastery_configuration_definition(character, spells, "spell_mastery_level_2", 2),
        ]
        if definition
    ]


def spell_mastery_configuration_definition(character, spells, key, spell_level):
    initial_value = character.get("class_options", {}).get(key, "")
    if not initial_value:
        return {}
    options = spell_mastery_options(character, spells, spell_level)
    if not options:
        return {}
    definition = configuration_definition(
        character,
        key=key,
        feature_name=f"Spell Mastery (Level {spell_level})",
        options=options,
        level_gained=18,
        change_timing="long_rest",
        initial_value=initial_value,
    )
    definition["value_type"] = "spell"
    definition["spell_level"] = spell_level
    definition["option_labels"] = {option: f"Level {spell_level} - {option}" for option in options}
    return definition


def spell_mastery_options(character, spells, spell_level):
    spellbook = set(wizard_spellbook_spells(character))
    return [
        spell["name"]
        for spell in spells or []
        if spell.get("name") in spellbook
        and "Wizard" in spell.get("classes", [])
        and spell.get("level") == spell_level
        and spell.get("casting_time") == "1 action"
    ]


def configured_feature_values(character):
    return [
        config.get("current_value", "")
        for config in character.get("feature_configurations", [])
        if config.get("feature_id") in CONFIGURABLE_CLASS_OPTION_KEYS
        and config.get("current_value")
    ]


def update_feature_configuration(character, feature_id, current_value):
    for config in character.get("feature_configurations", []):
        if config.get("feature_id") != feature_id:
            continue
        if current_value not in config.get("eligible_options", []):
            return False
        config["current_value"] = current_value
        return True
    return False


def feature_configuration_choice_id(character, feature_id):
    return f"{slug(character.get('class', 'class'))}_{slug(feature_id)}_configuration"
