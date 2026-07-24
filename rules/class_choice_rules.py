from rules.beasts import beast_catalog, beast_has_fly_speed
from rules.invocations import eligible_invocation_names
from rules.leveling import get_available_spell_levels, get_class_resources, slug
from rules.mystic_arcanum import (
    mystic_arcanum_choice_key,
    mystic_arcanum_choices_for_level,
    mystic_arcanum_options as arcanum_spell_options,
)


LANGUAGE_OPTIONS = [
    "Common",
    "Common Sign Language",
    "Draconic",
    "Dwarvish",
    "Elvish",
    "Giant",
    "Gnomish",
    "Goblin",
    "Halfling",
    "Orc",
    "Abyssal",
    "Celestial",
    "Deep Speech",
    "Infernal",
    "Primordial",
    "Sylvan",
    "Undercommon",
]

FIGHTING_STYLE_OPTIONS = [
    "Archery",
    "Blessed Warrior",
    "Blind Fighting",
    "Defense",
    "Druidic Warrior",
    "Dueling",
    "Great Weapon Fighting",
    "Interception",
    "Protection",
    "Thrown Weapon Fighting",
    "Two-Weapon Fighting",
    "Unarmed Fighting",
]

CLASS_FIGHTING_STYLE_OPTIONS = {
    "Fighter": [
        "Archery",
        "Blind Fighting",
        "Defense",
        "Dueling",
        "Great Weapon Fighting",
        "Interception",
        "Protection",
        "Thrown Weapon Fighting",
        "Two-Weapon Fighting",
        "Unarmed Fighting",
    ],
    "Paladin": [
        "Blessed Warrior",
        "Blind Fighting",
        "Defense",
        "Dueling",
        "Great Weapon Fighting",
        "Interception",
        "Protection",
        "Thrown Weapon Fighting",
        "Unarmed Fighting",
    ],
    "Ranger": [
        "Archery",
        "Blind Fighting",
        "Defense",
        "Druidic Warrior",
        "Dueling",
        "Thrown Weapon Fighting",
        "Two-Weapon Fighting",
    ],
}

METAMAGIC_OPTIONS = [
    "Careful Spell",
    "Distant Spell",
    "Empowered Spell",
    "Extended Spell",
    "Heightened Spell",
    "Quickened Spell",
    "Seeking Spell",
    "Subtle Spell",
    "Transmuted Spell",
    "Twinned Spell",
]

SCHOLAR_SKILLS = ["Arcana", "History", "Investigation", "Medicine", "Nature", "Religion"]
ASPECT_OF_THE_WILDS_OPTIONS = ["Owl", "Panther", "Salmon"]
BLESSED_STRIKES_OPTIONS = ["Divine Strike", "Potent Spellcasting"]
ELEMENTAL_FURY_OPTIONS = ["Potent Spellcasting", "Primal Strike"]
ELEMENTAL_AFFINITY_OPTIONS = ["Acid", "Cold", "Fire", "Lightning", "Poison"]
DEFENSIVE_TACTICS_OPTIONS = ["Escape the Horde", "Multiattack Defense"]
FEY_WANDERER_SKILL_OPTIONS = ["Deception", "Performance", "Persuasion"]
BATTLE_MASTER_PROGRESSION = {
    3: {"maneuvers_known": 3, "superiority_dice": 4, "superiority_die": "d8"},
    7: {"maneuvers_known": 5, "superiority_dice": 5, "superiority_die": "d8"},
    10: {"maneuvers_known": 7, "superiority_dice": 5, "superiority_die": "d10"},
    15: {"maneuvers_known": 9, "superiority_dice": 6, "superiority_die": "d10"},
    18: {"maneuvers_known": 9, "superiority_dice": 6, "superiority_die": "d12"},
}
METAMAGIC_PROGRESSION = {
    2: 2,
    10: 4,
    17: 6,
}


def class_level_up_option_choices(character, class_data, current_level, target_level, data=None):
    choices = []
    for definition in required_class_choice_definitions(character, class_data, target_level, data):
        if int(definition.get("level", 0) or 0) <= current_level:
            continue
        choice = missing_choice_from_definition(character, definition, target_level)
        if choice:
            choices.append(choice)
    return choices


