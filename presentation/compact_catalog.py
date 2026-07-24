from collections.abc import Iterable, Mapping

from presentation.option_models import DisplayMetadata, OptionViewModel, SourceInfo


def build_class_feature_choice_catalog(
    option_names: Iterable[str],
    *,
    selected_name: str | None = None,
    kind: str = "class_feature_choice",
    source_label: str = "",
    description_lookup: Mapping[str, str] | None = None,
    related_features: Iterable[Mapping] | None = None,
    metadata_lookup: Mapping[str, Mapping[str, str]] | None = None,
    parent_description: str = "",
) -> tuple[OptionViewModel, ...]:
    descriptions = description_lookup or {}
    related = {str(item.get("name") or ""): item for item in related_features or [] if isinstance(item, Mapping)}
    metadata = metadata_lookup or {}
    selected_name = str(selected_name or "")
    return tuple(
        build_compact_option(
            kind=kind,
            value=name,
            name=name,
            description=_choice_description(name, descriptions, related, parent_description),
            selected=name == selected_name,
            source_label=str(related.get(name, {}).get("source") or source_label),
            raw_ref=str(related.get(name, {}).get("id") or ""),
            metadata=metadata.get(name, {}),
        )
        for name in option_names or []
        if name
    )


def build_species_choice_catalog(
    species_data: Mapping,
    choice_rule: Mapping,
    selected_name: str | None = None,
) -> tuple[OptionViewModel, ...]:
    descriptions = species_data.get("trait_descriptions") or {}
    parent_name = str(choice_rule.get("name") or "")
    parent_description = str(descriptions.get(parent_name) or "")
    metadata_lookup = {}
    for option in choice_rule.get("options", []) or []:
        metadata = {}
        option_description_key = _species_option_description_key(option, descriptions)
        if option_description_key and option_description_key != option:
            metadata["Rules entry"] = option_description_key
        metadata_lookup[option] = metadata
    return build_class_feature_choice_catalog(
        choice_rule.get("options", []),
        selected_name=selected_name,
        kind="species_choice",
        source_label=str(species_data.get("source") or ""),
        description_lookup=descriptions,
        metadata_lookup=metadata_lookup,
        parent_description=parent_description,
    )


def build_lineage_catalog(
    species_data: Mapping,
    selected_name: str | None = None,
) -> tuple[OptionViewModel, ...]:
    descriptions = species_data.get("trait_descriptions") or {}
    lineage_options = species_data.get("lineage_options", []) or []
    parent_description = _lineage_parent_description(species_data, descriptions)
    options = []
    for lineage in lineage_options:
        name = str(lineage.get("name") or "")
        if not name:
            continue
        description = str(descriptions.get(name) or parent_description or "")
        level_1_spells = ", ".join(str(spell) for spell in lineage.get("level_1_spells", []) if spell)
        abilities = ", ".join(str(ability) for ability in lineage.get("spellcasting_abilities", []) if ability)
        metadata = {
            "Level 1 grant": level_1_spells or "No level 1 spell grant listed",
            "Spellcasting ability": abilities,
            "Later grants": "Additional lineage spells arrive at later character levels when listed by the source.",
        }
        options.append(
            build_compact_option(
                kind="lineage",
                value=name,
                name=name,
                description=description,
                selected=name == str(selected_name or ""),
                source_label=str(species_data.get("source") or ""),
                metadata=metadata,
            )
        )
    return tuple(options)


def build_equipment_package_catalog(
    packages: Iterable[Mapping],
    selected_name: str | None = None,
    *,
    source_label: str = "",
) -> tuple[OptionViewModel, ...]:
    selected_name = str(selected_name or "")
    options = []
    for package in packages or []:
        name = str(package.get("name") or "")
        if not name:
            continue
        items = [str(item) for item in package.get("items", []) or [] if item]
        description = ", ".join(items)
        display_name = equipment_package_label(package)
        options.append(
            build_compact_option(
                kind="equipment_package",
                value=name,
                name=display_name,
                description=description,
                full_description="\n".join(f"- {item}" for item in items),
                selected=name == selected_name,
                source_label=source_label,
                metadata={"Items": str(len(items)) if items else "0"},
            )
        )
    return tuple(options)


