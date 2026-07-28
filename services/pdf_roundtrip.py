import hashlib
import hmac
import json
from datetime import datetime, timezone

from services.save_load import CURRENT_SCHEMA_VERSION, serialize_character


ATTACHMENT_NAME = "dnd-character-builder-state.json"
FORMAT_ID = "dnd-character-builder.character"
PAYLOAD_VERSION = 1
RULESET = "dnd-5e-2024"
BUILDER_VERSION = "1.3"
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024
MAX_JSON_DEPTH = 24
MAX_JSON_ITEMS = 50_000


class PdfRoundTripError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def canonical_json_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def character_checksum(character):
    return hashlib.sha256(canonical_json_bytes(character)).hexdigest()


def build_payload_envelope(character, owned_pdf_field_snapshot, *, exported_at=None):
    canonical_character_json = serialize_character(character)
    canonical_character = json.loads(canonical_character_json)
    snapshot = normalize_owned_field_snapshot(owned_pdf_field_snapshot)
    return {
        "format_id": FORMAT_ID,
        "payload_version": PAYLOAD_VERSION,
        "character_schema_version": canonical_character["schema_version"],
        "ruleset": RULESET,
        "builder_version": BUILDER_VERSION,
        "exported_at": exported_at or utc_timestamp(),
        "character_sha256": hashlib.sha256(
            canonical_character_json.encode("utf-8")
        ).hexdigest(),
        "character": canonical_character,
        "owned_pdf_field_snapshot": snapshot,
    }


def payload_envelope_bytes(character, owned_pdf_field_snapshot, *, exported_at=None):
    envelope = build_payload_envelope(
        character,
        owned_pdf_field_snapshot,
        exported_at=exported_at,
    )
    encoded = canonical_json_bytes(envelope)
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise PdfRoundTripError(
            "payload_too_large",
            "The builder character attachment is larger than the supported 2 MB limit.",
        )
    return encoded


def parse_payload_envelope(payload_bytes):
    if not isinstance(payload_bytes, bytes):
        raise PdfRoundTripError(
            "payload_invalid_type",
            "The builder character attachment is not a byte payload.",
        )
    if len(payload_bytes) > MAX_PAYLOAD_BYTES:
        raise PdfRoundTripError(
            "payload_too_large",
            "The builder character attachment is larger than the supported 2 MB limit.",
        )
    try:
        envelope = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PdfRoundTripError(
            "payload_malformed_json",
            "The embedded builder character attachment is not valid UTF-8 JSON.",
        ) from exc

    validate_json_shape(envelope)
    validate_payload_envelope(envelope)
    return envelope


def validate_payload_envelope(envelope):
    if not isinstance(envelope, dict):
        raise PdfRoundTripError(
            "payload_invalid_envelope",
            "The embedded builder character attachment must contain a JSON object.",
        )
    if envelope.get("format_id") != FORMAT_ID:
        raise PdfRoundTripError(
            "payload_unknown_format",
            "The embedded attachment is not a D&D Character Builder character payload.",
        )
    if envelope.get("payload_version") != PAYLOAD_VERSION:
        raise PdfRoundTripError(
            "payload_unsupported_version",
            "This builder character attachment uses an unsupported payload version.",
        )

    schema_version = envelope.get("character_schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise PdfRoundTripError(
            "payload_invalid_schema_version",
            "The builder character schema version must be an integer.",
        )
    if schema_version < 1 or schema_version > CURRENT_SCHEMA_VERSION:
        raise PdfRoundTripError(
            "payload_unsupported_schema",
            "This PDF contains a character schema newer than this builder supports.",
        )

    character = envelope.get("character")
    if not isinstance(character, dict):
        raise PdfRoundTripError(
            "payload_invalid_character",
            "The embedded builder character must be a JSON object.",
        )
    character_schema = character.get("schema_version", schema_version)
    if character_schema != schema_version:
        raise PdfRoundTripError(
            "payload_schema_mismatch",
            "The envelope and embedded character schema versions do not match.",
        )
    validate_character_basics(character)

    expected_checksum = envelope.get("character_sha256")
    if not isinstance(expected_checksum, str) or len(expected_checksum) != 64:
        raise PdfRoundTripError(
            "payload_invalid_checksum",
            "The embedded builder character checksum is missing or invalid.",
        )
    actual_checksum = character_checksum(character)
    if not hmac.compare_digest(expected_checksum.lower(), actual_checksum):
        raise PdfRoundTripError(
            "payload_checksum_mismatch",
            "The embedded builder character checksum does not match its contents.",
        )

    snapshot = envelope.get("owned_pdf_field_snapshot")
    if not isinstance(snapshot, dict):
        raise PdfRoundTripError(
            "payload_invalid_field_snapshot",
            "The builder-owned PDF field snapshot must be a JSON object.",
        )
    for field_name, value in snapshot.items():
        if not isinstance(field_name, str) or not isinstance(value, (str, int, float, bool)):
            raise PdfRoundTripError(
                "payload_invalid_field_snapshot",
                "The builder-owned PDF field snapshot contains an unsupported value.",
            )


def validate_character_basics(character):
    level = character.get("level", 1)
    if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 20:
        raise PdfRoundTripError(
            "payload_invalid_character_level",
            "The embedded builder character level must be an integer from 1 through 20.",
        )
    for key in ("character_id", "name", "class", "subclass", "species", "background"):
        if key in character and not isinstance(character[key], str):
            raise PdfRoundTripError(
                "payload_invalid_character",
                f"The embedded builder character field '{key}' must be text.",
            )
    for key in (
        "ability_scores",
        "base_ability_scores",
        "class_options",
        "species_options",
        "background_options",
        "spells",
    ):
        if key in character and not isinstance(character[key], dict):
            raise PdfRoundTripError(
                "payload_invalid_character",
                f"The embedded builder character field '{key}' must be an object.",
            )


def validate_json_shape(value, *, depth=0, counter=None):
    if counter is None:
        counter = [0]
    if depth > MAX_JSON_DEPTH:
        raise PdfRoundTripError(
            "payload_too_deep",
            "The embedded builder character contains too many nested levels.",
        )
    counter[0] += 1
    if counter[0] > MAX_JSON_ITEMS:
        raise PdfRoundTripError(
            "payload_too_complex",
            "The embedded builder character contains too many values.",
        )
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PdfRoundTripError(
                    "payload_invalid_key",
                    "The embedded builder character contains a non-text JSON key.",
                )
            validate_json_shape(item, depth=depth + 1, counter=counter)
    elif isinstance(value, list):
        for item in value:
            validate_json_shape(item, depth=depth + 1, counter=counter)
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise PdfRoundTripError(
            "payload_invalid_value",
            "The embedded builder character contains an unsupported JSON value.",
        )


def normalize_owned_field_snapshot(field_values):
    normalized = {}
    for field_name, value in (field_values or {}).items():
        if not isinstance(field_name, str):
            continue
        if isinstance(value, tuple):
            value = value[0] if value else ""
        if value is None:
            value = ""
        if isinstance(value, (str, int, float, bool)):
            normalized[field_name] = value
        else:
            normalized[field_name] = str(value)
    return normalized


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
