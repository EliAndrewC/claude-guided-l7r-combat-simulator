#!/usr/bin/env python3

#
# courtier_school.py
#
# Implement Courtier School.
#
# School Ring: Air
# School Knacks: discern honor, oppose social, worldliness
#
# Special Ability: Add Air to all attack and damage rolls.
# 1st Dan: Extra rolled on tact, manipulation, wound check
# 2nd Dan: Free raise on manipulation
# 3rd Dan: AP system — ap_base_skill = "tact", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; TVP on successful attack (once per target per fight)
# 5th Dan: Add Air to all TN and contested rolls (stacks with special for attack)
#

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.schools.base import BaseSchool


class CourtierSchool(BaseSchool):
    def ap_base_skill(self):
        return "tact"

    def ap_skills(self):
        return ["attack", "wound check"]

    def apply_special_ability(self, character):
        character.set_roll_parameter_provider(CourtierRollParameterProvider())

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_listener("attack_succeeded", CourtierAttackSucceededListener())

    def apply_rank_five_ability(self, character):
        # Upgrade provider to 5th Dan version which adds Air to ALL TN/contested rolls
        character.set_roll_parameter_provider(CourtierFifthDanRollParameterProvider())

    def extra_rolled(self):
        return ["manipulation", "tact", "wound check"]

    def free_raise_skills(self):
        return ["manipulation"]

    def name(self):
        return "Courtier School"

    def school_knacks(self):
        return ["discern honor", "oppose social", "worldliness"]

    def school_ring(self):
        return "air"


class CourtierRollParameterProvider(DefaultRollParameterProvider):
    """Add Air to all attack and damage roll modifiers (special ability)."""

    def get_skill_roll_params(self, character, target, skill, contested_skill=None, ring=None, vp=0):
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        if skill in ATTACK_SKILLS:
            modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)

    def get_damage_roll_params(self, character, target, skill, attack_extra_rolled, vp=0):
        rolled, kept, modifier = super().get_damage_roll_params(character, target, skill, attack_extra_rolled, vp)
        modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)


class CourtierFifthDanRollParameterProvider(CourtierRollParameterProvider):
    """Add Air to ALL TN and contested roll modifiers (5th Dan, stacks with special)."""

    def get_skill_roll_params(self, character, target, skill, contested_skill=None, ring=None, vp=0):
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        # 5th Dan adds Air to all TN/contested rolls; special already adds Air to attacks
        # so for non-attack skills, add Air here
        if skill not in ATTACK_SKILLS:
            modifier += character.ring("air")
        else:
            # attack rolls already get Air from special; 5th Dan stacks
            modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character, vp=0):
        rolled, kept, modifier = super().get_wound_check_roll_params(character, vp)
        modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)


class CourtierAttackSucceededListener(Listener):
    """4th Dan: gain TVP on successful attack, once per target per fight."""

    def __init__(self):
        self._targets_triggered = set()

    def handle(self, character, event, context):
        if isinstance(event, events.AttackSucceededEvent):
            if event.action.subject() == character:
                target_id = event.action.target().character_id()
                if target_id not in self._targets_triggered:
                    self._targets_triggered.add(target_id)
                    yield events.GainTemporaryVoidPointsEvent(character, 1)
                    return
        yield from ()
