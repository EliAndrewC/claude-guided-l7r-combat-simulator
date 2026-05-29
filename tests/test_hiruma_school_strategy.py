#!/usr/bin/env python3

#
# test_hiruma_school_strategy.py
#
# Unit tests for Hiruma Scout School strategy bindings and the
# previously-unimplemented Special Ability (spec 019 Q1 fix).
#

import unittest
from typing import Any

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.formation import LineFormation
from simulation.groups import Group
from simulation.schools import hiruma_school
from simulation.strategies.base import (
    AlwaysParryStrategy,
    WoundCheckStrategy04,
)


def _build_hiruma() -> tuple[Character, hiruma_school.HirumaScoutSchool]:
    hiruma = Character("Hiruma")
    hiruma.set_skill("parry", 4)
    hiruma.set_skill("attack", 4)
    hiruma.set_ring("air", 4)
    school = hiruma_school.HirumaScoutSchool()
    hiruma.set_school(school)
    return hiruma, school


class TestHirumaSpecialAbilityWiring(unittest.TestCase):
    """Spec 019 T-B1 / Q1: apply_special_ability wires the parry
    strategy + wound check strategy + Special Ability listener."""

    def test_installs_always_parry_strategy(self) -> None:
        hiruma, school = _build_hiruma()
        school.apply_special_ability(hiruma)
        self.assertIsInstance(
            hiruma.parry_strategy(), AlwaysParryStrategy,
        )

    def test_installs_wound_check_strategy_04(self) -> None:
        hiruma, school = _build_hiruma()
        school.apply_special_ability(hiruma)
        self.assertIsInstance(
            hiruma.wound_check_strategy(), WoundCheckStrategy04,
        )

    def test_installs_new_round_listener(self) -> None:
        hiruma, school = _build_hiruma()
        school.apply_special_ability(hiruma)
        listener = hiruma._listeners.get("new_round")
        self.assertIsInstance(
            listener, hiruma_school.HirumaSpecialAbilityNewRoundListener,
        )


