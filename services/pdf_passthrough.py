SAFE_PASSTHROUGH_FIELDS = {
    "Age",
    "Alignment",
    "Allies",
    "Backstory",
    "Bonds",
    "CP",
    "EP",
    "Eyes",
    "FactionName",
    "Flaws",
    "GP",
    "Hair",
    "Height",
    "Ideals",
    "Inspiration",
    "PersonalityTraits ",
    "PlayerName",
    "PP",
    "Skin",
    "SP",
    "Treasure",
    "Weight",
}

UNSAFE_PASSTHROUGH_FIELDS = {
    "CHARACTER IMAGE",
    "Faction Symbol Image",
}


def normalize_pdf_passthrough_fields(values):
    """Keep only supported scalar fields that are safe to reapply to a PDF."""
    normalized = {}
    for field_name, value in (values or {}).items():
        if not isinstance(field_name, str):
            continue
        if (
            field_name not in SAFE_PASSTHROUGH_FIELDS
            and not (
                field_name.startswith("Check Box ")
                and field_name not in UNSAFE_PASSTHROUGH_FIELDS
            )
        ):
            continue
        if isinstance(value, bool):
            normalized[field_name] = value
        elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
            normalized[field_name] = str(value)
    return normalized
