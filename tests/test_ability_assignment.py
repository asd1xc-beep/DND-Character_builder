from models.character import ABILITIES
from rules.ability_assignment import normalize_score_assignments, swap_score_assignment


def test_normalize_score_assignments_repairs_duplicate_slots():
    assignments = {
        "Strength": 0,
        "Dexterity": 0,
        "Constitution": 7,
    }

    normalized = normalize_score_assignments(ABILITIES, [15, 14, 13, 12, 10, 8], assignments)

    assert sorted(normalized.values()) == [0, 1, 2, 3, 4, 5]
    assert normalized["Strength"] == 0


def test_swap_score_assignment_trades_scores_between_abilities():
    scores = [15, 14, 13, 12, 10, 8]
    assignments = normalize_score_assignments(ABILITIES, scores)

    swapped = swap_score_assignment(ABILITIES, scores, assignments, "Charisma", 0)

    assert swapped["Charisma"] == 0
    assert swapped["Strength"] == 5
    assert sorted(swapped.values()) == [0, 1, 2, 3, 4, 5]


def test_swap_score_assignment_works_with_duplicate_rolled_values():
    scores = [15, 15, 13, 12, 10, 8]
    assignments = normalize_score_assignments(ABILITIES, scores)

    swapped = swap_score_assignment(ABILITIES, scores, assignments, "Wisdom", 1)

    assert swapped["Wisdom"] == 1
    assert swapped["Dexterity"] == 4
    assert sorted(swapped.values()) == [0, 1, 2, 3, 4, 5]
