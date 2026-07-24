from dataclasses import dataclass
from typing import Iterable

from models.character import merge_unique
from presentation.option_models import DisplayMetadata, OptionGroupState, OptionViewModel, SourceInfo
from services.spell_labels import spell_level_label


@dataclass(frozen=True)
class SelectionResult:
    selection: tuple[str, ...]
    changed: bool
    accepted: bool
    reason: str = ""


@dataclass(frozen=True)
class SpellSelectionGroupSpec:
    key: str
    label: str
    option_names: tuple[str, ...]
    selected_names: tuple[str, ...]
    selection_limit: int | None
    add_label: str = "Add spell"
    remove_label: str = "Remove spell"


def build_spell_option_catalog(
    spells: Iterable[dict],
    option_names: Iterable[str],
    selected_names: Iterable[str],
    *,
    kind: str = "spell",
    selection_limit: int | None = 0,
) -> tuple[OptionViewModel, ...]:
    group = SpellSelectionGroupSpec(
        key=kind,
        label=kind.replace("_", " ").title(),
        option_names=tuple(name for name in option_names or [] if name),
        selected_names=tuple(name for name in selected_names or [] if name),
        selection_limit=selection_limit,
        add_label=f"Add {kind}",
        remove_label=f"Remove {kind}",
    )
    return build_grouped_spell_option_catalog(spells, (group,), kind=kind)


def build_grouped_spell_option_catalog(
    spells: Iterable[dict],
    groups: Iterable[SpellSelectionGroupSpec],
    *,
    kind: str = "spell",
) -> tuple[OptionViewModel, ...]:
    spell_lookup = {
        spell.get("name", ""): spell
        for spell in spells or []
        if spell.get("name")
    }
    group_specs = tuple(groups or ())
    names = merge_unique(
        *[
            list(group.option_names) + list(group.selected_names)
            for group in group_specs
        ]
    )

    options = [
        _spell_option(
            spell_lookup.get(name, {"name": name}),
            kind=kind,
            group_states=_spell_group_states(name, group_specs),
        )
        for name in names
    ]
    return tuple(sorted(options, key=_option_sort_key))


def option_by_id(options: Iterable[OptionViewModel], stable_id: str) -> OptionViewModel | None:
    return next((option for option in options if option.stable_id == stable_id), None)


def inspect_option(
    options: Iterable[OptionViewModel],
    stable_id: str,
) -> OptionViewModel | None:
    return option_by_id(options, stable_id)


def add_option_to_selection(
    selected_names: Iterable[str],
    options: Iterable[OptionViewModel],
    stable_id: str,
    *,
    selection_limit: int | None = 0,
) -> SelectionResult:
    options = tuple(options)
    group_key = _default_group_key(options)
    return add_option_to_group_selection(
        selected_names,
        options,
        stable_id,
        group_key=group_key,
        selection_limit=selection_limit,
    )


def add_option_to_group_selection(
    selected_names: Iterable[str],
    options: Iterable[OptionViewModel],
    stable_id: str,
    *,
    group_key: str,
    selection_limit: int | None = 0,
) -> SelectionResult:
    selected = tuple(name for name in selected_names or [] if name)
    option = option_by_id(options, stable_id)
    if option is None:
        return SelectionResult(selected, False, False, "This option is no longer available.")
    if option.name in selected:
        return SelectionResult(selected, False, True, "Already selected.")
    group_state = option_group_state(option, group_key)
    if group_state is None:
        return SelectionResult(selected, False, False, "This option is unavailable for this spell choice.")
    if group_state.availability_status == "unavailable":
        reason = group_state.eligibility_reasons[0] if group_state.eligibility_reasons else "This option is unavailable."
        return SelectionResult(selected, False, False, reason)
    if selection_limit is not None and len(selected) >= selection_limit:
        return SelectionResult(
            selected,
            False,
            False,
            full_selection_reason(len(selected), selection_limit),
        )
    return SelectionResult(tuple([*selected, option.name]), True, True)


def remove_option_from_selection(
    selected_names: Iterable[str],
    stable_id: str,
    options: Iterable[OptionViewModel],
) -> SelectionResult:
    options = tuple(options)
    group_key = _default_group_key(options)
    return remove_option_from_group_selection(selected_names, stable_id, options, group_key=group_key)


def remove_option_from_group_selection(
    selected_names: Iterable[str],
    stable_id: str,
    options: Iterable[OptionViewModel],
    *,
    group_key: str,
) -> SelectionResult:
    selected = tuple(name for name in selected_names or [] if name)
    option = option_by_id(options, stable_id)
    if option is None:
        return SelectionResult(selected, False, False, "This option is no longer available.")
    if option_group_state(option, group_key) is None:
        return SelectionResult(selected, False, False, "This option is unavailable for this spell choice.")
    if option.name not in selected:
        return SelectionResult(selected, False, True, "Not selected.")
    return SelectionResult(tuple(name for name in selected if name != option.name), True, True)


