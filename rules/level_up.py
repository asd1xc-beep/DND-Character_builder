import hashlib
import json
from copy import deepcopy
from uuid import uuid4

from rules.choice_validation import (
    ability_adjustment_from_asi,
    ability_adjustment_from_feat,
    validate_feat_selection,
    validate_asi_selection,
)
from rules.class_choice_rules import (
    battle_master_maneuver_total,
    class_level_up_option_choices,
    eligible_spell_lists_for_prepared_spells,
)
from rules.feat_rules import (
    eligible_feats,
    feat_ability_choice_is_valid,
    feat_choice_schema,
    feat_extra_choices_are_valid,
    feat_is_eligible,
    feat_is_supported_for_selection,
    feat_support_status,
    ritual_spell_options,
)
from rules.hit_points import fixed_hit_die_gain, fixed_hit_points_per_level
from rules.leveling import (
    available_spell_levels_from_slots,
    class_progression_at_level,
    get_available_spell_levels,
    get_cantrip_limit,
    get_class_resources,
    get_class_progression,
    get_casting_type,
    get_known_spell_limit,
    get_prepared_spell_limit,
    is_supported_level,
    normalize_level,
    effective_spellcasting,
    selected_subclass_options,
    subclass_features_at_level,
    supported_levels_message,
)
from rules.mystic_arcanum import (
    mystic_arcanum_source_level_for_spell_level,
    upsert_mystic_arcanum_record,
)
from rules.proficiencies import available_class_skill_options, proficiency_bonus_for_level
from rules.weapon_mastery import eligible_weapon_mastery_names
from rules.wizard_spellbook import wizard_spellbook_spells
from rules.wizard_savant import (
    is_savant_spell_choice_key,
    savant_spell_choice_key,
    savant_spell_choice_rule,
    savant_spell_source_level,
    selected_savant_spells,
)


def ensure_level_tracking(character):
    class_name = character.get("class", "")
    level = normalize_level(character.get("level", 1))
    class_levels = character.setdefault("class_levels", {})
    if class_name:
        class_levels[class_name] = level
    character.setdefault("pending_choices", [])
    character.setdefault("level_history", [])
    character.setdefault("completed_level_up_transactions", [])
    character.setdefault("hp_rolls", [])
    character.setdefault("hit_dice", {})
    return character


def classify_level_features(feature, character, class_data, class_name, target_level):
    if isinstance(feature, dict) and feature.get("type") == "subclass_choice":
        first_level = first_subclass_choice_level(class_data)
        if first_level and int(target_level) > first_level:
            subclass_name = character.get("subclass", "")
            subclass_features = subclass_features_at_level(class_data, subclass_name, target_level)
            return [
                {
                    "id": f"{slug(class_name)}_{target_level}_{slug(name)}",
                    "type": "automatic_feature",
                    "subtype": "subclass_feature_gain",
                    "name": name,
                    "source": subclass_name or class_name,
                    "level": target_level,
                }
                for name in subclass_features
            ] or [{
                "id": f"{slug(class_name)}_{target_level}_subclass_feature_gain",
                "type": "automatic_feature",
                "subtype": "subclass_feature_gain",
                "name": "Subclass Feature",
                "source": subclass_name or class_name,
                "level": target_level,
            }]
    return [classify_level_feature(feature, class_name, target_level)]


def first_subclass_choice_level(class_data):
    levels = []
    for level, entry in (class_data.get("progression") or {}).items():
        features = entry.get("features", []) if isinstance(entry, dict) else entry or []
        for feature in features:
            if isinstance(feature, dict) and feature.get("type") == "subclass_choice":
                levels.append(int(level))
    return min(levels) if levels else 0


def classify_level_feature(feature, class_name, target_level):
    if isinstance(feature, dict):
        if feature.get("name") == "Epic Boon":
            return epic_boon_choice(class_name, target_level, feature)
        if feature.get("name") == "Spell Mastery":
            return spell_mastery_choice(class_name, target_level, feature)
        if feature.get("name") == "Signature Spells":
            return signature_spells_choice(class_name, target_level, feature)
        return deepcopy(feature)
    if feature == "Epic Boon":
        return epic_boon_choice(class_name, target_level)
    if feature == "Spell Mastery":
        return spell_mastery_choice(class_name, target_level)
    if feature == "Signature Spells":
        return signature_spells_choice(class_name, target_level)
    return {
        "id": f"{class_name.lower()}_{target_level}_{slug(feature)}",
        "type": "automatic_feature",
        "name": feature,
        "source": class_name,
        "level": target_level,
    }


def spell_mastery_choice(class_name, target_level, feature=None):
    source = {}
    if isinstance(feature, dict):
        raw_source = feature.get("source", {}) or {}
        source = dict(raw_source) if isinstance(raw_source, dict) else {}
    if not source:
        source = {
            "type": "class_level",
            "class_name": class_name,
            "level": target_level,
        }
    return {
        "id": f"{slug(class_name)}_level_{target_level}_spell_mastery",
        "type": "spell_mastery_selection",
        "name": "Spell Mastery",
        "required": True,
        "source": source,
        "status": "unresolved",
    }


def signature_spells_choice(class_name, target_level, feature=None):
    source = {}
    if isinstance(feature, dict):
        raw_source = feature.get("source", {}) or {}
        source = dict(raw_source) if isinstance(raw_source, dict) else {}
    if not source:
        source = {
            "type": "class_level",
            "class_name": class_name,
            "level": target_level,
        }
    return {
        "id": f"{slug(class_name)}_level_{target_level}_signature_spells",
        "type": "signature_spells_selection",
        "name": "Signature Spells",
        "required": True,
        "choose": 2,
        "source": source,
        "status": "unresolved",
    }


def epic_boon_choice(class_name, target_level, feature=None):
    source = {}
    if isinstance(feature, dict):
        raw_source = feature.get("source", {}) or {}
        source = dict(raw_source) if isinstance(raw_source, dict) else {}
    if not source:
        source = {
            "type": "class_level",
            "class_name": class_name,
            "level": target_level,
        }
    return {
        "id": f"{slug(class_name)}_level_{target_level}_epic_boon",
        "type": "feat_selection",
        "name": "Epic Boon",
        "feat_label": "Epic Boon",
        "required": True,
        "source": source,
        "allowed_categories": ["epic_boon", "general"],
        "recommended_categories": ["epic_boon"],
        "status": "unresolved",
    }


