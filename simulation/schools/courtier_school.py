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

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.schools.base import BaseSchool


class CourtierSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return "tact"

    def ap_skills(self) -> list[str]:
        return ["attack", "wound check"]

    def apply_special_ability(self, character: Any) -> None:
        self._set_school_roll_parameter_provider(character, CourtierRollParameterProvider())

    def apply_rank_three_ability(self, character: Any) -> None:
        self.apply_ap(character)

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_listener(character, "attack_succeeded", CourtierAttackSucceededListener())

    def apply_rank_five_ability(self, character: Any) -> None:
        # Upgrade provider to 5th Dan version which adds Air to ALL TN/contested rolls
        self._set_school_roll_parameter_provider(character, CourtierFifthDanRollParameterProvider())

    def extra_rolled(self) -> list[str]:
        return ["manipulation", "tact", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["manipulation"]

    def name(self) -> str:
        return "Courtier School"

    def school_knacks(self) -> list[str]:
        return ["discern honor", "oppose social", "worldliness"]

    def school_ring(self) -> str:
        return "air"


class CourtierRollParameterProvider(DefaultRollParameterProvider):
    """Add Air to all attack and damage roll modifiers (special ability)."""

    def get_skill_roll_params(self, character: Any, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        if skill in ATTACK_SKILLS:
            modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)

    def get_damage_roll_params(self, character: Any, target: Any, skill: str, attack_extra_rolled: int, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_damage_roll_params(character, target, skill, attack_extra_rolled, vp)
        modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)


class CourtierFifthDanRollParameterProvider(CourtierRollParameterProvider):
    """Add Air to ALL TN and contested roll modifiers (5th Dan, stacks with special)."""

    def get_skill_roll_params(self, character: Any, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        # 5th Dan adds Air to all TN/contested rolls; special already adds Air to attacks
        # so for non-attack skills, add Air here
        if skill not in ATTACK_SKILLS:
            modifier += character.ring("air")
        else:
            # attack rolls already get Air from special; 5th Dan stacks
            modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character: Any, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_wound_check_roll_params(character, vp)
        modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)


class CourtierAttackSucceededListener(Listener):
    """4th Dan: gain TVP on successful attack, once per target per fight."""

    def __init__(self) -> None:
        self._targets_triggered: set[Any] = set()

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackSucceededEvent):
            if event.action.subject() == character:
                target_id = event.action.target().character_id()
                if target_id not in self._targets_triggered:
                    self._targets_triggered.add(target_id)
                    yield events.GainTemporaryVoidPointsEvent(character, 1)
                    return
        yield from ()
