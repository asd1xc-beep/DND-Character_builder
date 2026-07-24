from collections.abc import Iterable

from presentation.option_catalog import short_summary
from presentation.option_models import DisplayMetadata, OptionViewModel, SourceInfo


MISSING_EQUIPMENT_DESCRIPTION = "No equipment description is available in the imported source data."


def build_equipment_catalog(
    equipment_names: Iterable[str],
    custom_equipment: Iterable[str],
    package_equipment: Iterable[str] = (),
) -> tuple[OptionViewModel, ...]:
    custom = {str(item) for item in custom_equipment or () if item}
    package = {str(item) for item in package_equipment or () if item}
    names = _merge_names(equipment_names, custom, package)
    return tuple(
        _equipment_option(name, selected=name in custom, package_included=name in package)
        for name in names
    )


def equipment_stable_id(name: str) -> str:
    return f"equipment:{str(name or '').strip().casefold()}"


def option_value(option: OptionViewModel) -> str:
    return str(dict(option.payload).get("value", option.name))


def _equipment_option(name: str, *, selected: bool, package_included: bool) -> OptionViewModel:
    if selected:
        status = "selected"
        reasons = ("Included as custom equipment.",)
    elif package_included:
        status = "unavailable"
        reasons = ("Already included by selected default equipment.",)
    else:
        status = "available"
        reasons = ("Available to add as custom equipment.",)
    provenance = []
    if package_included:
        provenance.append("Default package")
    if selected:
        provenance.append("Custom")
    return OptionViewModel(
        stable_id=equipment_stable_id(name),
        kind="equipment",
        name=name,
        short_summary=short_summary(MISSING_EQUIPMENT_DESCRIPTION),
        full_description=MISSING_EQUIPMENT_DESCRIPTION,
        display_metadata=(
            DisplayMetadata("Category", "Unavailable in source data"),
            DisplayMetadata("Provenance", ", ".join(provenance) if provenance else "Not selected"),
        ),
        selected=selected,
        availability_status=status,
        eligibility_reasons=reasons,
        source=SourceInfo(source="Imported equipment list"),
        payload=(
            ("value", name),
            ("package_included", package_included),
        ),
    )


def _merge_names(
    equipment_names: Iterable[str],
    custom: set[str],
    package: set[str],
) -> tuple[str, ...]:
    seen = set()
    names = []
    for item in [*(equipment_names or ()), *sorted(custom), *sorted(package)]:
        name = str(item or "").strip()
        if name and name not in seen:
            names.append(name)
            seen.add(name)
    return tuple(sorted(names))