def get_level_up_plan(character, target_level, data):
    current_level = normalize_level(character.get("level", 1))
    target_level = normalize_level(target_level)
    class_name = character.get("class", "")
    class_data = data.get("classes_by_name", {}).get(class_name, {})

    if not class_name or not class_data:
        return empty_plan(current_level, target_level, class_name, "Choose a class before leveling up.")
    if not is_supported_level(current_level) or not is_supported_level(target_level):
        return empty_plan(current_level, target_level, class_name, supported_levels_message())
    if target_level <= current_level:
        return empty_plan(current_level, target_level, class_name, "Choose a higher level to preview.")
    if target_level != current_level + 1:
        return empty_plan(current_level, target_level, class_name, "Only one level at a time is supported right now.")

    constitution_modifier = character.get("ability_modifiers", {}).get("Constitution", 0)
    hit_die = class_data.get("hit_die", 0)
    hp_base_gain = fixed_hit_die_gain(hit_die) if hit_die else 0
    hp_increase = fixed_hit_points_per_level(hit_die, constitution_modifier) if hit_die else 0
    species_data = data.get("species_by_name", {}).get(character.get("species"), {})
    if "Dwarven Toughness" in species_data.get("traits", []):
        hp_increase += 1
    if "Tough" in active_origin_feats(character):
        hp_increase += 2

    automatic_features = []
    pending_choices = []
    for feature in class_progression_at_level(class_data, target_level):
        for feature_entry in classify_level_features(feature, character, class_data, class_name, target_level):
            feature_entry = enrich_level_choice(feature_entry, character, class_data, target_level, data)
            if feature_entry.get("type") == "automatic_feature":
                automatic_features.append(feature_entry)
            else:
                pending_choices.append(choice_with_current_status(character, feature_entry))
    spellbook_choice = wizard_spellbook_choice(character, class_data, target_level, data.get("spells", []))
    if spellbook_choice:
        pending_choices.append(choice_with_current_status(character, spellbook_choice))
    pending_choices.extend(
        choice_with_current_status(character, choice)
        for choice in spell_level_up_choices(character, class_data, current_level, target_level, data.get("spells", []))
    )
    weapon_mastery_choice = weapon_mastery_level_up_choice(character, class_data, current_level, target_level, data.get("weapons", []))
    if weapon_mastery_choice:
        pending_choices.append(choice_with_current_status(character, weapon_mastery_choice))
    pending_choices.extend(
        choice_with_current_status(character, choice)
        for choice in class_level_up_option_choices(character, class_data, current_level, target_level, data)
    )
    if character.get("subclass"):
        subclass_draft = {
            "current_level": current_level,
            "target_level": target_level,
        }
        pending_choices.extend(
            choice_with_current_status(character, choice)
            for choice in subclass_level_up_choices(
                character,
                subclass_draft,
                class_data,
                character.get("subclass", ""),
                data,
                include_spellcasting=False,
            )
        )
    pending_choices.extend(
        choice_with_current_status(character, choice)
        for choice in feat_level_up_choices(character, current_level, target_level, data)
    )

    return {
        "transaction_id": new_transaction_id(),
        "character_id": character.get("character_id", ""),
        "source_state_hash": level_up_source_state_hash(character),
        "current_level": current_level,
        "target_level": target_level,
        "class_name": class_name,
        "status": "draft",
        "hit_die": hit_die,
        "hp_base_gain": hp_base_gain,
        "hp_increase": hp_increase,
        "proficiency_bonus_before": proficiency_bonus_for_level(current_level),
        "proficiency_bonus_after": proficiency_bonus_for_level(target_level),
        "automatic_features": automatic_features,
        "pending_choices": pending_choices,
        "resolved_choices": [
            choice
            for choice in pending_choices
            if choice.get("status") == "resolved"
        ],
        "can_finalize": all(choice.get("status") == "resolved" for choice in pending_choices),
        "blocked_reason": "",
    }


def finalize_level_up(character, plan, data=None):
    validation = validate_level_up_plan(character, plan, data)
    if not validation["ok"]:
        return validation

    transaction_id = plan["transaction_id"]
    resolved_choices = [
        choice
        for choice in plan.get("pending_choices", [])
        if choice.get("status") == "resolved"
    ]
    apply_resolved_choices(character, resolved_choices, transaction_id)

    target_level = plan["target_level"]
    class_name = plan["class_name"]
    character["level"] = target_level
    character["_pending_current_hp_increase"] = plan.get("hp_increase", 0)
    character.setdefault("class_levels", {})[class_name] = target_level
    character.setdefault("hit_dice", {})[class_name] = target_level
    character.setdefault("hp_rolls", []).append({
        "class": class_name,
        "level": target_level,
        "mode": "fixed",
        "value": plan.get("hp_increase", 0),
    })
    character.setdefault("hp_history", []).append({
        "character_level": target_level,
        "class_name": class_name,
        "method": "fixed",
        "base_gain": plan.get("hp_base_gain", 0),
    })
    character.setdefault("level_history", []).append({
        "class": class_name,
        "from_level": plan["current_level"],
        "to_level": target_level,
        "transaction_id": transaction_id,
        "hp_increase": plan.get("hp_increase", 0),
        "automatic_features": [feature["name"] for feature in plan.get("automatic_features", [])],
        "resolved_choices": compact_resolved_choices(resolved_choices),
    })
    character.setdefault("completed_level_up_transactions", []).append(transaction_id)
    resolved_ids = {choice.get("id") for choice in resolved_choices}
    character["pending_choices"] = [
        choice
        for choice in character.get("pending_choices", [])
        if choice.get("id") not in resolved_ids
    ]
    plan["status"] = "completed"
    return {
        "ok": True,
        "status": "completed",
        "transaction_id": transaction_id,
        "message": f"Applied level {target_level}.",
    }


def validate_level_up_plan(character, plan, data=None):
    if plan.get("blocked_reason"):
        return failed_level_up(plan, plan["blocked_reason"])
    transaction_id = plan.get("transaction_id")
    if not transaction_id:
        return failed_level_up(plan, "Level-up plan is missing a transaction ID.")
    if transaction_id in character.get("completed_level_up_transactions", []):
        return failed_level_up(plan, "This level-up transaction has already been completed.")

    current_level = normalize_level(character.get("level", 1))
    plan_current = normalize_level(plan.get("current_level", current_level))
    target_level = normalize_level(plan.get("target_level", current_level))
    if current_level != plan_current:
        return failed_level_up(plan, "This level-up plan is stale. Start a new level-up draft.")
    if target_level != current_level + 1:
        return failed_level_up(plan, "Only one level at a time can be finalized.")
    if character.get("class", "") != plan.get("class_name", ""):
        return failed_level_up(plan, "This level-up plan is for a different class.")
    if plan.get("character_id") and character.get("character_id") != plan.get("character_id"):
        return failed_level_up(plan, "This level-up draft belongs to a different character. Start a new level-up draft.")
    if plan.get("source_state_hash") and level_up_source_state_hash(character) != plan.get("source_state_hash"):
        return failed_level_up(plan, "This level-up draft is stale because the character changed. Start a new level-up draft.")
    if not plan.get("automatic_features") and not plan.get("pending_choices"):
        return failed_level_up(plan, "No progression data exists for the target level.")

    unresolved_choices = [
        choice
        for choice in plan.get("pending_choices", [])
        if choice.get("status") != "resolved"
    ]
    if unresolved_choices:
        return failed_level_up(plan, "Resolve all required choices before finalizing.")
    invalid_choices = []
    for choice in plan.get("pending_choices", []):
        if choice.get("status") != "resolved":
            continue
        if not choice_value_is_valid(choice, choice.get("value")):
            invalid_choices.append(choice)
            continue
        if not resolved_choice_is_valid_for_character(character, plan, choice, data):
            invalid_choices.append(choice)
    if invalid_choices:
        return failed_level_up(plan, "One or more resolved choices are no longer valid. Start a new level-up draft.")
    if duplicate_spellbook_addition_choices(plan):
        return failed_level_up(plan, "Choose different Wizard spellbook additions before finalizing.")

    return {"ok": True, "status": "ready", "message": ""}


