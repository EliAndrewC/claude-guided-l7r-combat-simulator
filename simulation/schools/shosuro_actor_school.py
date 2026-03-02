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
from simulation.mechanics.roll_provider import RollProvider
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.schools.base import BaseSchool


class ShosuroActorSchool(BaseSchool):
    def ap_base_skill(self):
        return "sincerity"

    def ap_skills(self):
        return ["acting", "heraldry", "sincerity", "sneaking", "attack", "wound check"]

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
        character.set_roll_provider(ShosuroActorRollProvider(character.roll_provider()))

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


class ShosuroActorRollProvider(RollProvider):
    """Wrap an existing roll provider to add lowest 3 dice to skill and wound check results.

    Implements the Shosuro Actor School 5th Dan ability:
    "After making any TN or contested roll, add your lowest three dice to the result.
    (Some dice may be counted twice.)"

    TN/contested rolls are skill rolls and wound checks.
    Damage rolls and initiative rolls are NOT modified.
    """

    def __init__(self, inner):
        self._inner = inner

    def die_provider(self):
        return self._inner.die_provider()

    def get_damage_reduction_roll(self, rolled, kept, reduction):
        return self._inner.get_damage_reduction_roll(rolled, kept, reduction)

    def get_damage_roll(self, rolled, kept):
        return self._inner.get_damage_roll(rolled, kept)

    def get_initiative_roll(self, rolled, kept):
        return self._inner.get_initiative_roll(rolled, kept)

    def get_skill_roll(self, skill, rolled, kept, explode=True):
        result = self._inner.get_skill_roll(skill, rolled, kept, explode)
        bonus = self._lowest_three_bonus(self._inner.last_skill_info())
        return result + bonus

    def get_wound_check_roll(self, rolled, kept, explode=True):
        result = self._inner.get_wound_check_roll(rolled, kept, explode=explode)
        bonus = self._lowest_three_bonus(self._inner.last_wound_check_info())
        return result + bonus

    def last_damage_info(self):
        return self._inner.last_damage_info()

    def last_skill_info(self):
        return self._inner.last_skill_info()

    def last_wound_check_info(self):
        return self._inner.last_wound_check_info()

    def set_die_provider(self, die_provider):
        self._inner.set_die_provider(die_provider)

    @staticmethod
    def _lowest_three_bonus(info):
        """Return the sum of the lowest 3 dice from roll info, or 0 if unavailable."""
        if info is None:
            return 0
        dice = info.get("dice")
        if dice is None:
            return 0
        sorted_dice = sorted(dice)
        return sum(sorted_dice[:3])


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
