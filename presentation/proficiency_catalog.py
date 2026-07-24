from collections.abc import Iterable, Mapping

from presentation.compact_catalog import build_compact_option, option_value, stable_compact_id
from presentation.option_models import OptionViewModel


def build_skill_catalog(
    skill_records: Iterable[Mapping],
    option_names: Iterable[str],
    selected_names: Iterable[str] | None = None,
    *,
    kind: str = "skill",
) -> tuple[OptionViewModel, ...]:
    records = {
        str(record.get("name") or ""): record
        for record in skill_records or []
        if record.get("name")
    }
    selected = set(selected_names or [])
    return tuple(
        build_compact_option(
            kind=kind,
            value=name,
            name=name,
            description=str(records.get(name, {}).get("description") or ""),
            selected=name in selected,
            source_label=str(records.get(name, {}).get("source") or ""),
            raw_ref=str(records.get(name, {}).get("raw_ref") or ""),
            metadata={"Ability": records.get(name, {}).get("ability", "Unknown")},
        )
        for name in option_names or []
        if name
    )


def build_tool_catalog(
    option_names: Iterable[str],
    selected_names: Iterable[str] | None = None,
    *,
    category: str = "Tool",
    source_label: str = "",
    kind: str = "tool",
) -> tuple[OptionViewModel, ...]:
    selected = set(selected_names or [])
    return tuple(
        build_compact_option(
            kind=kind,
            value=name,
            name=name,
            description=f"{category} proficiency option. No further rules description is available in the imported source data.",
            selected=name in selected,
            source_label=source_label,
            metadata={"Category": category},
        )
        for name in option_names or []
        if name
    )


def build_language_catalog(
    option_names: Iterable[str],
    selected_names: Iterable[str] | None = None,
    *,
    source_label: str = "",
) -> tuple[OptionViewModel, ...]:
    selected = set(selected_names or [])
    return tuple(
        build_compact_option(
            kind="language",
            value=name,
            name=name,
            description="Language proficiency option. No mechanical effect is listed in the imported source data.",
            selected=name in selected,
            source_label=source_label,
            metadata={"Category": "Language"},
        )
        for name in option_names or []
        if name
    )


def build_prefixed_skill_tool_catalog(
    skill_records: Iterable[Mapping],
    skill_names: Iterable[str],
    tool_names: Iterable[str],
    selected_values: Iterable[str] | None = None,
) -> tuple[OptionViewModel, ...]:
    selected = set(selected_values or [])
    skill_options = [
        _prefixed_option(option, prefix="Skill", selected=f"Skill: {option.name}" in selected)
        for option in build_skill_catalog(skill_records, skill_names)
    ]
    tool_options = [
        _prefixed_option(option, prefix="Tool", selected=f"Tool: {option.name}" in selected)
        for option in build_tool_catalog(tool_names, category="Tool")
    ]
    return tuple(skill_options + tool_options)


def compact_selected_ids(options: Iterable[OptionViewModel], selected_values: Iterable[str]) -> list[str]:
    wanted = set(selected_values or [])
    return [
        option.stable_id
        for option in options
        if option_value(option) in wanted
    ]


def values_from_ids(options: Iterable[OptionViewModel], selected_ids: Iterable[str]) -> list[str]:
    by_id = {option.stable_id: option for option in options}
    return [
        option_value(by_id[selected_id])
        for selected_id in selected_ids or []
        if selected_id in by_id
    ]


def _prefixed_option(option: OptionViewModel, *, prefix: str, selected: bool) -> OptionViewModel:
    value = f"{prefix}: {option_value(option)}"
    return build_compact_option(
        kind="skill_tool",
        value=value,
        name=value,
        description=option.full_description or option.short_summary,
        selected=selected,
        source_label=option.source.source,
        raw_ref=stable_compact_id("skill_tool", value),
        metadata={metadata.label: metadata.value for metadata in option.display_metadata},
    )