def resolved_choice_is_valid_for_character(character, plan, choice, data=None):
    if choice.get("type") not in {"asi_or_feat", "feat_selection"}:
        return True
    value = choice.get("value", {})
    if choice.get("type") == "asi_or_feat" and value.get("mode") == "asi":
        return validate_asi_selection(character, value).get("ok", False)
    if value.get("mode") != "feat":
        return False
    if not data:
        return True
    class_data = data.get("classes_by_name", {}).get(plan.get("class_name", ""), {})
    eligibility_character = deepcopy(character)
    eligibility_character["level"] = normalize_level(plan.get("target_level", character.get("level", 1)))
    return validate_feat_selection(
        eligibility_character,
        class_data,
        data.get("feats", []),
        value.get("feat_id", ""),
        value.get("feat_ability_choice", ""),
        value.get("feat_choices", {}),
        data,
    ).get("ok", False)


def failed_level_up(plan, message):
    if isinstance(plan, dict):
        plan["status"] = "failed"
        plan["failure_reason"] = message
    return {
        "ok": False,
        "status": "failed",
        "transaction_id": plan.get("transaction_id", "") if isinstance(plan, dict) else "",
        "message": message,
    }


def create_level_up_draft(character, target_level, data):
    draft = get_level_up_plan(character, target_level, data)
    draft["status"] = "blocked" if draft.get("blocked_reason") else "draft"
    draft["resolved_choices"] = [
        choice
        for choice in draft.get("pending_choices", [])
        if choice.get("status") == "resolved"
    ]
    return draft


def update_level_up_draft_status(draft):
    draft["resolved_choices"] = [
        choice
        for choice in draft.get("pending_choices", [])
        if choice.get("status") == "resolved"
    ]
    draft["can_finalize"] = all(
        choice.get("status") == "resolved"
        for choice in draft.get("pending_choices", [])
    )
    if draft.get("blocked_reason"):
        draft["status"] = "blocked"
    elif draft["can_finalize"]:
        draft["status"] = "ready"
    else:
        draft["status"] = "draft"
    return draft


def refresh_level_up_draft_choices(character, draft, data):
    if not isinstance(draft, dict) or draft.get("blocked_reason"):
        return draft
    class_data = data.get("classes_by_name", {}).get(draft.get("class_name", ""), {})
    if not class_data:
        return update_level_up_draft_status(draft)

    clear_duplicate_spellbook_addition_choices(draft)
    subclass_name = selected_subclass_from_draft(character, draft)
    draft_character = draft_character_with_resolved_class_options(character, draft)
    if subclass_name:
        draft_character["subclass"] = subclass_name
    draft["pending_choices"] = [
        choice
        for choice in draft.get("pending_choices", [])
        if not stale_dependent_choice(choice, draft_character)
    ]
    if subclass_name:
        draft["pending_choices"] = merge_pending_choices(
            draft.get("pending_choices", []),
            subclass_level_up_choices(draft_character, draft, class_data, subclass_name, data),
        )
    draft["pending_choices"] = merge_pending_choices(
        draft.get("pending_choices", []),
        class_level_up_option_choices(
            draft_character,
            class_data,
            draft.get("current_level", character.get("level", 1)),
            draft.get("target_level", character.get("level", 1)),
            data,
        ),
    )
    draft["pending_choices"] = refresh_spellbook_dependent_choices(
        draft.get("pending_choices", []),
        draft_character,
        class_data,
        draft.get("target_level", character.get("level", 1)),
        data,
    )
    return update_level_up_draft_status(draft)


def commit_level_up_draft(character, draft, data=None):
    if data is not None:
        refresh_level_up_draft_choices(character, draft, data)
    update_level_up_draft_status(draft)
    return finalize_level_up(character, draft, data)


def cancel_level_up_draft():
    return None


def merge_pending_choices(existing, new_choices):
    merged = list(existing or [])
    existing_ids = {choice.get("id"): index for index, choice in enumerate(merged)}
    for choice in new_choices:
        choice_id = choice.get("id")
        if choice_id in existing_ids:
            current = merged[existing_ids[choice_id]]
            merged[existing_ids[choice_id]] = choice_with_refreshed_options(current, choice)
        else:
            merged.append(choice)
    return merged


def choice_with_refreshed_options(current, refreshed):
    if "value" in current and choice_value_is_valid(refreshed, current.get("value")):
        return {
            **refreshed,
            "status": "resolved",
            "value": current.get("value"),
        }
    if "value" in current and partial_choice_value_is_available(refreshed, current.get("value")):
        return {
            **refreshed,
            "status": "unresolved",
            "value": current.get("value"),
        }
    return {**refreshed, "status": "unresolved"}


def refresh_spellbook_dependent_choices(pending_choices, character, class_data, target_level, data):
    refreshed_choices = []
    for choice in pending_choices or []:
        if choice.get("type") not in {"spell_mastery_selection", "signature_spells_selection"}:
            refreshed_choices.append(choice)
            continue
        refreshed = enrich_level_choice(choice, character, class_data, target_level, data)
        refreshed_choices.append(choice_with_refreshed_options(choice, refreshed))
    return refreshed_choices


def spellbook_addition_values(choice):
    if choice.get("type") == "spellbook_spells":
        value = choice.get("value", [])
    elif (
        choice.get("type") == "class_option_selection"
        and is_savant_spell_choice_key(choice.get("class_option_key", ""))
    ):
        value = choice.get("value", [])
    else:
        return []
    return value if isinstance(value, list) else [value]


def duplicate_spellbook_addition_choices(plan):
    seen = set()
    duplicates = []
    for choice in plan.get("pending_choices", []) or []:
        if choice.get("status") != "resolved":
            continue
        for spell_name in spellbook_addition_values(choice):
            if spell_name in seen:
                duplicates.append(choice)
                break
            seen.add(spell_name)
    return duplicates


def clear_duplicate_spellbook_addition_choices(draft):
    seen = set()
    for choice in draft.get("pending_choices", []) or []:
        if choice.get("status") != "resolved":
            continue
        duplicate = False
        for spell_name in spellbook_addition_values(choice):
            if spell_name in seen:
                duplicate = True
                break
        if duplicate:
            choice["status"] = "unresolved"
            choice.pop("value", None)
            continue
        seen.update(spellbook_addition_values(choice))


def choice_with_current_status(character, choice):
    existing = next(
        (
            pending_choice
            for pending_choice in character.get("pending_choices", [])
            if pending_choice.get("id") == choice.get("id")
        ),
        None,
    )
    if existing and existing.get("status") == "resolved":
        return {**choice, **existing}

    if choice.get("type") == "subclass_choice":
        subclass = character.get("subclass", "")
        if subclass and choice_value_is_valid(choice, subclass):
            return {**choice, "status": "resolved", "value": subclass}

    return {**choice, "status": "unresolved"}


def resolve_pending_choice(character, choice_id, value, choice_template=None):
    pending_choices = character.setdefault("pending_choices", [])
    choice = next((item for item in pending_choices if item.get("id") == choice_id), None)
    if choice is None and choice_template:
        choice = {**choice_template, "status": "unresolved"}
        pending_choices.append(choice)
    if choice is None:
        return False
    if not choice_value_is_valid(choice, value):
        choice["value"] = value
        choice["status"] = "unresolved"
        if isinstance(character, dict) and "resolved_choices" in character:
            update_level_up_draft_status(character)
        return False

    choice["value"] = value
    choice["status"] = "resolved"
    if isinstance(character, dict) and "resolved_choices" in character:
        update_level_up_draft_status(character)
    return True


