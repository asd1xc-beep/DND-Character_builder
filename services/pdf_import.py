import hashlib
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from io import BytesIO

from pypdf import PdfReader

from services.pdf_export import WOTC_SLOT_FIELDS, WOTC_SPELL_FIELDS, WOTC_TEMPLATE
from services.pdf_passthrough import (
    SAFE_PASSTHROUGH_FIELDS,
    UNSAFE_PASSTHROUGH_FIELDS,
)
from services.pdf_roundtrip import (
    ATTACHMENT_NAME,
    MAX_PAYLOAD_BYTES,
    PdfRoundTripError,
    parse_payload_envelope,
)
from services.save_load import CURRENT_SCHEMA_VERSION, migrate_character


MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_FORM_FIELDS = 1_000
MAX_FIELD_NAME_LENGTH = 256
MAX_FIELD_VALUE_LENGTH = 100_000
MAX_TOTAL_FORM_TEXT = 2 * 1024 * 1024
COMPATIBLE_FIELD_OVERLAP = 0.80

REQUIRED_CORE_FIELDS = {
    "CharacterName",
    "ClassLevel",
    "Race ",
    "Background",
    "STR",
    "DEX",
    "CON",
    "INT",
    "WIS",
    "CHA",
    "HPMax",
}

ABILITY_FIELDS = {
    "Strength": "STR",
    "Dexterity": "DEX",
    "Constitution": "CON",
    "Intelligence": "INT",
    "Wisdom": "WIS",
    "Charisma": "CHA",
}

ABILITY_MODIFIER_FIELDS = {
    "Strength": "STRmod",
    "Dexterity": "DEXmod ",
    "Constitution": "CONmod",
    "Intelligence": "INTmod",
    "Wisdom": "WISmod",
    "Charisma": "CHamod",
}

SAVING_THROW_FIELDS = {
    "Strength": "ST Strength",
    "Dexterity": "ST Dexterity",
    "Constitution": "ST Constitution",
    "Intelligence": "ST Intelligence",
    "Wisdom": "ST Wisdom",
    "Charisma": "ST Charisma",
}

SKILL_FIELDS = {
    "Acrobatics": "Acrobatics",
    "Animal Handling": "Animal",
    "Arcana": "Arcana",
    "Athletics": "Athletics",
    "Deception": "Deception ",
    "History": "History ",
    "Insight": "Insight",
    "Intimidation": "Intimidation",
    "Investigation": "Investigation ",
    "Medicine": "Medicine",
    "Nature": "Nature",
    "Perception": "Perception ",
    "Performance": "Performance",
    "Persuasion": "Persuasion",
    "Religion": "Religion",
    "Sleight of Hand": "SleightofHand",
    "Stealth": "Stealth ",
    "Survival": "Survival",
}

ATTACK_FIELDS = (
    ("Wpn Name", "Wpn1 AtkBonus", "Wpn1 Damage"),
    ("Wpn Name 2", "Wpn2 AtkBonus ", "Wpn2 Damage "),
    ("Wpn Name 3", "Wpn3 AtkBonus  ", "Wpn3 Damage "),
)

BUILDER_OWNED_FIELDS = {
    "CharacterName",
    "CharacterName 2",
    "ClassLevel",
    "Background",
    "Race ",
    "XP",
    "ProfBonus",
    "AC",
    "Initiative",
    "Speed",
    "HPMax",
    "HPCurrent",
    "HDTotal",
    "HD",
    "Passive",
    "ProficienciesLang",
    "Equipment",
    "Features and Traits",
    "Feat+Traits",
    "AttacksSpellcasting",
    "Spellcasting Class 2",
    "SpellcastingAbility 2",
    *ABILITY_FIELDS.values(),
    *ABILITY_MODIFIER_FIELDS.values(),
    *SAVING_THROW_FIELDS.values(),
    *SKILL_FIELDS.values(),
    *(field for row in ATTACK_FIELDS for field in row),
    *(f"SlotsTotal {suffix}" for suffix in WOTC_SLOT_FIELDS.values()),
    *(f"SlotsRemaining {suffix}" for suffix in WOTC_SLOT_FIELDS.values()),
    *(field for fields in WOTC_SPELL_FIELDS.values() for field in fields),
}


