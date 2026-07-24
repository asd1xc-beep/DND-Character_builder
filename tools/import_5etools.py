import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from rules.class_choice_rules import CLASS_FIGHTING_STYLE_OPTIONS
from rules.beasts import beast_catalog
from rules.invocations import WARLOCK_INVOCATION_PREREQUISITES, invocation_support

RAW_DIR = ROOT_DIR / "data" / "raw" / "5etools"
IMPORTED_DIR = ROOT_DIR / "data" / "imported" / "5etools"
BASE_URL = "https://raw.githubusercontent.com/5etools-mirror-3/5etools-src/main/data"

DEFAULT_SOURCES = {"XPHB"}
CORE_CLASS_SLUGS = [
    "barbarian",
    "bard",
    "cleric",
    "druid",
    "fighter",
    "monk",
    "paladin",
    "ranger",
    "rogue",
    "sorcerer",
    "warlock",
    "wizard",
]
SPELL_FILES = ["spells-xphb.json"]
ROOT_FILES = [
    "backgrounds.json",
    "races.json",
    "feats.json",
    "optionalfeatures.json",
    "items-base.json",
    "items.json",
    "skills.json",
    "generated/gendata-spell-source-lookup.json",
]

ABILITY_NAMES = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}

SIZE_NAMES = {
    "S": "Small",
    "M": "Medium",
}

SCHOOL_NAMES = {
    "A": "Abjuration",
    "C": "Conjuration",
    "D": "Divination",
    "E": "Enchantment",
    "I": "Illusion",
    "N": "Necromancy",
    "T": "Transmutation",
    "V": "Evocation",
}

SKILL_NAMES = {
    "acrobatics": "Acrobatics",
    "animal handling": "Animal Handling",
    "arcana": "Arcana",
    "athletics": "Athletics",
    "deception": "Deception",
    "history": "History",
    "insight": "Insight",
    "intimidation": "Intimidation",
    "investigation": "Investigation",
    "medicine": "Medicine",
    "nature": "Nature",
    "perception": "Perception",
    "performance": "Performance",
    "persuasion": "Persuasion",
    "religion": "Religion",
    "sleight of hand": "Sleight of Hand",
    "stealth": "Stealth",
    "survival": "Survival",
}

SKILL_TO_ABILITY = {
    "Acrobatics": "Dexterity",
    "Animal Handling": "Wisdom",
    "Arcana": "Intelligence",
    "Athletics": "Strength",
    "Deception": "Charisma",
    "History": "Intelligence",
    "Insight": "Wisdom",
    "Intimidation": "Charisma",
    "Investigation": "Intelligence",
    "Medicine": "Wisdom",
    "Nature": "Intelligence",
    "Perception": "Wisdom",
    "Performance": "Charisma",
    "Persuasion": "Charisma",
    "Religion": "Intelligence",
    "Sleight of Hand": "Dexterity",
    "Stealth": "Dexterity",
    "Survival": "Wisdom",
}

CLASS_SPELLCASTING = {
    "Bard": {"ability": "Charisma", "cantrips_known": 2, "prepared_spells": 4, "spell_list": "Bard"},
    "Cleric": {"ability": "Wisdom", "cantrips_known": 3, "prepared_spells": 4, "spell_list": "Cleric"},
    "Druid": {"ability": "Wisdom", "cantrips_known": 2, "prepared_spells": 4, "spell_list": "Druid"},
    "Paladin": {"ability": "Charisma", "cantrips_known": 0, "prepared_spells": 2, "spell_list": "Paladin"},
    "Ranger": {"ability": "Wisdom", "cantrips_known": 0, "prepared_spells": 2, "spell_list": "Ranger"},
    "Sorcerer": {"ability": "Charisma", "cantrips_known": 4, "prepared_spells": 2, "spell_list": "Sorcerer"},
    "Warlock": {"ability": "Charisma", "cantrips_known": 2, "prepared_spells": 2, "spell_list": "Warlock"},
    "Wizard": {"ability": "Intelligence", "cantrips_known": 3, "known_spells": 6, "spell_list": "Wizard"},
}

CLASS_LEVEL_1_RULES = {
    "Barbarian": {"rages": 2, "rage_damage": 2, "weapon_mastery_count": 2, "armor_class_formula": "10 + Dexterity + Constitution"},
    "Bard": {"bardic_die": "d6", "spell_slots": {"1": 2}},
    "Cleric": {"channel_divinity": 0, "spell_slots": {"1": 2}},
    "Druid": {"wild_shape": 0, "spell_slots": {"1": 2}},
    "Fighter": {"second_wind": 2, "weapon_mastery_count": 3},
    "Monk": {"martial_arts_die": "d6", "focus_points": 0, "unarmored_movement": 0, "armor_class_formula": "10 + Dexterity + Wisdom"},
    "Paladin": {"lay_on_hands_pool": 5, "weapon_mastery_count": 2, "spell_slots": {"1": 2}},
    "Ranger": {"favored_enemy": 2, "weapon_mastery_count": 2, "spell_slots": {"1": 2}},
    "Rogue": {"sneak_attack": "1d6", "weapon_mastery_count": 2},
    "Sorcerer": {"sorcery_points": 0, "spell_slots": {"1": 2}},
    "Warlock": {"eldritch_invocations": 1, "spell_slots": {"1": 1}, "pact_slot_level": 1},
    "Wizard": {"arcane_recovery_levels": 1, "spell_slots": {"1": 2}},
}

SAVANT_SPELL_CHOICES_BY_LEVEL = {
    "3": {"choose": 2, "maximum_spell_level": 2},
    "5": {"choose": 1, "maximum_spell_level": 3},
    "7": {"choose": 1, "maximum_spell_level": 4},
    "9": {"choose": 1, "maximum_spell_level": 5},
    "11": {"choose": 1, "maximum_spell_level": 6},
    "13": {"choose": 1, "maximum_spell_level": 7},
    "15": {"choose": 1, "maximum_spell_level": 8},
    "17": {"choose": 1, "maximum_spell_level": 9},
}

ORIGIN_FEATS = [
    "Alert",
    "Crafter",
    "Healer",
    "Lucky",
    "Magic Initiate (Cleric)",
    "Magic Initiate (Druid)",
    "Magic Initiate (Wizard)",
    "Musician",
    "Savage Attacker",
    "Skilled",
    "Tavern Brawler",
    "Tough",
]

ARTISAN_TOOLS = [
    "Alchemist's Supplies",
    "Brewer's Supplies",
    "Calligrapher's Supplies",
    "Carpenter's Tools",
    "Cartographer's Tools",
    "Cobbler's Tools",
    "Cook's Utensils",
    "Glassblower's Tools",
    "Jeweler's Tools",
    "Leatherworker's Tools",
    "Mason's Tools",
    "Painter's Supplies",
    "Potter's Tools",
    "Smith's Tools",
    "Tinker's Tools",
    "Weaver's Tools",
    "Woodcarver's Tools",
]

SPECIES_CHOICE_OPTIONS = {
    "Dragonborn": {
        "name": "Draconic Ancestry",
        "key": "draconic_ancestry",
        "options": ["Black", "Blue", "Brass", "Bronze", "Copper", "Gold", "Green", "Red", "Silver", "White"],
    },
    "Gnome": {
        "name": "Gnomish Lineage",
        "key": "gnomish_lineage",
        "options": ["Forest Gnome", "Rock Gnome"],
    },
    "Goliath": {
        "name": "Giant Ancestry",
        "key": "giant_ancestry",
        "options": ["Cloud Giant", "Fire Giant", "Frost Giant", "Hill Giant", "Stone Giant", "Storm Giant"],
    },
}


def download_file(relative_path):
    target_path = RAW_DIR / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/{relative_path}"
    request = urllib.request.Request(url, headers={"User-Agent": "local-dnd-character-builder"})
    with urllib.request.urlopen(request, timeout=45) as response:
        target_path.write_bytes(response.read())
    return target_path


def load_raw(relative_path):
    with (RAW_DIR / relative_path).open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(filename, data):
    IMPORTED_DIR.mkdir(parents=True, exist_ok=True)
    with (IMPORTED_DIR / filename).open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def title_from_tag(value):
    if not value:
        return ""
    if isinstance(value, dict):
        value = value.get("item") or value.get("special") or value.get("displayName") or ""
    name = str(value).split("|", 1)[0]
    name = re.sub(r"^\{@\w+\s+", "", name)
    name = name.replace("}", "")
    return title_case_name(name)


def title_case_name(name):
    titled = " ".join(
        word.upper() if word.lower() in {"gp", "cp", "sp", "ep", "pp"} else word.capitalize()
        for word in str(name).strip().split()
    )
    return re.sub(r"\(([^)]+)\)", lambda match: f"({match.group(1).capitalize()})", titled)


def flatten_entries(entries):
    names = []
    for entry in entries or []:
        if isinstance(entry, dict):
            if entry.get("type") == "refClassFeature":
                name = entry.get("classFeature", "").split("|", 1)[0]
                if name:
                    names.append(name)
            elif entry.get("name"):
                names.append(entry["name"].replace("Feature: ", ""))
            names.extend(flatten_entries(entry.get("entries", [])))
            names.extend(flatten_entries(entry.get("items", [])))
    return names


