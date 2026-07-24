from collections.abc import Iterable, Mapping

from presentation.option_catalog import full_selection_reason, short_summary
from presentation.option_models import DisplayMetadata, OptionViewModel, SourceInfo


MISSING_MASTERY_DESCRIPTION = "No mastery-property description is available in the imported source data."


def build_weapon_mastery_catalog(
    weapons: Iterable[Mapping],
    *,
    eligible_names: Iterable[str],
    selected_names: Iterable[str],
    selection_limit: int,
    mastery_descriptions: Iterable[Mapping] = (),
    existing_masteries: Iterable[str] = (),
) -> tuple[OptionViewModel, ...]:
    selected = [name for name in selected_names or [] if name]
    selected_set = set(selected)
    eligible = set(eligible_names or [])
    existing = set(existing_masteries or [])
    mastery_lookup = {
        str(record.get("name") or ""): record
        for record in mastery_descriptions or []
        if record.get("name")
    }
    weapon_lookup = {
        str(weapon.get("name") or ""): weapon
        for weapon in weapons or []
        if weapon.get("name") and weapon.get("mastery")
    }
    names = _catalog_names(weapon_lookup, selected_set, existing)
    full = bool(selection_limit) and len(selected) >= selection_limit
    return tuple(
        _weapon_option(
            weapon_lookup.get(name, {"name": name}),
            mastery_lookup,
            selected=name in selected_set,
            eligible=name in eligible,
            existing=name in existing,
            full=full,
            selected_count=len(selected),
            selection_limit=selection_limit,
        )
        for name in names
    )


def weapon_mastery_stable_id(name: str) -> str:
    return f"weapon_mastery:{str(name or '').strip().casefold()}"


def option_value(option: OptionViewModel) -> str:
    return str(dict(option.payload).get("value", option.name))


def _weapon_option(
    weapon: Mapping,
    mastery_lookup: Mapping[str, Mapping],
    *,
    selected: bool,
    eligible: bool,
    existing: bool,
    full: bool,
    selected_count: int,
    selection_limit: int,
) -> OptionViewModel:
    name = str(weapon.get("name") or "")
    mastery = _clean_mastery_name(weapon.get("mastery", ""))
    mastery_record = mastery_lookup.get(mastery, {})
    description = str(mastery_record.get("description") or MISSING_MASTERY_DESCRIPTION)
    status, reasons = _status(
        selected=selected,
        eligible=eligible,
        existing=existing,
        full=full,
        selected_count=selected_count,
        selection_limit=selection_limit,
        known_weapon=bool(weapon.get("mastery")),
    )
    return OptionViewModel(
        stable_id=weapon_mastery_stable_id(name),
        kind="weapon_mastery",
        name=name,
        short_summary=short_summary(description),
        full_description=description,
        display_metadata=(
            DisplayMetadata("Mastery", mastery or "Unknown"),
            DisplayMetadata("Category", str(weapon.get("category") or "Unknown")),
            DisplayMetadata("Damage", _damage_label(weapon)),
            DisplayMetadata("Damage type", str(weapon.get("damage_type") or "Unknown")),
        ),
        selected=selected,
        availability_status=status,
        eligibility_reasons=tuple(reasons),
        source=SourceInfo(
            source=str(mastery_record.get("source") or "XPHB"),
            raw_ref=str(mastery_record.get("raw_ref") or ""),
        ),
        payload=(
            ("value", name),
            ("mastery", mastery),
            ("category", str(weapon.get("category") or "Unknown")),
            ("damage", _damage_label(weapon)),
            ("damage_type", str(weapon.get("damage_type") or "Unknown")),
            ("existing_mastery", existing),
        ),
    )


def _status(
    *,
    selected: bool,
    eligible: bool,
    existing: bool,
    full: bool,
    selected_count: int,
    selection_limit: int,
    known_weapon: bool,
) -> tuple[str, tuple[str, ...]]:
    if selected:
        return "selected", ("Already selected.",)
    if existing:
        return "unavailable", ("Already mastered by this character.",)
    if not known_weapon:
        return "unavailable", ("This saved weapon mastery is no longer available in the source data.",)
    if not eligible:
        return "unavailable", ("Requires proficiency with this weapon.",)
    if full:
        return "unavailable", (full_selection_reason(selected_count, selection_limit),)
    return "available", ("Available for this choice.",)


def _catalog_names(weapon_lookup: Mapping[str, Mapping], selected: set[str], existing: set[str]) -> tuple[str, ...]:
    names = set(weapon_lookup)
    names.update(selected)
    names.update(existing)
    return tuple(sorted(name for name in names if name))


def _clean_mastery_name(value) -> str:
    text = str(value or "")
    if "{'uid': '" in text:
        text = text.split("{'uid': '", 1)[1].split("|", 1)[0]
    if "|" in text:
        text = text.split("|", 1)[0]
    return text.strip()


def _damage_label(weapon: Mapping) -> str:
    damage = str(weapon.get("damage") or "")
    return damage or "-"
