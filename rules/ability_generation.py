import random


STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]


def roll_ability_score(rng=None):
    rng = rng or random.SystemRandom()
    rolls = [rng.randint(1, 6) for _ in range(4)]
    return sum(sorted(rolls)[1:])


def roll_ability_scores(rng=None):
    rng = rng or random.SystemRandom()
    return sorted((roll_ability_score(rng) for _ in range(6)), reverse=True)
