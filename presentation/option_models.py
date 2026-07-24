from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DisplayMetadata:
    label: str
    value: str


@dataclass(frozen=True)
class SourceInfo:
    source: str = ""
    raw_ref: str = ""


@dataclass(frozen=True)
class OptionGroupState:
    key: str
    label: str
    selected: bool
    availability_status: str
    eligibility_reasons: tuple[str, ...]
    selected_count: int
    selection_limit: int | None
    add_label: str = "Add"
    remove_label: str = "Remove"
    eligible: bool = False


@dataclass(frozen=True)
class OptionViewModel:
    stable_id: str
    kind: str
    name: str
    short_summary: str
    full_description: str
    display_metadata: tuple[DisplayMetadata, ...]
    selected: bool
    availability_status: str
    eligibility_reasons: tuple[str, ...]
    source: SourceInfo
    group_states: tuple[OptionGroupState, ...] = ()
    payload: tuple[tuple[str, Any], ...] = ()
