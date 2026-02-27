#!/usr/bin/env python3

#
# shosuro_actor_school.py
#
# Implement Shosuro Actor School.
#
# School Ring: Air
# School Knacks: athletics, discern honor, pontificate
#
# Special Ability: Roll extra dice equal to acting on attack, parry, wound check.
# 1st Dan: Extra rolled on attack, sincerity, wound check
# 2nd Dan: Free raise on sincerity
# 3rd Dan: AP system — ap_base_skill = "sincerity", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; stipend bonus (no-op in combat)
# 5th Dan: After TN/contested roll, add lowest 3 dice to result.
#

from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.schools.base import BaseSchool


class ShosuroActorSchool(BaseSchool):
    def ap_base_skill(self):
        return "sincerity"

    def ap_skills(self):
        return ["attack", "wound check"]

    def apply_special_ability(self, character):
        # Extra rolled dice equal to acting skill on attack, parry, and wound check.
        # Applied dynamically via a custom RollParameterProvider since acting
        # skill may increase during character building.
        character.set_roll_parameter_provider(ShosuroRollParameterProvider())

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # Rank 5.0 higher for stipend — no-op in combat

    def apply_rank_five_ability(self, character):
        # After any TN or contested roll, add lowest 3 dice to result.
        # This requires integration with the roll provider to track individual dice.
        # TODO: implement dice-tracking roll provider for 5th Dan
        pass

    def extra_rolled(self):
        return ["attack", "sincerity", "wound check"]

    def free_raise_skills(self):
        return ["sincerity"]

    def name(self):
        return "Shosuro Actor School"

    def school_knacks(self):
        return ["athletics", "discern honor", "pontificate"]

    def school_ring(self):
        return "air"


class ShosuroRollParameterProvider(DefaultRollParameterProvider):
    """Add acting skill rank as extra rolled dice on attack, parry, and wound check."""

    def get_skill_roll_params(self, character, target, skill, contested_skill=None, ring=None, vp=0):
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        if skill in ATTACK_SKILLS or skill == "parry":
            rolled += character.skill("acting")
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character, vp=0):
        rolled, kept, modifier = super().get_wound_check_roll_params(character, vp)
        rolled += character.skill("acting")
        return normalize_roll_params(rolled, kept, modifier)