@dataclass(frozen=True)
class PdfImportIssue:
    code: str
    severity: str
    section: str
    label: str
    observed: object = ""
    expected: object = ""
    remedy: str = ""


@dataclass
class PdfImportResult:
    status: str
    source_kind: str
    candidate_character: dict = field(default_factory=dict)
    observed_fields: dict = field(default_factory=dict)
    passthrough_fields: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)
    payload_info: dict = field(default_factory=dict)
    extracted_data: dict = field(default_factory=dict)

    def to_dict(self):
        result = asdict(self)
        result["issues"] = [
            asdict(issue) if isinstance(issue, PdfImportIssue) else deepcopy(issue)
            for issue in self.issues
        ]
        return result


class PdfFormError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def parse_pdf_import(pdf_bytes, data=None):
    """Parse a PDF into detached embedded-state or compatible-form evidence."""
    if not isinstance(pdf_bytes, bytes):
        return error_result(
            "pdf_invalid_type",
            "Choose a PDF file to import.",
        )
    if len(pdf_bytes) > MAX_PDF_BYTES:
        return error_result(
            "pdf_too_large",
            "The PDF is larger than the supported 20 MB import limit.",
        )
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        if reader.is_encrypted and not reader.decrypt(""):
            return error_result(
                "pdf_encrypted",
                "This PDF is encrypted and cannot be opened without a password.",
            )
        payload_bytes = builder_attachment_bytes(reader)
        if payload_bytes is not None:
            try:
                return parse_embedded_state(reader, payload_bytes)
            except PdfRoundTripError as exc:
                return error_result(exc.code, exc.message, source_kind="embedded_state")
        return parse_compatible_form(reader, data=data)
    except PdfFormError as exc:
        return error_result(exc.code, exc.message)
    except Exception as exc:
        return error_result(
            "pdf_unreadable",
            f"The PDF could not be read safely: {type(exc).__name__}.",
        )


def parse_embedded_state(reader, payload_bytes):
    envelope = parse_payload_envelope(payload_bytes)
    candidate = migrate_character(deepcopy(envelope["character"]))
    snapshot = envelope["owned_pdf_field_snapshot"]
    observed = observed_owned_fields(reader, snapshot)
    changed_fields = {
        field_name: {
            "exported": snapshot[field_name],
            "observed": observed.get(field_name, ""),
        }
        for field_name in snapshot
        if normalize_scalar(observed.get(field_name, "")) != normalize_scalar(snapshot[field_name])
    }

    issues = []
    if envelope["character_schema_version"] < CURRENT_SCHEMA_VERSION:
        issues.append(PdfImportIssue(
            code="character_schema_migrated",
            severity="info",
            section="character",
            label="The embedded character was migrated to the current schema.",
            observed=envelope["character_schema_version"],
            expected=CURRENT_SCHEMA_VERSION,
            remedy="Review the migration warnings before opening the character.",
        ))
    if changed_fields:
        issues.append(PdfImportIssue(
            code="builder_owned_fields_changed",
            severity="warning",
            section="visible_pdf",
            label="Builder-owned visible PDF fields changed after export.",
            observed=changed_fields,
            expected="Values matching the embedded export snapshot",
            remedy=(
                "Use the embedded builder state for a lossless import. "
                "Visible-field reconciliation is reserved for a later phase."
            ),
        ))

    return PdfImportResult(
        status="review_required" if changed_fields else "ready",
        source_kind="embedded_state",
        candidate_character=candidate,
        observed_fields=observed,
        passthrough_fields={},
        issues=issues,
        payload_info={
            "payload_version": envelope["payload_version"],
            "character_schema_version": envelope["character_schema_version"],
            "builder_version": envelope.get("builder_version", ""),
            "ruleset": envelope.get("ruleset", ""),
            "exported_at": envelope.get("exported_at", ""),
            "changed_fields": changed_fields,
        },
    )


