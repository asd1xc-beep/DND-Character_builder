import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field

from models.character import ABILITIES, merge_unique, new_character
from rules.character_validation import build_validation_report
from rules.feat_rules import (
    feat_choice_schema,
    feat_extra_choices_are_valid,
    feat_is_supported_for_selection,
)
from rules.leveling import effective_spellcasting
from services.character_engine import (
    apply_source_ability_adjustments,
    calculate_background_ability_bonuses,
    class_feature_ability_adjustments,
    recalculate_character,
)
from services.equipment_state import derive_equipment


RECONCILIATION_SECTIONS = (
    "identity",
    "abilities",
    "class_choices",
    "proficiencies",
    "spells",
    "equipment",
    "hit_points",
    "comparison",
)


@dataclass(frozen=True)
class ImportReconciliationIssue:
    code: str
    severity: str
    section: str
    label: str
    observed: object = ""
    expected: object = ""
    remedy: str = ""


@dataclass(frozen=True)
class ImportComparison:
    key: str
    label: str
    observed: object
    calculated: object
    status: str


@dataclass
class ImportReconciliationResult:
    status: str
    candidate_character: dict
    selections: dict
    issues: list[ImportReconciliationIssue] = field(default_factory=list)
    comparisons: list[ImportComparison] = field(default_factory=list)
    validation_report: dict = field(default_factory=dict)
    recovered: dict = field(default_factory=dict)
    can_confirm: bool = False

    def to_dict(self):
        return {
            "status": self.status,
            "candidate_character": deepcopy(self.candidate_character),
            "selections": deepcopy(self.selections),
            "issues": [asdict(issue) for issue in self.issues],
            "comparisons": [asdict(comparison) for comparison in self.comparisons],
            "validation_report": deepcopy(self.validation_report),
            "recovered": deepcopy(self.recovered),
            "can_confirm": self.can_confirm,
        }


def initial_reconciliation_selections(import_result, data):
    """Return detached, conservative selections seeded only by recoverable evidence."""
    if getattr(import_result, "source_kind", "") == "embedded_state":
        return {"embedded_candidate": deepcopy(getattr(import_result, "candidate_character", {}))}

    extracted = deepcopy(getattr(import_result, "extracted_data", {}) or {})
    identity = extracted.get("identity", {})
    class_name = exact_catalog_name(identity.get("class_name", ""), data.get("classes", []))
    species = exact_catalog_name(identity.get("species", ""), data.get("species", []))
    background = exact_catalog_name(identity.get("background", ""), data.get("backgrounds", []))
    level = identity.get("level")
    level = int(level) if isinstance(level, int) and 1 <= level <= 20 else 1
    observed_abilities = {
        ability: value
        for ability, value in extracted.get("abilities", {}).items()
        if ability in ABILITIES and isinstance(value, int)
    }
    recovered_spells, unmatched_spells = recover_spells(extracted, data)
    classified_spells = classify_recovered_spells(
        recovered_spells,
        data.get("classes_by_name", {}).get(class_name, {}),
        level,
        data.get("spells", []),
    )
    recovered_equipment, residual_equipment = recover_equipment(
        extracted.get("equipment", {}).get("raw", ""),
        data.get("equipment", []),
    )
    recovered_feats = recover_feature_names(extracted, data.get("feats", []))
    background_origin_feats = set(
        data.get("backgrounds_by_name", {})
        .get(background, {})
        .get("origin_feats", [])
    )
    recovered_feats = [
        feat for feat in recovered_feats
        if feat.get("name") not in background_origin_feats
    ]
    recovered_masteries = recover_weapon_masteries(extracted, data.get("weapons", []))

    return {
        "name": identity.get("name") or identity.get("alternate_name") or "",
        "class_name": class_name,
        "level": level,
        "species": species,
        "background": background,
        "background_primary_ability": "",
        "background_secondary_ability": "",
        "ability_scores": observed_abilities,
        "ability_scores_confirmed": False,
        "subclass": "",
        "class_skills": [],
        "species_options": {},
        "class_options": {},
        "origin_feat_choices": {
            "skills": [],
            "tools": [],
            "cantrips": [],
            "spell": "",
            "spellcasting_ability": "",
        },
        "expertise": [],
        "general_feat_ids": [
            feat["id"] for feat in recovered_feats if feat.get("id")
        ],
        "feat_choices": {},
        "feats_confirmed": not recovered_feats,
        "weapon_masteries": recovered_masteries,
        "masteries_confirmed": not recovered_masteries,
        "spells": classified_spells,
        "spells_confirmed": not recovered_spells and not unmatched_spells,
        "custom_equipment": merge_unique(recovered_equipment, residual_equipment),
        "include_default_equipment": False,
        "equipment_confirmed": not extracted.get("equipment", {}).get("raw", ""),
        "preserve_observed_maximum_hp": True,
        "observed_maximum_hp": extracted.get("hit_points", {}).get("maximum"),
        "observed_current_hp": extracted.get("hit_points", {}).get("current"),
        "observed_temporary_hp": extracted.get("hit_points", {}).get("temporary"),
        "recovered": {
            "spells": recovered_spells,
            "unmatched_spells": unmatched_spells,
            "equipment": recovered_equipment,
            "equipment_residual": residual_equipment,
            "feat_names": [feat.get("name", "") for feat in recovered_feats],
            "weapon_masteries": recovered_masteries,
        },
    }