class TestHirumaSpecialAbilityNeighborTNModifier(unittest.TestCase):
    """Spec 019 T-A1 (Q1 BLOCKING IDENTITY fix): the Special Ability
    listener installs +5 ``tn to hit`` modifiers on the Hiruma's
    formation neighbors each new round."""

    def _setup_formation(self) -> Any:
        """Build a 3-character line with Hiruma in the middle so it
        has two adjacent allies."""
        from simulation.mechanics.roll_provider import CalvinistRollProvider
        ally_left = Character("AllyLeft")
        hiruma, school = _build_hiruma()
        ally_right = Character("AllyRight")
        enemy = Character("Enemy")
        for c in [ally_left, ally_right, enemy]:
            c.set_actions([1])
        formation = LineFormation(
            [[ally_left, hiruma, ally_right], [enemy]],
        )
        groups = [
            Group("Crab", [ally_left, hiruma, ally_right]),
            Group("Enemy", enemy),
        ]
        context = EngineContext(groups, round=1, phase=1, formation=formation)
        context.initialize()
        # Give Hiruma a deterministic initiative roll so the listener
        # can call roll_initiative() without crashing.
        rp = CalvinistRollProvider()
        rp.put_initiative_roll([3])
        hiruma.set_roll_provider(rp)
        school.apply_special_ability(hiruma)
        return hiruma, ally_left, ally_right, enemy, context

    def test_neighbors_get_plus_5_tn_to_hit(self) -> None:
        hiruma, ally_left, ally_right, _, context = self._setup_formation()
        listener = hiruma._listeners["new_round"]
        emitted = list(listener.handle(hiruma, events.NewRoundEvent(1), context))
        # Two AddModifierEvents — one per neighbor.
        add_events = [e for e in emitted if isinstance(e, events.AddModifierEvent)]
        self.assertEqual(2, len(add_events))
        subjects = {e.subject for e in add_events}
        self.assertIn(ally_left, subjects)
        self.assertIn(ally_right, subjects)
        for e in add_events:
            self.assertEqual(5, e.modifier.adjustment())
            self.assertEqual("tn to hit", e.modifier.skills()[0])
            self.assertTrue(getattr(e.modifier, "_hiruma_special_ability", False))

    def test_modifiers_removed_when_hiruma_defeated(self) -> None:
        """If the Hiruma is defeated, the Special Ability no longer
        applies — existing modifiers MUST be removed (RemoveModifier
        Events emitted), AND no new ones installed."""
        from simulation.engine import CombatEngine
        from simulation.mechanics.roll_provider import CalvinistRollProvider
        hiruma, ally_left, ally_right, _, context = self._setup_formation()
        listener = hiruma._listeners["new_round"]
        engine = CombatEngine(context)
        # First round: install modifiers via the engine (processes
        # the AddModifierEvents so the modifier list actually updates
        # on ally_left / ally_right).
        rp = CalvinistRollProvider()
        rp.put_initiative_roll([3])
        hiruma.set_roll_provider(rp)
        for emitted in listener.handle(hiruma, events.NewRoundEvent(1), context):
            engine.event(emitted)
        # Confirm ally_left has the +5 modifier installed.
        self.assertEqual(5, ally_left.modifier(None, "tn to hit"))
        # Kill the Hiruma.
        hiruma.take_sw(hiruma.max_sw())
        self.assertFalse(hiruma.is_fighting())
        # Second round: listener should remove existing modifiers AND
        # not install new ones.
        rp2 = CalvinistRollProvider()
        rp2.put_initiative_roll([3])
        hiruma.set_roll_provider(rp2)
        emitted_events = list(listener.handle(hiruma, events.NewRoundEvent(2), context))
        remove_events = [e for e in emitted_events if isinstance(e, events.RemoveModifierEvent)]
        # At least one RemoveModifierEvent for each neighbor.
        self.assertGreaterEqual(len(remove_events), 1)
        add_events = [e for e in emitted_events if isinstance(e, events.AddModifierEvent)]
        # No new modifiers installed since Hiruma is defeated.
        self.assertEqual(0, len(add_events))


class TestHirumaRankAbilities(unittest.TestCase):
    """Coverage for apply_rank_*_ability methods."""

    def test_apply_rank_three_installs_parry_listeners(self) -> None:
        hiruma, school = _build_hiruma()
        school.apply_rank_three_ability(hiruma)
        self.assertIsInstance(
            hiruma._listeners.get("parry_succeeded"),
            hiruma_school.HirumaParryListener,
        )

    def test_apply_rank_four_installs_new_round_listener_and_raises_air(self) -> None:
        hiruma, school = _build_hiruma()
        air_before = hiruma.ring("air")
        school.apply_rank_four_ability(hiruma)
        self.assertEqual(air_before + 1, hiruma.ring("air"))
        listener = hiruma._listeners.get("new_round")
        self.assertIsInstance(listener, hiruma_school.HirumaNewRoundListener)

    def test_apply_rank_five_installs_fifth_dan_listeners(self) -> None:
        hiruma, school = _build_hiruma()
        school.apply_rank_five_ability(hiruma)
        self.assertIsInstance(
            hiruma._listeners.get("parry_succeeded"),
            hiruma_school.HirumaFifthDanParryListener,
        )
        self.assertIsInstance(
            hiruma._listeners.get("parry_failed"),
            hiruma_school.HirumaFifthDanParryListener,
        )


class TestHirumaMisc(unittest.TestCase):
    def test_ap_base_skill_returns_none(self) -> None:
        school = hiruma_school.HirumaScoutSchool()
        self.assertIsNone(school.ap_base_skill())

    def test_name(self) -> None:
        school = hiruma_school.HirumaScoutSchool()
        self.assertEqual("Hiruma Scout School", school.name())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