def required_class_choice_messages(character, class_data, level, data=None):
    messages = []
    for definition in required_class_choice_definitions(character, class_data, level, data):
        choice = missing_choice_from_definition(character, definition, level)
        if choice:
            messages.append(choice.get("missing_message") or choice.get("name"))
    return messages


def required_class_choice_definitions(character, class_data, level, data=None):
    class_name = class_data.get("name", character.get("class", ""))
    definitions = []

    if class_name == "Bard" and level >= 2:
        definitions.append(selection_definition(
            level=2,
            key="bard_expertise",
            name="Choose 2 Bard Expertise skills",
            choose=2,
            options=expertise_options(character),
            apply_to="expertise",
            missing_message="Choose 2 Bard Expertise skills",
        ))
        if level >= 6 and selected_subclass_name(character) == "Lore":
            definitions.append(selection_definition(
                level=6,
                key="magical_discoveries",
                name="Choose 2 Magical Discoveries spells",
                choose=2,
                options=magical_discoveries_options(class_data, level, data),
                apply_to="spell_grants",
                missing_message="Choose 2 Magical Discoveries spells",
            ))
        if level >= 9:
            definitions.append(selection_definition(
                level=9,
                key="bard_level_9_expertise",
                name="Choose 2 additional Bard Expertise skills",
                choose=2,
                options=expertise_options(character),
                apply_to="expertise",
                missing_message="Choose 2 additional Bard Expertise skills",
            ))
    if class_name == "Ranger" and level >= 2:
        definitions.extend([
            selection_definition(
                level=2,
                key="ranger_deft_explorer_expertise",
                name="Choose Deft Explorer Expertise skill",
                choose=1,
                options=expertise_options(character),
                apply_to="expertise",
                missing_message="Choose Deft Explorer Expertise skill",
            ),
            selection_definition(
                level=2,
                key="ranger_languages",
                name="Choose 2 Deft Explorer languages",
                choose=2,
                options=language_options(character),
                apply_to="languages",
                missing_message="Choose 2 Deft Explorer languages",
            ),
            single_definition(
                level=2,
                key="fighting_style",
                name="Choose Ranger Fighting Style",
                options=fighting_style_options(data, "Ranger"),
                missing_message="Choose Ranger Fighting Style",
            ),
        ])
        if level >= 7 and selected_subclass_name(character) == "Hunter":
            definitions.append(single_definition(
                level=7,
                key="defensive_tactics",
                name="Choose Defensive Tactics",
                options=DEFENSIVE_TACTICS_OPTIONS,
                missing_message="Choose Defensive Tactics",
            ))
        if level >= 7 and selected_subclass_name(character) == "Gloom Stalker":
            definitions.append(single_definition(
                level=7,
                key="iron_mind_saving_throw",
                name="Choose Iron Mind saving throw",
                options=iron_mind_options(character),
                apply_to="saving_throw_proficiencies",
                missing_message="Choose Iron Mind saving throw",
            ))
        if level >= 3 and selected_subclass_name(character) == "Fey Wanderer":
            definitions.append(single_definition(
                level=3,
                key="fey_wanderer_skill",
                name="Choose Otherworldly Glamour skill",
                options=[
                    skill
                    for skill in FEY_WANDERER_SKILL_OPTIONS
                    if skill not in character.get("skill_proficiencies", [])
                ] or FEY_WANDERER_SKILL_OPTIONS,
                apply_to="skill_proficiencies",
                missing_message="Choose Otherworldly Glamour skill",
            ))
        if level >= 9:
            definitions.append(selection_definition(
                level=9,
                key="ranger_level_9_expertise",
                name="Choose 2 additional Ranger Expertise skills",
                choose=2,
                options=expertise_options(character),
                apply_to="expertise",
                missing_message="Choose 2 additional Ranger Expertise skills",
            ))

    if class_name == "Sorcerer" and level >= 2:
        metamagic_count = metamagic_total_for_level(level)
        definitions.append(selection_definition(
            level=metamagic_feature_level(level),
            key="metamagic",
            name=f"Choose {metamagic_count} total Metamagic options",
            choose=metamagic_count,
            options=METAMAGIC_OPTIONS,
            valid_existing_options=METAMAGIC_OPTIONS,
            missing_message=f"Choose {metamagic_count} total Metamagic options",
        ))
        if level >= 6 and selected_subclass_name(character) == "Draconic":
            definitions.append(single_definition(
                level=6,
                key="elemental_affinity",
                name="Choose Elemental Affinity damage type",
                options=ELEMENTAL_AFFINITY_OPTIONS,
                missing_message="Choose Elemental Affinity damage type",
            ))

    if class_name == "Wizard" and level >= 2:
        definitions.append(single_definition(
            level=2,
            key="wizard_scholar_skill",
            name="Choose Scholar Expertise skill",
            options=scholar_options(character),
            apply_to="expertise",
            missing_message="Choose Scholar Expertise skill",
        ))

    if class_name == "Paladin" and level >= 2:
        definitions.append(single_definition(
            level=2,
            key="fighting_style",
            name="Choose Paladin Fighting Style",
            options=fighting_style_options(data, "Paladin"),
            missing_message="Choose Paladin Fighting Style",
        ))

    if class_name == "Warlock" and level >= 1:
        target_count = int(get_class_resources(class_data, level).get("eldritch_invocations", 0) or 0)
        invocation_rule = class_data.get("class_options", {}).get("eldritch_invocations", {})
        options = eligible_invocation_names(character, invocation_rule, level)
        if target_count:
            definitions.append(selection_definition(
                level=level,
                key="eldritch_invocations",
                name=f"Choose {target_count} Eldritch Invocations",
                choose=target_count,
                options=options,
                valid_existing_options=options,
                missing_message=f"Choose {target_count} Eldritch Invocations",
            ))
        for arcanum_choice in mystic_arcanum_choices_for_level(level):
            spell_level = arcanum_choice["spell_level"]
            definitions.append(selection_definition(
                level=arcanum_choice["source_level"],
                key=mystic_arcanum_choice_key(spell_level),
                name=f"Choose Mystic Arcanum level {spell_level} spell",
                choose=1,
                options=mystic_arcanum_options(data, spell_level),
                apply_to="spell_grants",
                missing_message=f"Choose Mystic Arcanum level {spell_level} spell",
            ))

    if class_name == "Cleric" and level >= 7:
        definitions.append(single_definition(
            level=7,
            key="blessed_strikes",
            name="Choose Blessed Strikes option",
            options=BLESSED_STRIKES_OPTIONS,
            missing_message="Choose Blessed Strikes option",
        ))

    if class_name == "Barbarian" and level >= 3:
        definitions.append(selection_definition(
            level=3,
            key="primal_knowledge_skill",
            name="Choose Primal Knowledge skill",
            choose=1,
            options=barbarian_primal_knowledge_options(character, class_data),
            apply_to="skill_proficiencies",
            missing_message="Choose Primal Knowledge skill",
        ))
        if level >= 6 and selected_subclass_name(character) == "Wild Heart":
            definitions.append(single_definition(
                level=6,
                key="aspect_of_the_wilds",
                name="Choose Aspect of the Wilds",
                options=ASPECT_OF_THE_WILDS_OPTIONS,
                missing_message="Choose Aspect of the Wilds",
            ))

    if class_name == "Druid" and level >= 2:
        progression = wild_shape_progression(character, level)
        forms = wild_shape_form_options(character, level, (data or {}).get("beasts"))
        definitions.append(selection_definition(
            level=progression["choice_level"],
            key="wild_shape_forms",
            name=f"Choose {progression['known_forms']} Wild Shape forms",
            choose=progression["known_forms"],
            options=forms,
            valid_existing_options=forms,
            missing_message=f"Choose {progression['known_forms']} Wild Shape forms",
        ))
        if level >= 7:
            definitions.append(single_definition(
                level=7,
                key="elemental_fury",
                name="Choose Elemental Fury option",
                options=ELEMENTAL_FURY_OPTIONS,
                missing_message="Choose Elemental Fury option",
            ))

    if class_name == "Fighter" and level >= 7 and selected_subclass_name(character) == "Champion":
        definitions.append(selection_definition(
            level=7,
            key="champion_additional_fighting_styles",
            name="Choose Additional Fighting Style",
            choose=1,
            options=additional_fighting_style_options(character, data),
            missing_message="Choose Additional Fighting Style",
        ))

    fighting_style = character.get("class_options", {}).get("fighting_style", "")
    if class_name == "Paladin" and fighting_style == "Blessed Warrior":
        definitions.append(selection_definition(
            level=2,
            key="blessed_warrior_cantrips",
            name="Choose 2 Blessed Warrior cantrips",
            choose=2,
            options=cantrip_options(data, "Cleric"),
            apply_to="spell_grants",
            depends_on={"type": "class_option", "key": "fighting_style", "value": "Blessed Warrior"},
            missing_message="Choose 2 Blessed Warrior cantrips",
        ))
    if class_name == "Ranger" and fighting_style == "Druidic Warrior":
        definitions.append(selection_definition(
            level=2,
            key="druidic_warrior_cantrips",
            name="Choose 2 Druidic Warrior cantrips",
            choose=2,
            options=cantrip_options(data, "Druid"),
            apply_to="spell_grants",
            depends_on={"type": "class_option", "key": "fighting_style", "value": "Druidic Warrior"},
            missing_message="Choose 2 Druidic Warrior cantrips",
        ))

    if class_name == "Rogue" and level >= 1:
        definitions.append(single_definition(
            level=1,
            key="rogue_thieves_cant_language",
            name="Choose Thieves' Cant language",
            options=language_options(character),
            apply_to="languages",
            missing_message="Choose Thieves' Cant language",
        ))

    if class_name == "Rogue" and level >= 6:
        definitions.append(selection_definition(
            level=6,
            key="rogue_level_6_expertise",
            name="Choose 2 additional Rogue Expertise skills",
            choose=2,
            options=expertise_options(character),
            apply_to="expertise",
            missing_message="Choose 2 additional Rogue Expertise skills",
        ))

    return definitions


