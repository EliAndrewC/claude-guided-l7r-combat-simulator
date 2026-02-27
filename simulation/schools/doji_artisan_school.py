#!/usr/bin/env python3

#
# doji_artisan_school.py
#
# Implement Doji Artisan School.
#
# School Ring: Water (default; rules say "Air or Water")
# School Knacks: counterattack, oppose social, worldliness
#
# Special Ability: Spend VP to counterattack as interrupt (cost 1 action die);
#                  VP gives +1k1. While counterattacking, bonus = attacker's roll / 5.
# 1st Dan: Extra rolled on counterattack, manipulation, wound check
# 2nd Dan: Free raise on manipulation
# 3rd Dan: AP system — ap_base_skill = "culture", ap_skills = ["counterattack", "wound check"]
# 4th Dan: Ring+1/discount; attacking target who hasn't attacked you this round,
#          bonus = current phase.
# 5th Dan: On TN/contested rolls, bonus = (X-10)/5 where X = TN or opponent's roll.
#

from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.schools.base import BaseSchool
from simulation.strategies.base import CounterattackInterruptStrategy


class DojiArtisanSchool(BaseSchool):
    def ap_base_skill(self):
        return "culture"

    def ap_skills(self):
        return ["counterattack", "wound check"]

    def apply_special_ability(self, character):
        # Counterattack as interrupt at cost of 1 action die
        character.set_interrupt_cost("counterattack", 1)
        character.set_strategy("interrupt", CounterattackInterruptStrategy())
        # TODO: implement VP spending for interrupt counterattack and bonus = attacker's roll / 5

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # TODO: phase bonus when attacking target who hasn't attacked this round

    def apply_rank_five_ability(self, character):
        # On TN/contested rolls, bonus = (X-10)/5 where X = TN or opponent's roll.
        # This requires knowing the TN or opponent's contested roll at roll time.
        character.set_roll_parameter_provider(DojiFifthDanRollParameterProvider())

    def extra_rolled(self):
        return ["counterattack", "manipulation", "wound check"]

    def free_raise_skills(self):
        return ["manipulation"]

    def name(self):
        return "Doji Artisan School"

    def school_knacks(self):
        return ["counterattack", "oppose social", "worldliness"]

    def school_ring(self):
        return "water"


class DojiFifthDanRollParameterProvider(DefaultRollParameterProvider):
    """5th Dan: on TN/contested rolls, bonus = max(0, (TN - 10) / 5)."""

    def get_skill_roll_params(self, character, target, skill, contested_skill=None, ring=None, vp=0):
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        # For attack rolls, the TN is the target's TN to hit
        if target is not None:
            tn = target.tn_to_hit()
            bonus = max(0, (tn - 10) // 5)
            modifier += bonus
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character, vp=0):
        rolled, kept, modifier = super().get_wound_check_roll_params(character, vp)
        # For wound checks, X = LW total (the TN).
        # Since we don't have the TN at this point, we use LW.
        lw = character.lw()
        bonus = max(0, (lw - 10) // 5)
        modifier += bonus
        return normalize_roll_params(rolled, kept, modifier)