def choice_value_is_valid(choice, value):
    options = choice_option_labels(choice)
    if choice.get("type") == "asi_or_feat":
        return asi_or_feat_value_is_valid(choice, value)
    if choice.get("type") == "feat_selection":
        return feat_selection_value_is_valid(choice, value)
    if choice.get("type") == "spell_mastery_selection":
        return spell_mastery_value_is_valid(choice, value)
    if choice.get("type") == "signature_spells_selection":
        return list_choice_value_is_valid(choice, value)
    if choice.get("type") == "spellbook_spells":
        return (
            isinstance(value, list)
            and len(value) == int(choice.get("choose", 0) or 0)
            and all(item in options for item in value)
            and len(set(value)) == len(value)
        )
    if choice.get("type") in {"spell_selection", "weapon_mastery_selection"}:
        return list_choice_value_is_valid(choice, value)
    if choice.get("type") == "feat_spell_selection":
        return list_choice_value_is_valid(choice, value)
    if choice.get("type") == "class_option_selection":
        return list_choice_value_is_valid(choice, value)
    if choice.get("type") == "class_option_single":
        return value in options
    return not options or value in options


def partial_choice_value_is_available(choice, value):
    options = choice_option_labels(choice)
    if choice.get("type") in {
        "spell_selection",
        "weapon_mastery_selection",
        "spellbook_spells",
        "feat_spell_selection",
        "signature_spells_selection",
        "class_option_selection",
    }:
        if not isinstance(value, list):
            return False
        limit = int(choice.get("choose", 0) or 0)
        return (
            len(value) <= limit
            and len(set(value)) == len(value)
            and all(item in options for item in value)
        )
    return False


def choice_option_labels(choice):
    labels = []
    for option in choice.get("options", []):
        if isinstance(option, dict):
            label = option.get("name") or option.get("label") or option.get("value")
        else:
            label = option
        if label:
            labels.append(label)
    return labels


def apply_resolved_choices(character, choices, transaction_id=""):
    for choice in choices:
        if choice.get("type") == "subclass_choice":
            character["subclass"] = choice.get("value", "")
        if choice.get("type") == "spellbook_spells":
            spells = character.setdefault("spells", {})
            spells["spellbook"] = merge_unique(spells.get("spellbook", []), choice.get("value", []))
            if character.get("class") == "Wizard":
                spells["known"] = []
        if choice.get("type") == "spell_selection":
            spells = character.setdefault("spells", {})
            field = choice.get("spell_field", "")
            if field:
                spells[field] = merge_unique(spells.get(field, []), choice.get("value", []))
        if choice.get("type") == "weapon_mastery_selection":
            character["weapon_masteries"] = merge_unique(character.get("weapon_masteries", []), choice.get("value", []))
        if choice.get("type") == "feat_spell_selection":
            apply_feat_spell_selection(character, choice)
        if choice.get("type") in {"class_option_selection", "class_option_single"}:
            apply_class_option_choice(character, choice)
        if choice.get("type") == "asi_or_feat":
            apply_asi_or_feat_choice(character, choice, transaction_id)
        if choice.get("type") == "feat_selection":
            apply_feat_selection_choice(character, choice, transaction_id)
        if choice.get("type") == "spell_mastery_selection":
            apply_spell_mastery_choice(character, choice)
        if choice.get("type") == "signature_spells_selection":
            apply_signature_spells_choice(character, choice)


def compact_resolved_choices(choices):
    return [
        {
            "choice_id": choice.get("id", ""),
            "type": choice.get("type", ""),
            "name": choice.get("name", ""),
            "value": compact_choice_value(choice.get("value")),
        }
        for choice in choices or []
    ]


def compact_choice_value(value):
    if isinstance(value, dict):
        compacted = {}
        for key, item in value.items():
            if key not in {
                "mode",
                "ability_increases",
                "feat_id",
                "feat_name",
                "feat_ability_choice",
                "feat_choices",
                "level_1",
                "level_2",
            }:
                continue
            if item in ({}, [], ""):
                continue
            if key == "feat_choices" and isinstance(item, dict):
                compacted[key] = {
                    choice_key: choice_value
                    for choice_key, choice_value in item.items()
                    if choice_value not in ({}, [], "")
                }
            else:
                compacted[key] = compact_choice_value(item)
        return compacted
    if isinstance(value, list):
        return list(value)
    return value


def empty_plan(current_level, target_level, class_name, reason):
    return {
        "transaction_id": new_transaction_id(),
        "character_id": "",
        "source_state_hash": "",
        "current_level": current_level,
        "target_level": target_level,
        "class_name": class_name,
        "status": "blocked",
        "hit_die": 0,
        "hp_base_gain": 0,
        "hp_increase": 0,
        "proficiency_bonus_before": proficiency_bonus_for_level(current_level),
        "proficiency_bonus_after": proficiency_bonus_for_level(target_level),
        "automatic_features": [],
        "pending_choices": [],
        "resolved_choices": [],
        "can_finalize": False,
        "blocked_reason": reason,
    }


def active_origin_feats(character):
    feats = []
    for source in (
        character.get("origin_feats", []),
        character.get("background_options", {}).get("origin_feats", []),
        character.get("species_options", {}).get("origin_feats", []),
    ):
        for feat in source or []:
            if feat and feat not in feats:
                feats.append(feat)
    return feats


def enrich_level_choice(choice, character, class_data, target_level, data):
    if choice.get("type") == "spell_mastery_selection":
        return {
            **choice,
            "level_1_options": spell_mastery_options(character, data.get("spells", []), 1),
            "level_2_options": spell_mastery_options(character, data.get("spells", []), 2),
            "spells": list(data.get("spells", [])),
        }
    if choice.get("type") == "signature_spells_selection":
        return {
            **choice,
            "options": signature_spell_options(character, data.get("spells", [])),
            "spells": list(data.get("spells", [])),
        }
    if choice.get("type") not in {"asi_or_feat", "feat_selection"}:
        return choice
    eligibility_character = deepcopy(character)
    eligibility_character["level"] = target_level
    feat_categories = set(choice.get("feat_categories", []))
    allowed_categories = set(choice.get("allowed_categories", []))
    eligible = eligible_feats(data.get("feats", []), eligibility_character, class_data)
    feat_candidates = feat_browser_options(
        data.get("feats", []),
        eligibility_character,
        class_data,
        data,
        allowed_categories=allowed_categories,
        feat_categories=feat_categories,
    )
    if allowed_categories:
        eligible = [
            feat
            for feat in eligible
            if feat.get("category") in allowed_categories
        ]
    elif feat_categories:
        eligible = [
            feat
            for feat in eligible
            if feat.get("category") in feat_categories
        ]
    return {
        **choice,
        "name": "Ability Score Improvement or general feat" if choice.get("type") == "asi_or_feat" else choice.get("name", "Feat"),
        "ability_scores": dict(character.get("ability_scores", {})),
        "skill_proficiencies": list(character.get("skill_proficiencies", [])),
        "expertise": list(character.get("expertise", [])),
        "saving_throw_proficiencies": list(character.get("saving_throw_proficiencies", [])),
        "weapon_proficiencies": list(character.get("weapon_proficiencies", [])),
        "weapon_masteries": list(character.get("weapon_masteries", [])),
        "general_feats": list(character.get("general_feats", [])),
        "weapons": list(data.get("weapons", [])),
        "rules": dict(data.get("rules", {})),
        "spells": list(data.get("spells", [])),
        "recommended_categories": list(choice.get("recommended_categories", [])),
        "allowed_categories": list(choice.get("allowed_categories", [])),
        "feat_candidates": feat_candidates,
        "asi_options": [
            {
                "mode": "single",
                "label": "+2 to one ability",
                "amounts": [2],
            },
            {
                "mode": "split",
                "label": "+1 to two abilities",
                "amounts": [1, 1],
            },
        ],
        "feat_options": supported_feat_options(eligible, eligibility_character, data),
    }


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