def feature_ref_parts(feature_ref):
    parts = str(feature_ref or "").split("|")
    if len(parts) < 4:
        return {}
    return {
        "name": parts[0],
        "class_name": parts[1],
        "class_source": parts[2],
        "level": int(parts[3]) if str(parts[3]).isdigit() else 0,
        "source": parts[4] if len(parts) > 4 else parts[2],
    }


def subclass_feature_ref_parts(feature_ref):
    parts = str(feature_ref or "").split("|")
    if len(parts) < 6:
        return {}
    return {
        "name": parts[0],
        "class_name": parts[1],
        "class_source": parts[2],
        "subclass_short_name": parts[3],
        "subclass_source": parts[4],
        "level": int(parts[5]) if str(parts[5]).isdigit() else 0,
    }


def class_feature_lookup(class_file_data):
    lookup = {}
    for feature in class_file_data.get("classFeature", []):
        key = (
            feature.get("name", ""),
            feature.get("className", ""),
            feature.get("classSource", ""),
            int(feature.get("level", 0) or 0),
            feature.get("source", ""),
        )
        lookup[key] = feature
    return lookup


def subclass_feature_lookup(class_file_data):
    lookup = {}
    for feature in class_file_data.get("subclassFeature", []):
        key = (
            feature.get("name", ""),
            feature.get("className", ""),
            feature.get("classSource", ""),
            feature.get("subclassShortName", ""),
            feature.get("subclassSource", ""),
            int(feature.get("level", 0) or 0),
        )
        lookup[key] = feature
        if feature.get("classSource"):
            lookup[(
                feature.get("name", ""),
                feature.get("className", ""),
                "",
                feature.get("subclassShortName", ""),
                feature.get("subclassSource", ""),
                int(feature.get("level", 0) or 0),
            )] = feature
    return lookup


def related_class_feature_refs(entries, lookup):
    related = []
    for entry in entries or []:
        if isinstance(entry, list):
            related.extend(related_class_feature_refs(entry, lookup))
        elif isinstance(entry, dict):
            if entry.get("type") == "refClassFeature":
                ref = feature_ref_parts(entry.get("classFeature", ""))
                feature = lookup.get((
                    ref.get("name", ""),
                    ref.get("class_name", ""),
                    ref.get("class_source", ""),
                    ref.get("level", 0),
                    ref.get("source", ""),
                ))
                if feature:
                    related.append(related_feature_record(feature))
            related.extend(related_class_feature_refs(entry.get("entries", []), lookup))
            related.extend(related_class_feature_refs(entry.get("items", []), lookup))
    return related


def related_subclass_feature_refs(entries, lookup):
    related = []
    for entry in entries or []:
        if isinstance(entry, list):
            related.extend(related_subclass_feature_refs(entry, lookup))
        elif isinstance(entry, dict):
            if entry.get("type") == "refSubclassFeature":
                ref = subclass_feature_ref_parts(entry.get("subclassFeature", ""))
                feature = lookup.get((
                    ref.get("name", ""),
                    ref.get("class_name", ""),
                    ref.get("class_source", ""),
                    ref.get("subclass_short_name", ""),
                    ref.get("subclass_source", ""),
                    ref.get("level", 0),
                ))
                if feature:
                    related.append(related_feature_record(feature))
            related.extend(related_subclass_feature_refs(entry.get("entries", []), lookup))
            related.extend(related_subclass_feature_refs(entry.get("items", []), lookup))
    return related


def related_feature_record(feature):
    name, cost = split_feature_cost(feature.get("name", ""))
    return {
        "id": f"{slug(feature.get('className', 'feature'))}_{slug(feature.get('subclassShortName', ''))}_{feature.get('level', 0)}_{slug(feature.get('name', ''))}",
        "name": name,
        "cost": cost,
        "source": feature.get("source", ""),
        "level": feature.get("level", 0),
        "description": entry_description(feature.get("entries", [])),
    }


def split_feature_cost(name):
    match = re.match(r"^(.*?)\s+\(Cost:\s*([^)]+)\)$", str(name or ""))
    if not match:
        return name, ""
    return match.group(1), match.group(2)


def entry_description(entries):
    return "\n\n".join(text for text in entry_text_parts(entries) if text)


def entry_text_parts(entries):
    parts = []
    for entry in entries or []:
        if isinstance(entry, str):
            parts.append(clean_rules_text(entry))
        elif isinstance(entry, list):
            parts.extend(entry_text_parts(entry))
        elif isinstance(entry, dict):
            name = entry.get("name", "")
            nested = entry_text_parts(entry.get("entries", []))
            nested.extend(entry_text_parts(entry.get("items", [])))
            if name and nested:
                parts.append(f"{clean_rules_text(name)}: {' '.join(nested)}")
            elif name:
                parts.append(clean_rules_text(name))
            else:
                parts.extend(nested)
    return parts


def clean_rules_text(text):
    text = re.sub(r"\{@(\w+)\s+([^}]+)}", tagged_text, str(text))
    text = text.replace("{@", "").replace("}", "")
    return re.sub(r"\s+", " ", text).strip()


def tagged_text(match):
    tag = match.group(1).lower()
    parts = match.group(2).split("|")
    if tag == "filter" and parts:
        return parts[0]
    if len(parts) >= 3:
        return parts[-1]
    return parts[0]


def normalize_skill_name(name):
    return SKILL_NAMES.get(name.lower(), name.title())


def normalize_ability_name(name):
    if isinstance(name, dict):
        return [
            ABILITY_NAMES.get(key.lower(), key.title())
            for key, value in name.items()
            if value is True
        ]
    return ABILITY_NAMES.get(name.lower(), name.title())


def extract_true_keys(proficiency_blocks, mapping=None):
    values = []
    for block in proficiency_blocks or []:
        if not isinstance(block, dict):
            continue
        for key, value in block.items():
            if value is True and key != "choose":
                values.append(mapping.get(key, title_case_name(key)) if mapping else title_case_name(key))
    return sorted(set(values))


def extract_choice_count(block):
    choose = block.get("choose") if isinstance(block, dict) else None
    if isinstance(choose, dict):
        return choose.get("count", 1)
    if block.get("any"):
        return block["any"]
    return 0


def extract_skill_choice(skill_proficiencies):
    for block in skill_proficiencies or []:
        if isinstance(block, dict) and block.get("any"):
            return {"choose": block["any"], "from": list(SKILL_TO_ABILITY.keys())}
        choose = block.get("choose") if isinstance(block, dict) else None
        if isinstance(choose, dict):
            from_values = [normalize_skill_name(item) for item in choose.get("from", [])]
            return {"choose": choose.get("count", 0), "from": from_values}
    return {"choose": 0, "from": []}


def extract_species_skill_choice(skill_proficiencies):
    for block in skill_proficiencies or []:
        if isinstance(block, dict) and block.get("any"):
            return {"choose": block["any"], "from": list(SKILL_TO_ABILITY.keys())}
        choose = block.get("choose") if isinstance(block, dict) else None
        if isinstance(choose, dict):
            return {
                "choose": choose.get("count", 1),
                "from": [normalize_skill_name(item) for item in choose.get("from", [])],
            }
    return {"choose": 0, "from": []}


def extract_saves(proficiencies):
    return [
        normalize_ability_name(ability)
        for ability in proficiencies or []
        if isinstance(ability, str)
    ]


def extract_background_skills(background):
    return extract_true_keys(background.get("skillProficiencies", []), SKILL_NAMES)


def extract_background_tools(background):
    return extract_true_keys(background.get("toolProficiencies", []))


def extract_tool_choice(proficiency_blocks):
    for block in proficiency_blocks or []:
        if not isinstance(block, dict):
            continue
        for key, value in block.items():
            if key.startswith("any") and isinstance(value, int):
                label = key.removeprefix("any")
                label = re.sub(r"(?<!^)([A-Z])", r" \1", label).strip()
                return {"choose": value, "from": [f"Any {label.lower()}"]}
    return {"choose": 0, "from": []}


def extract_background_languages(background):
    languages = []
    for block in background.get("languageProficiencies", []) or []:
        if block.get("anyStandard"):
            languages.append(f"{block['anyStandard']} standard languages")
        elif block.get("any"):
            languages.append(f"{block['any']} languages")
    return languages


def extract_starting_equipment(entry):
    equipment = []
    for choice in entry.get("startingEquipment", []) or []:
        if not isinstance(choice, dict):
            continue
        option = choice.get("A") or choice.get("a") or choice.get("_") or []
        for item in option:
            if isinstance(item, dict) and "value" in item:
                equipment.append(f"{item['value'] // 100} GP")
            else:
                name = title_from_tag(item)
                if name:
                    equipment.append(name)
    return sorted(set(equipment))


def normalize_equipment_item(item):
    if isinstance(item, dict) and "value" in item:
        return f"{item['value'] // 100} GP"
    name = title_from_tag(item)
    if not name:
        return ""
    quantity = item.get("quantity") if isinstance(item, dict) else None
    return f"{name} x{quantity}" if quantity else name


