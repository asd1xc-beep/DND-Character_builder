from collections import defaultdict
from dataclasses import asdict, is_dataclass

from rules.import_reconciliation import RECONCILIATION_SECTIONS


SECTION_LABELS = {
    "identity": "Identity and level",
    "abilities": "Ability-score baseline and background bonuses",
    "class_choices": "Subclass and class choices",
    "proficiencies": "Skills, expertise, feats, and masteries",
    "spells": "Spells and spell sources",
    "equipment": "Equipment",
    "hit_points": "Hit-point baseline",
    "comparison": "Calculated versus observed",
}

STATE_LABELS = {
    "match": "Recovered",
    "conflict": "Conflict",
    "not_observed": "Not modeled",
    "blocker": "Missing",
    "warning": "Inferred - confirm",
    "info": "Recovered",
}


def build_import_review_sections(result):
    issue_groups = defaultdict(list)
    for issue in getattr(result, "issues", []) or []:
        issue_groups[getattr(issue, "section", "comparison")].append(
            display_issue(issue)
        )

    comparison_groups = defaultdict(list)
    for comparison in getattr(result, "comparisons", []) or []:
        comparison_groups["comparison"].append(display_comparison(comparison))

    return [
        {
            "key": key,
            "label": SECTION_LABELS[key],
            "issues": issue_groups.get(key, []),
            "comparisons": comparison_groups.get(key, []),
        }
        for key in RECONCILIATION_SECTIONS
    ]


def display_issue(issue):
    value = asdict(issue) if is_dataclass(issue) else dict(issue)
    severity = str(value.get("severity") or "info")
    return {
        **value,
        "state_label": STATE_LABELS.get(severity, severity.title()),
    }


def display_comparison(comparison):
    value = asdict(comparison) if is_dataclass(comparison) else dict(comparison)
    status = str(value.get("status") or "not_observed")
    return {
        **value,
        "state_label": STATE_LABELS.get(status, status.title()),
    }
