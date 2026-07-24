from collections.abc import Iterable, Mapping

from presentation.option_catalog import short_summary
from presentation.option_models import DisplayMetadata, OptionViewModel, SourceInfo


def build_feat_catalog(
    feats: Iterable[Mapping],
    *,
    selected_feat_id: str = "",
) -> tuple[OptionViewModel, ...]:
    return tuple(
        _feat_option(feat, selected=str(feat.get("id") or "") == selected_feat_id)
        for feat in sorted(feats or [], key=lambda item: str(item.get("name") or ""))
        if feat.get("name")
    )


def feat_stable_id(feat_id: str) -> str:
    return f"feat:{str(feat_id or '').strip().casefold()}"


def option_value(option: OptionViewModel) -> str:
    return str(dict(option.payload).get("value", option.stable_id))


def _feat_option(feat: Mapping, *, selected: bool) -> OptionViewModel:
    eligible = bool(feat.get("eligible", True))
    supported = bool(feat.get("supported", True))
    if selected:
        status = "selected"
        reasons = ("Already selected.",)
    elif not eligible:
        status = "unavailable"
        reasons = tuple(feat.get("eligibility_reasons") or ("This character does not meet this feat's prerequisites.",))
    elif not supported:
        status = "unavailable"
        reasons = tuple(feat.get("eligibility_reasons") or ("This feat is not fully supported yet.",))
    else:
        status = "available"
        reasons = ("Available for this choice.",)
    description = str(feat.get("description") or "")
    support = feat.get("support") if isinstance(feat.get("support"), Mapping) else {}
    support_notes = support.get("notes", [])
    if isinstance(support_notes, str):
        support_notes = [support_notes] if support_notes else []
    return OptionViewModel(
        stable_id=feat_stable_id(str(feat.get("id") or "")),
        kind="feat",
        name=str(feat.get("name") or ""),
        short_summary=short_summary(description),
        full_description=description,
        display_metadata=(
            DisplayMetadata("Category", _category_label(feat.get("category", ""))),
            DisplayMetadata("Ability increase", _ability_increase_label(feat.get("ability_increase", {}))),
            DisplayMetadata("Choice support", str(support.get("selection") or "supported")),
            DisplayMetadata("Notes", "; ".join(str(note) for note in support_notes if note)),
        ),
        selected=selected,
        availability_status=status,
        eligibility_reasons=reasons,
        source=SourceInfo(source=str(feat.get("source") or "XPHB"), raw_ref=str(feat.get("raw_ref") or feat.get("id") or "")),
        payload=(
            ("value", str(feat.get("id") or "")),
            ("category", _category_label(feat.get("category", ""))),
            ("choice_support", str(support.get("selection") or "supported")),
        ),
    )


def _category_label(category: str) -> str:
    return str(category or "Unknown").replace("_", " ").title()


def _ability_increase_label(ability_increase) -> str:
    if not isinstance(ability_increase, Mapping) or not ability_increase:
        return "None"
    mode = ability_increase.get("mode")
    amount = ability_increase.get("amount", 1)
    options = ", ".join(str(item) for item in ability_increase.get("from", []) if item)
    if mode == "fixed":
        return f"{options} +{amount}" if options else f"+{amount}"
    if mode == "choose":
        return f"Choose +{amount}: {options}" if options else f"Choose +{amount}"
    return str(ability_increase)