def signature_spell_options(character, spells):
    spellbook = set(wizard_spellbook_spells(character))
    return [
        spell["name"]
        for spell in spells or []
        if spell.get("name") in spellbook
        and "Wizard" in spell.get("classes", [])
        and spell.get("level") == 3
    ]


def supported_feat_options(feats, character=None, data=None):
    return [
        {
            "id": feat.get("id", ""),
            "name": feat.get("name", ""),
            "category": feat.get("category", ""),
            "ability_increase": feat_ability_increase_for_character(feat, character),
            "description": feat.get("description", ""),
            "choice_schema": feat_choice_schema(feat, character, data),
            "unsupported_choices": feat.get("unsupported_choices", []),
            "repeatable": feat.get("repeatable", False),
            "support": feat_support_status(feat),
        }
        for feat in feats
        if feat.get("name") != "Ability Score Improvement"
        and feat_is_supported_for_selection(feat)
    ]


def feat_browser_options(feats, character, class_data, data, *, allowed_categories=None, feat_categories=None):
    allowed_categories = set(allowed_categories or [])
    feat_categories = set(feat_categories or [])
    options = []
    for feat in feats or []:
        if feat.get("name") == "Ability Score Improvement":
            continue
        if allowed_categories and feat.get("category") not in allowed_categories:
            continue
        if not allowed_categories and feat_categories and feat.get("category") not in feat_categories:
            continue
        eligible = feat_is_eligible(feat, character, class_data)
        supported = feat_is_supported_for_selection(feat)
        reasons = []
        if not eligible:
            reasons.append("This character does not meet this feat's prerequisites.")
        if not supported:
            reasons.append("This feat is not fully supported yet.")
        options.append({
            "id": feat.get("id", ""),
            "name": feat.get("name", ""),
            "category": feat.get("category", ""),
            "ability_increase": feat_ability_increase_for_character(feat, character),
            "description": feat.get("description", ""),
            "choice_schema": feat_choice_schema(feat, character, data) if eligible and supported else [],
            "unsupported_choices": feat.get("unsupported_choices", []),
            "repeatable": feat.get("repeatable", False),
            "support": feat_support_status(feat),
            "eligible": eligible,
            "supported": supported,
            "eligibility_reasons": reasons,
            "source": feat.get("source", ""),
            "raw_ref": feat.get("raw_ref", ""),
        })
    return options


def asi_or_feat_value_is_valid(choice, value):
    if not isinstance(value, dict):
        return False
    if value.get("mode") == "asi":
        return validate_asi_selection(
            {"ability_scores": choice.get("ability_scores", {})},
            value,
        )["ok"]
    if value.get("mode") != "feat":
        return False
    feat = selected_feat_option(choice, value.get("feat_id", ""))
    if not feat:
        return False
    adjustment = ability_adjustment_from_feat(feat, value.get("feat_ability_choice", ""))
    if adjustment.get("error"):
        return False
    choice_character = {
        "skill_proficiencies": choice.get("skill_proficiencies", []),
        "expertise": choice.get("expertise", []),
        "saving_throw_proficiencies": choice.get("saving_throw_proficiencies", []),
        "weapon_proficiencies": choice.get("weapon_proficiencies", []),
        "weapon_masteries": choice.get("weapon_masteries", []),
        "general_feats": choice.get("general_feats", []),
    }
    choice_data = {
        "weapons": choice.get("weapons", []),
        "rules": choice.get("rules", {}),
        "spells": choice.get("spells", []),
    }
    return (
        feat_ability_choice_is_valid(feat, choice_character, value.get("feat_ability_choice", ""))
        and feat_extra_choices_are_valid(feat, choice_character, value.get("feat_choices", {}), choice_data)
    )


def feat_selection_value_is_valid(choice, value):
    if not isinstance(value, dict) or value.get("mode") != "feat":
        return False
    feat = selected_feat_option(choice, value.get("feat_id", ""))
    if not feat:
        return False
    adjustment = ability_adjustment_from_feat(feat, value.get("feat_ability_choice", ""))
    if adjustment.get("error"):
        return False
    choice_character = {
        "skill_proficiencies": choice.get("skill_proficiencies", []),
        "expertise": choice.get("expertise", []),
        "saving_throw_proficiencies": choice.get("saving_throw_proficiencies", []),
        "weapon_proficiencies": choice.get("weapon_proficiencies", []),
        "weapon_masteries": choice.get("weapon_masteries", []),
        "general_feats": choice.get("general_feats", []),
    }
    choice_data = {
        "weapons": choice.get("weapons", []),
        "rules": choice.get("rules", {}),
        "spells": choice.get("spells", []),
    }
    return (
        feat_ability_choice_is_valid(feat, choice_character, value.get("feat_ability_choice", ""))
        and feat_extra_choices_are_valid(feat, choice_character, value.get("feat_choices", {}), choice_data)
    )


def spell_mastery_value_is_valid(choice, value):
    if not isinstance(value, dict):
        return False
    level_1 = value.get("level_1", "")
    level_2 = value.get("level_2", "")
    return (
        level_1 in set(choice.get("level_1_options", []))
        and level_2 in set(choice.get("level_2_options", []))
    )


def selected_feat_option(choice, feat_id):
    return next(
        (
            feat
            for feat in choice.get("feat_options", [])
            if feat.get("id") == feat_id
        ),
        {},
    )


def feat_ability_increase_for_character(feat, character=None):
    ability_increase = dict(feat.get("ability_increase", {}))
    if feat.get("name") == "Resilient" and ability_increase.get("mode") == "choose":
        known_saves = set((character or {}).get("saving_throw_proficiencies", []))
        ability_increase["from"] = [
            ability
            for ability in ability_increase.get("from", [])
            if ability not in known_saves
        ]
    return ability_increase


def apply_asi_or_feat_choice(character, choice, transaction_id=""):
    value = choice.get("value", {})
    if value.get("mode") == "asi":
        append_ability_adjustment(character, ability_adjustment_from_asi(choice, value))
    if value.get("mode") == "feat":
        feat = selected_feat_option(choice, value.get("feat_id", ""))
        if feat.get("name"):
            feat_instance = build_feat_instance(feat, choice, value, transaction_id)
            character["general_feats"] = append_feat_instance(character.get("general_feats", []), feat_instance)
            apply_feat_instance_grants(character, feat_instance)
        adjustment = ability_adjustment_from_feat(feat, value.get("feat_ability_choice", ""))
        if adjustment and not adjustment.get("error"):
            if feat.get("name"):
                adjustment["feat_instance_id"] = feat_instance["instance_id"]
                adjustment["source"] = feat_instance["source"]
            append_ability_adjustment(character, adjustment)