def selection_definition(level, key, name, choose, options, apply_to="", missing_message="", valid_existing_options=None, depends_on=None):
    return {
        "type": "class_option_selection",
        "level": level,
        "key": key,
        "name": name,
        "choose": choose,
        "options": options,
        "apply_to": apply_to,
        "missing_message": missing_message,
        "valid_existing_options": valid_existing_options,
        "depends_on": depends_on or {},
    }


def single_definition(level, key, name, options, apply_to="", missing_message="", valid_existing_options=None, depends_on=None):
    return {
        "type": "class_option_single",
        "level": level,
        "key": key,
        "name": name,
        "choose": 1,
        "options": options,
        "apply_to": apply_to,
        "missing_message": missing_message,
        "valid_existing_options": valid_existing_options,
        "depends_on": depends_on or {},
    }


def missing_choice_from_definition(character, definition, target_level):
    key = definition["key"]
    selected = selected_class_choice_values(character, key, definition["type"])
    valid_existing = definition.get("valid_existing_options")
    if valid_existing is not None:
        valid_set = set(valid_existing)
        selected = [value for value in selected if value in valid_set]
    choose = int(definition.get("choose", 0) or 0)
    needed = choose - len(selected) if definition["type"] == "class_option_selection" else int(not selected)
    if needed <= 0:
        return {}
    selected_set = set(selected)
    options = [option for option in definition.get("options", []) if option and option not in selected_set]
    return {
        "id": f"{slug(character.get('class', 'class'))}_{target_level}_{slug(key)}",
        "type": definition["type"],
        "name": definition["name"] if needed == choose else definition["name"].replace(str(choose), str(needed), 1),
        "class_option_key": key,
        "required": True,
        "choose": needed,
        "options": options,
        "apply_to": definition.get("apply_to", ""),
        "missing_message": definition.get("missing_message", definition["name"]),
        "depends_on": definition.get("depends_on", {}),
        "status": "unresolved",
    }