def parse_compatible_form(reader, data=None):
    fields = reader.get_fields() or {}
    template = classify_form_template(reader, fields)
    if template["match"] == "flattened":
        return PdfImportResult(
            status="unsupported",
            source_kind="flattened",
            issues=[PdfImportIssue(
                code="flattened_pdf",
                severity="blocker",
                section="source",
                label="This PDF has pages but no usable editable form fields.",
                expected="An editable builder-compatible character sheet",
                remedy="Import the original editable PDF instead of a printed, scanned, or flattened copy.",
            )],
            payload_info=template,
        )
    if template["match"] == "unsupported":
        return PdfImportResult(
            status="unsupported",
            source_kind="other",
            issues=[PdfImportIssue(
                code="unsupported_template",
                severity="blocker",
                section="source",
                label="The editable PDF does not match the supported character-sheet layout.",
                observed={
                    "known_field_ratio": template["known_field_ratio"],
                    "missing_core_fields": template["missing_core_fields"],
                },
                expected=sorted(REQUIRED_CORE_FIELDS),
                remedy="Choose an editable PDF based on the builder's supported WotC-style template.",
            )],
            payload_info=template,
        )

    observed, normalization_issues = normalize_form_fields(fields)
    extracted = extract_form_evidence(observed)
    issues = list(normalization_issues)
    issues.extend(build_form_evidence_issues(extracted))
    issues.extend(build_catalog_evidence_issues(extracted, data))
    if template["match"] == "compatible":
        issues.insert(0, PdfImportIssue(
            code="compatible_template_signature",
            severity="info",
            section="source",
            label="The PDF is compatible with the supported template but its field signature differs.",
            observed=template["signature"],
            expected=template["reference_signature"],
            remedy="Review all recovered evidence before creating a working character.",
        ))

    return PdfImportResult(
        status="review_required",
        source_kind="compatible_form",
        candidate_character={},
        observed_fields=observed,
        passthrough_fields=extract_safe_passthrough_fields(observed),
        issues=issues,
        payload_info=template,
        extracted_data=extracted,
    )


def builder_attachment_bytes(reader):
    attachments = reader.attachments
    payloads = attachments.get(ATTACHMENT_NAME, [])
    if isinstance(payloads, bytes):
        payloads = [payloads]
    if not payloads:
        return None
    if len(payloads) != 1:
        raise PdfRoundTripError(
            "payload_attachment_ambiguous",
            "The PDF contains more than one builder character attachment.",
        )
    payload = payloads[0]
    if not isinstance(payload, bytes):
        raise PdfRoundTripError(
            "payload_invalid_type",
            "The builder character attachment is not a byte payload.",
        )
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise PdfRoundTripError(
            "payload_too_large",
            "The builder character attachment is larger than the supported 2 MB limit.",
        )
    return payload


def classify_form_template(reader, fields=None):
    fields = fields if fields is not None else (reader.get_fields() or {})
    field_names = {
        str(field_name)
        for field_name in fields
        if isinstance(field_name, str) and field_name
    }
    reference_names = reference_template_field_names()
    signature = field_name_signature(field_names)
    reference_signature = field_name_signature(reference_names)
    missing_core = sorted(REQUIRED_CORE_FIELDS - field_names)
    known_count = len(field_names & reference_names)
    known_ratio = known_count / len(reference_names) if reference_names else 0.0

    if not field_names:
        match = "flattened" if len(reader.pages) else "unsupported"
    elif signature == reference_signature:
        match = "exact"
    elif not missing_core and known_ratio >= COMPATIBLE_FIELD_OVERLAP:
        match = "compatible"
    else:
        match = "unsupported"
    return {
        "match": match,
        "signature": signature,
        "reference_signature": reference_signature,
        "field_count": len(field_names),
        "reference_field_count": len(reference_names),
        "known_field_count": known_count,
        "known_field_ratio": round(known_ratio, 4),
        "missing_core_fields": missing_core,
    }


@lru_cache(maxsize=1)
def reference_template_field_names():
    if not WOTC_TEMPLATE.exists():
        raise PdfFormError(
            "reference_template_missing",
            "The supported editable PDF template is missing from this builder installation.",
        )
    reader = PdfReader(str(WOTC_TEMPLATE))
    return frozenset(str(name) for name in (reader.get_fields() or {}))