def build_reconciliation_draft(import_result, selections, data):
    """Build and validate a detached candidate without mutating caller-owned state."""
    selected = deepcopy(selections or {})
    source_kind = getattr(import_result, "source_kind", "")
    if source_kind == "embedded_state":
        candidate = deepcopy(
            selected.get("embedded_candidate")
            or getattr(import_result, "candidate_character", {})
        )
        if not candidate:
            return _failed_result(
                selected,
                "embedded_candidate_missing",
                "The embedded character state is unavailable.",
            )
        recalculate_character(candidate, data)
        validation = current_validation(candidate, data)
        issues = validation_issues(validation)
        return _result(
            candidate,
            selected,
            issues,
            [],
            validation,
            {"source_kind": "embedded_state"},
        )

    if source_kind != "compatible_form":
        return _failed_result(
            selected,
            "source_not_reconcilable",
            "This PDF cannot be reconciled into a working character.",
        )

    candidate = new_character()
    apply_identity(candidate, selected)
    apply_current_choices(candidate, selected, data)
    issues = []
    issues.extend(identity_issues(candidate, data))
    issues.extend(ability_baseline(candidate, selected, data))

    recalculate_character(candidate, data)
    apply_hit_point_override(candidate, selected, data, issues)
    candidate["equipment"] = derive_equipment(
        candidate,
        data.get("classes_by_name", {}).get(candidate.get("class"), {}),
        data.get("backgrounds_by_name", {}).get(candidate.get("background"), {}),
    )
    add_import_checkpoint(candidate)

    issues.extend(confirmation_issues(selected))
    issues.extend(import_choice_issues(candidate, selected, data))
    validation = current_validation(candidate, data)
    issues.extend(validation_issues(validation))
    comparisons = build_comparisons(
        candidate,
        deepcopy(getattr(import_result, "extracted_data", {}) or {}),
    )
    issues.extend(comparison_issues(comparisons))
    return _result(
        candidate,
        selected,
        deduplicate_issues(issues),
        comparisons,
        validation,
        deepcopy(selected.get("recovered", {})),
    )


def apply_identity(candidate, selections):
    candidate["name"] = str(selections.get("name") or "").strip()
    candidate["class"] = str(selections.get("class_name") or "").strip()
    candidate["level"] = _bounded_level(selections.get("level", 1))
    candidate["species"] = str(selections.get("species") or "").strip()
    candidate["background"] = str(selections.get("background") or "").strip()
    if candidate["class"]:
        candidate["class_levels"] = {candidate["class"]: candidate["level"]}


