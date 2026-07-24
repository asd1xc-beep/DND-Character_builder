from rules.ability_generation import STANDARD_ARRAY, roll_ability_score, roll_ability_scores


class FixedRoller:
    def __init__(self, rolls):
        self.rolls = list(rolls)

    def randint(self, low, high):
        value = self.rolls.pop(0)
        assert low <= value <= high
        return value


def test_standard_array_matches_2024_character_creation_default():
    assert STANDARD_ARRAY == [15, 14, 13, 12, 10, 8]


def test_roll_ability_score_uses_four_d6_drop_lowest():
    roller = FixedRoller([1, 2, 3, 4])
    assert roll_ability_score(roller) == 9


def test_roll_ability_scores_returns_six_scores_high_to_low():
    roller = FixedRoller([
        1, 2, 3, 4,
        6, 6, 6, 1,
        2, 2, 2, 2,
        5, 4, 3, 2,
        6, 5, 4, 3,
        1, 1, 1, 6,
    ])

    assert roll_ability_scores(roller) == [18, 15, 12, 9, 8, 6]
