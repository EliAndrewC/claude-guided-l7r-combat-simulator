#!/usr/bin/env python3

#
# priest_school.py
#
# Implement Priest School.
#
# School Ring: Water
# School Knacks: conviction, otherworldliness, pontificate
#
# Special Ability: Has all 10 rituals — no combat effect.
# 1st Dan: Extra rolled on precepts, initiative, wound check
# 2nd Dan: Free raise on bragging, precepts, sincerity (self + allies TODO)
# 3rd Dan: Roll X dice at combat start (X = precepts). Store as pool.
#          Each die can be spent as a flat bonus to attack/parry/WC/damage.
# 4th Dan: Ring+1/discount (+ contested roll free raises TODO)
# 5th Dan: Conviction on allies + refresh + lower action dice (TODO)
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.floating_bonuses import FloatingBonus
from simulation.schools.base import BaseSchool

PRIEST_POOL_SKILLS = ["attack", "parry", "wound check", "damage",
                      "double attack", "feint", "iaijutsu", "lunge",
                      "counterattack"]


class PriestSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # All 10 rituals — no combat effect
        pass

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_listener(character, "new_round", PriestNewRoundListener())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # TODO: free raise on contested rolls vs equal/higher skill (self + allies)

    def apply_rank_five_ability(self, character: Any) -> None:
        # TODO: conviction on allies' rolls + refresh each round + lower action dice
        pass

    def extra_rolled(self) -> list[str]:
        return ["precepts", "initiative", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["bragging", "precepts", "sincerity"]

    def name(self) -> str:
        return "Priest School"

    def school_knacks(self) -> list[str]:
        return ["conviction", "otherworldliness", "pontificate"]

    def school_ring(self) -> str:
        return "water"


class PriestNewRoundListener(Listener):
    """
    3rd Dan: At the start of each round, roll initiative and then roll X dice
    (X = precepts skill). Each die is stored as a floating bonus that can be
    applied to attack, parry, wound check, or damage rolls.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            precepts = character.skill("precepts")
            if precepts > 0:
                for _ in range(precepts):
                    die_value = character.roll_provider().get_skill_roll("precepts", 1, 1, True)
                    bonus = FloatingBonus(PRIEST_POOL_SKILLS, die_value)
                    character.gain_floating_bonus(bonus)
            yield from ()