def full_selection_reason(selected_count: int, selection_limit: int) -> str:
    return (
        f"Selection is full ({selected_count}/{selection_limit}). "
        "Remove an option before adding another."
    )


def _spell_option(
    spell: dict,
    *,
    kind: str,
    group_states: tuple[OptionGroupState, ...],
) -> OptionViewModel:
    name = spell.get("name", "")
    level = spell.get("level")
    selected = any(group.selected for group in group_states)
    status, reasons = _combined_availability(group_states)
    return OptionViewModel(
        stable_id=spell_stable_id(spell),
        kind=kind,
        name=name,
        short_summary=short_summary(spell.get("description", "")),
        full_description=spell.get("description", ""),
        display_metadata=(
            DisplayMetadata("Level", spell_level_label(level)),
            DisplayMetadata("School", spell.get("school", "")),
            DisplayMetadata("Casting time", spell.get("casting_time", "")),
            DisplayMetadata("Range", spell.get("range", "")),
            DisplayMetadata("Duration", spell.get("duration", "")),
            DisplayMetadata("Components", format_components(spell.get("components", []))),
        ),
        selected=selected,
        availability_status=status,
        eligibility_reasons=tuple(reasons),
        source=SourceInfo(
            source=spell.get("source", ""),
            raw_ref=spell.get("raw_ref", ""),
        ),
        group_states=group_states,
        payload=(
            ("level", level),
            ("school", spell.get("school", "")),
            ("casting_time", spell.get("casting_time", "")),
            ("range", spell.get("range", "")),
            ("duration", spell.get("duration", "")),
            ("components", format_components(spell.get("components", []))),
            ("source", spell.get("source", "")),
        ),
    )


def _spell_group_states(
    spell_name: str,
    groups: tuple[SpellSelectionGroupSpec, ...],
) -> tuple[OptionGroupState, ...]:
    states = []
    for group in groups:
        selected = spell_name in set(group.selected_names)
        eligible = spell_name in set(group.option_names)
        selected_count = len([name for name in group.selected_names if name])
        full = group.selection_limit is not None and selected_count >= group.selection_limit
        status, reasons = _availability_status(
            selected=selected,
            eligible=eligible,
            full=full,
            selected_count=selected_count,
            selection_limit=group.selection_limit,
        )
        states.append(OptionGroupState(
            key=group.key,
            label=group.label,
            selected=selected,
            availability_status=status,
            eligibility_reasons=tuple(reasons),
            selected_count=selected_count,
            selection_limit=group.selection_limit,
            add_label=group.add_label,
            remove_label=group.remove_label,
            eligible=eligible,
        ))
    return tuple(states)


def _availability_status(
    *,
    selected: bool,
    eligible: bool,
    full: bool,
    selected_count: int,
    selection_limit: int | None,
) -> tuple[str, list[str]]:
    if selected:
        return "selected", ["Already selected."]
    if not eligible:
        return "unavailable", ["Not available for this choice."]
    if full and selection_limit is not None:
        return "unavailable", [full_selection_reason(selected_count, selection_limit)]
    return "available", ["Available for this choice."]


def _combined_availability(group_states: tuple[OptionGroupState, ...]) -> tuple[str, tuple[str, ...]]:
    selected = [group for group in group_states if group.selected]
    if selected:
        return "selected", tuple(f"{group.label}: selected." for group in selected)
    available = [group for group in group_states if group.availability_status == "available"]
    if available:
        return "available", tuple(f"{group.label}: available." for group in available)
    reasons = []
    for group in group_states:
        reasons.extend(f"{group.label}: {reason}" for reason in group.eligibility_reasons)
    return "unavailable", tuple(reasons or ["Unavailable for this choice."])


def option_group_state(option: OptionViewModel, group_key: str) -> OptionGroupState | None:
    return next((group for group in option.group_states if group.key == group_key), None)


def _default_group_key(options: tuple[OptionViewModel, ...]) -> str:
    if not options:
        return ""
    if options[0].group_states:
        return options[0].group_states[0].key
    return options[0].kind


def spell_stable_id(spell: dict) -> str:
    source = spell.get("source", "")
    raw_ref = spell.get("raw_ref", "")
    name = spell.get("name", "")
    identity = raw_ref or (f"{name}|{source}" if source else name)
    return "spell:" + identity.strip().casefold()


def short_summary(description: str, *, max_length: int = 140) -> str:
    text = " ".join((description or "").split())
    if not text:
        return ""
    sentence_end = text.find(". ")
    if 0 <= sentence_end < max_length:
        return text[: sentence_end + 1]
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "..."


def format_components(components) -> str:
    if isinstance(components, str):
        return components
    return ", ".join(str(component) for component in components or [] if component)


def _payload_value(option: OptionViewModel, key: str):
    return dict(option.payload).get(key)


def _option_sort_key(option: OptionViewModel):
    level = _payload_value(option, "level")
    level_sort = level if isinstance(level, int) else 99
    return (level_sort, option.name)
