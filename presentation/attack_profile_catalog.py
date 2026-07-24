from collections.abc import Iterable, Mapping

from presentation.option_models import DisplayMetadata, OptionViewModel, SourceInfo


def build_attack_profile_catalog(
    profiles: Iterable[Mapping],
    *,
    selected_name: str = "",
    kind: str = "attack_profile",
) -> tuple[OptionViewModel, ...]:
    return tuple(
        OptionViewModel(
            stable_id=attack_profile_stable_id(profile.get("kind", kind), profile.get("name", "")),
            kind=str(profile.get("kind") or kind),
            name=str(profile.get("name") or ""),
            short_summary=_summary(profile),
            full_description=_summary(profile),
            display_metadata=(
                DisplayMetadata("Attack", str(profile.get("attack_display") or "")),
                DisplayMetadata("Damage", str(profile.get("damage_display") or "")),
            ),
            selected=str(profile.get("name") or "") == selected_name,
            availability_status="selected" if str(profile.get("name") or "") == selected_name else "available",
            eligibility_reasons=("Selected for PDF export.",) if str(profile.get("name") or "") == selected_name else ("Available for PDF export.",),
            source=SourceInfo(source="calculated", raw_ref=str(profile.get("kind") or kind)),
            payload=(
                ("value", str(profile.get("name") or "")),
                ("attack_display", str(profile.get("attack_display") or "")),
                ("damage_display", str(profile.get("damage_display") or "")),
            ),
        )
        for profile in profiles or []
        if profile.get("name")
    )


def attack_profile_stable_id(kind: str, name: str) -> str:
    return f"{str(kind or 'attack_profile').casefold()}:{str(name or '').strip().casefold()}"


def _summary(profile: Mapping) -> str:
    attack = str(profile.get("attack_display") or "")
    damage = str(profile.get("damage_display") or "")
    parts = [part for part in (attack, damage) if part]
    return " | ".join(parts)
