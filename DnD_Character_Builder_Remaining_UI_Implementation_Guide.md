# D&D 5E Character Builder

## Remaining UI Implementation Guide

Version 1.0  
Prepared against the July 16, 2026 portable build

## 1. Purpose

This guide turns the remaining UI work into a sequence Codex can implement without destabilizing the rules engine or repeating the spell-browser work in every screen.

The desired experience remains:

- The explanation appears where the decision is made.
- Large catalogs use search, filtering, and an inspector.
- Small choices retain a compact native control and reveal details after selection.
- Inspecting an option never mutates the character.
- Rules, eligibility, selection limits, save/load behavior, level-up transactions, and PDF output remain owned by the existing domain and service layers.

Spell-card export is deliberately outside this guide. It should begin only after the remaining selection UI is stable.

## 2. Current Baseline

The updated build is a good starting point:

- The complete test suite passes: **227 tests**.
- `presentation/option_models.py` provides a frontend-neutral `OptionViewModel`.
- `presentation/option_catalog.py` builds spell catalogs and keeps selection logic outside Streamlit.
- `ui/option_browser.py` owns the Streamlit spell-browser rendering.
- Initial known-spell, prepared-spell, and Wizard spellbook selection use grouped catalogs with independent limits.
- Level-up spell and spellbook choices can share one browser without merging their rules.
- Inspection and selection are separate actions.

Preserve these boundaries. Do not move rules checks into the new compact components.

## 3. Audit Findings to Address

### 3.1 Special spell selectors still bypass the inspector

The primary class spell flows use the new browser, but these paths still use native `selectbox` or `multiselect` controls without the shared inspector:

- Magic Initiate cantrips and level 1 spell in `render_origin_feat_controls`.
- Blessed Warrior and Druidic Warrior cantrips.
- Thaumaturge and Magician bonus cantrips.
- Wizard Savant spell choices in `render_subclass_option_controls`.
- Wizard prepared-spell selection from the completed spellbook.
- Spell Mastery selection and later Spell Mastery reconfiguration.
- Feat spell selections, including Ritual Caster and similar feat-specific choices.
- Signature Spells and other special pending-choice spell types.

Before declaring spell UI complete, route these through the existing catalog and inspector. Some are single-selection groups, but they still benefit from the same spell details and search surface.

Do not force every special spell choice into one global table. Reuse the same browser component with a context-specific group specification and selection limit.

### 3.2 Browser state needs stale-option reconciliation

`_initialize_browser_state` initializes an inspected spell only when the session key is absent. If the class, level, or option catalog changes while the same state key remains, the stored inspected ID can point to an option no longer in the catalog. The inspector then becomes empty until the user chooses another row.

Required behavior:

1. If the stored inspected ID is still present, preserve it.
2. Otherwise inspect the first selected option that remains in the catalog.
3. Otherwise inspect the first available option.
4. Otherwise show the empty-state message.

Keep valid search and filter state. Reset only filters whose selected value is no longer valid.

### 3.3 Equipment package state has no provenance

The current equipment screen merges package items into `character["equipment"]`. After that merge, the program cannot distinguish package-provided items from manually added items.

This creates two likely problems:

- Switching from package A to package B can retain package A items alongside package B.
- Turning off “Include default class and background equipment” can leave the old default items selected because they are already stored in the combined equipment list.

Correct the state model before polishing this screen.

Recommended compatibility model:

```python
character["class_options"]["equipment_package"]
character["background_options"]["equipment_package"]
character["include_default_equipment"]
character["custom_equipment"]
character["equipment"]  # derived compatibility list
```

Derive `character["equipment"]` from the selected package items plus `custom_equipment`. Never use the derived list as the source for the next UI selection.

For legacy saves that only contain `equipment`, preserve data rather than guessing destructively. Treat unmatched existing items as custom equipment. Add a migration test.

### 3.4 Description coverage varies by option family

The current data already supports several compact panels:

