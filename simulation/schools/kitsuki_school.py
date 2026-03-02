#!/usr/bin/env python3

#
# kitsuki_school.py
#
# Implement Kitsuki Magistrate School.
#
# School Ring: Water
# School Knacks: discern honor, iaijutsu, presence
#
# Special Ability: Add 2*Water to all attack rolls.
# 1st Dan: Extra rolled on investigation, interrogation, wound check
# 2nd Dan: Free raise on interrogation
# 3rd Dan: AP system — ap_base_skill = "investigation", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; know Void, parry, and phase of next action (knowledge)
# 5th Dan: Reduce Air, Fire, Water of chosen characters by 1.
#

from simulation import events
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.schools.base import BaseSchool


class KitsukiMagistrateSchool(BaseSchool):
    def ap_base_skill(self):
        return "investigation"

    def ap_skills(self):
        return ["attack", "wound check"]

    def apply_special_ability(self, character):
        character.set_roll_parameter_provider(KitsukiRollParameterProvider())

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # TODO: automatically know Void, parry, and phase of each character's next action

    def apply_rank_five_ability(self, character):
        # Reduce Air, Fire, Water of all opponents by 1 on the first round.
        existing_listener = character._listeners.get("new_round")
        character.set_listener(
            "new_round",
            KitsukiFifthDanNewRoundListener(existing_listener),
        )

    def extra_rolled(self):
        return ["interrogation", "investigation", "wound check"]

    def free_raise_skills(self):
        return ["interrogation"]

    def name(self):
        return "Kitsuki Magistrate School"

    def school_knacks(self):
        return ["discern honor", "iaijutsu", "presence"]

    def school_ring(self):
        return "water"


class KitsukiRollParameterProvider(DefaultRollParameterProvider):
    """Add 2*Water to all attack roll modifiers."""

    def get_skill_roll_params(self, character, target, skill, contested_skill=None, ring=None, vp=0):
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        if skill in ATTACK_SKILLS:
            modifier += 2 * character.ring("water")
        return normalize_roll_params(rolled, kept, modifier)


class KitsukiFifthDanNewRoundListener(Listener):
    """5th Dan: On the first round of combat, reduce all opponents'
    Air, Fire, and Water rings by 1 (minimum 1).

    Wraps an existing new_round listener so initiative is still rolled.
    """

    def __init__(self, wrapped_listener):
        self._wrapped = wrapped_listener
        self._applied = False

    def handle(self, character, event, context):
        # Delegate to the wrapped listener first (rolls initiative)
        if self._wrapped is not None:
            yield from self._wrapped.handle(character, event, context)
        else:
            if isinstance(event, events.NewRoundEvent):
                character.roll_initiative()
                yield from ()

        # Apply ring reduction only on the first NewRoundEvent
        if isinstance(event, events.NewRoundEvent) and not self._applied:
            self._applied = True
            kitsuki_group = character.group()
            for other in context.characters():
                if other not in kitsuki_group:
                    for ring_name in ("air", "fire", "water"):
                        current = other.ring(ring_name)
                        new_value = max(1, current - 1)
                        other.set_ring(ring_name, new_value)
                    logger.info(
                        f"{character.name()} (Kitsuki 5th Dan) reduces "
                        f"{other.name()}'s Air, Fire, and Water by 1"
                    )