def apply_feat_selection_choice(character, choice, transaction_id=""):
    value = choice.get("value", {})
    feat = selected_feat_option(choice, value.get("feat_id", ""))
    if not feat.get("name"):
        return
    feat_instance = build_feat_instance(feat, choice, value, transaction_id)
    character["general_feats"] = append_feat_instance(character.get("general_feats", []), feat_instance)
    apply_feat_instance_grants(character, feat_instance)
    adjustment = ability_adjustment_from_feat(feat, value.get("feat_ability_choice", ""))
    if adjustment and not adjustment.get("error"):
        adjustment["feat_instance_id"] = feat_instance["instance_id"]
        adjustment["source"] = feat_instance["source"]
        append_ability_adjustment(character, adjustment)


def apply_spell_mastery_choice(character, choice):
    value = choice.get("value", {})
    if not spell_mastery_value_is_valid(choice, value):
        return
    class_options = character.setdefault("class_options", {})
    class_options["spell_mastery_level_1"] = value.get("level_1", "")
    class_options["spell_mastery_level_2"] = value.get("level_2", "")


def apply_signature_spells_choice(character, choice):
    value = choice.get("value", [])
    if not list_choice_value_is_valid(choice, value):
        return
    character.setdefault("class_options", {})["signature_spells"] = list(value)


def append_ability_adjustment(character, adjustment):
    if not adjustment.get("adjustments"):
        return
    character.setdefault("ability_score_adjustments", []).append(adjustment)


def build_feat_instance(feat, choice, value, transaction_id=""):
    raw_source = choice.get("source", {}) or {}
    source = dict(raw_source) if isinstance(raw_source, dict) else {
        "type": "class_level",
        "class_name": str(raw_source),
        "level": choice.get("level", 0),
    }
    if transaction_id:
        source["transaction_id"] = transaction_id
    choices = {}
    if value.get("feat_ability_choice"):
        choices["ability"] = value.get("feat_ability_choice")
    if isinstance(value.get("feat_choices"), dict):
        choices.update({
            key: selected
            for key, selected in value.get("feat_choices", {}).items()
            if selected
        })
    return {
        "instance_id": uuid4().hex,
        "feat_id": feat.get("id", ""),
        "name": feat.get("name", ""),
        "repeatable": feat.get("repeatable", False),
        "source": source or {"type": "class_level"},
        "choices": choices,
    }


def append_feat_instance(existing, feat_instance):
    feats = list(existing or [])
    if not feat_instance:
        return feats
    if not any(
        isinstance(entry, dict)
        and entry.get("feat_id") == feat_instance.get("feat_id")
        and not feat_instance.get("repeatable")
        for entry in feats
    ):
        feats.append(feat_instance)
    return feats


def apply_feat_instance_grants(character, feat_instance):
    choices = feat_instance.get("choices", {})
    if feat_instance.get("name") == "Weapon Master" and choices.get("weapon_mastery"):
        character["weapon_masteries"] = merge_unique(
            character.get("weapon_masteries", []),
            [choices["weapon_mastery"]],
        )


def apply_feat_spell_selection(character, choice):
    feat_instance_id = choice.get("feat_instance_id", "")
    choice_key = choice.get("feat_choice_key", "spells")
    for feat in character.get("general_feats", []) or []:
        if not isinstance(feat, dict) or feat.get("instance_id") != feat_instance_id:
            continue
        choices = feat.setdefault("choices", {})
        choices[choice_key] = merge_unique(choices.get(choice_key, []), choice.get("value", []))
        return


def selected_subclass_from_draft(character, draft):
    for choice in draft.get("pending_choices", []):
        if choice.get("type") == "subclass_choice" and choice.get("status") == "resolved":
            return choice.get("value", "")
    return character.get("subclass", "")


def draft_character_with_resolved_class_options(character, draft):
    draft_character = deepcopy(character)
    class_options = dict(draft_character.get("class_options", {}))
    spells = dict(draft_character.get("spells", {}))
    for choice in draft.get("pending_choices", []):
        if choice.get("status") != "resolved":
            continue
        if choice.get("type") == "subclass_choice":
            draft_character["subclass"] = choice.get("value", "")
        if choice.get("type") == "spellbook_spells":
            spells["spellbook"] = merge_unique(spells.get("spellbook", []), choice.get("value", []))
            if draft_character.get("class") == "Wizard":
                spells["known"] = []
        if choice.get("type") not in {"class_option_selection", "class_option_single"}:
            continue
        key = choice.get("class_option_key", "")
        if not key:
            continue
        if choice.get("type") == "class_option_selection":
            class_options[key] = merge_unique(class_options.get(key, []), choice.get("value", []))
        else:
            class_options[key] = choice.get("value", "")
    draft_character["class_options"] = class_options
    draft_character["spells"] = spells
    return draft_character


def stale_dependent_choice(choice, draft_character):
    depends_on = choice.get("depends_on", {})
    if depends_on.get("type") == "subclass_choice":
        return depends_on.get("value") != draft_character.get("subclass", "")
    if depends_on.get("type") == "class_option":
        return (
            draft_character.get("class_options", {}).get(depends_on.get("key", ""))
            != depends_on.get("value")
        )
    return False