- Subclass identity descriptions are available at `subclass["feature_descriptions"][subclass["name"]]` for all 48 imported subclasses.
- Subclass level features and their descriptions are available.
- Fighting Style and Origin feat descriptions are available in `data["rules"]["feature_descriptions"]`.
- Divine Order and Primal Order option descriptions are available in class feature descriptions and related-feature records.
- Species trait and ancestry descriptions are available in `trait_descriptions`.
- General feat descriptions are already normalized.
- Equipment package item lists are available.
- Weapons have basic category, damage, damage type, and mastery metadata.

These families need additional normalization before a complete inspector is possible:

- Equipment is currently a list of 217 names, with no normalized category, price, weight, or description.
- Skill descriptions exist in raw `skills.json` but are not exposed as normalized records.
- Maneuver and Eldritch Invocation names and prerequisites exist, but their rules descriptions are not in the imported catalog. Add the relevant 5etools optional-feature source before presenting a “full details” view.
- Some imported feature text still contains artifacts such as `class=Cleric`, `category=FS`, `type=martial weapon`, and raw filter fragments. Improve shared inline-tag cleanup before showing those descriptions more widely.

Do not fabricate missing descriptions in the UI. Render an explicit “No description available” state until the importer supplies the record.

### 3.5 `app.py` should not absorb the next component family

The main app is already responsible for many widget branches. Add the compact-choice renderer and catalog builders in dedicated modules rather than adding another large set of UI helpers to `app.py`.

## 4. UI Pattern Decision Table

Choose the interaction based on decision complexity, not only the number of options.

| Choice family | Preferred surface | Detail behavior |
| --- | --- | --- |
| One choice from roughly 2–10 options | Compact single-choice control | Description appears directly below the control after selection |
| Two or three short, clearly contrasting options | Segmented control or radio buttons | Same selected-description panel below |
| Small multi-select list with short definitions | Native multiselect | Show count and compact details for selected entries in a collapsed disclosure |
| Large or comparison-heavy catalog | Searchable browser plus inspector | Inspect any option before adding or removing it |
| Derived value or configuration with no meaningful rules comparison | Existing native control | One-line consequence or change-timing caption |

Hover must not be required. Native Streamlit tooltips may supplement the UI, but every detail needed to choose must be reachable by click and keyboard.

## 5. Compact Choice Component Contract

Create:

- `presentation/compact_catalog.py`
- `ui/compact_choice.py`

Continue using `OptionViewModel`; do not create a separate incompatible description model.

### 5.1 Single-choice renderer

Suggested interface:

```python
def render_compact_single_choice(
    options: tuple[OptionViewModel, ...],
    selected_id: str | None,
    *,
    state_key: str,
    label: str,
    placeholder: str = "Choose an option",
    control: str = "selectbox",
) -> str | None:
    ...
```

Required behavior:

- Render one native control.
- Change the selected description on the same interaction; never require a second click.
- Show no large empty panel before a selection. A one-line prompt is enough.
- After selection, show a bordered compact detail container immediately below the control.
- Show name, short summary, the most decision-relevant metadata, status, and source.
- Put long rules text or full progression inside `st.expander("View full details")`.
- Return a stable ID or domain value. The renderer must not directly mutate the character.
- Preserve the selected value when unrelated widgets rerun.
- If a saved selection is no longer valid, keep it visible as a review state rather than silently deleting it.

### 5.2 Multi-choice renderer

Suggested interface:

```python
def render_compact_multi_choice(
    options: tuple[OptionViewModel, ...],
    selected_ids: list[str],
    *,
    selection_limit: int,
    state_key: str,
    label: str,
) -> list[str]:
    ...
```

Required behavior:

- Keep the native multiselect for small lists.
- Display `selected / limit` next to the choice.
- Enforce the limit through the existing rules or choice resolver, not only through widget configuration.
- When descriptions exist, show selected entries inside a collapsed “About selected options” disclosure.
- If a selected option becomes invalid, explain why and preserve it for review until the owning workflow deliberately resolves it.
- Do not attempt true hover inspection inside a native Streamlit multiselect.

### 5.3 Catalog builders