def normalize_equipment_packages(starting_equipment):
    if isinstance(starting_equipment, dict):
        blocks = starting_equipment.get("defaultData", [])
    elif isinstance(starting_equipment, list):
        blocks = starting_equipment
    else:
        blocks = []

    packages = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        for key, values in block.items():
            if key.startswith("_"):
                continue
            items = [
                normalize_equipment_item(item)
                for item in values
            ]
            packages.append({
                "name": key,
                "items": [item for item in items if item],
            })
    return packages


def first_feature_name(entry):
    feats = extract_feat_names(entry.get("feats", []))
    if feats:
        return "Origin Feat: " + ", ".join(feats)
    for item in entry.get("entries", []) or []:
        if isinstance(item, dict) and item.get("name"):
            return item["name"].replace("Feature: ", "")
    return ""


def origin_feat_feature_descriptions(background, sources):
    descriptions = {}
    feat_descriptions = normalize_feat_descriptions(sources)
    for feat_name in extract_feat_names(background.get("feats", [])):
        description = feat_descriptions.get(feat_name, "")
        if description:
            descriptions[feat_name] = description
            descriptions[f"Origin Feat: {feat_name}"] = description
    return descriptions


def extract_feat_names(feats):
    names = []
    for feat_block in feats or []:
        if not isinstance(feat_block, dict):
            continue
        for key, enabled in feat_block.items():
            if not enabled:
                continue
            name = key.split("|", 1)[0]
            if ";" in name:
                main_name, detail = name.split(";", 1)
                name = f"{main_name.strip()} ({detail.strip()}"
            if "(" in name and not name.endswith(")"):
                name = f"{name})"
            names.append(title_case_name(name))
    return names


def named_entry_descriptions(entries):
    descriptions = {}
    for entry in entries or []:
        if isinstance(entry, dict) and entry.get("name"):
            name = entry["name"].replace("Feature: ", "")
            description = entry_description(entry.get("entries", []))
            if description:
                descriptions[name] = description
        if isinstance(entry, dict):
            descriptions.update(named_entry_descriptions(entry.get("entries", [])))
            descriptions.update(named_entry_descriptions(entry.get("items", [])))
    return descriptions


def extract_background_ability_options(background):
    ability = background.get("ability", [])
    if not ability:
        return {"mode": "none", "abilities": [], "primary_bonus": 0, "secondary_bonus": 0}

    weighted = ability[0].get("choose", {}).get("weighted", {}) if isinstance(ability[0], dict) else {}
    abilities = [normalize_ability_name(item) for item in weighted.get("from", [])]
    weights = weighted.get("weights", [])
    primary_bonus = max(weights) if weights else 2
    secondary_bonus = min(weights) if weights else 1
    return {
        "mode": "choose_weighted",
        "abilities": abilities,
        "primary_bonus": primary_bonus,
        "secondary_bonus": secondary_bonus,
    }


def normalize_backgrounds(sources):
    raw = load_raw("backgrounds.json")
    backgrounds = []
    for background in raw.get("background", []):
        if background.get("source") not in sources:
            continue
        backgrounds.append({
            "name": background["name"],
            "source": background.get("source", ""),
            "ability_options": extract_background_ability_options(background),
            "origin_feats": extract_feat_names(background.get("feats", [])),
            "skill_proficiencies": extract_background_skills(background),
            "tool_proficiencies": extract_background_tools(background),
            "tool_choices": extract_tool_choice(background.get("toolProficiencies", [])),
            "languages": extract_background_languages(background),
            "feature": first_feature_name(background),
            "feature_descriptions": origin_feat_feature_descriptions(background, sources),
            "equipment": extract_starting_equipment(background),
            "equipment_packages": normalize_equipment_packages(background.get("startingEquipment", [])),
            "raw_ref": f"{background['name']}|{background.get('source', '')}",
        })
    return sorted(backgrounds, key=lambda item: item["name"])


def normalize_species(sources):
    raw = load_raw("races.json")
    species = []
    for race in raw.get("race", []):
        if race.get("source") not in sources:
            continue
        speed = race.get("speed", 30)
        if isinstance(speed, dict):
            speed = speed.get("walk", 30)
        species.append({
            "name": race["name"],
            "source": race.get("source", ""),
            "size": " or ".join(SIZE_NAMES.get(size, size) for size in race.get("size", [])) or "Medium",
            "speed": speed,
            "languages": extract_language_names(race),
            "skill_choices": extract_species_skill_choice(race.get("skillProficiencies", [])),
            "choice_options": SPECIES_CHOICE_OPTIONS.get(race["name"]),
            "lineage_options": extract_lineage_options(race),
            "traits": flatten_entries(race.get("entries", [])),
            "trait_descriptions": named_entry_descriptions(race.get("entries", [])),
            "raw_ref": f"{race['name']}|{race.get('source', '')}",
        })
    return sorted(species, key=lambda item: item["name"])


def extract_language_names(entry):
    languages = []
    for block in entry.get("languageProficiencies", []) or []:
        if not isinstance(block, dict):
            continue
        for key, value in block.items():
            if key == "common" and value is True:
                languages.append("Common")
            elif key == "anyStandard":
                languages.append(f"{value} standard languages")
            elif key == "any":
                languages.append(f"{value} languages")
    return sorted(set(languages))


def extract_lineage_options(race):
    lineages = []
    for spell_block in race.get("additionalSpells", []) or []:
        name = spell_block.get("name")
        if not name:
            continue
        level_one_spells = []
        known = spell_block.get("known", {}).get("1")
        if isinstance(known, list):
            level_one_spells.extend(title_from_tag(spell) for spell in known)
        elif isinstance(known, dict):
            level_one_spells.append("Choose a cantrip")
        lineages.append({
            "name": name,
            "level_1_spells": [spell for spell in level_one_spells if spell],
            "spellcasting_abilities": [
                normalize_ability_name(ability)
                for ability in spell_block.get("ability", {}).get("choose", [])
            ],
        })
    return lineages


def normalize_class(class_entry, class_file_data=None):
    starting = class_entry.get("startingProficiencies", {})
    skill_choices = extract_skill_choice(starting.get("skills", []))
    level_features = extract_class_features_by_level(class_entry.get("classFeatures", []))
    features = level_features.get("1", [])
    name = class_entry["name"]
    subclasses = normalize_subclasses(class_file_data or {}, name, {class_entry.get("source", "")})
    feature_descriptions = extract_class_feature_descriptions(class_file_data or {}, name, {class_entry.get("source", "")})
    feature_related_features, missing_feature_refs = extract_class_feature_related_features(
        class_file_data or {},
        name,
        {class_entry.get("source", "")},
    )
    if name == "Warlock":
        feature_descriptions["Mystic Arcanum"] = (
            "You gain one Warlock spell of the Arcanum level for your Warlock level: "
            "level 6 at Warlock level 11, level 7 at Warlock level 13, "
            "level 8 at Warlock level 15, and level 9 at Warlock level 17. "
            "You can cast each Arcanum spell once without expending a Pact Magic spell slot, "
            "and you regain that casting when you finish a Long Rest."
        )
    return {
        "name": name,
        "source": class_entry.get("source", ""),
        "hit_die": class_entry.get("hd", {}).get("faces", 0),
        "primary_ability": flatten_list(
            normalize_ability_name(ability)
            for ability in class_entry.get("primaryAbility", [])
        ),
        "saving_throw_proficiencies": extract_saves(class_entry.get("proficiency", [])),
        "skill_choices": skill_choices,
        "armor_proficiencies": extract_armor_proficiencies(starting),
        "weapon_proficiencies": extract_weapon_proficiencies(starting),
        "tool_proficiencies": extract_tool_proficiencies(starting),
        "level_1_features": features,
        "level_features": level_features,
        "feature_descriptions": feature_descriptions,
        "feature_related_features": feature_related_features,
        "import_warnings": [
            f"Missing referenced class feature: {feature_ref}"
            for feature_ref in missing_feature_refs
        ],
        "progression": extract_class_progression_by_level(class_entry, name, subclasses),
        "subclasses": subclasses,
        "level_1_rules": CLASS_LEVEL_1_RULES.get(name, {}),
        "class_options": default_class_options(name, class_file_data or {}),
        "spellcasting": CLASS_SPELLCASTING.get(name),
        "starting_equipment": first_package_items(class_entry.get("startingEquipment", {})),
        "equipment_packages": normalize_equipment_packages(class_entry.get("startingEquipment", {})),
        "raw_ref": f"{name}|{class_entry.get('source', '')}",
    }


def extract_class_features_by_level(feature_refs):
    features_by_level = {}
    for feature_ref in feature_refs:
        if isinstance(feature_ref, dict):
            feature_ref = feature_ref.get("classFeature", "")
        if not isinstance(feature_ref, str):
            continue
        parts = feature_ref.split("|")
        if len(parts) < 4 or not parts[3].isdigit():
            continue
        features_by_level.setdefault(parts[3], []).append(parts[0])
    return features_by_level


