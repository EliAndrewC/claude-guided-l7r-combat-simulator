#!/usr/bin/env python3

#
# ikoma_bard_school.py
#
# Implement Ikoma Bard School.
#
# School Ring: Water (default; rules say "any non-Void")
# School Knacks: discern honor, oppose knowledge, oppose social
#
# Special Ability: Once per round, force opponent to parry your attack
#                  (opponent does not get a free raise for pre-declaring).
# 1st Dan: Extra rolled on attack, bragging, wound check
# 2nd Dan: Free raise on attack
# 3rd Dan: AP system — ap_base_skill = "bragging", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; unparried attack without extra kept damage dice -> roll 10 damage dice
# 5th Dan: Use special ability or oppose knack an extra time per round;
#          may cancel opponent's attack and use their roll as parry.
#

from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.schools.base import BaseSchool


class IkomaBardSchool(BaseSchool):
    def ap_base_skill(self):
        return "bragging"

    def ap_skills(self):
        return ["attack", "wound check"]

    def apply_special_ability(self, character):
        # Force opponent to parry: in the current simulator, parry decisions
        # are made by the target's interrupt strategy after the attack roll.
        # The Bard's ability forces a parry before the roll.
        # TODO: implement forced parry via custom TakeActionEventFactory
        pass

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_roll_parameter_provider(IkomaFourthDanRollParameterProvider())

    def apply_rank_five_ability(self, character):
        # Extra use of special ability or oppose knack per round;
        # can cancel opponent's attack after seeing their roll.
        # TODO: implement 5th Dan
        pass

    def extra_rolled(self):
        return ["attack", "bragging", "wound check"]

    def free_raise_skills(self):
        return ["attack"]

    def name(self):
        return "Ikoma Bard School"

    def school_knacks(self):
        return ["discern honor", "oppose knowledge", "oppose social"]

    def school_ring(self):
        return "water"


class IkomaFourthDanRollParameterProvider(DefaultRollParameterProvider):
    """4th Dan: unparried attack without extra kept damage dice -> always roll 10 dice."""

    def get_damage_roll_params(self, character, target, skill, attack_extra_rolled, vp=0):
        rolled, kept, modifier = super().get_damage_roll_params(character, target, skill, attack_extra_rolled, vp)
        # If no extra kept damage dice (attack_extra_rolled == 0 means no raises
        # were called on the attack), roll 10 dice
        if attack_extra_rolled == 0:
            rolled = max(rolled, 10)
        return normalize_roll_params(rolled, kept, modifier)
