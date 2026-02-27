#!/usr/bin/env python3

#
# mirumoto_school.py
#
# Implement Mirumoto Bushi School.
#
# School Ring: Void
# School Knacks: counterattack, double attack, iaijutsu
#
# Special Ability: TVP on parry (success or fail).
# 1st Dan: Extra rolled on attack, double attack, parry
# 2nd Dan: Free raise on parry
# 3rd Dan: NewRoundListener grants 2*attack_skill resource points.
#          Spend to decrease action die by 1 for parry, or +2 on attack/parry after seeing roll.
# 4th Dan: Ring+1/discount; failed parries subtract only half the normal extra damage dice (round down).
# 5th Dan: VP provides +10 instead of +5 on combat rolls.
#

from simulation import events
from simulation.actions import ParryAction
from simulation.listeners import Listener
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import CounterattackInterruptStrategy


class MirumotoBushiSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        character.set_listener("parry_succeeded", MirumotoParryTVPListener())
        character.set_listener("parry_failed", MirumotoParryTVPListener())
        character.set_interrupt_cost("counterattack", 1)
        character.set_strategy("interrupt", CounterattackInterruptStrategy())

    def apply_rank_three_ability(self, character):
        character.set_listener("new_round", MirumotoNewRoundListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_action_factory(MIRUMOTO_ACTION_FACTORY)

    def apply_rank_five_ability(self, character):
        character.set_roll_parameter_provider(MIRUMOTO_ROLL_PARAMETER_PROVIDER)

    def extra_rolled(self):
        return ["attack", "double attack", "parry"]

    def free_raise_skills(self):
        return ["parry"]

    def name(self):
        return "Mirumoto Bushi School"

    def school_knacks(self):
        return ["counterattack", "double attack", "iaijutsu"]

    def school_ring(self):
        return "void"


class MirumotoParryTVPListener(Listener):
    """
    Listener to implement the Mirumoto special ability:
    gain 1 TVP on parry (success or fail).
    """

    def handle(self, character, event, context):
        if isinstance(event, (events.ParrySucceededEvent, events.ParryFailedEvent)):
            if event.action.subject() == character:
                yield events.GainTemporaryVoidPointsEvent(character, 1)


class MirumotoNewRoundListener(Listener):
    """
    Listener to implement the Mirumoto 3rd Dan technique:
    At the start of each round, grant 2*attack_skill resource points.
    These are stored as a pool on the character that can be spent
    to decrease action die phase by 1 for parry or +2 on attack/parry after seeing roll.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            # Grant resource pool
            pool = 2 * character.skill("attack")
            character._mirumoto_pool = pool
        yield from ()


class MirumotoParryAction(ParryAction):
    """
    Custom ParryAction for Mirumoto 4th Dan:
    Failed parries subtract only half the normal extra damage dice (round down).
    This is implemented by overriding the attack's calculate_extra_damage_dice
    when the parry fails.
    """

    def set_attack_parry_attempted(self):
        super().set_attack_parry_attempted()
        # Override the attack's extra damage dice calculation for failed parries
        attack = self.attack()
        original_calc = attack.calculate_extra_damage_dice

        def half_extra_damage_dice(skill_roll=None, tn=None):
            result = original_calc(skill_roll, tn)
            # On failed parry, halve the extra damage dice (round down)
            return result // 2

        attack.calculate_extra_damage_dice = half_extra_damage_dice


class MirumotoActionFactory(DefaultActionFactory):
    """
    ActionFactory for Mirumoto: returns MirumotoParryAction for parries.
    """

    def get_parry_action(self, subject, target, attack, skill, initiative_action, context, vp=0):
        return MirumotoParryAction(subject, target, skill, initiative_action, context, attack, vp=vp)


MIRUMOTO_ACTION_FACTORY = MirumotoActionFactory()


class MirumotoRollParameterProvider(DefaultRollParameterProvider):
    """
    RollParameterProvider to implement the Mirumoto 5th Dan ability:
    VP provides +10 instead of +5 on combat rolls.
    """

    def get_skill_roll_params(self, character, target, skill, contested_skill=None, ring=None, vp=0):
        (rolled, kept, modifier) = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        # Add extra +5 per VP (total +10 instead of +5)
        if vp > 0:
            modifier += 5 * vp
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character, vp=0):
        (rolled, kept, modifier) = super().get_wound_check_roll_params(character, vp)
        # Add extra +5 per VP (total +10 instead of +5)
        if vp > 0:
            modifier += 5 * vp
        return normalize_roll_params(rolled, kept, modifier)


MIRUMOTO_ROLL_PARAMETER_PROVIDER = MirumotoRollParameterProvider()