def equipment_package_label(package: Mapping) -> str:
    name = str(package.get("name") or "")
    items = [str(item) for item in package.get("items", []) or [] if item]
    if not items:
        return name
    preview = ", ".join(items[:3])
    if len(items) > 3:
        preview += f", and {len(items) - 3} more"
    return f"Package {name} - {preview}" if len(name) <= 2 else f"{name} - {preview}"


def build_named_feature_catalog(
    option_names: Iterable[str],
    description_lookup: Mapping[str, str] | None = None,
    *,
    kind: str = "feature",
    selected_ids: Iterable[str] | None = None,
    source_label: str = "",
    metadata_lookup: Mapping[str, Mapping[str, str]] | None = None,
) -> tuple[OptionViewModel, ...]:
    descriptions = description_lookup or {}
    metadata = metadata_lookup or {}
    selected = set(selected_ids or ())
    return tuple(
        build_compact_option(
            kind=kind,
            value=name,
            name=name,
            description=descriptions.get(name, ""),
            selected=stable_compact_id(kind, name, source_label=source_label) in selected,
            source_label=source_label,
            metadata=metadata.get(name, {}),
        )
        for name in option_names or []
        if name
    )


def build_subclass_catalog(
    class_data: Mapping,
    target_level: int,
    selected_name: str | None = None,
    *,
    option_names: Iterable[str] | None = None,
) -> tuple[OptionViewModel, ...]:
    class_name = str(class_data.get("name") or "")
    allowed = {str(name) for name in option_names or () if name}
    selected_name = str(selected_name or "")
    options = []
    for subclass in class_data.get("subclasses", []) or []:
        name = str(subclass.get("name") or subclass.get("short_name") or "")
        if not name:
            continue
        short_name = str(subclass.get("short_name") or "")
        if allowed and name not in allowed and short_name not in allowed:
            continue

        source_label = str(subclass.get("source") or class_data.get("source") or "")
        identity = subclass_identity_description(subclass)
        target_features = subclass_features_at_level(subclass, target_level)
        follow_ups = subclass_follow_up_summaries(subclass, target_level)
        selected = selected_name in {name, short_name}
        metadata = {
            "Class": class_name,
            "Target level gains": ", ".join(target_features) if target_features else "No subclass features at this level",
            "Follow-up choices": "; ".join(follow_ups) if follow_ups else "None",
        }
        options.append(
            build_compact_option(
                kind="subclass",
                value=name,
                name=name,
                description=identity,
                full_description=subclass_full_description(subclass, target_level),
                selected=selected,
                source_label=source_label,
                raw_ref=str(subclass.get("id") or ""),
                metadata=metadata,
            )
        )
    return tuple(options)


def subclass_stable_id(class_data: Mapping, subclass_name: str | None) -> str | None:
    if not subclass_name:
        return None
    wanted = str(subclass_name)
    for subclass in class_data.get("subclasses", []) or []:
        name = str(subclass.get("name") or "")
        short_name = str(subclass.get("short_name") or "")
        if wanted in {name, short_name}:
            return stable_compact_id(
                "subclass",
                name,
                source_label=str(subclass.get("source") or class_data.get("source") or ""),
                raw_ref=str(subclass.get("id") or ""),
            )
    return None


def build_legacy_review_option(
    stable_id: str,
    *,
    kind: str = "legacy",
    source_label: str = "",
) -> OptionViewModel:
    return OptionViewModel(
        stable_id=stable_id,
        kind=kind,
        name=stable_id,
        short_summary="This saved selection is no longer available. Review before changing it.",
        full_description="",
        display_metadata=(),
        selected=True,
        availability_status="unavailable",
        eligibility_reasons=("This saved selection is no longer available.",),
        source=SourceInfo(source=source_label),
        payload=(("value", stable_id),),
    )


