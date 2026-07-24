from copy import deepcopy

from models.character import DEFAULT_CHARACTER


def change_character_class(character, new_class):
    if character.get("class") == new_class:
        return character
    character["class"] = new_class
    character["subclass"] = ""
    character["level"] = 1
    character["class_levels"] = {new_class: 1} if new_class else {}
    character["class_options"] = {}
    character["spells"] = deepcopy(DEFAULT_CHARACTER["spells"])
    character["expertise"] = []
    character["weapon_masteries"] = []
    character["pending_choices"] = []
    character["feature_configurations"] = []
    character["level_history"] = []
    character["hit_dice"] = {}
    character["hp_rolls"] = []
    character["hp_history"] = []
    character["completed_level_up_transactions"] = []
    character["ability_score_adjustments"] = []
    character["ability_score_adjustment_bonuses"] = {}
    character["general_feats"] = []
    reset_hit_points(character)
    return character


def change_background(character, new_background):
    if character.get("background") == new_background:
        return character
    character["background"] = new_background
    character["background_options"] = {}
    character["origin_feats"] = []
    character["origin_feat_choices"] = deepcopy(DEFAULT_CHARACTER["origin_feat_choices"])
    return character


def change_species(character, new_species):
    if character.get("species") == new_species:
        return character
    character["species"] = new_species
    character["species_options"] = {}
    return character


def change_origin_feat(character, new_feat):
    current = character.get("species_options", {}).get("origin_feats", [])
    if current == [new_feat]:
        return character
    character.setdefault("species_options", {})["origin_feats"] = [new_feat] if new_feat else []
    character["origin_feat_choices"] = deepcopy(DEFAULT_CHARACTER["origin_feat_choices"])
    return character


def reset_hit_points(character):
    character["hit_points"] = deepcopy(DEFAULT_CHARACTER["hit_points"])