Builders convert domain/content records into `OptionViewModel` instances. They may format presentation text, but they must not write character state.

Add focused builders rather than one function with many type switches:

```python
build_subclass_catalog(class_data, target_level, selected_name)
build_named_feature_catalog(option_names, description_lookup, ...)
build_species_choice_catalog(species_data, choice_rule, selected_name)
build_equipment_package_catalog(packages, selected_name, source_label)
build_skill_catalog(skill_records, selected_names, ...)
build_weapon_mastery_catalog(weapons, eligibility_results, selected_names)
```

Use stable IDs based on source identity, not list position.

## 6. Target Experience by Choice Family

### 6.1 Subclass — first compact-choice pilot

Subclass is the best pilot because it has few options, meaningful descriptions, high player impact, and complete imported data.

Use the component in the `subclass_choice` level-up flow.

The compact panel should show:

- Subclass name and source.
- The subclass identity paragraph.
- Features gained at the target level.
- Any immediately created follow-up choices, such as maneuvers or spells.
- A “View subclass progression” expander showing feature names by level and available descriptions.

Inspection must not resolve the level-up choice. Only changing the actual selection should call `resolve_pending_choice`.

Pass the full app data or a presentation context to the level-choice renderer. Do not add presentation text to rules-domain pending-choice records merely to make it available to Streamlit.

Acceptance cases:

- Fighter level 3 shows all four Fighter subclasses.
- Selecting Battle Master immediately shows its summary and level 3 features.
- Changing to Champion replaces the detail panel on the first interaction.
- The draft remains uncommitted until level-up finalization.
- Canceling the draft leaves the character unchanged.

### 6.2 Fighting Style, Divine Order, and Primal Order

Use compact single-choice controls.

For Fighting Style:

- Source descriptions from `data["rules"]["feature_descriptions"]`.
- Show the mechanical effect in the compact panel.
- Blessed Warrior and Druidic Warrior must launch the existing spell inspector for their dependent cantrip choices.

For Divine Order and Primal Order:

- Two short options may use a segmented control if the labels remain readable; otherwise use a selectbox.
- Show exact proficiencies, bonuses, and newly required cantrip choices.
- The dependent cantrip selection remains a separate spell-browser group.

### 6.3 Species ancestries and lineages

Apply the compact pattern to:

- Draconic Ancestry.
- Gnomish Lineage.
- Giant Ancestry.
- Elven Lineage.
- Fiendish Legacy.
- Other `choice_options` or `lineage_options` added later.

Build descriptions from `trait_descriptions` and lineage spell records. Include the immediate level 1 grant and a concise note about later grants when available.

Keep spellcasting-ability selection adjacent to the lineage description. If the lineage requires a selectable spell, use the spell browser for that dependent choice.

### 6.4 Background and class summaries

The selected background and class already expose some benefits, but they should use the same compact visual language:

- Background: skills, tools, Origin feat, ability choices, and equipment package summary.
- Class: Hit Die, primary ability, saves, armor, weapons, level 1 features, and spellcasting status.

These do not need a separate inspector. Keep the existing dropdown and replace scattered writes with a bordered selected-summary container.

### 6.5 Proficiencies, expertise, tools, and languages

Keep native small controls.

- Normalize 2024 skill records from raw `skills.json` so each skill can show its ability and one-line definition.
- For class skill and expertise selections, show selected definitions in a collapsed disclosure.
- Tool and language choices may use plain-language category descriptions when the source provides them. Do not invent mechanical effects for tools or languages.
- Continue to explain duplicate exclusions, exact counts, and why an option is unavailable.

### 6.6 Feats, maneuvers, invocations, and Weapon Mastery

These are not truly “small” choices even when only one or two selections are allowed. They require comparison or prerequisite visibility.

- **General feats:** move from selectbox plus one expander to a searchable browser using the established option model.
- **Battle Master maneuvers:** use a searchable browser after maneuver descriptions are imported.
- **Eldritch Invocations:** use a searchable browser that shows every invocation, including blocked choices with prerequisite explanations. Do not continue hiding every ineligible invocation.
- **Weapon Mastery:** use a compact searchable catalog with weapon, category, damage, damage type, mastery property, and proficiency status.