def build_compact_option(
    *,
    kind: str,
    value: str,
    name: str,
    description: str = "",
    full_description: str | None = None,
    selected: bool = False,
    availability_status: str | None = None,
    eligibility_reasons: Iterable[str] = (),
    source_label: str = "",
    raw_ref: str = "",
    metadata: Mapping[str, str] | None = None,
) -> OptionViewModel:
    status = availability_status or ("selected" if selected else "available")
    reasons = tuple(eligibility_reasons or ())
    if not reasons:
        reasons = ("Already selected.",) if status == "selected" else ("Available for this choice.",)
    return OptionViewModel(
        stable_id=stable_compact_id(kind, value, source_label=source_label, raw_ref=raw_ref),
        kind=kind,
        name=name,
        short_summary=short_summary(clean_presentation_text(description)),
        full_description=clean_presentation_text(full_description if full_description is not None else description or ""),
        display_metadata=tuple(
            DisplayMetadata(str(label), str(metadata_value))
            for label, metadata_value in (metadata or {}).items()
            if metadata_value not in {None, ""}
        ),
        selected=selected,
        availability_status=status,
        eligibility_reasons=reasons,
        source=SourceInfo(source=source_label, raw_ref=raw_ref),
        payload=(("value", value),),
    )


def subclass_identity_description(subclass: Mapping) -> str:
    descriptions = subclass.get("feature_descriptions") or {}
    name = str(subclass.get("name") or "")
    short_name = str(subclass.get("short_name") or "")
    return str(
        descriptions.get(name)
        or descriptions.get(short_name)
        or subclass.get("description")
        or ""
    )


def subclass_features_at_level(subclass: Mapping, target_level: int) -> tuple[str, ...]:
    features = (subclass.get("level_features") or {}).get(str(target_level), [])
    return tuple(str(feature) for feature in features or [] if feature)


def subclass_follow_up_summaries(subclass: Mapping, target_level: int) -> tuple[str, ...]:
    options = subclass.get("subclass_options") or {}
    if not isinstance(options, Mapping):
        return ()
    summaries = []
    seen = set()
    for key, rule in options.items():
        if str(key).endswith("_by_level") and isinstance(rule, Mapping):
            level_rule = rule.get(str(target_level))
            if level_rule:
                _append_unique_summary(summaries, seen, _choice_rule_summary(key, level_rule))
            continue
        _append_unique_summary(summaries, seen, _choice_rule_summary(key, rule))
    return tuple(summaries)


def subclass_full_description(subclass: Mapping, target_level: int) -> str:
    sections = []
    identity = subclass_identity_description(subclass)
    if identity:
        sections.append(identity)
    else:
        sections.append("No subclass overview was found in the imported source data.")

    sections.append(_target_level_section(subclass, target_level))

    follow_ups = subclass_follow_up_summaries(subclass, target_level)
    if follow_ups:
        sections.append("### Follow-up Choices\n\n" + "\n".join(f"- {summary}" for summary in follow_ups))
    else:
        sections.append("### Follow-up Choices\n\nNone at this step.")

    progression = _progression_section(subclass)
    if progression:
        sections.append(progression)
    return "\n\n".join(section for section in sections if section)


def _target_level_section(subclass: Mapping, target_level: int) -> str:
    features = subclass_features_at_level(subclass, target_level)
    descriptions = subclass.get("feature_descriptions") or {}
    if not features:
        return f"### Level {target_level} Features\n\nNo subclass features are listed for this level."
    lines = []
    for feature in features:
        description = str(descriptions.get(feature) or "").strip()
        if description:
            lines.append(f"**{feature}**\n\n{description}")
        else:
            lines.append(f"**{feature}**\n\nNo description was found in the imported source data.")
    return f"### Level {target_level} Features\n\n" + "\n\n".join(lines)


def _progression_section(subclass: Mapping) -> str:
    levels = subclass.get("level_features") or {}
    if not isinstance(levels, Mapping):
        return ""
    descriptions = subclass.get("feature_descriptions") or {}
    lines = []
    for level, features in sorted(levels.items(), key=lambda item: int(item[0]) if str(item[0]).isdigit() else 999):
        feature_names = [str(feature) for feature in features or [] if feature]
        feature_list = ", ".join(feature_names)
        if feature_list:
            lines.append(f"- Level {level}: {feature_list}")
        for feature in feature_names:
            description = str(descriptions.get(feature) or "").strip()
            if description:
                lines.append(f"  - **{feature}:** {short_summary(description, max_length=220)}")
    if not lines:
        return ""
    return "### Full Progression\n\n" + "\n".join(lines)


