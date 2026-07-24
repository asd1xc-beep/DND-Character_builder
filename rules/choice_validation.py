from rules.feat_rules import (
    feat_ability_choice_is_valid,
    feat_by_id,
    feat_choice_schema,
    feat_extra_choices_are_valid,
    feat_is_eligible,
    feat_is_supported_for_selection,
    valid_ability_name,
)


def build_asi_or_feat_choice(class_id, class_name, level):
    return {
        "id": f"{slug(class_id or class_name)}_level_{level}_asi_or_feat",
        "type": "asi_or_feat",
        "name": "Ability Score Improvement or general feat",
        "required": True,
        "status": "unresolved",
        "source": {
            "type": "class_level",
            "class_id": class_id,
            "class_name": class_name,
            "level": level,
        },
        "selection": {
            "mode": "",
            "ability_increases": {},
            "feat_id": "",
            "feat_ability_choice": "",
        },
    }


def validate_asi_selection(character, selection, maximum=20):
    increases = selection.get("ability_increases", selection) if isinstance(selection, dict) else {}
    increases = {
        ability: int(amount)
        for ability, amount in (increases or {}).items()
        if int(amount or 0)
    }
    if not increases or any(not valid_ability_name(ability) for ability in increases):
        return failed("Choose valid abilities for the score increase.")
    amounts = sorted(increases.values())
    if amounts not in ([2], [1, 1]):
        return failed("An Ability Score Improvement must be +2 to one ability or +1 to two abilities.")
    scores = character.get("ability_scores", {})
    for ability, amount in increases.items():
        if int(scores.get(ability, 0)) + amount > maximum:
            return failed(f"{ability} cannot be increased above {maximum}.")
    return {"ok": True, "message": ""}


def ability_adjustment_from_asi(choice, selection):
    increases = selection.get("ability_increases", selection)
    source = choice.get("source", {})
    source_class = source.get("class_name", "") if isinstance(source, dict) else source
    source_level = source.get("level", 0) if isinstance(source, dict) else choice.get("level", 0)
    return {
        "type": "ability_score_adjustment",
        "source_type": "class_level",
        "source_class": source_class,
        "source_level": source_level,
        "adjustments": dict(increases or {}),
        "maximum": 20,
    }


def validate_feat_selection(character, class_data, feats, feat_id, ability_choice="", feat_choices=None, data=None):
    feat = feat_by_id(feats, feat_id)
    if not feat:
        return failed("Choose a valid feat.")
    if not feat_is_eligible(feat, character, class_data):
        return failed("This character does not meet that feat's prerequisites.")
    if not feat_is_supported_for_selection(feat):
        return failed("This feat is not fully supported yet.")
    if feat.get("required_choices") and not feat_choice_schema(feat, character, data):
        return failed("This feat needs additional choice UI before it can be finalized.")
    ability_adjustment = ability_adjustment_from_feat(feat, ability_choice)
    if ability_adjustment.get("error"):
        return failed(ability_adjustment["error"])
    if not feat_ability_choice_is_valid(feat, character, ability_choice):
        return failed("Choose an ability that does not already have saving throw proficiency.")
    if not feat_extra_choices_are_valid(feat, character, feat_choices or {}, data):
        return failed("Choose all required options for this feat.")
    return {"ok": True, "message": ""}


def ability_adjustment_from_feat(feat, ability_choice=""):
    ability_increase = feat.get("ability_increase", {})
    if not ability_increase:
        return {}
    if ability_increase.get("mode") == "fixed":
        ability = next(iter(ability_increase.get("from", [])), "")
        return feat_adjustment(feat, {ability: ability_increase.get("amount", 1)})
    if ability_increase.get("mode") == "choose":
        choices = ability_increase.get("from", [])
        if ability_choice not in choices:
            return {"error": "Choose a valid ability for this feat."}
        return feat_adjustment(feat, {ability_choice: ability_increase.get("amount", 1)})
    return {}


def feat_adjustment(feat, adjustments):
    return {
        "type": "ability_score_adjustment",
        "source_type": "feat",
        "source_feat": feat.get("id", ""),
        "source_name": feat.get("name", ""),
        "adjustments": {
            ability: int(amount)
            for ability, amount in adjustments.items()
            if ability
        },
        "maximum": feat.get("ability_increase", {}).get("maximum", 20),
    }


def failed(message):
    return {"ok": False, "message": message}


def slug(value):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(value)).strip("_")