These should follow the compact-choice rollout rather than being included in the first component task.

### 6.7 Equipment

Treat the two equipment decisions differently.

#### Equipment packages

Class and background package dropdowns are compact choices. The selected panel should list every item granted by the package. Replace opaque labels such as only “A” or “B” with a formatted label or nearby summary, for example:

`Package A — Chain Mail, Greatsword, Flail, and adventuring gear`

Do not change the stored package ID solely for display.

#### Custom equipment catalog

The free equipment list contains roughly 217 options and should eventually use a searchable catalog rather than a larger multiselect.

Before building it, normalize equipment records from the existing raw item sources with at least:

```text
stable_id, name, source, category, cost, weight, description,
armor data, weapon data, properties, quantity defaults
```

The first equipment browser can reuse the spell layout conceptually, but its filters should be equipment-specific: category, weapon/armor/gear, proficiency relevance, and selected status.

Do not add encumbrance, shopping, currency deduction, magic items, or inventory quantities in this UI phase unless separately approved.

## 7. Implementation Sequence

Each phase should be a separate Codex task or commit-sized change. Run the entire test suite after every phase.

### Phase 0 — Close the spell-browser gaps

1. Add stale inspected-ID reconciliation.
2. Route the remaining special spell selectors listed in section 3.1 through the shared browser.
3. Keep each choice's existing limit and destination field unchanged.
4. Add AppTest coverage for at least Magic Initiate, one Fighting Style cantrip grant, Wizard prepared spells, one Savant choice, Spell Mastery, and one feat spell choice.
5. Confirm save/load and normalized character-sheet output are unchanged.

Completion gate: no user-selectable spell or cantrip remains on a plain selectbox or multiselect unless a documented exception explains why.

### Phase 1 — Build the compact-choice foundation

1. Add `presentation/compact_catalog.py` and `ui/compact_choice.py`.
2. Implement single- and multi-choice contracts from section 5.
3. Add unit tests for view-model construction and selection preservation.
4. Add Streamlit AppTest coverage for one single and one multi control.
5. Do not migrate production screens yet.

Completion gate: the component works independently and contains no D&D rules imports.

### Phase 2 — Subclass pilot

1. Build subclass view models from imported class data.
2. Replace only the `subclass_choice` pending-choice control.
3. Show identity summary, target-level gains, follow-up-choice notice, source, and full progression disclosure.
4. Test Fighter, one full-caster subclass, and a subclass that introduces spell choices.
5. Manually verify level-up cancellation and finalization.

Completion gate: subclass selection feels correct before any broader migration.

### Phase 3 — Compact single-choice rollout

Migrate in this order:

1. Divine Order and Primal Order.
2. Fighting Style.
3. Species ancestry and lineage choices.
4. Feature configurations such as Hunter's Prey, Defensive Tactics, terrain, damage type, and Third Eye.
5. Equipment packages.
6. Background and class selected-summary containers.

Completion gate: each selected description updates with one interaction and does not create a new large persistent panel.

### Phase 4 — Compact multi-choice rollout

1. Normalize skill descriptions.
2. Update class skills, species skills, lore skills, expertise, Skilled, Crafter tools, Musician instruments, and similar small lists.
3. Preserve exact-count validation and duplicate exclusions.
4. Keep selected details collapsed by default to avoid page growth.

Completion gate: every multi-choice communicates its count, duplicate restrictions, and selected-option meaning without requiring an external lookup.

### Phase 5 — Correct and improve equipment

1. Introduce package/custom equipment provenance and legacy migration.
2. Add package detail panels.
3. Normalize structured equipment records.
4. Add a searchable custom-equipment browser.
5. Verify package switching, default-equipment toggling, save/load, character sheet, and PDF export.

Completion gate: changing packages never silently accumulates old package items and never deletes custom equipment.

### Phase 6 — Medium catalog rollout

