# Level 13-16 Support Audit

Generated from `data/coverage/level_13_16_feature_choice_map.json`.

## Summary

- Levels 13-16: enabled
- Required-choice blockers: 0
- Partial-support entries: 0
- Class feature entries needing classification: 0
- Subclass feature entries needing classification: 0

## Automated Sheet Values

- Monk 14 Disciplined Survivor: grants proficiency in all saving throws; the standing save proficiencies are automated. The failed-save Focus Point reroll remains descriptive.
- Rogue 15 Slippery Mind: grants Wisdom and Charisma saving throw proficiencies; both are automated.
- Wizard Diviner 14 Greater Portent: increases Portent dice from 2 to 3; automated as a resource.
- Ranger Fey Wanderer 15 Misty Wanderer: grants free Misty Step uses based on Wisdom modifier plus the willing-creature rider; automated as feature spell metadata.

## Likely Description-Only By Design

These appear to be combat timing, conditional movement, temporary defenses, rerolls, or narrative/active-play effects that do not have a clean standing field on the current sheet:

- Barbarian 13 Improved Brutal Strike
- Barbarian 15 Persistent Rage
- Cleric 14 Improved Blessed Strikes
- Druid 15 Improved Elemental Fury
- Fighter 13 Studied Attacks
- Monk 13 Deflect Energy
- Monk 15 Perfect Focus
- Paladin 14 Restoring Touch
- Ranger 13 Relentless Hunter
- Ranger 14 Nature's Veil
- Rogue 14 Devious Strikes
- Warlock Great Old One 14 Create Thrall

## Classified Subclass Entries

- Barbarian 14: Intimidating Presence, Power of the Wilds, Travel Along the Tree, Rage of the Gods
- Bard 14: Leading Evasion, Unbreakable Majesty, Peerless Skill, Battle Magic
- Druid 14: Nature's Sanctuary, Lunar Form, Oceanic Gift, Full of Stars
- Fighter 15: Relentless, Superior Critical, Arcane Charge, Bulwark of Force
- Paladin 15: Smite of Protection, Glorious Defense, Soul of Vengeance, Undying Sentinel
- Ranger 15: Share Spells, Misty Wanderer, Shadowy Dodge, Superior Hunter's Defense
- Rogue 13: Versatile Trickster, Envenom Weapons, Psychic Veil, Use Magic Device
- Sorcerer 14: Revelation in Flesh, Trance of Order, Dragon Wings, Controlled Chaos
- Warlock 14: Bewitching Magic, Searing Vengeance, Hurl Through Hell, Create Thrall
- Wizard 14: Spell Resistance, Greater Portent, Overchannel, Illusory Reality

## Recommended Next Pass

1. Run the same audit pattern for levels 17-20.
2. Verify capstone and epic-level feature handling before enabling the final band.
3. Keep the level 13-16 flow tests in place as regression coverage.
