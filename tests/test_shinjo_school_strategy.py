#!/usr/bin/env python3

#
# test_shinjo_school_strategy.py
#
# Unit tests for Shinjo Bushi School strategy bindings and
# apply_* ability wiring per spec 017 T-B1 + coverage padding.
#

import unittest

from simulation.character import Character
from simulation.schools import shinjo_school
from simulation.strategies.base import (
    AlwaysParryStrategy,
    HoldOneActionStrategy,
    WoundCheckStrategy04,
)


def _build_shinjo() -> tuple[Character, shinjo_school.ShinjoBushiSchool]:
    shinjo = Character("Shinjo")
    shinjo.set_skill("parry", 4)
    shinjo.set_skill("attack", 4)
    shinjo.set_ring("air", 4)
    school = shinjo_school.ShinjoBushiSchool()
    shinjo.set_school(school)
    return shinjo, school


class TestShinjoSpecialAbilityWiring(unittest.TestCase):
    def test_apply_special_ability_installs_hold_one_action_strategy(self) -> None:
        shinjo, school = _build_shinjo()
        school.apply_special_ability(shinjo)
        self.assertIsInstance(
            shinjo.action_strategy(), HoldOneActionStrategy,
        )

    def test_apply_special_ability_installs_always_parry_strategy(self) -> None:
        shinjo, school = _build_shinjo()
        school.apply_special_ability(shinjo)
        self.assertIsInstance(
            shinjo.parry_strategy(), AlwaysParryStrategy,
        )

    def test_apply_special_ability_installs_wound_check_strategy_04(self) -> None:
        shinjo, school = _build_shinjo()
        school.apply_special_ability(shinjo)
        self.assertIsInstance(
            shinjo.wound_check_strategy(), WoundCheckStrategy04,
        )

    def test_apply_special_ability_installs_spend_action_listener(self) -> None:
        shinjo, school = _build_shinjo()
        school.apply_special_ability(shinjo)
        # The listener is installed on the "spend_action" slot,
        # replacing the engine default.
        listener = shinjo._listeners.get("spend_action")
        self.assertIsInstance(listener, shinjo_school.ShinjoSpendActionListener)


class TestShinjoRankAbilities(unittest.TestCase):
    """Coverage for apply_rank_*_ability methods."""

    def test_apply_rank_three_installs_parry_listeners(self) -> None:
        shinjo, school = _build_shinjo()
        school.apply_rank_three_ability(shinjo)
        self.assertIsInstance(
            shinjo._listeners.get("parry_succeeded"),
            shinjo_school.ShinjoParryListener,
        )
        self.assertIsInstance(
            shinjo._listeners.get("parry_failed"),
            shinjo_school.ShinjoParryListener,
        )

    def test_apply_rank_four_installs_new_round_listener_and_air_raise(self) -> None:
        shinjo, school = _build_shinjo()
        air_before = shinjo.ring("air")
        school.apply_rank_four_ability(shinjo)
        self.assertEqual(air_before + 1, shinjo.ring("air"))
        self.assertIsInstance(
            shinjo._listeners.get("new_round"),
            shinjo_school.ShinjoNewRoundListener,
        )

    def test_apply_rank_five_installs_fifth_dan_listener(self) -> None:
        shinjo, school = _build_shinjo()
        school.apply_rank_five_ability(shinjo)
        # parry_succeeded -> 5th Dan listener, parry_failed -> 3rd Dan listener.
        self.assertIsInstance(
            shinjo._listeners.get("parry_succeeded"),
            shinjo_school.ShinjoFifthDanParryListener,
        )
        self.assertIsInstance(
            shinjo._listeners.get("parry_failed"),
            shinjo_school.ShinjoParryListener,
        )


class TestShinjoMisc(unittest.TestCase):
    """Coverage for trivial accessors."""

    def test_ap_base_skill_returns_none(self) -> None:
        school = shinjo_school.ShinjoBushiSchool()
        self.assertIsNone(school.ap_base_skill())

    def test_name(self) -> None:
        school = shinjo_school.ShinjoBushiSchool()
        self.assertEqual("Shinjo Bushi School", school.name())


class TestShinjoSpendActionListenerOtherSubject(unittest.TestCase):
    """Coverage padding for the subject-filter branch (line 93 in
    listener)."""

    def test_event_for_different_subject_yields_nothing(self) -> None:
        from simulation import events
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.mechanics.initiative_actions import InitiativeAction
        shinjo = Character("Shinjo")
        shinjo.set_actions([3])
        other = Character("Other")
        other.set_actions([3])
        groups = [Group("A", shinjo), Group("B", other)]
        ctx = EngineContext(groups, phase=5)
        ctx.initialize()
        ia = InitiativeAction([3], 3)
        # Event for 'other' character — the Shinjo's listener must
        # NOT act on it.
        event = events.SpendActionEvent(other, "attack", ia)
        listener = shinjo_school.ShinjoSpendActionListener()
        emitted = list(listener.handle(shinjo, event, ctx))
        self.assertEqual([], emitted)
        # The 'other' character's actions are unchanged (the Shinjo's
        # listener does not spend other's dice).
        self.assertEqual([3], other.actions())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
