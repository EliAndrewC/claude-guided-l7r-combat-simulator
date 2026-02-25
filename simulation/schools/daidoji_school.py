#!/usr/bin/env python3

#
# daidoji_school.py
#
# Implement Daidoji Yojimbo School.
#
# School Ring: Water
# School Knacks: counterattack, double attack, iaijutsu
#
# Special Ability: You may counterattack as an interrupt action by spending
# only 1 action die, but if you do so then your opponent gets a free raise
# on their wound check if you hit.  You may counterattack for other
# characters at no penalty.
#

from simulation.actions import CounterattackAction
from simulation.events import (
    CounterattackDeclaredEvent,
    CounterattackFailedEvent,
    CounterattackRolledEvent,
    CounterattackSucceededEvent,
    LightWoundsDamageEvent,
    SpendVoidPointsEvent,
    TakeCounterattackActionEvent,
)
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import CounterattackInterruptStrategy
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory


class DaidojiYojimboSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        character.set_interrupt_cost("counterattack", 1)
        character.set_action_factory(DAIDOJI_ACTION_FACTORY)
        character.set_take_action_event_factory(DAIDOJI_TAKE_ACTION_EVENT_FACTORY)
        character.set_strategy("interrupt", CounterattackInterruptStrategy())

    def apply_rank_three_ability(self, character):
        # TODO: Add X free raises to wound check from original attack (X = attack skill)
        pass

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # TODO: Choose to take damage from hits to adjacent characters before damage rolls

    def apply_rank_five_ability(self, character):
        # TODO: After successful wound check, lower next attacker's TN by amount
        # check exceeded damage (minimum 0)
        pass

    def extra_rolled(self):
        return ["attack", "counterattack", "wound check"]

    def free_raise_skills(self):
        return ["counterattack"]

    def name(self):
        return "Daidoji Yojimbo School"

    def school_knacks(self):
        return ["counterattack", "double attack", "iaijutsu"]

    def school_ring(self):
        return "water"


class DaidojiCounterattackAction(CounterattackAction):
    """Daidoji counterattacks have no TN penalty for counterattacking
    on behalf of other characters."""

    def tn(self):
        return self.target().tn_to_hit()


class DaidojiActionFactory(DefaultActionFactory):
    """ActionFactory that returns DaidojiCounterattackAction for counterattacks."""

    def get_counterattack_action(self, subject, target, attack, skill, initiative_action, context, vp=0):
        return DaidojiCounterattackAction(subject, target, skill, initiative_action, context, attack, vp=vp)


DAIDOJI_ACTION_FACTORY = DaidojiActionFactory()


class DaidojiTakeCounterattackActionEvent(TakeCounterattackActionEvent):
    """Custom TakeCounterattackActionEvent for the Daidoji special ability.

    When the counterattack is used as an interrupt (1-die cost) and hits,
    the opponent gets a free raise on their wound check (+5 to roll,
    implemented as -5 on the wound check TN).
    """

    def play(self, context):
        yield CounterattackDeclaredEvent(self.action)
        self.action.roll_skill()
        if self.action.vp() > 0:
            yield SpendVoidPointsEvent(self.action.subject(), self.action.skill(), self.action.vp())
        yield CounterattackRolledEvent(self.action, self.action.skill_roll())
        if self.action.is_hit():
            yield CounterattackSucceededEvent(self.action)
            if self.action.target().is_fighting():
                damage = self.action.roll_damage()
                if self.action.initiative_action().is_interrupt():
                    # Daidoji penalty: opponent gets free raise on wound check (-5 TN)
                    wound_check_tn = max(0, damage - 5)
                    yield LightWoundsDamageEvent(
                        self.action.subject(), self.action.target(), damage, tn=wound_check_tn,
                    )
                else:
                    yield LightWoundsDamageEvent(
                        self.action.subject(), self.action.target(), damage,
                    )
        else:
            yield CounterattackFailedEvent(self.action)


class DaidojiTakeActionEventFactory(DefaultTakeActionEventFactory):
    """Custom TakeActionEventFactory that returns Daidoji-specific counterattack events."""

    def get_take_counterattack_action_event(self, action):
        return DaidojiTakeCounterattackActionEvent(action)


DAIDOJI_TAKE_ACTION_EVENT_FACTORY = DaidojiTakeActionEventFactory()
