def normalize_score_assignments(abilities, scores, assignments=None):
    assignments = dict(assignments or {})
    normalized = {}
    used_slots = set()
    for index, ability in enumerate(abilities):
        slot = assignments.get(ability)
        if not isinstance(slot, int) or slot < 0 or slot >= len(scores) or slot in used_slots:
            slot = next(
                (candidate for candidate in range(len(scores)) if candidate not in used_slots),
                0,
            )
        normalized[ability] = slot
        used_slots.add(slot)
    return normalized


def swap_score_assignment(abilities, scores, assignments, ability, new_slot):
    assignments = normalize_score_assignments(abilities, scores, assignments)
    if ability not in assignments or new_slot not in range(len(scores)):
        return assignments

    old_slot = assignments[ability]
    if old_slot == new_slot:
        return assignments

    other_ability = next(
        (
            candidate
            for candidate, slot in assignments.items()
            if candidate != ability and slot == new_slot
        ),
        None,
    )
    assignments[ability] = new_slot
    if other_ability:
        assignments[other_ability] = old_slot
    return assignments
