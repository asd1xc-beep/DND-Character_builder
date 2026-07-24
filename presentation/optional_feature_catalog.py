from collections.abc import Iterable, Mapping

from presentation.option_catalog import full_selection_reason, short_summary
from presentation.option_models import DisplayMetadata, OptionViewModel, SourceInfo


MISSING_OPTIONAL_FEATURE_DESCRIPTION = "No optional-feature description is available in the imported source data."


def build_optional_feature_catalog(
    records: Iterable[Mapping],
    *,
    selected_names: Iterable[str],
    selection_limit: int,
    kind: str,
    existing_names: Iterable[str] = (),
) -> tuple[OptionViewModel, ...]:
    selected = [name for name in selected_names or [] if name]
    selected_set = set(selected)
    existing = set(existing_names or [])
    full = bool(selection_limit) and len(selected) >= selection_limit
    return tuple(
        _optional_feature_option(
            record,
            selected=str(record.get("name") or "") in selected_set,
            existing=str(record.get("name") or "") in existing,
            full=full,
            selected_count=len(selected),
            selection_limit=selection_limit,
            kind=kind,
        )
        for record in sorted(records or [], key=lambda item: str(item.get("name") or ""))
        if record.get("name")
    )


def optional_feature_stable_id(kind: str, name: str) -> str:
    return f"{kind}:{str(name or '').strip().casefold()}"


def option_value(option: OptionViewModel) -> str:
    return str(dict(option.payload).get("value", option.name))


def _optional_feature_option(
    record: Mapping,
    *,
    selected: bool,
    existing: bool,
    full: bool,
    selected_count: int,
    selection_limit: int,
    kind: str,
) -> OptionViewModel:
    name = str(record.get("name") or "")
    eligible = bool(record.get("eligible", True))
    description = str(record.get("description") or MISSING_OPTIONAL_FEATURE_DESCRIPTION)
    status, reasons = _status(
        record,
        selected=selected,
        existing=existing,
        eligible=eligible,
        full=full,
        selected_count=selected_count,
        selection_limit=selection_limit,
    )
    metadata = {
        "Category": str(record.get("category") or kind.replace("_", " ").title()),
    }
    prerequisites = "; ".join(str(item) for item in record.get("prerequisite_labels", []) if item)
    if prerequisites:
        metadata["Prerequisites"] = prerequisites
    support = record.get("support") if isinstance(record.get("support"), Mapping) else {}
    if support.get("notes"):
        metadata["Support notes"] = str(support.get("notes"))
    return OptionViewModel(
        stable_id=optional_feature_stable_id(kind, name),
        kind=kind,
        name=name,
        short_summary=short_summary(description),
        full_description=description,
        display_metadata=tuple(DisplayMetadata(label, value) for label, value in metadata.items() if value),
        selected=selected,
        availability_status=status,
        eligibility_reasons=tuple(reasons),
        source=SourceInfo(source=str(record.get("source") or "XPHB"), raw_ref=str(record.get("raw_ref") or name)),
        payload=(
            ("value", name),
            ("category", metadata["Category"]),
            ("eligible", eligible),
        ),
    )


def _status(
    record: Mapping,
    *,
    selected: bool,
    existing: bool,
    eligible: bool,
    full: bool,
    selected_count: int,
    selection_limit: int,
) -> tuple[str, tuple[str, ...]]:
    if selected:
        return "selected", ("Already selected.",)
    if existing:
        return "unavailable", ("Already selected for this character.",)
    if not eligible:
        return "unavailable", tuple(record.get("eligibility_reasons") or ("Prerequisites are not met.",))
    if full:
        return "unavailable", (full_selection_reason(selected_count, selection_limit),)
    return "available", ("Available for this choice.",)
