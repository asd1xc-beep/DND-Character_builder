MYSTIC_ARCANUM_PROGRESSION = {
    11: 6,
    13: 7,
    15: 8,
    17: 9,
}


def mystic_arcanum_spell_level_for_source_level(source_level):
    return MYSTIC_ARCANUM_PROGRESSION.get(int(source_level or 0), 0)


def mystic_arcanum_source_level_for_spell_level(spell_level):
    spell_level = int(spell_level or 0)
    for source_level, arcanum_spell_level in MYSTIC_ARCANUM_PROGRESSION.items():
        if arcanum_spell_level == spell_level:
            return source_level
    return 0


def mystic_arcanum_choice_key(spell_level):
    return f"mystic_arcanum_{int(spell_level or 0)}"


def mystic_arcanum_choices_for_level(character_level):
    level = int(character_level or 1)
    return [
        {
            "source_level": source_level,
            "spell_level": spell_level,
            "key": mystic_arcanum_choice_key(spell_level),
        }
        for source_level, spell_level in sorted(MYSTIC_ARCANUM_PROGRESSION.items())
        if level >= source_level
    ]


def mystic_arcanum_options(spells, spell_level):
    spell_level = int(spell_level or 0)
    return sorted({
        spell.get("name", "")
        for spell in spells or []
        if spell.get("name")
        and spell.get("level") == spell_level
        and "Warlock" in spell.get("classes", [])
    })


def mystic_arcanum_record(spell_name, spell_level, source_level, class_name="Warlock"):
    spell_level = int(spell_level or 0)
    source_level = int(source_level or mystic_arcanum_source_level_for_spell_level(spell_level) or 0)
    return {
        "instance_id": f"warlock_mystic_arcanum_{spell_level}",
        "spell_id": slug_spell_id(spell_name),
        "spell_name": spell_name,
        "name": spell_name,
        "spell_level": spell_level,
        "source_level": source_level,
        "spellcasting_ability": "Charisma",
        "source": {
            "type": "class_feature",
            "class_name": class_name,
            "feature_name": "Mystic Arcanum",
            "source_name": "Mystic Arcanum",
            "level": source_level,
        },
        "casting_rules": {
            "free_casts": 1,
            "recharge": "long_rest",
            "uses_pact_slots": False,
        },
        "always_prepared": True,
        "counts_against_limit": False,
        "grant_type": "mystic_arcanum",
    }


def upsert_mystic_arcanum_record(character, spell_name, spell_level, source_level):
    if not spell_name:
        return
    records = character.setdefault("mystic_arcanum", [])
    instance_id = f"warlock_mystic_arcanum_{int(spell_level or 0)}"
    record = mystic_arcanum_record(spell_name, spell_level, source_level, character.get("class", "Warlock"))
    for index, existing in enumerate(records):
        if isinstance(existing, dict) and existing.get("instance_id") == instance_id:
            records[index] = record
            return
    records.append(record)


def sync_mystic_arcanum_class_options(character):
    class_options = character.setdefault("class_options", {})
    for choice in mystic_arcanum_choices_for_level(character.get("level", 1)):
        selected = class_options.get(choice["key"], [])
        if isinstance(selected, str):
            selected = [selected] if selected else []
        for spell_name in selected or []:
            upsert_mystic_arcanum_record(
                character,
                spell_name,
                choice["spell_level"],
                choice["source_level"],
            )


def migrate_legacy_mystic_arcanum(character):
    class_options = character.setdefault("class_options", {})
    legacy_spells = class_options.get("mystic_arcanum", [])
    if isinstance(legacy_spells, str):
        legacy_spells = [legacy_spells] if legacy_spells else []
    legacy_spells = [spell for spell in legacy_spells or [] if spell]
    if not legacy_spells:
        sync_mystic_arcanum_class_options(character)
        return

    migrated = []
    for index, spell_name in enumerate(legacy_spells):
        source_levels = sorted(MYSTIC_ARCANUM_PROGRESSION)
        source_level = source_levels[index] if index < len(source_levels) else 11
        spell_level = MYSTIC_ARCANUM_PROGRESSION[source_level]
        class_options[mystic_arcanum_choice_key(spell_level)] = [spell_name]
        upsert_mystic_arcanum_record(character, spell_name, spell_level, source_level)
        migrated.append(spell_name)
    class_options["legacy_mystic_arcanum"] = migrated
    class_options.pop("mystic_arcanum", None)
    character.setdefault("migration_warnings", []).append(
        "Legacy Mystic Arcanum selections were converted into level-specific Arcanum records."
    )


def mystic_arcanum_grant_records(character):
    records = []
    seen = set()
    for record in character.get("mystic_arcanum", []) or []:
        if not isinstance(record, dict):
            continue
        spell_name = record.get("spell_name") or record.get("name")
        spell_level = int(record.get("spell_level", 0) or 0)
        if not spell_name or not spell_level:
            continue
        key = (spell_name, spell_level)
        if key in seen:
            continue
        item = dict(record)
        item["name"] = spell_name
        item["spellcasting_ability"] = item.get("spellcasting_ability") or "Charisma"
        item["grant_type"] = "mystic_arcanum"
        item["always_prepared"] = True
        item["counts_against_limit"] = False
        item.setdefault("source", {
            "type": "class_feature",
            "class_name": character.get("class", "Warlock"),
            "feature_name": "Mystic Arcanum",
            "source_name": "Mystic Arcanum",
            "level": item.get("source_level"),
        })
        item.setdefault("casting_rules", {
            "free_casts": 1,
            "recharge": "long_rest",
            "uses_pact_slots": False,
        })
        records.append(item)
        seen.add(key)
    return records


def slug_spell_id(spell_name):
    return "".join(char.lower() if char.isalnum() else "_" for char in str(spell_name)).strip("_") + "_xphb"