1. Normalize missing optional-feature descriptions.
2. Add browsers for feats, maneuvers, invocations, and Weapon Mastery.
3. Extend eligibility results so blocked options remain visible with specific remedies.
4. Reuse the existing `OptionViewModel` status vocabulary.

Completion gate: large comparison choices no longer rely on bare multiselects, and blocked options explain their prerequisites.

### Phase 7 — Consistency and cleanup

1. Clean imported inline-tag artifacts through one shared formatter/import step.
2. Remove dead UI helpers and unused parameters only after migrations are complete.
3. Check state keys for uniqueness across initial build and level-up drafts.
4. Verify focus order, keyboard operation, status text, and non-color-only feedback.
5. Profile reruns and cache only pure catalog-building work.
6. Update the main design guide with any approved deviations.

## 8. Test Matrix

### Presentation tests

- Stable IDs do not depend on list position.
- Missing descriptions produce an explicit empty-data state.
- Selected, available, blocked, warning, and legacy-review statuses serialize consistently.
- Subclass builders expose correct target-level features.
- Package builders preserve package IDs and item lists.
- Equipment builders deduplicate source records correctly.

### Streamlit interaction tests

- Selection and description update on the first interaction.
- Opening or reading details never changes character state.
- Switching selections replaces the description rather than stacking panels.
- Clearing a selection collapses the details.
- Widget reruns preserve current choices.
- Stale inspected IDs recover to a valid option.
- Search and filters do not remove committed selections.

### Domain-regression tests

- Existing character creation and level-up tests continue to pass.
- Selection limits remain enforced outside the UI.
- Canceling a level-up draft remains non-mutating.
- Save/load retains compact-choice selections.
- Legacy saves retain equipment without data loss.
- Character sheet and PDF output remain unchanged except for intentional equipment corrections.

### Manual class coverage

At minimum, manually exercise:

- Fighter: Fighting Style, subclass, Battle Master maneuvers, Weapon Mastery.
- Cleric: Divine Order and bonus cantrip.
- Druid: Primal Order, subclass terrain, and bonus cantrip.
- Rogue: expertise, language, and subclass.
- Warlock: invocations and their prerequisites.
- Wizard: spellbook, preparation, Savant, Spell Mastery, and subclass.
- A character with Magic Initiate.
- A character that changes both class and background equipment packages.

## 9. Non-Goals for This UI Phase

- Spell-card PDF export.
- A migration away from Streamlit.
- Custom JavaScript hover cards.
- Resizable rails or mobile bottom sheets.
- Inventory quantities, encumbrance, shops, or currency accounting.
- Active-play tracking such as expended spell slots or item charges.
- Rewriting the rules engine to suit widget behavior.

## 10. Codex Working Instructions

Use this at the beginning of each implementation phase:

> Work from the current stable portable build and implement only the requested phase from `DnD_Character_Builder_Remaining_UI_Implementation_Guide.md`. Preserve existing rules behavior, character state fields, save/load compatibility, level-up transaction semantics, and PDF output. Keep Streamlit rendering in `ui/`, presentation builders in `presentation/`, and rules logic out of both. Reuse `OptionViewModel` and the established status vocabulary. Add focused unit and Streamlit AppTest coverage, then run the complete test suite. Do not begin a later phase or the spell-card exporter in the same task. Report any missing source data instead of inventing descriptions.

For the next task specifically, start with Phase 0. The spell browser is the known-good interaction; close its remaining coverage gaps before introducing the compact component family.

## 11. Definition of Done

The remaining UI phase is complete when:

- Every spell choice uses the shared spell-details experience or has a documented exception.
- Small choices show their selected description immediately beside the decision.
- Large catalogs are searchable and inspectable.
- Blocked choices are visible and explain why they are blocked where the rules engine has enough information.
- Equipment packages and custom equipment have distinct state provenance.
- Inspecting never mutates character or draft state.
- No UI migration changes rules outcomes unintentionally.
- The complete automated suite passes, and the manual class matrix has been exercised.