def selected_class_choice_values(character, key, choice_type):
    value = character.get("class_options", {}).get(key, [] if choice_type == "class_option_selection" else "")
    if choice_type == "class_option_selection":
        if isinstance(value, list):
            return [item for item in value if item]
        return [value] if value else []
    return [value] if value else []


def expertise_options(character):
    existing_expertise = set(character.get("expertise", []))
    options = [
        skill
        for skill in character.get("skill_proficiencies", [])
        if skill and skill not in existing_expertise
    ]
    return options or [skill for skill in character.get("skill_proficiencies", []) if skill]


def scholar_options(character):
    proficient = set(character.get("skill_proficiencies", []))
    available = [skill for skill in SCHOLAR_SKILLS if skill in proficient and skill not in set(character.get("expertise", []))]
    return available or [skill for skill in SCHOLAR_SKILLS if skill not in set(character.get("expertise", []))]


def selected_subclass_name(character):
    subclass = character.get("subclass", "")
    if subclass.startswith("College of "):
        return subclass.replace("College of ", "", 1)
    if subclass.startswith("Path of the "):
        return subclass.replace("Path of the ", "", 1)
    if subclass.startswith("Circle of the "):
        return subclass.replace("Circle of the ", "", 1)
    if subclass.endswith(" Domain"):
        return subclass.replace(" Domain", "")
    if subclass.endswith(" Sorcery"):
        return subclass.replace(" Sorcery", "")
    return subclass