def extract_class_progression_by_level(class_entry, class_name, subclasses):
    feature_refs = class_entry.get("classFeatures", [])
    progression_by_level = {
        str(level): {
            "features": [],
            "resources": class_resources_at_level(class_entry, level),
            "spell_slots": class_spell_slots_at_level(class_entry, level),
            "cantrips_known": progression_value(class_entry.get("cantripProgression", []), level),
            "prepared_spells": progression_value(class_entry.get("preparedSpellsProgression", []), level),
            "known_spells": cumulative_progression_value(class_entry.get("spellsKnownProgressionFixed", []), level),
            "spellbook_spells_added": progression_value(class_entry.get("spellsKnownProgressionFixed", []), level),
        }
        for level in range(1, 21)
    }
    subclass_options = [subclass["name"] for subclass in subclasses]
    for feature_ref in feature_refs:
        raw_feature_ref = feature_ref
        if isinstance(feature_ref, dict):
            feature_ref = feature_ref.get("classFeature", "")
        if not isinstance(feature_ref, str):
            continue
        parts = feature_ref.split("|")
        if len(parts) < 4 or not parts[3].isdigit():
            continue
        feature_name = parts[0]
        level = int(parts[3])
        entry = {
            "id": f"{slug(class_name)}_{level}_{slug(feature_name)}",
            "type": "automatic_feature",
            "name": feature_name,
            "source": class_name,
            "level": level,
        }
        if isinstance(raw_feature_ref, dict) and raw_feature_ref.get("gainSubclassFeature"):
            entry.update({
                "type": "subclass_choice",
                "required": True,
                "options": subclass_options,
            })
        elif feature_name == "Ability Score Improvement":
            entry.update({
                "type": "asi_or_feat",
                "required": True,
            })
        progression_by_level.setdefault(str(level), {"features": []}).setdefault("features", []).append(entry)
    return {
        level: clean_progression_entry(entry)
        for level, entry in progression_by_level.items()
        if entry.get("features") or entry.get("resources") or entry.get("spell_slots")
    }


def clean_progression_entry(entry):
    cleaned = dict(entry)
    if not cleaned.get("features"):
        cleaned.pop("features", None)
    if not cleaned.get("resources"):
        cleaned.pop("resources", None)
    if not cleaned.get("spell_slots"):
        cleaned.pop("spell_slots", None)
    if not cleaned.get("cantrips_known"):
        cleaned.pop("cantrips_known", None)
    if not cleaned.get("prepared_spells"):
        cleaned.pop("prepared_spells", None)
    if not cleaned.get("known_spells"):
        cleaned.pop("known_spells", None)
    if not cleaned.get("spellbook_spells_added"):
        cleaned.pop("spellbook_spells_added", None)
    return cleaned


def class_resources_at_level(class_entry, level):
    resources = {}
    index = int(level) - 1
    for group in class_entry.get("classTableGroups", []):
        rows = group.get("rows", [])
        labels = group.get("colLabels", [])
        if not rows or index < 0 or index >= len(rows):
            continue
        row = rows[index]
        for label, value in zip(labels, row):
            key = class_resource_key(label)
            if not key:
                continue
            normalized = normalize_table_cell(value)
            if normalized not in {"", None, 0}:
                resources[key] = normalized
    if resources.get("spell_slot_count") and resources.get("pact_slot_level"):
        resources["spell_slots"] = {str(resources["pact_slot_level"]): int(resources["spell_slot_count"])}
    if class_entry.get("name") == "Paladin":
        resources["lay_on_hands_pool"] = int(level) * 5
    return resources


def class_spell_slots_at_level(class_entry, level):
    index = int(level) - 1
    for group in class_entry.get("classTableGroups", []):
        rows = group.get("rowsSpellProgression")
        if not rows or index < 0 or index >= len(rows):
            continue
        slots = {}
        for slot_level, value in enumerate(rows[index], start=1):
            if int(value or 0):
                slots[str(slot_level)] = int(value)
        if slots:
            return slots
    resources = class_resources_at_level(class_entry, level)
    return resources.get("spell_slots", {})


def class_resource_key(label):
    plain = class_table_label_text(label).lower()
    if "cantrips" in plain or "prepared spells" in plain:
        return ""
    mapping = {
        "bardic die": "bardic_die",
        "channel divinity": "channel_divinity",
        "eldritch invocations": "eldritch_invocations",
        "invocations": "eldritch_invocations",
        "favored enemy": "favored_enemy",
        "focus points": "focus_points",
        "martial arts": "martial_arts_die",
        "rages": "rages",
        "rage damage": "rage_damage",
        "second wind": "second_wind",
        "sneak attack": "sneak_attack",
        "sorcery points": "sorcery_points",
        "spell slots": "spell_slot_count",
        "slot level": "pact_slot_level",
        "unarmored movement": "unarmored_movement",
        "weapon mastery": "weapon_mastery_count",
        "wild shape": "wild_shape",
    }
    return mapping.get(plain, "")


def class_table_label_text(label):
    raw = str(label)
    tag_match = re.match(r"\{@\w+\s+([^}|]+)", raw)
    if tag_match:
        return tag_match.group(1).strip()
    return clean_rules_text(raw).strip()


def normalize_table_cell(value):
    if isinstance(value, dict):
        if value.get("type") == "dice":
            dice = value.get("toRoll", [{}])[0]
            number = dice.get("number", 1)
            faces = dice.get("faces", "")
            return f"{number}d{faces}" if faces else ""
        if value.get("type") in {"bonus", "bonusSpeed"}:
            return value.get("value", 0)
    if isinstance(value, str):
        cleaned = clean_rules_text(value)
        return int(cleaned) if cleaned.isdigit() else cleaned
    return value


def cumulative_progression_value(values, level):
    if not isinstance(values, list):
        return 0
    return sum(int(value or 0) for value in values[:int(level)])


def extract_level_one_class_features(feature_refs):
    return extract_class_features_by_level(feature_refs).get("1", [])


def normalize_subclasses(class_file_data, class_name, sources):
    subclass_features = extract_subclass_features_by_short_name(class_file_data, class_name, sources)
    subclass_feature_descriptions = extract_subclass_feature_descriptions(class_file_data, class_name, sources)
    subclass_related_features, missing_subclass_refs = extract_subclass_feature_related_features(class_file_data, class_name, sources)
    subclasses = []
    for subclass in class_file_data.get("subclass", []):
        if subclass.get("source") not in sources:
            continue
        if subclass.get("className") != class_name:
            continue
        if subclass.get("classSource") and subclass.get("classSource") not in sources:
            continue
        subclasses.append({
            "id": f"{slug(subclass.get('name', 'subclass'))}_{subclass.get('source', '').lower()}",
            "name": subclass.get("name", ""),
            "short_name": subclass.get("shortName", subclass.get("name", "")),
            "source": subclass.get("source", ""),
            "level_features": subclass_features.get(subclass.get("shortName", subclass.get("name", "")), {}),
            "feature_descriptions": subclass_feature_descriptions.get(subclass.get("shortName", subclass.get("name", "")), {}),
            "feature_related_features": subclass_related_features.get(subclass.get("shortName", subclass.get("name", "")), {}),
            "import_warnings": [
                f"Missing referenced subclass feature: {feature_ref}"
                for feature_ref in missing_subclass_refs
            ],
            "subclass_options": subclass_options(subclass, class_file_data, class_name, sources),
            "spellcasting_progression": subclass_spellcasting_progression(subclass),
            "grants_by_level": subclass_grants_by_level(subclass),
            "spellcasting": subclass_spellcasting(subclass, 3),
            "always_prepared_spells": subclass_spell_grants(subclass, 3, "prepared"),
            "always_known_spells": subclass_spell_grants(subclass, 3, "known"),
            "granted_cantrips": subclass_granted_cantrips(subclass, 3),
            "resources": subclass_resources(subclass, 3),
        })
    return sorted(subclasses, key=lambda item: item["name"])


def subclass_options(subclass, class_file_data, class_name, sources):
    options = {}
    short_name = subclass.get("shortName", subclass.get("name", ""))
    maneuvers = maneuver_options(class_file_data, class_name, short_name, sources)
    maneuver_count = optional_feature_choice_count(subclass, "Maneuvers", 3)
    if maneuvers and maneuver_count:
        maneuver_details = load_maneuver_details()
        options["maneuvers"] = {
            "choose": maneuver_count,
            "from": maneuvers,
            "options": [
                maneuver_option_record(maneuver, maneuver_details.get(maneuver, {}))
                for maneuver in maneuvers
            ],
        }
        options["maneuver_save_ability"] = ["Strength", "Dexterity"]
    if has_subclass_feature(class_file_data, class_name, short_name, sources, 3, "Student of War"):
        options["student_of_war_skill"] = {"choose": 1, "from": "class_skill_options"}
        options["student_of_war_tool"] = {"choose": 1, "from": ARTISAN_TOOLS}
    if has_subclass_feature(class_file_data, class_name, short_name, sources, 3, "Bonus Proficiencies"):
        options["lore_skills"] = {"choose": 3, "from": sorted(SKILL_TO_ABILITY.keys())}
    if has_subclass_feature(class_file_data, class_name, short_name, sources, 3, "Hunter's Prey"):
        options["hunters_prey"] = {
            "choose": 1,
            "from": ["Colossus Slayer", "Horde Breaker"],
        }
    if has_subclass_feature(class_file_data, class_name, short_name, sources, 3, "Primal Companion"):
        options["primal_companion"] = {
            "choose": 1,
            "from": ["Beast of the Land", "Beast of the Sea", "Beast of the Sky"],
        }
    structured_spell_choice = subclass_structured_spell_choice(subclass, 3)
    if structured_spell_choice:
        options["structured_spell_choice"] = structured_spell_choice
    savant_rule = subclass_savant_spell_choice(subclass, 3)
    if savant_rule:
        options["savant_spells"] = savant_rule
        options["savant_spell_choices_by_level"] = subclass_savant_spell_choices_by_level(subclass, savant_rule)
    return options


