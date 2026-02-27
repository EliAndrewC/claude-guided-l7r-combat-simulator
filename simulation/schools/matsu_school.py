#!/usr/bin/env python3

#
# matsu_school.py
#
# Implement Matsu Bushi School.
#
# School Ring: Fire
# School Knacks: double attack, iaijutsu, lunge
#
# Special Ability: Always roll 10 dice on initiative.
# 1st Dan: Extra rolled on double attack, iaijutsu, wound check
# 2nd Dan: Free raise on iaijutsu
# 3rd Dan: On any VP spend, gain WoundCheckFloatingBonus(3 * attack_skill)
# 4th Dan: Ring+1/discount; custom MatsuDoubleAttackAction where is_hit()
#          returns True if within 20 of TN (near-miss), but
#          calculate_extra_damage_dice returns 0 for near-misses
# 5th Dan: When Matsu's attack causes a failed wound check,
#          set defender's LW to 15 instead of 0
#

from simulation import events
from simulation.actions import DoubleAttackAction
from simulation.listeners import Listener
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.mechanics.roll_provider import DefaultRollProvider
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory


class MatsuBushiSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        character.set_roll_provider(MATSU_ROLL_PROVIDER)

    def apply_rank_three_ability(self, character):
        character.set_listener("spend_vp", MatsuSpendVoidPointsListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_action_factory(MATSU_ACTION_FACTORY)

    def apply_rank_five_ability(self, character):
        character.set_listener("wound_check_failed", MatsuWoundCheckFailedListener())

    def extra_rolled(self):
        return ["double attack", "iaijutsu", "wound check"]

    def free_raise_skills(self):
        return ["iaijutsu"]

    def name(self):
        return "Matsu Bushi School"

    def school_knacks(self):
        return ["double attack", "iaijutsu", "lunge"]

    def school_ring(self):
        return "fire"


class MatsuRollProvider(DefaultRollProvider):
    """
    RollProvider to implement the Matsu special ability:
    always roll 10 dice on initiative.
    """

    def get_initiative_roll(self, rolled, kept):
        return super().get_initiative_roll(max(rolled, 10), kept)


MATSU_ROLL_PROVIDER = MatsuRollProvider()


class MatsuSpendVoidPointsListener(Listener):
    """
    Listener to implement the Matsu 3rd Dan technique:
    on any VP spend, gain WoundCheckFloatingBonus(3 * attack_skill).
    """

    def handle(self, character, event, context):
        if isinstance(event, events.SpendVoidPointsEvent):
            if event.subject == character:
                character.spend_vp(event.amount)
                bonus = 3 * character.skill("attack")
                character.gain_floating_bonus(WoundCheckFloatingBonus(bonus))
        yield from ()


class MatsuDoubleAttackAction(DoubleAttackAction):
    """
    Custom DoubleAttackAction for Matsu 4th Dan:
    is_hit() returns True if within 20 of TN (near-miss),
    but calculate_extra_damage_dice returns 0 for near-misses.
    """

    def is_hit(self):
        if self.parried():
            return False
        # Hit if skill roll is within 20 below TN (near-miss) or above TN
        return self.skill_roll() >= self.tn() - 20

    def calculate_extra_damage_dice(self, skill_roll=None, tn=None):
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn()
        # Near-miss: hit but below actual TN
        if skill_roll < tn:
            return 0
        # Normal hit: use standard DoubleAttackAction logic
        return super().calculate_extra_damage_dice(skill_roll, tn)

    def direct_damage(self):
        if self.parry_attempted():
            return None
        # Near-miss: no direct SW damage
        if self.skill_roll() < self.tn():
            return None
        return super().direct_damage()


class MatsuActionFactory(DefaultActionFactory):
    """
    ActionFactory to return Matsu-specific attack actions.
    """

    def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
        if skill == "double attack":
            return MatsuDoubleAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


MATSU_ACTION_FACTORY = MatsuActionFactory()


class MatsuWoundCheckFailedListener(Listener):
    """
    Listener to implement the Matsu 5th Dan technique:
    when Matsu's attack causes a failed wound check,
    set defender's LW to 15 instead of 0.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.WoundCheckFailedEvent):
            if event.attacker == character:
                # The standard WoundCheckFailedListener will reset LW to 0
                # and yield SeriousWoundsDamageEvent. We intervene to set LW to 15.
                sw = event.subject.wound_check(event.roll)
                event.subject.reset_lw()
                event.subject._lw = 15
                yield events.SeriousWoundsDamageEvent(character, event.subject, sw)
            elif event.subject == character:
                # Matsu taking their own wound check failure - standard behavior
                sw = character.wound_check(event.roll)
                character.reset_lw()
                yield events.SeriousWoundsDamageEvent(event.attacker, character, sw)