def field_name_signature(field_names):
    encoded = "\n".join(sorted(set(field_names or []))).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalize_form_fields(fields):
    if len(fields) > MAX_FORM_FIELDS:
        raise PdfFormError(
            "form_too_many_fields",
            f"The PDF contains more than the supported {MAX_FORM_FIELDS} form fields.",
        )
    observed = {}
    issues = []
    total_text = 0
    for field_name, field in fields.items():
        if not isinstance(field_name, str) or not field_name:
            issues.append(PdfImportIssue(
                code="form_field_invalid_name",
                severity="warning",
                section="source",
                label="A form field with an invalid name was ignored.",
                remedy="Review the original PDF for damaged form fields.",
            ))
            continue
        if len(field_name) > MAX_FIELD_NAME_LENGTH:
            issues.append(PdfImportIssue(
                code="form_field_name_too_long",
                severity="warning",
                section="source",
                label="A form field with an excessively long name was ignored.",
                observed=field_name[:80],
                expected=f"At most {MAX_FIELD_NAME_LENGTH} characters",
                remedy="Review the original PDF for damaged form fields.",
            ))
            continue
        field_type = str(field.get("/FT", ""))
        raw_value = field.get("/V", "")
        try:
            value = normalize_form_value(raw_value, field_type)
        except PdfFormError as exc:
            issues.append(PdfImportIssue(
                code=exc.code,
                severity="warning",
                section="source",
                label=exc.message,
                observed=field_name,
                remedy="Review this field manually during reconciliation.",
            ))
            continue
        value_size = len(value.encode("utf-8")) if isinstance(value, str) else 1
        total_text += value_size
        if value_size > MAX_FIELD_VALUE_LENGTH:
            issues.append(PdfImportIssue(
                code="form_field_value_too_long",
                severity="warning",
                section="source",
                label=f"The value in '{field_name}' is too long and was ignored.",
                expected=f"At most {MAX_FIELD_VALUE_LENGTH} UTF-8 bytes",
                remedy="Shorten the field in the editable PDF and import it again.",
            ))
            continue
        if total_text > MAX_TOTAL_FORM_TEXT:
            raise PdfFormError(
                "form_values_too_large",
                "The PDF form values exceed the supported 2 MB text limit.",
            )
        observed[field_name] = value
    return observed, issues


def normalize_form_value(value, field_type=""):
    if field_type == "/Btn":
        return normalize_checkbox_value(value)
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return normalize_text(value)
    raise PdfFormError(
        "form_field_unsupported_value",
        "A form field contains a complex value that cannot be imported safely.",
    )


def normalize_checkbox_value(value):
    if value is None or str(value).strip().lower() in {"", "/off", "off", "false", "0", "no"}:
        return False
    if isinstance(value, (str, bool, int, float)):
        return True
    raise PdfFormError(
        "form_field_unsupported_value",
        "A checkbox contains a complex value that cannot be imported safely.",
    )


def normalize_text(value):
    text = str(value).replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def extract_form_evidence(observed):
    class_name, level = parse_class_level(text_value(observed, "ClassLevel"))
    return {
        "identity": {
            "name": text_value(observed, "CharacterName"),
            "alternate_name": text_value(observed, "CharacterName 2"),
            "class_level": text_value(observed, "ClassLevel"),
            "class_name": class_name,
            "level": level,
            "species": text_value(observed, "Race "),
            "background": text_value(observed, "Background"),
        },
        "abilities": {
            ability: integer_value(observed.get(field_name))
            for ability, field_name in ABILITY_FIELDS.items()
        },
        "hit_points": {
            "maximum": integer_value(observed.get("HPMax")),
            "current": integer_value(observed.get("HPCurrent")),
            "temporary": integer_value(observed.get("HPTemp")),
            "hit_die": text_value(observed, "HD"),
            "hit_dice_total": text_value(observed, "HDTotal"),
        },
        "spells": {
            "by_level": {
                level: [
                    text_value(observed, field_name)
                    for field_name in field_names
                    if text_value(observed, field_name)
                ]
                for level, field_names in WOTC_SPELL_FIELDS.items()
            },
            "slot_totals": {
                level: integer_value(observed.get(f"SlotsTotal {suffix}"))
                for level, suffix in WOTC_SLOT_FIELDS.items()
            },
            "slot_remaining": {
                level: integer_value(observed.get(f"SlotsRemaining {suffix}"))
                for level, suffix in WOTC_SLOT_FIELDS.items()
            },
            "spellcasting_class": text_value(observed, "Spellcasting Class 2"),
            "spellcasting_ability": text_value(observed, "SpellcastingAbility 2"),
            "spell_save_dc": integer_value(observed.get("SpellSaveDC  2")),
            "spell_attack_bonus": text_value(observed, "SpellAtkBonus 2"),
        },
        "equipment": {
            "raw": text_value(observed, "Equipment"),
        },
        "presentation": {
            "attacks": [
                {
                    "name": text_value(observed, name_field),
                    "attack_bonus": text_value(observed, attack_field),
                    "damage": text_value(observed, damage_field),
                }
                for name_field, attack_field, damage_field in ATTACK_FIELDS
            ],
            "features": text_value(observed, "Features and Traits"),
            "additional_features": text_value(observed, "Feat+Traits"),
            "proficiencies_and_languages": text_value(observed, "ProficienciesLang"),
        },
        "comparison": {
            "armor_class": integer_value(observed.get("AC")),
            "initiative": text_value(observed, "Initiative"),
            "proficiency_bonus": text_value(observed, "ProfBonus"),
            "passive_perception": integer_value(observed.get("Passive")),
            "ability_modifiers": {
                ability: text_value(observed, field_name)
                for ability, field_name in ABILITY_MODIFIER_FIELDS.items()
            },
            "saving_throws": {
                ability: text_value(observed, field_name)
                for ability, field_name in SAVING_THROW_FIELDS.items()
            },
            "skills": {
                skill: text_value(observed, field_name)
                for skill, field_name in SKILL_FIELDS.items()
            },
        },
    }


