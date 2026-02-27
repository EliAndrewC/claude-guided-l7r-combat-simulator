#!/usr/bin/env python3

#
# yogo_school.py
#
# Implement Yogo Warden School.
#
# School Ring: Earth
# School Knacks: double attack, iaijutsu, feint
#
# Special Ability: Gain TVP when taking a serious wound.
#
# 1st Dan: Extra rolled on attack, damage, wound check
# 2nd Dan: Free raise on wound check
# 3rd Dan: SpendVoidPointsListener — on VP spend, reduce LW by 2*attack_skill
# 4th Dan: Ring+1/discount; +10 per VP on wound checks instead of +5
# 5th Dan: TBD
#

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.schools.base import BaseSchool


class YogoWardenSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        character.set_listener("sw_damage", YogoSeriousWoundsDamageListener())

    def apply_rank_three_ability(self, character):
        character.set_listener("spend_vp", YogoSpendVoidPointsListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_roll_parameter_provider(YOGO_ROLL_PARAMETER_PROVIDER)

    def apply_rank_five_ability(self, character):
        # TBD
        pass

    def extra_rolled(self):
        return ["attack", "damage", "wound check"]

    def free_raise_skills(self):
        return ["wound check"]

    def name(self):
        return "Yogo Warden School"

    def school_knacks(self):
        return ["double attack", "feint", "iaijutsu"]

    def school_ring(self):
        return "earth"


class YogoSeriousWoundsDamageListener(Listener):
    """
    Listener to implement the Yogo special ability
    to gain TVP when taking a serious wound.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.SeriousWoundsDamageEvent):
            if event.target == character:
                character.take_sw(event.damage)
                if not character.is_alive():
                    yield events.DeathEvent(character)
                elif not character.is_conscious():
                    yield events.UnconsciousEvent(character)
                elif not character.is_fighting():
                    yield events.SurrenderEvent(character)
                else:
                    yield events.GainTemporaryVoidPointsEvent(character, 1)
            else:
                character.knowledge().observe_wounds(event.target, event.damage)


class YogoSpendVoidPointsListener(Listener):
    """
    Listener to implement the Yogo 3rd Dan technique
    to reduce LW by 2*attack_skill when spending VP.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.SpendVoidPointsEvent):
            if event.subject == character:
                character.spend_vp(event.amount)
                reduction = 2 * character.skill("attack")
                new_lw = max(0, character.lw() - reduction)
                character._lw = new_lw
        yield from ()


class YogoRollParameterProvider(DefaultRollParameterProvider):
    """
    RollParameterProvider to implement the Yogo 4th Dan ability:
    +10 per VP on wound checks instead of +5.
    """

    def get_wound_check_roll_params(self, character, vp=0):
        ring = character.ring(character.get_skill_ring("wound check"))
        rolled = ring + 1 + character.extra_rolled("wound check") + vp
        kept = ring + character.extra_kept("wound check") + vp
        # +10 per VP instead of the normal +5
        modifier = character.modifier(None, "wound check") + (5 * vp)
        return normalize_roll_params(rolled, kept, modifier)


YOGO_ROLL_PARAMETER_PROVIDER = YogoRollParameterProvider()