def apply_current_choices(candidate, selections, data):
    candidate["background_options"] = {
        "primary_ability": selections.get("background_primary_ability", ""),
        "secondary_ability": selections.get("background_secondary_ability", ""),
    }
    candidate["subclass"] = str(selections.get("subclass") or "")
    candidate["class_options"] = deepcopy(selections.get("class_options", {}) or {})
    candidate["class_options"]["class_skills"] = merge_unique(
        selections.get("class_skills", [])
    )
    candidate["species_options"] = deepcopy(selections.get("species_options", {}) or {})
    candidate["origin_feat_choices"] = {
        "skills": merge_unique((selections.get("origin_feat_choices", {}) or {}).get("skills", [])),
        "tools": merge_unique((selections.get("origin_feat_choices", {}) or {}).get("tools", [])),
        "cantrips": merge_unique((selections.get("origin_feat_choices", {}) or {}).get("cantrips", [])),
        "spell": str((selections.get("origin_feat_choices", {}) or {}).get("spell", "") or ""),
        "spellcasting_ability": str(
            (selections.get("origin_feat_choices", {}) or {}).get("spellcasting_ability", "")
            or ""
        ),
    }
    candidate["expertise"] = merge_unique(selections.get("expertise", []))
    candidate["weapon_masteries"] = merge_unique(selections.get("weapon_masteries", []))
    candidate["spells"] = {
        key: merge_unique((selections.get("spells", {}) or {}).get(key, []))
        for key in ("cantrips", "prepared", "known", "spellbook")
    }
    candidate["include_default_equipment"] = bool(
        selections.get("include_default_equipment", False)
    )
    candidate["custom_equipment"] = merge_unique(selections.get("custom_equipment", []))
    candidate["general_feats"] = general_feat_instances(
        selections.get("general_feat_ids", []),
        data.get("feats", []),
        selections.get("feat_choices", {}),
    )


def ability_baseline(candidate, selections, data):
    issues = []
    observed = selections.get("ability_scores", {}) or {}
    missing = [ability for ability in ABILITIES if not isinstance(observed.get(ability), int)]
    if missing:
        for ability in missing:
            issues.append(ImportReconciliationIssue(
                code=f"ability_{slug(ability)}_missing",
                severity="blocker",
                section="abilities",
                label=f"{ability} needs a confirmed final score.",
                expected="A whole-number score",
                remedy=f"Enter the {ability} score shown on the character sheet.",
            ))
        return issues

    class_data = data.get("classes_by_name", {}).get(candidate.get("class"), {})
    background_data = data.get("backgrounds_by_name", {}).get(candidate.get("background"), {})
    background_bonuses = calculate_background_ability_bonuses(candidate, background_data)
    automatic_adjustments = class_feature_ability_adjustments(candidate, class_data)
    baseline = {}
    for ability in ABILITIES:
        final_score = int(observed[ability])
        base = solve_imported_base_score(
            ability,
            final_score,
            background_bonuses,
            automatic_adjustments,
        )
        if base is None:
            issues.append(ImportReconciliationIssue(
                code=f"ability_{slug(ability)}_cannot_reproduce",
                severity="blocker",
                section="abilities",
                label=f"{ability} cannot be reproduced by the current rules.",
                observed=final_score,
                expected="A score reproducible from the imported baseline and automatic bonuses",
                remedy="Review the final score and background allocation.",
            ))
            base = final_score - int(background_bonuses.get(ability, 0))
        baseline[ability] = base

    candidate["base_ability_scores"] = baseline
    candidate["ability_scores"] = dict(observed)
    candidate["ability_score_method"] = "Manual entry"
    candidate["ability_score_assignments"] = {}
    candidate["rolled_ability_scores"] = []
    candidate["ability_score_adjustments"] = []
    if not selections.get("ability_scores_confirmed"):
        issues.append(ImportReconciliationIssue(
            code="ability_baseline_unconfirmed",
            severity="blocker",
            section="abilities",
            label="The imported final ability scores and reconstructed baseline need confirmation.",
            observed=dict(observed),
            expected=baseline,
            remedy="Confirm the ability-score baseline after choosing the background bonuses.",
        ))
    return issues


def solve_imported_base_score(
    ability,
    observed_final,
    background_bonuses,
    automatic_adjustments,
):
    preferred = int(observed_final) - int(background_bonuses.get(ability, 0))
    for adjustment in automatic_adjustments:
        preferred -= int(adjustment.get("adjustments", {}).get(ability, 0) or 0)
    candidates = list(range(preferred - 4, preferred + 5))
    candidates.extend(range(-30, 41))
    seen = set()
    for base in candidates:
        if base in seen:
            continue
        seen.add(base)
        scores, _ = apply_source_ability_adjustments(
            {name: base if name == ability else 10 for name in ABILITIES},
            {name: background_bonuses.get(name, 0) for name in ABILITIES},
            automatic_adjustments,
        )
        if scores[ability] == int(observed_final):
            return base
    return None