def build_form_evidence_issues(extracted):
    issues = []
    identity = extracted["identity"]
    required_identity = {
        "name": ("character_name_missing", "Character name"),
        "class_level": ("class_level_missing", "Class and level"),
        "species": ("species_missing", "Species"),
        "background": ("background_missing", "Background"),
    }
    for key, (code, label) in required_identity.items():
        if not identity.get(key):
            issues.append(PdfImportIssue(
                code=code,
                severity="blocker",
                section="identity",
                label=f"{label} is missing from the PDF.",
                expected=label,
                remedy=f"Confirm the character's {label.lower()} during reconciliation.",
            ))
    if (
        identity.get("name")
        and identity.get("alternate_name")
        and identity["name"] != identity["alternate_name"]
    ):
        issues.append(PdfImportIssue(
            code="character_name_conflict",
            severity="warning",
            section="identity",
            label="The two character-name fields do not match.",
            observed={
                "CharacterName": identity["name"],
                "CharacterName 2": identity["alternate_name"],
            },
            expected="Matching character names",
            remedy="Choose the intended character name during reconciliation.",
        ))

    for ability, value in extracted["abilities"].items():
        if value is None:
            issues.append(PdfImportIssue(
                code="ability_score_missing_or_invalid",
                severity="blocker",
                section="abilities",
                label=f"{ability} score is missing or invalid.",
                expected="A whole-number ability score",
                remedy=f"Confirm the character's {ability} score during reconciliation.",
            ))

    if extracted["hit_points"]["maximum"] is None:
        issues.append(PdfImportIssue(
            code="maximum_hp_missing_or_invalid",
            severity="blocker",
            section="hit_points",
            label="Maximum hit points are missing or invalid.",
            expected="A whole-number maximum HP value",
            remedy="Confirm maximum HP during reconciliation.",
        ))
    return issues