def optional_feature_choice_count(subclass, name, level):
    for progression in subclass.get("optionalfeatureProgression", []):
        if progression.get("name") != name:
            continue
        levels = progression.get("progression", {})
        return int(levels.get(str(level), 0) or 0)
    return 0


def maneuver_options(class_file_data, class_name, subclass_short_name, sources):
    for feature in class_file_data.get("subclassFeature", []):
        if feature.get("source") not in sources:
            continue
        if feature.get("className") != class_name:
            continue
        if feature.get("subclassShortName") != subclass_short_name:
            continue
        if feature.get("name") != "Maneuver Options":
            continue
        return sorted(extract_optional_feature_names(feature.get("entries", [])))
    return []


def extract_optional_feature_names(entries):
    names = []
    for entry in entries or []:
        if isinstance(entry, dict):
            if entry.get("type") == "refOptionalfeature":
                names.append(entry.get("optionalfeature", "").split("|", 1)[0])
            names.extend(extract_optional_feature_names(entry.get("entries", [])))
            names.extend(extract_optional_feature_names(entry.get("items", [])))
    return [name for name in names if name]


def has_subclass_feature(class_file_data, class_name, subclass_short_name, sources, level, name):
    for feature in class_file_data.get("subclassFeature", []):
        if feature.get("source") not in sources:
            continue
        if feature.get("className") != class_name:
            continue
        if feature.get("subclassShortName") != subclass_short_name:
            continue
        if feature.get("level") == level and feature.get("name") == name:
            return True
    return False


def subclass_spellcasting(subclass, level):
    progression = subclass_spellcasting_progression(subclass)
    if progression:
        return progression.get(str(level))
    return None


def subclass_spellcasting_progression(subclass):
    ability = normalize_ability_name(subclass.get("spellcastingAbility", ""))
    if not ability:
        return {}

    progression = {}
    for level in range(1, 21):
        cantrips_known = progression_value(subclass.get("cantripProgression", []), level)
        prepared_spells = progression_value(subclass.get("preparedSpellsProgression", []), level)
        known_spells = subclass_known_spell_count(subclass, level)
        spell_slots = subclass_spell_slots(subclass, level)
        granted_cantrips = subclass_granted_cantrips(subclass, level)
        if not any((cantrips_known, prepared_spells, known_spells, spell_slots, granted_cantrips)):
            continue
        entry = {
            "ability": ability,
            "spell_list": subclass_spell_list(subclass),
            "spell_slots": spell_slots,
            "maximum_spell_level": max((int(spell_level) for spell_level in spell_slots), default=0),
            "granted_cantrips": granted_cantrips,
        }
        if cantrips_known:
            entry["cantrips_known"] = cantrips_known
        if prepared_spells:
            entry["prepared_spells"] = prepared_spells
        elif known_spells:
            entry["known_spells"] = known_spells
        progression[str(level)] = entry
    return progression


def subclass_known_spell_count(subclass, level):
    index = int(level) - 1
    for group in subclass.get("subclassTableGroups", []):
        rows = group.get("rows", [])
        labels = [clean_rules_text(class_table_label_text(label)).lower() for label in group.get("colLabels", [])]
        if index < 0 or index >= len(rows):
            continue
        for label_index, label in enumerate(labels):
            if "spells known" not in label:
                continue
            row = rows[index]
            if label_index < len(row):
                return int(row[label_index] or 0)
    return 0


def progression_value(values, level):
    index = int(level) - 1
    if not isinstance(values, list) or index < 0 or index >= len(values):
        return 0
    return int(values[index] or 0)


def subclass_spell_list(subclass):
    for block in subclass.get("additionalSpells", []):
        for level_entries in block.get("expanded", {}).values():
            for entry in level_entries:
                value = entry.get("all", "") if isinstance(entry, dict) else ""
                for part in value.split("|"):
                    if part.startswith("class="):
                        return part.split("=", 1)[1]
    return "Wizard"


def subclass_spell_slots(subclass, level):
    index = int(level) - 1
    for group in subclass.get("subclassTableGroups", []):
        rows = group.get("rowsSpellProgression")
        labels = group.get("colLabels", [])
        if not rows or index < 0 or index >= len(rows):
            continue
        slots = {}
        for slot_index, value in enumerate(rows[index], start=1):
            if slot_index <= len(labels) and int(value or 0):
                slots[str(slot_index)] = int(value)
        if slots:
            return slots
    return {}


def subclass_granted_cantrips(subclass, level):
    return subclass_spell_grants(subclass, level, "known", cantrips_only=True)


def subclass_spell_grants(subclass, level, grant_type, cantrips_only=False):
    spells = []
    for block in subclass.get("additionalSpells", []):
        if is_structured_spell_block(subclass, block):
            continue
        for grant_level, granted_spells in block.get(grant_type, {}).items():
            if int(grant_level) > level:
                continue
            for spell in granted_spells:
                if not isinstance(spell, str):
                    continue
                if cantrips_only and "#c" not in spell:
                    continue
                spell_name = spell_ref_name(spell)
                if spell_name:
                    spells.append(spell_name)
    return sorted(set(spells))


def subclass_spell_grants_exact(subclass, level, grant_type, cantrips_only=False):
    spells = []
    for block in subclass.get("additionalSpells", []):
        if is_structured_spell_block(subclass, block):
            continue
        granted_spells = block.get(grant_type, {}).get(str(level), [])
        if not isinstance(granted_spells, list):
            continue
        for spell in granted_spells:
            if not isinstance(spell, str):
                continue
            if cantrips_only and "#c" not in spell:
                continue
            if not cantrips_only and "#c" in spell:
                continue
            spell_name = spell_ref_name(spell)
            if spell_name:
                spells.append(spell_name)
    return sorted(set(spells))


def subclass_grants_by_level(subclass):
    grants = {}
    ability = normalize_ability_name(subclass.get("spellcastingAbility", ""))
    for level in range(1, 21):
        always_prepared = subclass_spell_grants_exact(subclass, level, "prepared")
        known_spells = subclass_spell_grants_exact(subclass, level, "known")
        granted_cantrips = subclass_spell_grants_exact(subclass, level, "known", cantrips_only=True)
        resources = subclass_resources(subclass, level)
        spell_grants = []
        for spell in always_prepared:
            spell_grants.append(subclass_spell_grant_record(subclass, spell, level, ability, "always_prepared"))
        for spell in known_spells:
            spell_grants.append(subclass_spell_grant_record(subclass, spell, level, ability, "always_known"))
        for spell in granted_cantrips:
            spell_grants.append(subclass_spell_grant_record(subclass, spell, level, ability, "granted_cantrip"))
        if not any((always_prepared, known_spells, granted_cantrips, resources, spell_grants)):
            continue
        grants[str(level)] = {
            "always_prepared_spells": always_prepared,
            "always_known_spells": known_spells,
            "granted_cantrips": granted_cantrips,
            "resources": resources,
            "spell_grants": spell_grants,
        }
    return grants


def subclass_spell_grant_record(subclass, spell, level, ability, grant_type):
    return {
        "name": spell,
        "level_gained": level,
        "source": {
            "type": "subclass",
            "subclass_id": f"{slug(subclass.get('name', 'subclass'))}_{subclass.get('source', '').lower()}",
            "subclass_name": subclass.get("name", ""),
            "source": subclass.get("source", ""),
        },
        "spellcasting_ability": ability,
        "grant_type": grant_type,
        "always_prepared": grant_type == "always_prepared",
        "counts_against_limit": False,
    }


def is_structured_spell_block(subclass, block):
    named_blocks = [
        spell_block
        for spell_block in subclass.get("additionalSpells", [])
        if spell_block.get("name")
    ]
    return bool(block.get("name") and len(named_blocks) > 1)


def subclass_structured_spell_choice(subclass, level):
    options = []
    for block in subclass.get("additionalSpells", []):
        if not is_structured_spell_block(subclass, block):
            continue
        spells = merge_spell_grant_lists(block, level)
        spells_by_level = merge_spell_grant_lists_by_level(block)
        if spells:
            options.append({
                "id": slug(block.get("name", "")),
                "name": block.get("name", ""),
                "granted_spells": spells,
                "granted_spells_by_level": spells_by_level,
            })
    if not options:
        return {}
    return {
        "id": f"{slug(subclass.get('name', 'subclass'))}_spell_group",
        "type": "structured_spell_choice",
        "name": "Subclass spell group",
        "required": True,
        "choose": 1,
        "options": options,
    }


def merge_spell_grant_lists(block, level):
    spells = []
    for grant_type in ("known", "prepared", "innate"):
        entries = block.get(grant_type, {})
        if not isinstance(entries, dict):
            continue
        for grant_level, granted_spells in entries.items():
            if str(grant_level) == "_":
                continue
            if int(grant_level) > level:
                continue
            if isinstance(granted_spells, list):
                for spell in granted_spells:
                    if isinstance(spell, str):
                        spells.append(spell_ref_name(spell))
    return sorted(set(spell for spell in spells if spell))