def apply_hit_point_override(candidate, selections, data, issues):
    calculated = int(candidate.get("hit_points", {}).get("maximum", 0) or 0)
    observed = selections.get("observed_maximum_hp")
    preserve = bool(selections.get("preserve_observed_maximum_hp", True))
    if observed is None:
        issues.append(ImportReconciliationIssue(
            code="maximum_hp_missing",
            severity="blocker",
            section="hit_points",
            label="Maximum HP needs confirmation.",
            expected="A whole-number maximum HP",
            remedy="Enter the maximum HP shown on the PDF or use calculated HP.",
        ))
        adjustment = 0
    elif preserve:
        if int(observed) < 1:
            issues.append(ImportReconciliationIssue(
                code="maximum_hp_invalid",
                severity="blocker",
                section="hit_points",
                label="Maximum HP must be at least 1.",
                observed=observed,
                expected="A positive whole number",
                remedy="Enter a valid maximum HP or use calculated HP.",
            ))
            adjustment = 0
        else:
            adjustment = int(observed) - calculated
    else:
        adjustment = 0

    candidate["import_overrides"] = {"maximum_hp_adjustment": adjustment}
    recalculate_character(candidate, data)
    maximum = int(candidate.get("hit_points", {}).get("maximum", 0) or 0)
    current = selections.get("observed_current_hp")
    temporary = selections.get("observed_temporary_hp")
    if isinstance(current, int):
        candidate["hit_points"]["current"] = min(max(0, current), maximum)
    if isinstance(temporary, int):
        candidate["hit_points"]["temporary"] = max(0, temporary)


def identity_issues(candidate, data):
    issues = []
    checks = (
        ("name", candidate.get("name"), None, "Enter the character name."),
        ("class", candidate.get("class"), data.get("classes_by_name", {}), "Choose a supported class."),
        ("species", candidate.get("species"), data.get("species_by_name", {}), "Choose a supported species."),
        ("background", candidate.get("background"), data.get("backgrounds_by_name", {}), "Choose a supported background."),
    )
    for key, value, catalog, remedy in checks:
        if not value or (catalog is not None and value not in catalog):
            issues.append(ImportReconciliationIssue(
                code=f"{key}_missing_or_unknown",
                severity="blocker",
                section="identity",
                label=f"A supported {key} is required.",
                observed=value or "",
                remedy=remedy,
            ))
    return issues


def confirmation_issues(selections):
    checks = (
        ("spells_confirmed", "spells_unconfirmed", "spells", "Confirm each recovered spell and its rules source."),
        ("feats_confirmed", "feats_unconfirmed", "proficiencies", "Confirm the recovered feats and any required feat choices."),
        ("masteries_confirmed", "masteries_unconfirmed", "proficiencies", "Confirm the recovered Weapon Mastery selections."),
        ("equipment_confirmed", "equipment_unconfirmed", "equipment", "Confirm recovered and unmatched equipment."),
    )
    return [
        ImportReconciliationIssue(
            code=code,
            severity="blocker",
            section=section,
            label=label,
            remedy=label,
        )
        for flag, code, section, label in checks
        if not selections.get(flag)
    ]


