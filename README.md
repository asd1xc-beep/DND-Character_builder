# Local D&D 5e 2024 Character Builder

This is a local Streamlit app for building and leveling 2024 D&D characters from normalized 5e.tools JSON data. It is designed to run on your own Windows computer and keep character files local.

## Quick Start

On this computer, run:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

For a portable copy on another Windows computer:

1. Extract `dnd-character-builder-portable.zip`.
2. Install Python 3.11 or newer if needed.
3. Double-click `Setup First Time.cmd`.
4. Double-click `Start Character Builder.cmd`.

The first setup on a new computer needs internet access so Python can install the packages in `requirements.txt`.

## Current Rules Coverage

- Uses imported 2024 data for the 12 core classes, species, backgrounds, general feats, spells, equipment, and weapons.
- Supports character creation through level 1 and one-level-at-a-time level-up flow through level 20.
- Supports manual scores, standard array assignment, and rolled score assignment.
- Supports subclass selection, class and subclass features, ASI or general feat choices, spell choices during level up, weapon mastery choices, and editable local save/load.
- Generates a sheet-ready summary and an editable WotC-style PDF export.
- Imports builder-generated PDFs losslessly through an embedded, checksummed
  schema-5 JSON payload.
- Recovers compatible older editable PDFs through an explicit reconciliation
  review without changing the active character until confirmation.
- Shows feature and spell descriptions on the final sheet view so the player can read what their character can do.

## Automated Choices

The app currently automates sheet-value choices for:

- Background ability bonuses and origin feats.
- Species skill, lineage, ancestry, spell, and always-on trait effects currently wired into the sheet.
- Core class choices such as Expertise, Fighting Style, Weapon Mastery, Metamagic, Eldritch Invocations, Wild Shape forms, Divine Order, Primal Order, and subclass choices.
- Level 3 subclass choices and grants, including Battle Master maneuvers and spell-granting subclasses.
- Level 4, 6, and 8 ASI/general feat choices.
- Level 5-20 spell progression, class resources, subclass choices, rest-changeable feature configurations, higher-level saving throw proficiencies, and sheet-value resource counters.
- Wizard spellbook growth, prepared-spell tracking, Savant spell choices, and Arcane Recovery scaling.
- Imported related feature references such as Rogue Cunning Strike and Devious Strikes options, including costs and descriptions on the final sheet.
- Epic Boon feats are imported and wired for level 19 selection.
- Wizard Spell Mastery is wired for level 18, including one level 1 and one level 2 spellbook spell choice.
- Level 20 capstones with durable sheet values are wired, including Barbarian and Monk ability caps, Bard Words of Creation spells, Wizard Signature Spells, Ranger Foe Slayer, Paladin capstone counters, and other level 20 resource notes.
- General feats that create permanent sheet values or spell choices, including Skill Expert, Weapon Master, Elemental Adept, Fey-Touched, Shadow-Touched, Ritual Caster, Resilient, Telepathic, and related supported feats.
- Epic Boon selection support, including Boon of Skill, Boon of Speed, Boon of Fortitude, Boon of Energy Resistance, and Boon of Truesight sheet-value choices/effects.
- Wizard Spell Mastery choices, stored as always-prepared at-will lowest-level spell grants on the final sheet, with long-rest editable active configurations.
- High-level durable sheet values such as Action Surge uses, Battle Master progression, Feral Senses, Paladin aura range, Avatar of Battle resistances, Corona of Light uses, Telekinetic Master, and Dragon Companion.

Active-play features such as reactions, rerolls, temporary combat buffs, and timing-based effects are usually kept descriptive rather than changing standing sheet values.

Support labels use these boundaries:

- `supported`: selection, permanent choices, and durable sheet values are represented.
- `partial`: the character can keep the feature, but one or more permanent sheet values or resource pools are still not fully modeled.
- `description_only`: the feature is retained with rules text because it depends on active play timing, conditions, reactions, or temporary states.

## Data Import

The app uses normalized local data generated from the 5e.tools JSON mirror.

```powershell
.\.venv\Scripts\python.exe tools\import_5etools.py
```

That command downloads selected raw files into `data/raw/5etools/`, writes app-ready files into `data/imported/5etools/`, and regenerates `data/coverage/imported_feature_audit.json`.

If the raw files are already present, you can refresh the normalized files without downloading:

```powershell
.\.venv\Scripts\python.exe tools\import_5etools.py --skip-download
```

## Coverage Audits

The stabilization pass includes coverage files in `data/coverage/`:

- `subclass_level_3_coverage.json`
- `level_5_8_choice_coverage.json`
- `level_9_12_feature_choice_map.json`
- `level_13_16_feature_choice_map.json`
- `level_1_20_feature_choice_map.json`
- `imported_feature_audit.json`

The generated audit lists imported class features, subclass features, subclass spell grants, species traits, background features, and general feats. Known automation points include their handler, expected sheet fields when relevant, and imported child-feature references. Active-play timing effects are kept descriptive by design.

The imported feature audit also includes explicit expected-value checkpoints for high-risk progression values such as Metamagic totals, Battle Master dice/maneuvers, Action Surge uses, Feral Senses, and Paladin aura range. The test suite compares those checkpoints against the actual calculation output.

## Tests

Run the full test suite with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests
```

The tests cover representative builds, level-up drafts, subclass rules, spell and feature descriptions, PDF export helpers, feat support, Epic Boon support, Wizard Spell Mastery support, level 5-20 stabilization, sheet-value resources, and generated coverage audit shape.

For release verification, the tests also build level 20 sheets for every imported class/subclass path, round-trip characters through save/load migration, verify audit expected-value checkpoints, and check that the portable zip excludes generated/local-only files.

## PDF Import and Round Trip

Use **Save / Load > Import editable PDF**.

- PDFs exported by this builder contain
  `dnd-character-builder-state.json`. The attachment uses a versioned JSON
  envelope, a SHA-256 checksum, and a snapshot of builder-owned visible PDF
  fields. These imports preserve the canonical character state exactly.
- Older editable PDFs using the supported WotC-style template open a review
  wizard. Confirm recovered identity, ability baseline, choices, spells,
  equipment, and maximum HP before adoption.
- Visible calculated values are comparison evidence. They never silently
  overwrite structured character choices.
- Unmodeled safe scalar fields such as alignment, backstory, appearance, and
  currency are preserved for later PDF exports. Builder-owned calculated
  fields always take precedence.
- Import does not automatically create or overwrite a JSON save. Use
  **Save Character** after reviewing the adopted character.

The active character is replaced only after the detached candidate has
successfully migrated, recalculated, and passed current-state validation.
Confirmed adoption clears stale character widgets and level-up drafts, opens
the Character Sheet tab, and records import provenance. Level up stays disabled
until the imported state and normal character validation are complete.

For safety, the importer rejects malformed, encrypted, oversized, flattened,
unrelated, checksum-failing, or unsupported PDFs with an actionable error.
Raw PDF bytes, upload paths, Streamlit widget state, and active level-up drafts
are never stored in character JSON.

## Portable Zip

Build a fresh portable source zip with:

```powershell
.\.venv\Scripts\python.exe tools\package_project.py
```

The zip excludes `.venv`, `.tmp`, temporary folders, generated PDFs, saved character JSON files, test caches, and older zip files. It includes the setup/start shortcuts and the local imported rules data needed to run the app after installing dependencies.

It also includes the editable PDF template and all import/reconciliation
modules. Generated character PDFs and imported/saved character data remain
local and are intentionally excluded from the portable source package.
