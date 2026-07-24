WARLOCK_INVOCATION_PREREQUISITES = {
    "Agonizing Blast": {"minimum_warlock_level": 2, "requires_damage_cantrip": True},
    "Ascendant Step": {"minimum_warlock_level": 5},
    "Devouring Blade": {
        "minimum_warlock_level": 12,
        "required_invocations": ["Pact of the Blade", "Thirsting Blade"],
    },
    "Eldritch Smite": {"minimum_warlock_level": 5, "required_invocations": ["Pact of the Blade"]},
    "Eldritch Spear": {"minimum_warlock_level": 2, "requires_damage_cantrip": True},
    "Gift of the Protectors": {"required_invocations": ["Pact of the Tome"]},
    "Investment of the Chain Master": {"required_invocations": ["Pact of the Chain"]},
    "Lifedrinker": {"minimum_warlock_level": 9, "required_invocations": ["Pact of the Blade"]},
    "Master of Myriad Forms": {"minimum_warlock_level": 5},
    "One with Shadows": {"minimum_warlock_level": 5},
    "Repelling Blast": {"minimum_warlock_level": 2, "requires_damage_cantrip": True},
    "Thirsting Blade": {"minimum_warlock_level": 5, "required_invocations": ["Pact of the Blade"]},
    "Visions of Distant Realms": {"minimum_warlock_level": 9},
    "Whispers of the Grave": {"minimum_warlock_level": 7},
    "Witch Sight": {"minimum_warlock_level": 15},
}

INVOCATION_SUPPORT_OVERRIDES = {
    "Agonizing Blast": {
        "permanent_choices": "partial",
        "sheet_grants": "partial",
        "notes": "Needs a stored eligible damaging Warlock cantrip selection.",
    },
    "Eldritch Spear": {
        "permanent_choices": "partial",
        "sheet_grants": "partial",
        "notes": "Needs a stored eligible damaging Warlock cantrip selection.",
    },
    "Repelling Blast": {
        "permanent_choices": "partial",
        "sheet_grants": "partial",
        "notes": "Needs a stored eligible damaging Warlock cantrip selection.",
    },
    "Lessons of the First Ones": {
        "permanent_choices": "partial",
        "sheet_grants": "partial",
        "notes": "Needs an invocation-sourced Origin feat instance.",
    },
    "Pact of the Tome": {
        "permanent_choices": "partial",
        "sheet_grants": "partial",
        "notes": "Needs cantrip and ritual/spell choices with source metadata.",
    },
    "Pact of the Chain": {
        "permanent_choices": "partial",
        "sheet_grants": "partial",
        "notes": "Needs familiar/pact grant support.",
    },
    "Pact of the Blade": {
        "permanent_choices": "partial",
        "sheet_grants": "partial",
        "notes": "Needs pact weapon configuration and sheet grant support.",
    },
}

DEFAULT_INVOCATION_SUPPORT = {
    "selection": "supported",
    "prerequisites": "supported",
    "permanent_choices": "supported",
    "sheet_grants": "supported",
    "active_play": "description_only",
    "notes": "",
}

DAMAGE_CANTRIPS = {
    "Acid Splash",
    "Chill Touch",
    "Eldritch Blast",
    "Fire Bolt",
    "Poison Spray",
    "Produce Flame",
    "Ray of Frost",
    "Sacred Flame",
    "Shocking Grasp",
    "Starry Wisp",
    "Thunderclap",
    "Toll the Dead",
    "Vicious Mockery",
}


def normalize_invocation_options(invocation_rule):
    options = invocation_rule.get("options", []) if isinstance(invocation_rule, dict) else []
    if options:
        return [
            option if isinstance(option, dict) else {"name": option}
            for option in options
            if option
        ]
    names = invocation_rule.get("from", []) if isinstance(invocation_rule, dict) else []
    return [
        {"name": name, "prerequisites": WARLOCK_INVOCATION_PREREQUISITES.get(name, {})}
        for name in names
        if name
    ]


def eligible_invocation_names(character, invocation_rule, level):
    return [
        invocation.get("name", "")
        for invocation in normalize_invocation_options(invocation_rule)
        if invocation.get("name") and invocation_is_eligible(character, invocation, level)
    ]


def invocation_is_eligible(character, invocation, level):
    prerequisites = dict(invocation.get("prerequisites", {}))
    prerequisites.update(WARLOCK_INVOCATION_PREREQUISITES.get(invocation.get("name", ""), {}))

    if int(level or 1) < int(prerequisites.get("minimum_warlock_level", 1) or 1):
        return False

    selected_invocations = set(character.get("class_options", {}).get("eldritch_invocations", []))
    required_invocations = prerequisites.get("required_invocations", [])
    if any(invocation not in selected_invocations for invocation in required_invocations):
        return False

    if prerequisites.get("requires_damage_cantrip") and not selected_damage_cantrips(character):
        return False

    return True


def invocation_eligibility_reasons(character, invocation, level):
    prerequisites = dict(invocation.get("prerequisites", {}))
    prerequisites.update(WARLOCK_INVOCATION_PREREQUISITES.get(invocation.get("name", ""), {}))
    reasons = []

    minimum_level = int(prerequisites.get("minimum_warlock_level", 1) or 1)
    if int(level or 1) < minimum_level:
        reasons.append(f"Requires Warlock level {minimum_level}.")

    selected_invocations = set(character.get("class_options", {}).get("eldritch_invocations", []))
    missing_invocations = [
        invocation_name
        for invocation_name in prerequisites.get("required_invocations", []) or []
        if invocation_name not in selected_invocations
    ]
    if missing_invocations:
        reasons.append("Requires invocation: " + ", ".join(missing_invocations) + ".")

    if prerequisites.get("requires_damage_cantrip") and not selected_damage_cantrips(character):
        reasons.append("Requires a selected damaging cantrip.")

    return reasons


def invocation_support(name):
    support = dict(DEFAULT_INVOCATION_SUPPORT)
    support.update(INVOCATION_SUPPORT_OVERRIDES.get(name, {}))
    return support


def selected_damage_cantrips(character):
    selected = set(character.get("spells", {}).get("cantrips", []))
    selected.update(character.get("class_options", {}).get("blessed_warrior_cantrips", []))
    selected.update(character.get("class_options", {}).get("druidic_warrior_cantrips", []))
    selected.update(character.get("origin_feat_choices", {}).get("cantrips", []))
    selected.update(character.get("species_options", {}).get("lineage_spells", []))
    return selected.intersection(DAMAGE_CANTRIPS)