def import_choice_issues(candidate, selections, data):
    issues = []
    class_data = data.get("classes_by_name", {}).get(candidate.get("class"), {})
    subclass_level = first_subclass_choice_level(class_data)
    if (
        subclass_level
        and candidate.get("level", 1) >= subclass_level
        and not candidate.get("subclass")
    ):
        issues.append(ImportReconciliationIssue(
            code="subclass_missing",
            severity="blocker",
            section="class_choices",
            label=f"A subclass is required at level {subclass_level}.",
            remedy="Choose the current subclass using the shared subclass control.",
        ))

    recovered = selections.get("recovered", {}) or {}
    unmatched = recovered.get("unmatched_spells", [])
    if unmatched:
        issues.append(ImportReconciliationIssue(
            code="unmatched_spells",
            severity="blocker",
            section="spells",
            label="Some PDF spell names do not match the active catalog.",
            observed=unmatched,
            expected="Supported spell names",
            remedy="Choose replacements or remove the unmatched spell entries.",
        ))
    feat_lookup = {
        feat.get("id"): feat
        for feat in data.get("feats", [])
        if feat.get("id")
    }
    feat_choices = selections.get("feat_choices", {}) or {}
    for feat_id in selections.get("general_feat_ids", []) or []:
        feat = feat_lookup.get(feat_id)
        if not feat:
            issues.append(ImportReconciliationIssue(
                code=f"feat_{slug(feat_id)}_unknown",
                severity="blocker",
                section="proficiencies",
                label="A selected feat is no longer in the active catalog.",
                observed=feat_id,
                remedy="Remove the unavailable feat or choose its supported replacement.",
            ))
            continue
        if not feat_is_supported_for_selection(feat):
            issues.append(ImportReconciliationIssue(
                code=f"feat_{slug(feat_id)}_unsupported",
                severity="blocker",
                section="proficiencies",
                label=f"{feat.get('name')} is not fully modeled for selection.",
                remedy="Remove it or wait for rules support before confirming this import.",
            ))
            continue
        choices = feat_choices.get(feat_id, {}) or {}
        schema = feat_choice_schema(feat, candidate, data)
        choices_valid = not schema or feat_extra_choices_are_valid(
            feat,
            candidate,
            choices,
            data,
        )
        if feat.get("name") == "Resilient" and not choices.get("ability"):
            choices_valid = False
        if not choices_valid:
            issues.append(ImportReconciliationIssue(
                code=f"feat_{slug(feat_id)}_choices_missing",
                severity="blocker",
                section="proficiencies",
                label=f"Complete the current choices for {feat.get('name')}.",
                remedy="Use the feat choice controls below the recovered feat browser.",
            ))
    return issues


def current_validation(candidate, data):
    return build_validation_report(
        candidate,
        data.get("classes_by_name", {}).get(candidate.get("class"), {}),
        data.get("species_by_name", {}).get(candidate.get("species"), {}),
        data.get("backgrounds_by_name", {}).get(candidate.get("background"), {}),
        data.get("spells", []),
        data.get("weapons", []),
    )


def level_up_safety_report(character, data):
    """Return stable blockers for entering or finalizing the level-up flow."""
    validation = current_validation(character, data)
    blockers = [
        *validation.get("missing", []),
        *validation.get("unsupported", []),
    ]
    provenance = character.get("import_provenance", {}) or {}
    if provenance and provenance.get("status") not in {"verified", "reviewed"}:
        blockers.insert(
            0,
            "Complete PDF import reconciliation before leveling up",
        )
    return {
        "safe": not blockers,
        "blockers": blockers,
        "validation_report": validation,
    }


def validation_issues(validation):
    issues = [
        ImportReconciliationIssue(
            code=f"validation_missing_{index}",
            severity="blocker",
            section=validation_section(message),
            label=message,
            remedy="Complete this choice using the reconciliation controls.",
        )
        for index, message in enumerate(validation.get("missing", []))
    ]
    issues.extend(
        ImportReconciliationIssue(
            code=f"validation_unsupported_{index}",
            severity="blocker",
            section="class_choices",
            label=message,
            remedy="Choose a supported current state.",
        )
        for index, message in enumerate(validation.get("unsupported", []))
    )
    issues.extend(
        ImportReconciliationIssue(
            code=f"validation_warning_{index}",
            severity="warning",
            section="class_choices",
            label=message,
        )
        for index, message in enumerate(validation.get("warnings", []))
    )
    return issues