def subclass_level_up_choices(character, draft, class_data, subclass_name, data, include_spellcasting=True):
    subclass_options = selected_subclass_options(class_data, subclass_name)
    if not subclass_options:
        subclass_options = {}

    choices = []
    target_level = draft.get("target_level", character.get("level", 1))
    current_level = draft.get("current_level", character.get("level", 1))
    source = {
        "type": "subclass_choice",
        "value": subclass_name,
    }
    if include_spellcasting:
        choices.extend(
            spell_level_up_choices(
                character,
                class_data,
                current_level,
                target_level,
                data.get("spells", []),
                subclass_name=subclass_name,
                depends_on=source,
            )
        )
    savant_rule = savant_spell_choice_rule(subclass_options, subclass_name, 3) or subclass_options.get("savant_spells", {})
    if savant_rule:
        blocked = set(wizard_spellbook_spells(character)) | set(selected_savant_spells(character))
        options = [
            spell
            for spell in filtered_spell_options(data.get("spells", []), savant_rule.get("from", {}))
            if spell not in blocked
        ]
        choices.extend(class_option_selection_choice(
            character,
            key="savant_spells",
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_savant_spells",
            name=savant_rule.get("label", f"Choose {savant_rule.get('choose', 0)} subclass spells"),
            choose=savant_rule.get("choose", 0),
            options=options,
            depends_on=source,
        ))
    later_savant_rule = savant_spell_choice_rule(subclass_options, subclass_name, target_level)
    if later_savant_rule and target_level != 3:
        blocked = set(wizard_spellbook_spells(character)) | set(selected_savant_spells(character))
        options = [
            spell
            for spell in filtered_spell_options(data.get("spells", []), later_savant_rule.get("from", {}))
            if spell not in blocked
        ]
        choices.extend(class_option_selection_choice(
            character,
            key=savant_spell_choice_key(target_level),
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_savant_spell",
            name=later_savant_rule.get("label", f"Choose {subclass_name} Savant spell"),
            choose=later_savant_rule.get("choose", 0),
            options=options,
            depends_on=source,
        ))

    if subclass_options.get("maneuvers"):
        rule = subclass_options["maneuvers"]
        maneuver_total = rule.get("choose", 0)
        if class_data.get("name") == "Fighter" and subclass_name == "Battle Master":
            maneuver_total = battle_master_maneuver_total(target_level)
        choices.extend(class_option_selection_choice(
            character,
            key="maneuvers",
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_maneuvers",
            name=f"Choose {maneuver_total} total Battle Master maneuvers",
            choose=maneuver_total,
            options=rule.get("from", []),
            depends_on=source,
        ))
    if subclass_options.get("maneuver_save_ability"):
        choices.append(class_option_single_choice(
            key="battle_master_save_ability",
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_maneuver_save_ability",
            name="Maneuver save ability",
            options=subclass_options.get("maneuver_save_ability", []),
            depends_on=source,
        ))
    if subclass_options.get("student_of_war_skill"):
        skill_options = available_class_skill_options(
            class_data,
            character.get("skill_proficiencies", []),
        )
        choices.append(class_option_single_choice(
            key="student_of_war_skill",
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_student_of_war_skill",
            name="Student of War skill",
            options=skill_options,
            depends_on=source,
        ))
    if subclass_options.get("student_of_war_tool"):
        choices.append(class_option_single_choice(
            key="student_of_war_tool",
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_student_of_war_tool",
            name="Student of War artisan tool",
            options=subclass_options.get("student_of_war_tool", {}).get("from", []),
            depends_on=source,
        ))
    if subclass_options.get("lore_skills"):
        rule = subclass_options["lore_skills"]
        choices.extend(class_option_selection_choice(
            character,
            key="lore_skills",
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_lore_skills",
            name=f"Choose {rule.get('choose', 0)} College of Lore skills",
            choose=rule.get("choose", 0),
            options=rule.get("from", []),
            depends_on=source,
        ))
    if subclass_options.get("hunters_prey"):
        choices.append(class_option_single_choice(
            key="hunters_prey",
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_hunters_prey",
            name="Hunter's Prey",
            options=subclass_options.get("hunters_prey", {}).get("from", []),
            depends_on=source,
        ))
    if subclass_options.get("primal_companion"):
        choices.append(class_option_single_choice(
            key="primal_companion",
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_primal_companion",
            name="Primal Companion",
            options=subclass_options.get("primal_companion", {}).get("from", []),
            depends_on=source,
        ))
    if subclass_options.get("structured_spell_choice"):
        rule = subclass_options["structured_spell_choice"]
        choices.append(class_option_single_choice(
            key="structured_spell_choice",
            choice_id=f"{slug(class_data.get('name', 'class'))}_{slug(subclass_name)}_{target_level}_structured_spell_choice",
            name=rule.get("name", "Subclass spell group"),
            options=[option.get("name", "") for option in rule.get("options", []) if option.get("name")],
            depends_on=source,
        ))
    return choices


def class_option_selection_choice(character, key, choice_id, name, choose, options, depends_on):
    selected = character.get("class_options", {}).get(key, [])
    needed = max(0, int(choose or 0) - len(selected))
    if needed <= 0:
        return []
    selected_set = set(selected)
    return [{
        "id": choice_id,
        "type": "class_option_selection",
        "name": name,
        "class_option_key": key,
        "required": True,
        "choose": needed,
        "options": [option for option in options if option not in selected_set],
        "depends_on": depends_on,
        "status": "unresolved",
    }]


def class_option_single_choice(key, choice_id, name, options, depends_on):
    return {
        "id": choice_id,
        "type": "class_option_single",
        "name": name,
        "class_option_key": key,
        "required": True,
        "options": options,
        "depends_on": depends_on,
        "status": "unresolved",
    }


def apply_class_option_choice(character, choice):
    key = choice.get("class_option_key", "")
    if not key:
        return
    class_options = character.setdefault("class_options", {})
    if choice.get("type") == "class_option_selection":
        class_options[key] = merge_unique(class_options.get(key, []), choice.get("value", []))
    else:
        class_options[key] = choice.get("value", "")
    if key.startswith("mystic_arcanum_"):
        spell_level = int(key.rsplit("_", 1)[-1] or 0)
        source_level = mystic_arcanum_source_level_for_spell_level(spell_level)
        values = choice.get("value", [])
        values = values if isinstance(values, list) else [values]
        for spell_name in values:
            upsert_mystic_arcanum_record(character, spell_name, spell_level, source_level)
    if is_savant_spell_choice_key(key):
        values = choice.get("value", [])
        values = values if isinstance(values, list) else [values]
        spells = character.setdefault("spells", {})
        spells["spellbook"] = merge_unique(spells.get("spellbook", []), values)
        spells["known"] = []
        source_level = savant_spell_source_level(key)
        records = character.setdefault("savant_spell_records", [])
        for spell_name in values:
            if not spell_name:
                continue
            if any(record.get("name") == spell_name and record.get("source", {}).get("level") == source_level for record in records):
                continue
            records.append({
                "name": spell_name,
                "source": {
                    "type": "subclass_feature",
                    "subclass_name": character.get("subclass", ""),
                    "feature_name": "Savant",
                    "level": source_level,
                },
            })
    if choice.get("apply_to") == "expertise":
        value = choice.get("value", [])
        values = value if isinstance(value, list) else [value]
        character["expertise"] = merge_unique(character.get("expertise", []), values)


def filtered_spell_options(spells, rule):
    spell_class = rule.get("class", "")
    levels = set(rule.get("levels", []))
    school = rule.get("school", "")
    return [
        spell["name"]
        for spell in spells
        if (not spell_class or spell_class in spell.get("classes", []))
        and (not levels or spell.get("level") in levels)
        and (not school or spell.get("school_code") == school)
    ]


def spell_level_up_choices(character, class_data, current_level, target_level, spells, subclass_name=None, depends_on=None):
    active_subclass = subclass_name if subclass_name is not None else character.get("subclass", "")
    spellcasting = effective_spellcasting(class_data, active_subclass, target_level)
    if not spellcasting:
        return []

    choices = []
    spell_list = spellcasting.get("spell_list", class_data.get("name", ""))
    current_spellcasting = effective_spellcasting(class_data, active_subclass, current_level) or {}
    current_cantrips = current_spellcasting.get("cantrips_known", get_cantrip_limit(class_data, current_level))
    target_cantrips = spellcasting.get("cantrips_known", get_cantrip_limit(class_data, target_level))
    available_levels = available_spell_levels_for_choice(class_data, spellcasting, target_level)
    choices.extend(spell_count_choice(
        character,
        spells,
        choice_id=f"{slug(class_data.get('name', 'class'))}_{target_level}_cantrips",
        name=f"Choose {class_data.get('name', 'class')} cantrip gained at level {target_level}",
        spell_field="cantrips",
        current_limit=current_cantrips,
        target_limit=target_cantrips,
        spell_list=spell_list,
        levels=[0],
        exclude=spellcasting.get("granted_cantrips", []),
        depends_on=depends_on,
    ))
    if class_data.get("name") != "Wizard" and "known_spells" in spellcasting:
        choices.extend(spell_count_choice(
            character,
            spells,
            choice_id=f"{slug(class_data.get('name', 'class'))}_{target_level}_known_spells",
            name=f"Choose {class_data.get('name', 'class')} spell gained at level {target_level}",
            spell_field="known",
            current_limit=current_spellcasting.get("known_spells", get_known_spell_limit(class_data, current_level)),
            target_limit=spellcasting.get("known_spells", get_known_spell_limit(class_data, target_level)),
            spell_list=spell_list,
            levels=available_levels,
            depends_on=depends_on,
        ))
    if class_data.get("name") != "Wizard" and "prepared_spells" in spellcasting:
        prepared_spell_lists = eligible_spell_lists_for_prepared_spells(class_data, target_level, spellcasting)
        choices.extend(spell_count_choice(
            character,
            spells,
            choice_id=f"{slug(class_data.get('name', 'class'))}_{target_level}_prepared_spells",
            name=f"Choose {class_data.get('name', 'class')} prepared spell gained at level {target_level}",
            spell_field="prepared",
            current_limit=current_spellcasting.get("prepared_spells", get_prepared_spell_limit(class_data, current_level)),
            target_limit=spellcasting.get("prepared_spells", get_prepared_spell_limit(class_data, target_level)),
            spell_list=prepared_spell_lists,
            levels=available_levels,
            depends_on=depends_on,
        ))
    return choices


