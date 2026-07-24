"""Generate feature and choice coverage maps for a level band."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from rules.proficiencies import proficiency_bonus_for_level
from tools.generate_coverage_audit import CLASS_FEATURE_CLASSIFICATIONS, handler_verified

IMPORTED_DIR = ROOT_DIR / "data" / "imported" / "5etools"
COVERAGE_DIR = ROOT_DIR / "data" / "coverage"
DESCRIPTION_ONLY_HANDLER = "services.character_engine.feature_descriptions_for_character"

FEATURE_CHOICE_HANDLERS = {
    ("Bard", 9, "Expertise"): {
        "choice_type": "expertise_choice",
        "status": "generic_ready",
        "handler": "rules.class_choice_rules.bard_level_9_expertise",
        "blocks_level_path": False,
        "notes": "Bard gains another Expertise choice at level 9; handled as an additional class-option Expertise selection.",
    },
    ("Ranger", 9, "Expertise"): {
        "choice_type": "expertise_choice",
        "status": "generic_ready",
        "handler": "rules.class_choice_rules.ranger_level_9_expertise",
        "blocks_level_path": False,
        "notes": "Ranger gains another Expertise choice at level 9; handled as an additional class-option Expertise selection.",
    },
    ("Sorcerer", 10, "Metamagic"): {
        "choice_type": "metamagic_choice",
        "status": "generic_ready",
        "handler": "rules.class_choice_rules.metamagic",
        "blocks_level_path": False,
        "notes": "Sorcerer Metamagic count scales to four total options at level 10.",
    },
    ("Warlock", 11, "Mystic Arcanum"): {
        "choice_type": "mystic_arcanum_spell_choice",
        "status": "generic_ready",
        "handler": "rules.mystic_arcanum.mystic_arcanum_options",
        "blocks_level_path": False,
        "notes": "Mystic Arcanum is handled as a level-specific Warlock Arcanum spell choice.",
    },
    ("Warlock", 13, "Mystic Arcanum"): {
        "choice_type": "mystic_arcanum_spell_choice",
        "status": "generic_ready",
        "handler": "rules.mystic_arcanum.mystic_arcanum_options",
        "blocks_level_path": False,
        "notes": "Mystic Arcanum is handled as a level 7 Warlock Arcanum spell choice.",
    },
    ("Warlock", 15, "Mystic Arcanum"): {
        "choice_type": "mystic_arcanum_spell_choice",
        "status": "generic_ready",
        "handler": "rules.mystic_arcanum.mystic_arcanum_options",
        "blocks_level_path": False,
        "notes": "Mystic Arcanum is handled as a level 8 Warlock Arcanum spell choice.",
    },
    ("Warlock", 17, "Mystic Arcanum"): {
        "choice_type": "mystic_arcanum_spell_choice",
        "status": "generic_ready",
        "handler": "rules.mystic_arcanum.mystic_arcanum_options",
        "blocks_level_path": False,
        "notes": "Mystic Arcanum is handled as a level 9 Warlock Arcanum spell choice.",
    },
}

GENERIC_FEATURE_HANDLERS = {
    "Ability Score Improvement": {
        "choice_type": "asi_or_feat",
        "status": "generic_ready",
        "handler": "rules.level_up.asi_or_feat",
        "blocks_level_path": False,
        "notes": "Existing ASI/general feat handler can be reused when this level is enabled.",
    },
    "Subclass Feature": {
        "choice_type": "subclass_feature_gain",
        "status": "generic_ready",
        "handler": "rules.level_up.classify_level_features",
        "blocks_level_path": False,
        "notes": "Existing later-subclass-feature handling should turn this into the selected subclass features.",
    },
    "Epic Boon": {
        "choice_type": "epic_boon_or_general_feat_choice",
        "status": "generic_ready",
        "handler": "rules.level_up.epic_boon_choice",
        "blocks_level_path": False,
        "notes": "Level 19 is handled as an eligible Epic Boon or other qualified supported feat choice.",
    },
    "Spell Mastery": {
        "choice_type": "spell_mastery_selection",
        "status": "generic_ready",
        "handler": "rules.level_up.spell_mastery_choice",
        "blocks_level_path": False,
        "notes": "Wizard level 18 Spell Mastery is handled as one level 1 and one level 2 spellbook spell choice.",
    },
    "Signature Spells": {
        "choice_type": "signature_spells_selection",
        "status": "generic_ready",
        "handler": "rules.level_up.signature_spells_choice",
        "blocks_level_path": False,
        "notes": "Wizard level 20 Signature Spells is handled as two level 3 spellbook spell choices.",
    },
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def slug(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")


def normalize_feature_name(feature):
    if isinstance(feature, dict):
        return feature.get("name", "")
    return str(feature)


def feature_type(feature):
    if isinstance(feature, dict):
        return feature.get("type", "automatic_feature")
    return "automatic_feature"


def feature_classification(name):
    return CLASS_FEATURE_CLASSIFICATIONS.get(
        name,
        ("active_play_description_only", DESCRIPTION_ONLY_HANDLER),
    )


def progression_entry(class_data, level):
    entry = (class_data.get("progression") or {}).get(str(level), {})
    return entry if isinstance(entry, dict) else {"features": list(entry or [])}


def progression_resources(class_data, level):
    return dict(progression_entry(class_data, level).get("resources", {}))


def progression_spell_fields(class_data, level):
    return {
        key: value
        for key, value in progression_entry(class_data, level).items()
        if key not in {"features", "resources"}
    }


def changed_values(before, after):
    changes = {}
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changes[key] = {
                "before": before.get(key),
                "after": after.get(key),
            }
    return changes


def classify_feature(class_data, level, feature):
    class_name = class_data["name"]
    name = normalize_feature_name(feature)
    feature_kind = feature_type(feature)
    rule = FEATURE_CHOICE_HANDLERS.get((class_name, level, name)) or GENERIC_FEATURE_HANDLERS.get(name)
    if rule:
        return {
            "id": f"{slug(class_name)}_{level}_{slug(name)}",
            "name": name,
            "feature_type": feature_kind,
            **rule,
        }
    classification, handler = feature_classification(name)
    return {
        "id": f"{slug(class_name)}_{level}_{slug(name)}",
        "name": name,
        "feature_type": feature_kind,
        "choice_type": "none",
        "status": "partial_support" if classification == "unsupported" else "audited_automatic",
        "classification": classification,
        "handler": handler or "rules.level_up.classify_level_feature",
        "handler_verified": handler_verified(handler or "rules.level_up.classify_level_feature"),
        "blocks_level_path": False,
        "notes": "Feature is explicitly classified for the enabled level band." if name in CLASS_FEATURE_CLASSIFICATIONS else "Feature text is retained on the final sheet; no durable build-time sheet value is modeled for this feature.",
    }


def resource_choice_entries(class_data, level):
    class_name = class_data["name"]
    before = progression_resources(class_data, level - 1)
    after = progression_resources(class_data, level)
    entries = []

    mastery_before = int(before.get("weapon_mastery_count", 0) or 0)
    mastery_after = int(after.get("weapon_mastery_count", 0) or 0)
    if mastery_after > mastery_before:
        entries.append({
            "id": f"{slug(class_name)}_{level}_weapon_mastery",
            "name": "Weapon Mastery",
            "feature_type": "resource_delta",
            "choice_type": "weapon_mastery_selection",
            "status": "generic_ready",
            "handler": "rules.level_up.weapon_mastery_level_up_choice",
            "blocks_level_path": False,
            "notes": f"Weapon Mastery count increases from {mastery_before} to {mastery_after}.",
        })

    invocation_before = int(before.get("eldritch_invocations", 0) or 0)
    invocation_after = int(after.get("eldritch_invocations", 0) or 0)
    if invocation_after > invocation_before:
        entries.append({
            "id": f"{slug(class_name)}_{level}_eldritch_invocations",
            "name": "Eldritch Invocations",
            "feature_type": "resource_delta",
            "choice_type": "invocation_choice",
            "status": "generic_ready",
            "handler": "rules.class_choice_rules.eldritch_invocations",
            "blocks_level_path": False,
            "notes": f"Invocation count increases from {invocation_before} to {invocation_after}.",
        })

    return entries


def spell_progression_entry(class_data, level):
    before = progression_spell_fields(class_data, level - 1)
    after = progression_spell_fields(class_data, level)
    changes = changed_values(before, after)
    if not changes:
        return {}
    return {
        "id": f"{slug(class_data['name'])}_{level}_spell_progression",
        "name": "Spellcasting progression",
        "feature_type": "progression_delta",
        "choice_type": "spell_selection",
        "status": "generic_ready",
        "handler": "rules.level_up.spell_level_up_choices",
        "blocks_level_path": False,
        "notes": "Existing spell level-up choices should cover cantrip, prepared, known, and Wizard spellbook increases; verify high-level PDF display when enabling.",
        "changes": changes,
    }


def ritual_caster_entry(class_data, level):
    if proficiency_bonus_for_level(level) <= proficiency_bonus_for_level(level - 1):
        return {}
    return {
        "id": f"{slug(class_data['name'])}_{level}_ritual_caster_bonus_spells",
        "name": "Ritual Caster proficiency-bonus scaling",
        "feature_type": "proficiency_bonus_delta",
        "choice_type": "feat_spell_selection",
        "status": "generic_ready",
        "handler": "rules.level_up.ritual_caster_level_up_choices",
        "blocks_level_path": False,
        "notes": f"Proficiency bonus increases at level {level}, so Ritual Caster may grant another ritual spell choice.",
    }


def subclass_feature_entries(class_data, level):
    entries = []
    for subclass in class_data.get("subclasses", []):
        features = subclass.get("level_features", {}).get(str(level), [])
        grants = subclass.get("grants_by_level", {}).get(str(level), {})
        if not features and not grants:
            continue
        spell_grants = grants.get("spell_grants", []) if isinstance(grants, dict) else []
        resources = grants.get("resources", {}) if isinstance(grants, dict) else {}
        classifications = [
            {
                "name": feature,
                "classification": feature_classification(feature)[0],
                "handler": feature_classification(feature)[1],
            }
            for feature in features
        ]
        unsupported = [item["name"] for item in classifications if item["classification"] == "unsupported"]
        handler = "rules.leveling.get_active_subclass_grants" if spell_grants or resources else "rules.level_up.classify_level_features"
        if len(classifications) == 1 and classifications[0]["handler"]:
            handler = classifications[0]["handler"]
        entries.append({
            "id": f"{slug(class_data['name'])}_{slug(subclass['short_name'])}_{level}",
            "class": class_data["name"],
            "subclass": subclass["name"],
            "level": level,
            "features": list(features),
            "feature_classifications": classifications,
            "spell_grants": [
                grant.get("name", "")
                for grant in spell_grants
                if grant.get("name")
            ],
            "resources": resources,
            "status": "partial_support" if unsupported else "generic_ready",
            "handler": handler,
            "handler_verified": handler_verified(handler),
            "blocks_level_path": False,
            "notes": "Spell grants/resources are represented in normalized subclass grants." if spell_grants or resources else "Feature text is explicitly classified for the enabled level band.",
            "unsupported_features": unsupported,
        })
    return entries


def class_level_entry(class_data, level):
    progression = progression_entry(class_data, level)
    feature_entries = [
        classify_feature(class_data, level, feature)
        for feature in progression.get("features", []) or []
    ]
    required_choices = [
        entry
        for entry in [
            *feature_entries,
            *resource_choice_entries(class_data, level),
            spell_progression_entry(class_data, level),
            ritual_caster_entry(class_data, level),
        ]
        if entry and entry.get("choice_type") != "none"
    ]
    resources_before = progression_resources(class_data, level - 1)
    resources_after = progression_resources(class_data, level)
    subclass_entries = subclass_feature_entries(class_data, level)
    return {
        "id": f"{slug(class_data['name'])}_{level}",
        "class": class_data["name"],
        "level": level,
        "features": [normalize_feature_name(feature) for feature in progression.get("features", []) or []],
        "feature_entries": feature_entries,
        "required_choices": required_choices,
        "resource_changes": changed_values(resources_before, resources_after),
        "spellcasting_changes": changed_values(
            progression_spell_fields(class_data, level - 1),
            progression_spell_fields(class_data, level),
        ),
        "subclass_features": subclass_entries,
        "blocks_level_path": any(choice.get("blocks_level_path") for choice in required_choices),
    }


def recommended_order(start_level, end_level, blocking_items):
    recommendations = []
    if blocking_items:
        recommendations.append("Implement the blocking required-choice handlers listed in blocking_items.")
    recommendations.extend([
        f"Verify level {start_level}-{end_level} spell progression, Wizard spellbook gains, Ritual Caster scaling, and high-level PDF spell placement.",
        "Review automatic class/subclass features for hidden sheet-value effects.",
        f"Enable levels {start_level}-{end_level} and add end-to-end level-up tests.",
    ])
    return recommendations


def generate_level_band_map(start_level, end_level, output_path):
    levels = range(start_level, end_level + 1)
    classes = read_json(IMPORTED_DIR / "classes.json")
    class_levels = {}
    blocking_items = []
    generic_ready = []
    subclass_feature_count = 0

    for class_data in classes:
        for level in levels:
            entry = class_level_entry(class_data, level)
            class_levels[entry["id"]] = entry
            subclass_feature_count += len(entry["subclass_features"])
            for choice in entry["required_choices"]:
                key = choice["id"]
                if choice.get("blocks_level_path"):
                    blocking_items.append(key)
                elif choice.get("status") == "generic_ready":
                    generic_ready.append(key)

    required_choice_count = sum(
        len(entry["required_choices"])
        for entry in class_levels.values()
    )
    level_map = {
        "generated_from": "data/imported/5etools/classes.json",
        "level_range": [start_level, end_level],
        "summary": {
            "class_level_count": len(class_levels),
            "subclass_feature_count": subclass_feature_count,
            "required_choice_count": required_choice_count,
            "blocking_choice_count": len(blocking_items),
            "generic_ready_choice_count": len(generic_ready),
        },
        "blocking_items": sorted(blocking_items),
        "generic_ready_items": sorted(generic_ready),
        "recommended_order": recommended_order(start_level, end_level, blocking_items),
        "class_levels": class_levels,
    }
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(level_map, indent=2) + "\n", encoding="utf-8")
    return level_map