def build_comparisons(candidate, extracted):
    observed = extracted.get("comparison", {})
    hit_points = extracted.get("hit_points", {})
    comparisons = []
    append_comparison(
        comparisons,
        "maximum_hp",
        "Maximum HP",
        hit_points.get("maximum"),
        candidate.get("hit_points", {}).get("maximum"),
    )
    append_comparison(
        comparisons,
        "armor_class",
        "Armor Class",
        observed.get("armor_class"),
        candidate.get("armor_class"),
    )
    append_comparison(
        comparisons,
        "initiative",
        "Initiative",
        signed_integer(observed.get("initiative")),
        candidate.get("initiative"),
    )
    append_comparison(
        comparisons,
        "proficiency_bonus",
        "Proficiency bonus",
        signed_integer(observed.get("proficiency_bonus")),
        candidate.get("proficiency_bonus"),
    )
    append_comparison(
        comparisons,
        "passive_perception",
        "Passive Perception",
        observed.get("passive_perception"),
        10 + int(candidate.get("skill_bonuses", {}).get("Perception", 0) or 0),
    )
    for ability in ABILITIES:
        append_comparison(
            comparisons,
            f"ability_score_{slug(ability)}",
            f"{ability} score",
            extracted.get("abilities", {}).get(ability),
            candidate.get("ability_scores", {}).get(ability),
        )
        append_comparison(
            comparisons,
            f"ability_modifier_{slug(ability)}",
            f"{ability} modifier",
            signed_integer(observed.get("ability_modifiers", {}).get(ability)),
            candidate.get("ability_modifiers", {}).get(ability),
        )
    return comparisons


def append_comparison(comparisons, key, label, observed, calculated):
    if observed in (None, ""):
        status = "not_observed"
    elif observed == calculated:
        status = "match"
    else:
        status = "conflict"
    comparisons.append(ImportComparison(key, label, observed, calculated, status))


def comparison_issues(comparisons):
    return [
        ImportReconciliationIssue(
            code=f"comparison_{comparison.key}",
            severity="warning",
            section="comparison",
            label=f"{comparison.label} differs from the PDF.",
            observed=comparison.observed,
            expected=comparison.calculated,
            remedy="Review whether the recovered choices explain this difference.",
        )
        for comparison in comparisons
        if comparison.status == "conflict"
    ]


def recover_spells(extracted, data):
    lookup = catalog_lookup(data.get("spells", []))
    recovered = []
    unmatched = []
    for names in extracted.get("spells", {}).get("by_level", {}).values():
        for name in names or []:
            match = lookup.get(str(name).strip().casefold())
            if match:
                if match not in recovered:
                    recovered.append(match)
            elif name and name not in unmatched:
                unmatched.append(name)
    return recovered, unmatched


def classify_recovered_spells(spell_names, class_data, level, spell_catalog):
    spell_lookup = {
        str(spell.get("name") or ""): spell
        for spell in spell_catalog or []
        if spell.get("name")
    }
    spellcasting = effective_spellcasting(class_data, "", level) or {}
    cantrips = [
        name for name in spell_names
        if int(spell_lookup.get(name, {}).get("level", -1)) == 0
    ]
    leveled = [name for name in spell_names if name not in cantrips]
    result = {"cantrips": cantrips, "prepared": [], "known": [], "spellbook": []}
    if class_data.get("name") == "Wizard":
        result["spellbook"] = leveled
    elif spellcasting.get("known_spells"):
        result["known"] = leveled
    else:
        result["prepared"] = leveled
    return result


def recover_equipment(raw_text, equipment_names):
    text = str(raw_text or "")
    if not text:
        return [], []
    recovered = []
    residual = text
    for item in sorted(
        {str(name).strip() for name in equipment_names or [] if str(name).strip()},
        key=lambda value: (-len(value), value.casefold()),
    ):
        pattern = re.compile(
            rf"(?<![\w']){re.escape(item)}(?![\w'])",
            flags=re.IGNORECASE,
        )
        if pattern.search(residual):
            recovered.append(item)
            residual = pattern.sub(" ", residual)
    residual = re.sub(r"\bx\s*\d+\b|\(\s*\d+\s*\)", " ", residual, flags=re.IGNORECASE)
    residual_items = [
        clean
        for part in re.split(r"[,;\n]+", residual)
        if (clean := re.sub(r"\s+", " ", part).strip(" .:-"))
    ]
    return recovered, merge_unique(residual_items)


def recover_feature_names(extracted, catalog):
    text = "\n".join([
        str(extracted.get("presentation", {}).get("features", "") or ""),
        str(extracted.get("presentation", {}).get("additional_features", "") or ""),
    ])
    return [
        record
        for record in catalog or []
        if record.get("name") and complete_name_present(text, record["name"])
    ]