def available_spell_levels_for_choice(class_data, spellcasting, target_level):
    if spellcasting.get("spell_slots"):
        return available_spell_levels_from_slots(
            spellcasting.get("spell_slots", {}),
            spellcasting.get("type", get_casting_type(class_data, target_level)),
        )
    return get_available_spell_levels(class_data, target_level)


def spell_count_choice(character, spells, choice_id, name, spell_field, current_limit, target_limit, spell_list, levels, exclude=None, depends_on=None):
    existing = character.get("spells", {}).get(spell_field, [])
    needed = max(0, int(target_limit or 0) - len(existing))
    if needed <= 0:
        return []
    blocked = set(existing) | set(exclude or [])
    spell_lists = {spell_list} if isinstance(spell_list, str) else set(spell_list or [])
    options = [
        spell["name"]
        for spell in spells
        if spell_lists.intersection(spell.get("classes", []))
        and spell.get("level") in set(levels or [])
        and spell["name"] not in blocked
    ]
    return [{
        "id": choice_id,
        "type": "spell_selection",
        "name": name if needed == 1 else name.replace("spell ", "spells "),
        "spell_field": spell_field,
        "required": True,
        "choose": needed,
        "options": options,
        "depends_on": depends_on or {},
        "status": "unresolved",
    }]


def feat_level_up_choices(character, current_level, target_level, data):
    choices = []
    if proficiency_bonus_for_level(target_level) <= proficiency_bonus_for_level(current_level):
        return choices
    choices.extend(ritual_caster_level_up_choices(character, target_level, data.get("spells", [])))
    return choices


def ritual_caster_level_up_choices(character, target_level, spells):
    target_count = proficiency_bonus_for_level(target_level)
    choices = []
    options = ritual_spell_options(spells)
    for feat in character.get("general_feats", []) or []:
        if not isinstance(feat, dict) or feat.get("name") != "Ritual Caster":
            continue
        selected = feat.get("choices", {}).get("spells", [])
        needed = max(0, target_count - len(selected))
        if needed <= 0:
            continue
        choices.append({
            "id": f"ritual_caster_{target_level}_ritual_spells",
            "type": "feat_spell_selection",
            "name": f"Choose {needed} additional Ritual Caster spell" if needed == 1 else f"Choose {needed} additional Ritual Caster spells",
            "feat_instance_id": feat.get("instance_id", ""),
            "feat_name": feat.get("name", ""),
            "feat_choice_key": "spells",
            "required": True,
            "choose": needed,
            "options": [spell for spell in options if spell not in selected],
            "status": "unresolved",
        })
    return choices


def weapon_mastery_level_up_choice(character, class_data, current_level, target_level, weapons):
    target_count = int(get_class_resources(class_data, target_level).get("weapon_mastery_count", 0) or 0)
    existing = character.get("weapon_masteries", [])
    needed = max(0, target_count - len(existing))
    if needed <= 0:
        return {}
    existing_set = set(existing)
    eligible_names = eligible_weapon_mastery_names(character, weapons)
    return {
        "id": f"{slug(class_data.get('name', 'class'))}_{target_level}_weapon_mastery",
        "type": "weapon_mastery_selection",
        "name": f"Choose {needed} new Weapon Mastery weapon" if needed == 1 else f"Choose {needed} new Weapon Mastery weapons",
        "required": True,
        "choose": needed,
        "options": [
            name
            for name in eligible_names
            if name not in existing_set
        ],
        "status": "unresolved",
    }


def list_choice_value_is_valid(choice, value):
    options = choice_option_labels(choice)
    return (
        isinstance(value, list)
        and len(value) == int(choice.get("choose", 0) or 0)
        and all(item in options for item in value)
        and len(set(value)) == len(value)
    )


def wizard_spellbook_choice(character, class_data, target_level, spells):
    if class_data.get("name") != "Wizard":
        return {}
    added = get_class_progression(class_data, target_level).get("spellbook_spells_added", 0)
    if not added:
        return {}
    available_levels = set(get_available_spell_levels(class_data, target_level))
    existing_spells = set(wizard_spellbook_spells(character))
    options = [
        spell["name"]
        for spell in spells
        if "Wizard" in spell.get("classes", [])
        and spell.get("level") in available_levels
        and spell["name"] not in existing_spells
    ]
    return {
        "id": f"wizard_{target_level}_spellbook_spells",
        "type": "spellbook_spells",
        "name": f"Add {added} Wizard spellbook spells",
        "source": "Wizard",
        "level": target_level,
        "required": True,
        "choose": int(added),
        "options": options,
        "status": "unresolved",
    }


def merge_unique(*lists):
    merged = []
    for items in lists:
        for item in items or []:
            if item and item not in merged:
                merged.append(item)
    return merged


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")


def new_transaction_id():
    return uuid4().hex


def level_up_source_state_hash(character):
    state = {
        "character_id": character.get("character_id", ""),
        "class": character.get("class", ""),
        "subclass": character.get("subclass", ""),
        "level": normalize_level(character.get("level", 1)),
        "species": character.get("species", ""),
        "background": character.get("background", ""),
        "ability_scores": character.get("ability_scores", {}),
        "base_ability_scores": character.get("base_ability_scores", {}),
        "ability_score_adjustments": character.get("ability_score_adjustments", []),
        "general_feats": character.get("general_feats", []),
        "origin_feats": character.get("origin_feats", []),
        "species_options": character.get("species_options", {}),
        "background_options": character.get("background_options", {}),
        "class_options": character.get("class_options", {}),
        "origin_feat_choices": character.get("origin_feat_choices", {}),
        "armor_proficiencies": character.get("armor_proficiencies", []),
        "weapon_proficiencies": character.get("weapon_proficiencies", []),
        "tool_proficiencies": character.get("tool_proficiencies", []),
        "skill_proficiencies": character.get("skill_proficiencies", []),
        "saving_throw_proficiencies": character.get("saving_throw_proficiencies", []),
        "languages": character.get("languages", []),
        "weapon_masteries": character.get("weapon_masteries", []),
        "spells": character.get("spells", {}),
        "spellcasting_ability": character.get("spellcasting_ability", ""),
    }
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