def barbarian_primal_knowledge_options(character, class_data):
    known = set(character.get("skill_proficiencies", []))
    options = class_data.get("skill_choices", {}).get("from", [])
    return [skill for skill in options if skill not in known] or list(options)


def language_options(character):
    class_options = character.get("class_options", {})
    known = set(character.get("languages", []))
    known.update(class_options.get("ranger_languages", []))
    if class_options.get("rogue_thieves_cant_language"):
        known.add(class_options["rogue_thieves_cant_language"])
    return [language for language in LANGUAGE_OPTIONS if language not in known]


def fighting_style_options(data=None, class_name=""):
    data = data or {}
    class_data = data.get("classes_by_name", {}).get(class_name, {}) if class_name else {}
    imported = class_data.get("class_options", {}).get("fighting_style", [])
    fallback = CLASS_FIGHTING_STYLE_OPTIONS.get(class_name, FIGHTING_STYLE_OPTIONS)
    allowed = set(fallback)
    return merge_unique([style for style in imported if style in allowed], fallback)


def additional_fighting_style_options(character, data=None):
    known = set(character.get("class_options", {}).get("champion_additional_fighting_styles", []))
    known.add(character.get("class_options", {}).get("fighting_style", ""))
    return [style for style in fighting_style_options(data, "Fighter") if style not in known]


def cantrip_options(data=None, class_name=""):
    spells = (data or {}).get("spells", [])
    return sorted({
        spell.get("name", "")
        for spell in spells
        if spell.get("name")
        and spell.get("level") == 0
        and class_name in spell.get("classes", [])
    })