def build_catalog_evidence_issues(extracted, data):
    issues = []
    identity = extracted["identity"]
    class_level = identity.get("class_level", "")
    if class_level:
        if looks_multiclass(class_level):
            issues.append(PdfImportIssue(
                code="multiclass_unsupported",
                severity="blocker",
                section="identity",
                label="The class and level field appears to contain more than one class.",
                observed=class_level,
                expected="One supported class and a level from 1 through 20",
                remedy="This builder currently supports single-class characters only.",
            ))
        elif not identity.get("class_name") or identity.get("level") is None:
            issues.append(PdfImportIssue(
                code="class_level_unrecognized",
                severity="blocker",
                section="identity",
                label="The class and level field could not be parsed safely.",
                observed=class_level,
                expected="A class name followed by a level, such as Fighter 5",
                remedy="Confirm the class and current level during reconciliation.",
            ))
        elif not 1 <= identity["level"] <= 20:
            issues.append(PdfImportIssue(
                code="character_level_out_of_range",
                severity="blocker",
                section="identity",
                label="The character level is outside the supported range.",
                observed=identity["level"],
                expected="A level from 1 through 20",
                remedy="Confirm the current character level during reconciliation.",
            ))

    if not data:
        return issues

    catalog_checks = (
        (
            "class",
            identity.get("class_name", ""),
            data.get("classes", []),
            "class_choices",
        ),
        (
            "species",
            identity.get("species", ""),
            data.get("species", []),
            "identity",
        ),
        (
            "background",
            identity.get("background", ""),
            data.get("backgrounds", []),
            "identity",
        ),
    )
    for label, observed, catalog, section in catalog_checks:
        if not observed:
            continue
        matches = exact_catalog_matches(observed, catalog)
        if not matches:
            issues.append(PdfImportIssue(
                code=f"{label}_unknown",
                severity="blocker",
                section=section,
                label=f"The PDF {label} does not exactly match the active catalog.",
                observed=observed,
                expected=f"One supported {label}",
                remedy=f"Choose the intended supported {label} during reconciliation.",
            ))
        elif len(matches) > 1:
            issues.append(PdfImportIssue(
                code=f"{label}_ambiguous",
                severity="blocker",
                section=section,
                label=f"The PDF {label} matches more than one active catalog entry.",
                observed=observed,
                expected=matches,
                remedy=f"Choose the intended {label} during reconciliation.",
            ))

    spell_catalog = data.get("spells", [])
    spell_names = [
        spell_name
        for spells in extracted["spells"]["by_level"].values()
        for spell_name in spells
    ]
    for spell_name in spell_names:
        matches = exact_catalog_matches(spell_name, spell_catalog)
        if not matches:
            issues.append(PdfImportIssue(
                code="spell_unknown",
                severity="blocker",
                section="spells",
                label="A PDF spell does not exactly match the active spell catalog.",
                observed=spell_name,
                expected="One supported spell name",
                remedy="Choose the intended spell or remove the unmatched entry during reconciliation.",
            ))
        elif len(matches) > 1:
            issues.append(PdfImportIssue(
                code="spell_ambiguous",
                severity="blocker",
                section="spells",
                label="A PDF spell matches more than one active catalog entry.",
                observed=spell_name,
                expected=matches,
                remedy="Choose the intended spell during reconciliation.",
            ))
    return issues


def extract_safe_passthrough_fields(observed):
    return {
        field_name: value
        for field_name, value in observed.items()
        if (
            field_name in SAFE_PASSTHROUGH_FIELDS
            or (
                isinstance(value, bool)
                and value is True
                and field_name not in UNSAFE_PASSTHROUGH_FIELDS
            )
        )
        and field_name not in BUILDER_OWNED_FIELDS
        and value not in ("", False, None)
        and isinstance(value, (str, int, float, bool))
    }


def parse_class_level(value):
    text = normalize_text(value)
    if not text or looks_multiclass(text):
        return "", None
    match = re.fullmatch(r"(.+?\S)\s+(\d{1,3})", text)
    if not match:
        return "", None
    return match.group(1), int(match.group(2))


def looks_multiclass(value):
    text = normalize_text(value)
    return any(separator in text for separator in ("/", ",", "&", "+"))


def exact_catalog_matches(observed, catalog):
    normalized = normalize_text(observed).casefold()
    return [
        str(entry.get("name", ""))
        for entry in catalog or []
        if isinstance(entry, dict)
        and str(entry.get("name", "")).casefold() == normalized
    ]


def text_value(observed, field_name):
    value = observed.get(field_name, "")
    if isinstance(value, bool):
        return ""
    return normalize_text(value) if value is not None else ""


def integer_value(value):
    if isinstance(value, bool) or value is None:
        return None
    text = normalize_text(value)
    if not re.fullmatch(r"[+-]?\d+", text):
        return None
    return int(text)


def observed_owned_fields(reader, snapshot):
    fields = reader.get_fields() or {}
    observed = {}
    for field_name in snapshot:
        field = fields.get(field_name, {})
        observed[field_name] = normalize_scalar(field.get("/V", ""))
    return observed


def normalize_scalar(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, int, float)):
        return value
    return str(value)


def error_result(code, message, *, source_kind="other"):
    return PdfImportResult(
        status="error",
        source_kind=source_kind,
        issues=[PdfImportIssue(
            code=code,
            severity="blocker",
            section="source",
            label=message,
            remedy="Export the character again or choose an unmodified supported builder PDF.",
        )],
    )
