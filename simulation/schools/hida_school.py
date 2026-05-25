#!/usr/bin/env python3

#
# hida_school.py
#
# Implement Hida Bushi School.
#
# School Ring: Water
# School Knacks: counterattack, iaijutsu, lunge
#
# Special Ability: You may counterattack as an interrupt action by spending
# only 1 action die, but if you do so then the attacker gets a free raise
# on their attack roll (+5).
#

from collections.abc import Iterator
from typing import Any

from simulation.events import TakeCounterattackActionEvent
from simulation.schools.base import BaseSchool
from simulation.strategies.base import CounterattackInterruptStrategy
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory


class HidaBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        character.set_interrupt_cost("counterattack", 1)
        character.set_take_action_event_factory(HIDA_TAKE_ACTION_EVENT_FACTORY)
        character.set_strategy("interrupt", CounterattackInterruptStrategy())

    def apply_rank_three_ability(self, character: Any) -> None:
        # TODO: Reroll 2X dice on counterattack or X dice on other attacks
        pass

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # TODO: Instead of wound check, spend 2 SW to reset LW to 0

    def apply_rank_five_ability(self, character: Any) -> None:
        # TODO: After successful counterattack, add excess roll to wound check;
        # may counterattack after seeing opponent's damage roll
        pass

    def extra_rolled(self) -> list[str]:
        return ["attack", "counterattack", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["counterattack"]

    def name(self) -> str:
        return "Hida Bushi School"

    def school_knacks(self) -> list[str]:
        return ["counterattack", "iaijutsu", "lunge"]

    def school_ring(self) -> str:
        return "water"


class HidaTakeCounterattackActionEvent(TakeCounterattackActionEvent):
    """Custom TakeCounterattackActionEvent for the Hida special ability.

    When the counterattack is used as an interrupt (1-die cost), the
    original attacker gets +5 to their attack roll (a free raise).
    Since the counterattack now happens before the attack roll, we
    store the bonus as a pending attribute on the attack action.
    """

    def play(self, context: Any) -> Iterator[Any]:
        if self.action.initiative_action().is_interrupt():
            original_attack = self.action.attack()
            bonus = getattr(original_attack, '_counterattack_roll_bonus', 0)
            original_attack._counterattack_roll_bonus = bonus + 5
        yield from super().play(context)


class HidaTakeActionEventFactory(DefaultTakeActionEventFactory):
    """Custom TakeActionEventFactory that returns Hida-specific counterattack events."""

    def get_take_counterattack_action_event(self, action: Any) -> Any:
        return HidaTakeCounterattackActionEvent(action)


HIDA_TAKE_ACTION_EVENT_FACTORY = HidaTakeActionEventFactory()