def _append_unique_summary(summaries: list[str], seen: set[str], summary: str) -> None:
    if not summary or summary in seen:
        return
    seen.add(summary)
    summaries.append(summary)


def _choice_rule_summary(key: str, rule) -> str:
    label = ""
    choose = None
    if isinstance(rule, Mapping):
        label = str(rule.get("label") or "")
        choose = rule.get("choose")
    if not label:
        label = _humanize_key(key)
    if choose and "choose" not in label.casefold():
        label = f"{label} (choose {choose})"
    return label


def _humanize_key(key: str) -> str:
    return str(key).replace("_", " ").strip().capitalize()


def _choice_description(
    name: str,
    descriptions: Mapping[str, str],
    related: Mapping[str, Mapping],
    parent_description: str = "",
) -> str:
    if name in descriptions:
        return str(descriptions.get(name) or "")
    if name in related:
        return str(related[name].get("description") or "")
    extracted = extract_named_option_description(parent_description, name)
    if extracted:
        return extracted
    option_key = _species_option_description_key(name, descriptions)
    if option_key:
        return str(descriptions.get(option_key) or "")
    return parent_description or ""


def _species_option_description_key(option_name: str, descriptions: Mapping[str, str]) -> str:
    option_name = str(option_name or "")
    for key in descriptions:
        if key == option_name or key.endswith(f"({option_name})"):
            return str(key)
    return ""


def _lineage_parent_description(species_data: Mapping, descriptions: Mapping[str, str]) -> str:
    for trait in species_data.get("traits", []) or []:
        trait = str(trait)
        if "Lineage" in trait or "Legacy" in trait:
            return str(descriptions.get(trait) or "")
    for key, description in descriptions.items():
        if "Lineage" in str(key) or "Legacy" in str(key):
            return str(description or "")
    return ""


def extract_named_option_description(description: str, option_name: str) -> str:
    description = str(description or "")
    option_name = str(option_name or "")
    marker = f"{option_name}:"
    start = description.find(marker)
    if start < 0:
        return ""
    body = description[start + len(marker):].strip()
    next_break = -1
    paragraphs = body.split("\n\n")
    if paragraphs:
        first = paragraphs[0].strip()
        if first:
            return first
    for index, char in enumerate(body):
        if char == "\n" and index + 1 < len(body) and body[index + 1].isupper():
            next_break = index
            break
    return (body[:next_break] if next_break >= 0 else body).strip()


def clean_presentation_text(text: str) -> str:
    cleaned = str(text or "")
    school_codes = {
        "school=A": "Abjuration",
        "school=C": "Conjuration",
        "school=D": "Divination",
        "school=E": "Enchantment",
        "school=V": "Evocation",
        "school=I": "Illusion",
        "school=N": "Necromancy",
        "school=T": "Transmutation",
    }
    for raw, replacement in school_codes.items():
        cleaned = cleaned.replace(raw, replacement)
    replacements = {
        "class=": "",
        "type=": "",
        "school=": "",
        "category=": "",
    }
    for raw, replacement in replacements.items():
        cleaned = cleaned.replace(raw, replacement)
    return cleaned


def option_value(option: OptionViewModel) -> str:
    return str(dict(option.payload).get("value", option.stable_id))


def stable_compact_id(
    kind: str,
    value: str,
    *,
    source_label: str = "",
    raw_ref: str = "",
) -> str:
    identity = raw_ref or "|".join(part for part in (source_label, value) if part)
    return f"{kind}:{identity or value}".strip().casefold()


def short_summary(description: str, *, max_length: int = 140) -> str:
    text = " ".join((description or "").split())
    if not text:
        return "No description available."
    sentence_end = text.find(". ")
    if 0 <= sentence_end < max_length:
        return text[: sentence_end + 1]
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "..."