def wild_shape_progression(character, level):
    level = int(level or 1)
    known_forms = 4
    max_cr = 0.25
    allow_flying = False
    choice_level = 2
    if level >= 4:
        known_forms = 6
        max_cr = 0.5
        choice_level = 4
    if level >= 8:
        known_forms = 8
        max_cr = 1
        allow_flying = True
        choice_level = 8
    if selected_subclass_name(character) == "Moon" and level >= 3:
        max_cr = max(max_cr, level // 3)
    return {
        "known_forms": known_forms,
        "max_cr": max_cr,
        "allow_flying": allow_flying,
        "choice_level": choice_level,
    }


def wild_shape_form_options(character, level, beasts=None):
    progression = wild_shape_progression(character, level)
    return [
        beast["name"]
        for beast in sorted(beasts or beast_catalog(), key=lambda item: (float(item.get("challenge_rating", 0) or 0), item.get("name", "")))
        if beast.get("creature_type") == "Beast"
        and float(beast.get("challenge_rating", 0) or 0) <= progression["max_cr"]
        and (progression["allow_flying"] or not beast_has_fly_speed(beast))
    ]


def iron_mind_options(character):
    if "Wisdom" not in character.get("saving_throw_proficiencies", []):
        return ["Wisdom"]
    return [
        ability
        for ability in ["Intelligence", "Charisma"]
        if ability not in character.get("saving_throw_proficiencies", [])
    ]


def magical_discoveries_options(class_data, level, data=None):
    return cross_list_spell_options(class_data, level, data, {"Cleric", "Druid", "Wizard"}, include_cantrips=True)


def magical_secrets_options(class_data, level, data=None):
    return cross_list_spell_options(class_data, level, data, {"Cleric", "Druid", "Wizard"}, include_cantrips=False)


def bard_eligible_spell_lists(character_level):
    if int(character_level or 1) >= 10:
        return ["Bard", "Cleric", "Druid", "Wizard"]
    return ["Bard"]


def eligible_spell_lists_for_prepared_spells(class_data, character_level, spellcasting=None):
    class_name = class_data.get("name", "")
    if class_name == "Bard":
        return bard_eligible_spell_lists(character_level)
    spell_list = (spellcasting or {}).get("spell_list", class_name)
    return [spell_list] if spell_list else []


def metamagic_total_for_level(level):
    level = int(level or 1)
    total = 0
    for threshold, count in sorted(METAMAGIC_PROGRESSION.items()):
        if level >= threshold:
            total = count
    return total


def metamagic_feature_level(level):
    level = int(level or 1)
    current_level = 2
    for threshold in sorted(METAMAGIC_PROGRESSION):
        if level >= threshold:
            current_level = threshold
    return current_level


def battle_master_progression(level):
    level = int(level or 1)
    current = BATTLE_MASTER_PROGRESSION[3]
    for threshold, values in sorted(BATTLE_MASTER_PROGRESSION.items()):
        if level >= threshold:
            current = values
    return dict(current)


def battle_master_maneuver_total(level):
    return battle_master_progression(level)["maneuvers_known"]


def cross_list_spell_options(class_data, level, data=None, source_classes=None, include_cantrips=False):
    spells = (data or {}).get("spells", [])
    available_levels = set(get_available_spell_levels(class_data, level))
    if include_cantrips:
        available_levels.add(0)
    source_classes = set(source_classes or [])
    return sorted({
        spell.get("name", "")
        for spell in spells
        if spell.get("name")
        and spell.get("level") in available_levels
        and source_classes.intersection(spell.get("classes", []))
    })


def mystic_arcanum_options(data=None, spell_level=6):
    return arcanum_spell_options((data or {}).get("spells", []), spell_level)


def class_choice_expertise(character):
    options = character.get("class_options", {})
    return merge_unique(
        options.get("bard_expertise", []),
        options.get("bard_level_9_expertise", []),
        options.get("ranger_deft_explorer_expertise", []),
        options.get("ranger_level_9_expertise", []),
        options.get("rogue_level_6_expertise", []),
        [options.get("wizard_scholar_skill", "")],
    )


def class_choice_skill_proficiencies(character):
    options = character.get("class_options", {})
    return merge_unique(
        options.get("primal_knowledge_skill", []),
        [options.get("fey_wanderer_skill", "")],
    )


def class_choice_languages(character):
    options = character.get("class_options", {})
    return merge_unique(
        options.get("ranger_languages", []),
        [options.get("rogue_thieves_cant_language", "")],
    )


def class_choice_saving_throw_proficiencies(character):
    options = character.get("class_options", {})
    return merge_unique([options.get("iron_mind_saving_throw", "")])


def merge_unique(*lists):
    merged = []
    for items in lists:
        for item in items or []:
            if item and item not in merged:
                merged.append(item)
    return merged