def recover_weapon_masteries(extracted, weapons):
    text = str(extracted.get("presentation", {}).get("features", "") or "")
    match = re.search(r"Weapon Master(?:y|ies)\s*:\s*([^\n]+)", text, flags=re.IGNORECASE)
    if not match:
        return []
    lookup = catalog_lookup(weapons)
    recovered = []
    for value in re.split(r"[,;]", match.group(1)):
        name = lookup.get(value.strip().casefold())
        if name and name not in recovered:
            recovered.append(name)
    return recovered


def exact_catalog_name(value, catalog):
    matches = [
        str(record.get("name"))
        for record in catalog or []
        if record.get("name") and str(record.get("name")).casefold() == str(value or "").strip().casefold()
    ]
    return matches[0] if len(matches) == 1 else ""


def general_feat_instances(feat_ids, feats, feat_choices):
    lookup = {str(feat.get("id") or ""): feat for feat in feats or []}
    instances = []
    for feat_id in merge_unique(feat_ids):
        feat = lookup.get(feat_id)
        if not feat:
            continue
        instances.append({
            "instance_id": f"pdf_import_{slug(feat_id)}",
            "feat_id": feat_id,
            "name": feat.get("name", ""),
            "source": {"type": "pdf_import_reconciliation"},
            "choices": deepcopy((feat_choices or {}).get(feat_id, {})),
        })
    return instances


def first_subclass_choice_level(class_data):
    levels = []
    for level, entry in (class_data.get("progression") or {}).items():
        features = entry.get("features", []) if isinstance(entry, dict) else entry or []
        if any(
            isinstance(feature, dict) and feature.get("type") == "subclass_choice"
            for feature in features
        ):
            levels.append(int(level))
    return min(levels) if levels else 0


def add_import_checkpoint(candidate):
    if not candidate.get("class") or any(
        entry.get("source") == "pdf_import_checkpoint"
        for entry in candidate.get("level_history", [])
    ):
        return
    candidate.setdefault("level_history", []).append({
        "class": candidate["class"],
        "from_level": 0,
        "to_level": candidate.get("level", 1),
        "transaction_id": "pdf_import_checkpoint",
        "hp_increase": 0,
        "automatic_features": [],
        "resolved_choices": [],
        "source": "pdf_import_checkpoint",
    })


def catalog_lookup(catalog):
    return {
        str(record.get("name")).casefold(): str(record.get("name"))
        for record in catalog or []
        if isinstance(record, dict) and record.get("name")
    }


def complete_name_present(text, name):
    return bool(re.search(
        rf"(?<![\w']){re.escape(str(name))}(?![\w'])",
        str(text or ""),
        flags=re.IGNORECASE,
    ))


def signed_integer(value):
    if isinstance(value, int):
        return value
    match = re.fullmatch(r"\s*([+-]?\d+)\s*", str(value or ""))
    return int(match.group(1)) if match else None


def validation_section(message):
    lowered = str(message).casefold()
    if "spell" in lowered or "cantrip" in lowered:
        return "spells"
    if "skill" in lowered or "proficien" in lowered or "mastery" in lowered:
        return "proficiencies"
    if "background ability" in lowered:
        return "abilities"
    return "class_choices"


def deduplicate_issues(issues):
    unique = []
    seen = set()
    for issue in issues:
        key = (issue.code, issue.label)
        if key not in seen:
            unique.append(issue)
            seen.add(key)
    return unique


def _result(candidate, selections, issues, comparisons, validation, recovered):
    blockers = [issue for issue in issues if issue.severity == "blocker"]
    can_confirm = not blockers and bool(validation.get("complete"))
    return ImportReconciliationResult(
        status="ready" if can_confirm else "review_required",
        candidate_character=candidate,
        selections=selections,
        issues=issues,
        comparisons=comparisons,
        validation_report=validation,
        recovered=recovered,
        can_confirm=can_confirm,
    )


def _failed_result(selections, code, label):
    issue = ImportReconciliationIssue(
        code=code,
        severity="blocker",
        section="identity",
        label=label,
    )
    return ImportReconciliationResult(
        status="unsupported",
        candidate_character={},
        selections=selections,
        issues=[issue],
        validation_report={"complete": False, "missing": [label], "warnings": [], "unsupported": []},
    )


def _bounded_level(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 1
    return min(max(parsed, 1), 20)


def slug(value):
    return "".join(
        character.lower() if character.isalnum() else "_"
        for character in str(value or "")
    ).strip("_")