def merge_spell_grant_lists_by_level(block):
    spells_by_level = {}
    for grant_type in ("known", "prepared", "innate"):
        entries = block.get(grant_type, {})
        if not isinstance(entries, dict):
            continue
        for grant_level, granted_spells in entries.items():
            if str(grant_level) == "_":
                continue
            level_key = str(int(grant_level))
            names = []
            if isinstance(granted_spells, list):
                for spell in granted_spells:
                    if isinstance(spell, str):
                        names.append(spell_ref_name(spell))
            if names:
                spells_by_level[level_key] = sorted(set(spells_by_level.get(level_key, []) + names))
    return spells_by_level


def spell_ref_name(ref):
    raw_name = str(ref).split("|", 1)[0].split("#", 1)[0].strip()
    if not raw_name:
        return ""
    small_words = {"a", "an", "and", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with", "without"}
    words = raw_name.split()
    formatted = []
    for index, word in enumerate(words):
        lower = word.lower()
        if index and lower in small_words:
            formatted.append(lower)
        else:
            formatted.append(word.capitalize())
    return " ".join(formatted)


def subclass_savant_spell_choice(subclass, level):
    choices = []
    for block in subclass.get("additionalSpells", []):
        for grant_level, spells in block.get("known", {}).items():
            if int(grant_level) > level:
                continue
            for spell in spells:
                if isinstance(spell, dict) and spell.get("choose"):
                    choices.append(spell["choose"])
    if not choices:
        return {}
    parsed = parse_spell_choice(choices[0])
    if not parsed:
        return {}
    parsed["levels"] = [1, 2]
    return {
        "choose": len(choices),
        "from": parsed,
        "label": f"Choose {len(choices)} {subclass.get('shortName', subclass.get('name', 'Subclass'))} spells",
    }


def subclass_savant_spell_choices_by_level(subclass, base_rule):
    school = base_rule.get("from", {}).get("school", "")
    short_name = subclass.get("shortName", subclass.get("name", "Subclass"))
    return {
        level: {
            **rule,
            "from": {
                "levels": list(range(1, int(rule["maximum_spell_level"]) + 1)),
                "class": "Wizard",
                "school": school,
            },
            "label": f"Choose {short_name} Savant spell",
        }
        for level, rule in SAVANT_SPELL_CHOICES_BY_LEVEL.items()
    }


def parse_spell_choice(value):
    rule = {}
    for part in str(value).split("|"):
        key, _, raw = part.partition("=")
        if not raw:
            continue
        if key == "level":
            rule["levels"] = [int(item) for item in raw.split(";") if item.isdigit()]
        elif key == "class":
            rule["class"] = raw
        elif key == "school":
            rule["school"] = raw
    return rule


def subclass_resources(subclass, level):
    resources = {}
    index = int(level) - 1
    for group in subclass.get("subclassTableGroups", []):
        rows = group.get("rows", [])
        labels = " ".join(group.get("colLabels", []))
        if index < 0 or index >= len(rows) or "Energy Die" not in labels:
            continue
        row = rows[index]
        if len(row) >= 2 and row[0] and row[1]:
            resources["psionic_energy_die"] = clean_rules_text(str(row[0])).lower()
            resources["psionic_energy_dice"] = int(row[1])
    return resources


def extract_class_feature_descriptions(class_file_data, class_name, sources):
    descriptions = {}
    for feature in class_file_data.get("classFeature", []):
        if feature.get("source") not in sources:
            continue
        if feature.get("className") != class_name:
            continue
        if feature.get("classSource") and feature.get("classSource") not in sources:
            continue
        description = entry_description(feature.get("entries", []))
        if description:
            descriptions[feature.get("name", "")] = description
    return descriptions


def extract_class_feature_related_features(class_file_data, class_name, sources):
    related_by_feature = {}
    lookup = class_feature_lookup(class_file_data)
    missing = []
    for feature in class_file_data.get("classFeature", []):
        if feature.get("source") not in sources:
            continue
        if feature.get("className") != class_name:
            continue
        if feature.get("classSource") and feature.get("classSource") not in sources:
            continue
        related = related_class_feature_refs(feature.get("entries", []), lookup)
        if related:
            related_by_feature[feature.get("name", "")] = related
        missing.extend(missing_class_feature_refs(feature.get("entries", []), lookup))
    return related_by_feature, missing


def missing_class_feature_refs(entries, lookup):
    missing = []
    for entry in entries or []:
        if isinstance(entry, list):
            missing.extend(missing_class_feature_refs(entry, lookup))
        elif isinstance(entry, dict):
            if entry.get("type") == "refClassFeature":
                ref = feature_ref_parts(entry.get("classFeature", ""))
                key = (
                    ref.get("name", ""),
                    ref.get("class_name", ""),
                    ref.get("class_source", ""),
                    ref.get("level", 0),
                    ref.get("source", ""),
                )
                if key not in lookup:
                    missing.append(entry.get("classFeature", ""))
            missing.extend(missing_class_feature_refs(entry.get("entries", []), lookup))
            missing.extend(missing_class_feature_refs(entry.get("items", []), lookup))
    return missing


def extract_subclass_feature_related_features(class_file_data, class_name, sources):
    related_by_subclass = {}
    lookup = subclass_feature_lookup(class_file_data)
    missing = []
    for feature in class_file_data.get("subclassFeature", []):
        if feature.get("source") not in sources:
            continue
        if feature.get("className") != class_name:
            continue
        if feature.get("classSource") and feature.get("classSource") not in sources:
            continue
        if feature.get("subclassSource") and feature.get("subclassSource") not in sources:
            continue
        related = related_subclass_feature_refs(feature.get("entries", []), lookup)
        if related:
            related_by_subclass.setdefault(feature.get("subclassShortName", ""), {})[feature.get("name", "")] = related
        missing.extend(missing_subclass_feature_refs(feature.get("entries", []), lookup))
    return related_by_subclass, missing


def missing_subclass_feature_refs(entries, lookup):
    missing = []
    for entry in entries or []:
        if isinstance(entry, list):
            missing.extend(missing_subclass_feature_refs(entry, lookup))
        elif isinstance(entry, dict):
            if entry.get("type") == "refSubclassFeature":
                ref = subclass_feature_ref_parts(entry.get("subclassFeature", ""))
                key = (
                    ref.get("name", ""),
                    ref.get("class_name", ""),
                    ref.get("class_source", ""),
                    ref.get("subclass_short_name", ""),
                    ref.get("subclass_source", ""),
                    ref.get("level", 0),
                )
                if key not in lookup:
                    missing.append(entry.get("subclassFeature", ""))
            missing.extend(missing_subclass_feature_refs(entry.get("entries", []), lookup))
            missing.extend(missing_subclass_feature_refs(entry.get("items", []), lookup))
    return missing


def extract_subclass_features_by_short_name(class_file_data, class_name, sources):
    features_by_subclass = {}
    for feature in class_file_data.get("subclassFeature", []):
        if feature.get("source") not in sources:
            continue
        if feature.get("className") != class_name:
            continue
        if feature.get("classSource") and feature.get("classSource") not in sources:
            continue
        if feature.get("subclassSource") and feature.get("subclassSource") not in sources:
            continue
        subclass_short_name = feature.get("subclassShortName", "")
        level = feature.get("level")
        name = feature.get("name", "")
        if not subclass_short_name or not level or not name:
            continue
        level_features = features_by_subclass.setdefault(subclass_short_name, {})
        level_features.setdefault(str(level), []).append(name)
    return features_by_subclass


def extract_subclass_feature_descriptions(class_file_data, class_name, sources):
    descriptions_by_subclass = {}
    for feature in class_file_data.get("subclassFeature", []):
        if feature.get("source") not in sources:
            continue
        if feature.get("className") != class_name:
            continue
        if feature.get("classSource") and feature.get("classSource") not in sources:
            continue
        if feature.get("subclassSource") and feature.get("subclassSource") not in sources:
            continue
        subclass_short_name = feature.get("subclassShortName", "")
        name = feature.get("name", "")
        description = entry_description(feature.get("entries", []))
        if subclass_short_name and name and description:
            descriptions_by_subclass.setdefault(subclass_short_name, {})[name] = description
    return descriptions_by_subclass


def extract_armor_proficiencies(starting):
    armor = []
    armor_names = {
        "light": "Light Armor",
        "medium": "Medium Armor",
        "heavy": "Heavy Armor",
        "shield": "Shields",
    }
    armor_block = starting.get("armor", [])
    for item in armor_block:
        if isinstance(item, str):
            clean = item.replace("|xphb", "").replace("|phb", "")
            armor.append(armor_names.get(clean, clean.title()))
        elif isinstance(item, dict):
            for key, value in item.items():
                if value is True:
                    armor.append(armor_names.get(key, key.title()))
    return sorted(set(armor))


def extract_weapon_proficiencies(starting):
    weapons = []
    weapon_names = {
        "simple": "Simple Weapons",
        "martial": "Martial Weapons",
    }
    weapon_block = starting.get("weapons", [])
    for item in weapon_block:
        if isinstance(item, str):
            clean = item.replace("|xphb", "").replace("|phb", "")
            weapons.append(weapon_names.get(clean, clean.title()))
        elif isinstance(item, dict):
            for key, value in item.items():
                if value is True:
                    weapons.append(weapon_names.get(key, key.title()))
    return sorted(set(weapons))


def extract_tool_proficiencies(starting):
    tools = []
    for block in starting.get("tools", []) or []:
        if isinstance(block, dict):
            for key, value in block.items():
                if value is True and key != "choose":
                    tools.append(key.title())
    return sorted(set(tools))


def default_class_options(class_name, class_file_data=None):
    if class_name in {"Fighter", "Paladin", "Ranger"}:
        return {"fighting_style": extract_fighting_style_options(class_name)}
    if class_name == "Rogue":
        return {"expertise": {"choose": 2, "from": "skill_proficiencies"}}
    if class_name == "Cleric":
        return {"divine_order": ["Protector", "Thaumaturge"]}
    if class_name == "Druid":
        return {"primal_order": ["Magician", "Warden"]}
    if class_name == "Warlock":
        invocations = extract_warlock_invocations(class_file_data or {})
        invocation_details = load_invocation_details()
        return {
            "eldritch_invocations": {
                "choose": 1,
                "from": invocations,
                "options": [
                    invocation_option_record(
                        invocation,
                        invocation_details.get(invocation, {}),
                    )
                    for invocation in invocations
                ],
            }
        }
    return {}


def invocation_option_record(invocation, details):
    return {
        "name": invocation,
        "source": details.get("source", "XPHB"),
        "page": details.get("page"),
        "raw_ref": details.get("raw_ref", f"{invocation}|XPHB"),
        "description": details.get("description", ""),
        "prerequisite_labels": details.get("prerequisite_labels", []),
        "prerequisites": WARLOCK_INVOCATION_PREREQUISITES.get(invocation, {}),
        "support": invocation_support(invocation),
    }


def load_invocation_details():
    return load_optional_feature_details("EI")


def load_maneuver_details():
    return load_optional_feature_details("MV:B")


def maneuver_option_record(maneuver, details):
    return {
        "name": maneuver,
        "source": details.get("source", "XPHB"),
        "page": details.get("page"),
        "raw_ref": details.get("raw_ref", f"{maneuver}|XPHB"),
        "description": details.get("description", ""),
        "prerequisite_labels": details.get("prerequisite_labels", []),
        "prerequisites": {},
        "support": {
            "selection": "supported",
            "prerequisites": "supported",
            "permanent_choices": "supported",
            "sheet_grants": "supported",
            "active_play": "description_only",
            "notes": "",
        },
    }


def load_optional_feature_details(feature_type):
    path = RAW_DIR / "optionalfeatures.json"
    if not path.exists():
        return {}
    records = load_raw("optionalfeatures.json").get("optionalfeature", [])
    details = {}
    for record in records:
        if record.get("source") != "XPHB":
            continue
        if feature_type not in set(record.get("featureType", []) or []):
            continue
        name = record.get("name", "")
        if not name:
            continue
        details[name] = {
            "source": record.get("source", ""),
            "page": record.get("page"),
            "raw_ref": f"{name}|{record.get('source', '')}",
            "description": entry_description(record.get("entries", [])),
            "prerequisite_labels": invocation_prerequisite_labels(record.get("prerequisite", [])),
        }
    return details


def invocation_prerequisite_labels(prerequisites):
    labels = []
    for prerequisite in prerequisites or []:
        if not isinstance(prerequisite, dict):
            continue
        level = prerequisite.get("level")
        if isinstance(level, dict) and level.get("level"):
            class_name = level.get("class", {}).get("name", "")
            class_text = f" {class_name}" if class_name else ""
            labels.append(f"Level {level['level']}{class_text}")
        for spell in prerequisite.get("spell", []) or []:
            if isinstance(spell, str):
                labels.append(clean_rules_text(spell.split("#", 1)[0].replace("|", " ")).title())
            elif isinstance(spell, dict):
                labels.append(clean_rules_text(spell.get("entrySummary") or spell.get("entry") or ""))
        for invocation in prerequisite.get("optionalfeature", []) or []:
            labels.append(clean_rules_text(str(invocation).split("|", 1)[0]))
        if prerequisite.get("otherSummary"):
            labels.append(clean_rules_text(
                prerequisite["otherSummary"].get("entrySummary")
                or prerequisite["otherSummary"].get("entry")
                or ""
            ))
    return sorted(set(label for label in labels if label))


def extract_fighting_style_options(class_name):
    available = {
        feat.get("name", "")
        for feat in load_raw("feats.json").get("feat", [])
        if feat.get("source") == "XPHB"
        and str(feat.get("category", "")).startswith("FS")
    }
    return [
        style
        for style in CLASS_FIGHTING_STYLE_OPTIONS.get(class_name, [])
        if style in available
    ]


def extract_warlock_invocations(class_file_data):
    for feature in class_file_data.get("classFeature", []):
        if feature.get("name") != "Eldritch Invocation Options" or feature.get("source") != "XPHB":
            continue
        options = []
        for entry in feature.get("entries", []):
            if isinstance(entry, dict) and entry.get("type") == "options":
                for option in entry.get("entries", []):
                    ref = option.get("optionalfeature", "") if isinstance(option, dict) else ""
                    if ref:
                        options.append(ref.split("|", 1)[0])
        return sorted(set(options))
    return []


def first_package_items(starting_equipment):
    packages = normalize_equipment_packages(starting_equipment)
    return packages[0]["items"] if packages else []


def flatten_list(values):
    flattened = []
    for value in values:
        if isinstance(value, list):
            flattened.extend(value)
        else:
            flattened.append(value)
    return flattened


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")


def normalize_classes(sources):
    classes = []
    for slug in CORE_CLASS_SLUGS:
        raw = load_raw(f"class/class-{slug}.json")
        for class_entry in raw.get("class", []):
            if class_entry.get("source") in sources:
                classes.append(normalize_class(class_entry, raw))
                break
    return sorted(classes, key=lambda item: item["name"])


def clean_components(components):
    names = []
    for key, value in components.items():
        if value:
            names.append(key.upper())
    return names


def clean_spell_classes(spell, spell_lookup):
    lookup = (
        spell_lookup
        .get(spell.get("source", "").lower(), {})
        .get(spell["name"].lower(), {})
    )
    classes = []
    for source, class_map in lookup.get("class", {}).items():
        if source not in {"XPHB", "PHB"}:
            continue
        classes.extend(class_name for class_name, enabled in class_map.items() if enabled)
    return sorted(set(classes))


def normalize_spells(sources):
    spell_lookup = load_raw("generated/gendata-spell-source-lookup.json")
    spells = []
    for filename in SPELL_FILES:
        raw = load_raw(f"spells/{filename}")
        for spell in raw.get("spell", []):
            if spell.get("source") not in sources:
                continue
            spells.append({
                "name": spell["name"],
                "source": spell.get("source", ""),
                "level": spell.get("level", 0),
                "school": SCHOOL_NAMES.get(spell.get("school", ""), spell.get("school", "")),
                "school_code": spell.get("school", ""),
                "description": spell_description(spell),
                "classes": clean_spell_classes(spell, spell_lookup),
                "casting_time": ", ".join(
                    f"{time.get('number', '')} {time.get('unit', '')}".strip()
                    for time in spell.get("time", [])
                ),
                "range": normalize_range(spell.get("range", {})),
                "components": clean_components(spell.get("components", {})),
                "duration": normalize_duration(spell.get("duration", [])),
                "raw_ref": f"{spell['name']}|{spell.get('source', '')}",
            })
    return sorted(spells, key=lambda item: (item["level"], item["name"]))


def spell_description(spell):
    parts = []
    description = entry_description(spell.get("entries", []))
    if description:
        parts.append(description)
    higher_level = entry_description(spell.get("entriesHigherLevel", []))
    if higher_level:
        if higher_level.startswith("Using a Higher-Level Spell Slot"):
            parts.append(higher_level)
        else:
            parts.append(f"Using a Higher-Level Spell Slot. {higher_level}")
    return "\n\n".join(parts)


def normalize_range(range_data):
    distance = range_data.get("distance", {})
    if isinstance(distance, dict):
        amount = distance.get("amount")
        unit = distance.get("type", "")
        return f"{amount} {unit}".strip() if amount else unit.title()
    return range_data.get("type", "").title()


def normalize_duration(duration_data):
    parts = []
    for item in duration_data:
        if item.get("type") == "instant":
            parts.append("Instantaneous")
        elif item.get("type") == "timed":
            duration = item.get("duration", {})
            amount = duration.get("amount", "")
            unit = duration.get("type", "")
            concentration = "Concentration, up to " if item.get("concentration") else ""
            parts.append(f"{concentration}{amount} {unit}".strip())
        else:
            parts.append(item.get("type", "").title())
    return ", ".join(part for part in parts if part)


def normalize_equipment():
    names = set()
    for filename in ("items-base.json", "items.json"):
        raw = load_raw(filename)
        for item in raw.get("baseitem", []) + raw.get("item", []):
            if item.get("source") in DEFAULT_SOURCES:
                names.add(item["name"])
    return sorted(names)


def normalize_mastery_name(value):
    if not value:
        return ""
    return str(value).split("|", 1)[0]


def normalize_weapons():
    weapons = []
    for filename in ("items-base.json", "items.json"):
        raw = load_raw(filename)
        for item in raw.get("baseitem", []) + raw.get("item", []):
            if item.get("source") not in DEFAULT_SOURCES:
                continue
            if not item.get("weaponCategory"):
                continue
            weapons.append({
                "name": item["name"],
                "category": item.get("weaponCategory", "").title(),
                "damage": item.get("dmg1", ""),
                "damage_type": item.get("dmgType", ""),
                "mastery": normalize_mastery_name((item.get("mastery") or [""])[0]),
            })
    return sorted(weapons, key=lambda item: item["name"])


def normalize_feat_descriptions(sources):
    raw = load_raw("feats.json")
    descriptions = {}
    for feat in raw.get("feat", []):
        if feat.get("source") not in sources:
            continue
        description = entry_description(feat.get("entries", []))
        if description:
            descriptions[feat["name"]] = description
    return descriptions


def normalize_general_feats(sources):
    raw = load_raw("feats.json")
    feats = []
    for feat in raw.get("feat", []):
        if feat.get("source") not in sources or feat.get("category") not in {"G", "EB"}:
            continue
        category = "epic_boon" if feat.get("category") == "EB" else "general"
        feats.append({
            "id": f"{slug(feat.get('name', 'feat'))}_{feat.get('source', '').lower()}",
            "name": feat.get("name", ""),
            "category": category,
            "source": feat.get("source", ""),
            "repeatable": bool(feat.get("repeatable")),
            "prerequisites": normalize_feat_prerequisites(feat.get("prerequisite", [])),
            "ability_increase": normalize_feat_ability_increase(feat.get("ability", [])),
            "automatic_features": [feat.get("name", "")],
            "required_choices": normalize_feat_required_choices(feat),
            "description": entry_description(feat.get("entries", [])),
            "unsupported_choices": unsupported_feat_choices(feat),
            "raw_ref": f"{feat.get('name', '')}|{feat.get('source', '')}",
        })
    return sorted(feats, key=lambda item: item["name"])


def normalize_feat_prerequisites(prerequisites):
    groups = []
    for prereq in prerequisites or []:
        group = {
            "minimum_level": int(prereq.get("level", 0) or 0),
            "ability_scores": normalize_prerequisite_abilities(prereq.get("ability", [])),
            "spellcasting": bool(prereq.get("spellcasting2020") or prereq.get("spellcasting")),
            "proficiencies": normalize_prerequisite_proficiencies(prereq.get("proficiency", [])),
            "features": list(prereq.get("feature", [])),
            "other": [],
        }
        if prereq.get("otherSummary"):
            group["other"].append(prereq["otherSummary"].get("entrySummary") or prereq["otherSummary"].get("entry", ""))
        groups.append(group)
    if not groups:
        groups.append({
            "minimum_level": 0,
            "ability_scores": {},
            "spellcasting": False,
            "proficiencies": [],
            "features": [],
            "other": [],
        })
    minimum_level = min((group["minimum_level"] for group in groups if group["minimum_level"]), default=0)
    return {
        "minimum_level": minimum_level,
        "any": groups,
    }


def normalize_prerequisite_abilities(abilities):
    options = []
    for option in abilities or []:
        if not isinstance(option, dict):
            continue
        required = {}
        for ability, score in option.items():
            required[normalize_ability_name(ability)] = int(score)
        if required:
            options.append(required)
    return options


def normalize_prerequisite_proficiencies(proficiencies):
    normalized = []
    for item in proficiencies or []:
        if not isinstance(item, dict):
            continue
        if item.get("armor"):
            normalized.append({"type": "armor", "value": armor_prerequisite_name(item["armor"])})
        if item.get("weapon"):
            normalized.append({"type": "weapon", "value": str(item["weapon"]).title()})
        if item.get("tool"):
            normalized.append({"type": "tool", "value": title_case_name(item["tool"])})
    return normalized


def armor_prerequisite_name(value):
    return {
        "light": "Light Armor",
        "medium": "Medium Armor",
        "heavy": "Heavy Armor",
        "shield": "Shields",
    }.get(str(value).lower(), title_case_name(value))


def normalize_feat_ability_increase(ability_entries):
    if not ability_entries:
        return {}
    modes = []
    for entry in ability_entries:
        if not isinstance(entry, dict):
            continue
        choose = entry.get("choose", {})
        maximum = int(entry.get("max", 20) or 20)
        fixed = {
            normalize_ability_name(ability): int(amount)
            for ability, amount in entry.items()
            if ability in ABILITY_NAMES and isinstance(amount, int)
        }
        if fixed:
            modes.append({
                "mode": "fixed",
                "choose": 1,
                "from": list(fixed.keys()),
                "amount": next(iter(fixed.values())),
                "maximum": maximum,
            })
        elif choose:
            modes.append({
                "mode": "choose",
                "choose": int(choose.get("count", 1) or 1),
                "from": [normalize_ability_name(ability) for ability in choose.get("from", [])],
                "amount": int(choose.get("amount", 1) or 1),
                "maximum": maximum,
                "note": choose.get("entry", ""),
            })
    if len(modes) == 1:
        return modes[0]
    return {"mode": "multi_mode", "modes": modes}


def normalize_feat_required_choices(feat):
    choices = []
    for key, label in (
        ("skillProficiencies", "Skill proficiency"),
        ("toolProficiencies", "Tool proficiency"),
        ("languageProficiencies", "Language proficiency"),
    ):
        for index, choice in enumerate(feat.get(key, []) or []):
            if isinstance(choice, dict) and "choose" in choice:
                choices.append({
                    "id": f"{slug(feat.get('name', 'feat'))}_{slug(label)}_{index}",
                    "type": key,
                    "name": label,
                    "required": True,
                    "raw": choice,
                })
    for index, spell_block in enumerate(feat.get("additionalSpells", []) or []):
        if contains_spell_choice(spell_block):
            choices.append({
                "id": f"{slug(feat.get('name', 'feat'))}_spell_choice_{index}",
                "type": "spell_choice",
                "name": "Spell choice",
                "required": True,
                "raw": spell_block,
            })
    return choices


def contains_spell_choice(value):
    if isinstance(value, dict):
        if "choose" in value:
            return True
        return any(contains_spell_choice(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_spell_choice(item) for item in value)
    return False


def unsupported_feat_choices(feat):
    unsupported = []
    if normalize_feat_required_choices(feat):
        unsupported.append("Has required choices that need UI support")
    if feat.get("additionalSpells"):
        unsupported.append("May grant or choose spells")
    return unsupported


def write_metadata(sources):
    metadata = {
        "source_repo": "5etools-mirror-3/5etools-src",
        "source_base_url": BASE_URL,
        "sources": sorted(sources),
        "raw_dir": str(RAW_DIR.relative_to(ROOT_DIR)),
        "imported_dir": str(IMPORTED_DIR.relative_to(ROOT_DIR)),
    }
    write_json("metadata.json", metadata)


def download_all():
    paths = [*ROOT_FILES]
    paths.extend(f"class/class-{slug}.json" for slug in CORE_CLASS_SLUGS)
    paths.extend(f"spells/{filename}" for filename in SPELL_FILES)
    for relative_path in paths:
        print(f"Downloading {relative_path}")
        download_file(relative_path)


def import_all(sources):
    write_json("classes.json", normalize_classes(sources))
    write_json("species.json", normalize_species(sources))
    write_json("backgrounds.json", normalize_backgrounds(sources))
    write_json("feats.json", normalize_general_feats(sources))
    write_json("spells.json", normalize_spells(sources))
    write_json("equipment.json", normalize_equipment())
    write_json("weapons.json", normalize_weapons())
    write_json("beasts.json", beast_catalog())
    write_json("rules.json", {
        "abilities": list(ABILITY_NAMES.values()),
        "skills": SKILL_TO_ABILITY,
        "origin_feats": ORIGIN_FEATS,
        "feature_descriptions": normalize_feat_descriptions(sources),
    })
    write_metadata(sources)
    try:
        from tools.generate_coverage_audit import generate_coverage_audit
        from tools.generate_level_13_16_map import generate_level_13_16_map
        from tools.generate_level_9_12_map import generate_level_9_12_map
    except ModuleNotFoundError:
        from generate_coverage_audit import generate_coverage_audit
        from generate_level_13_16_map import generate_level_13_16_map
        from generate_level_9_12_map import generate_level_9_12_map
    generate_coverage_audit()
    generate_level_9_12_map()
    generate_level_13_16_map()


def main():
    parser = argparse.ArgumentParser(description="Download and normalize 5e.tools JSON data.")
    parser.add_argument("--skip-download", action="store_true", help="Use existing files in data/raw/5etools.")
    parser.add_argument(
        "--sources",
        nargs="+",
        default=sorted(DEFAULT_SOURCES),
        help="5e.tools source codes to import, e.g. XPHB PHB.",
    )
    args = parser.parse_args()

    sources = {source.upper() for source in args.sources}
    if not args.skip_download:
        download_all()
    import_all(sources)
    print(f"Imported 5e.tools data for sources: {', '.join(sorted(sources))}")


if __name__ == "__main__":
    main()
