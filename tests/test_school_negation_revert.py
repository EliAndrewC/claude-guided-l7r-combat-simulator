#!/usr/bin/env python3

#
# test_school_negation_revert.py
#
# Tests for the "active revert + zero rank" 5th Dan school-negation mechanism
# (rules/04-schools.md "Isawa Ishi School: 5th Dan").
#
# Whereas test_school_negation_dispatch.py exercised the legacy "dispatch-time
# gate" semantics (school-owned listeners/strategies stay installed but
# accessors skip them while _school_negated_by is set), this file exercises
# the active-revert behavior:
#
#   * negate_school(by) clears all school-installed listener slots, restores
#     pre-school strategies, restores pre-school providers, removes
#     school-installed modifiers (e.g. FreeRaise on parry), subtracts
#     school-added extra_rolled bonuses, sets _school_rank_override to 0.
#   * Permanent stat modifications (e.g. the 4th Dan Void +1 from
#     apply_school_ring_raise_and_discount) STAY.
#   * Character.reset() restores the school's mutations so the character
#     re-acquires their school for the next combat.
#

import unittest
from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.listeners import Listener
from simulation.mechanics.modifiers import FreeRaise
from simulation.schools import ishi_school, mirumoto_school
from simulation.strategies.action_factory import DEFAULT_ACTION_FACTORY
from simulation.strategies.base import Strategy


class _RecordingListener(Listener):
    def __init__(self) -> None:
        self.calls = 0

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        self.calls += 1
        yield from ()


class _RecordingStrategy(Strategy):
    def __init__(self) -> None:
        self.calls = 0

    def recommend(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        self.calls += 1
        yield from ()


def _build_fourth_dan_mirumoto() -> Character:
    """Build a 4th-dan Mirumoto with all build-time school mutations applied."""
    mirumoto = Character("Mirumoto")
    school = mirumoto_school.MirumotoBushiSchool()
    mirumoto.set_school(school)
    for knack in school.school_knacks():
        mirumoto.set_skill(knack, 4)
    school.apply_special_ability(mirumoto)
    school.apply_rank_one_ability(mirumoto)
    school.apply_rank_two_ability(mirumoto)
    school.apply_rank_three_ability(mirumoto)
    school.apply_rank_four_ability(mirumoto)
    return mirumoto


def _build_fifth_dan_ishi() -> Character:
    ishi = Character("Ishi")
    ishi.set_ring("air", 3)
    ishi.set_ring("earth", 3)
    ishi.set_ring("fire", 3)
    ishi.set_ring("water", 3)
    ishi.set_ring("void", 5)
    ishi.set_skill("precepts", 5)
    school = ishi_school.IsawaIshiSchool()
    ishi.set_school(school)
    for knack in school.school_knacks():
        ishi.set_skill(knack, 5)
    school.apply_special_ability(ishi)
    school.apply_rank_one_ability(ishi)
    school.apply_rank_two_ability(ishi)
    school.apply_rank_three_ability(ishi)
    school.apply_rank_four_ability(ishi)
    school.apply_rank_five_ability(ishi)
    return ishi


class TestSchoolRankAccessor(unittest.TestCase):
    """``Character.school_rank()`` returns the override when set
    (rules/04-schools.md "Isawa Ishi School: 5th Dan" -- "school rank 0")."""

    def test_default_school_rank_uses_knacks(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        self.assertEqual(4, mirumoto.school_rank())

    def test_school_rank_override_returns_zero(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        mirumoto._school_rank_override = 0
        self.assertEqual(0, mirumoto.school_rank())

    def test_school_rank_no_school_is_zero(self) -> None:
        c = Character("X")
        self.assertEqual(0, c.school_rank())


class TestNegateSchoolRevertsModifiers(unittest.TestCase):
    """rules/04-schools.md "Isawa Ishi School: 5th Dan": negating a school
    must remove the modifiers installed by the school's 2nd Dan
    apply_rank_two_ability (e.g. FreeRaise on parry for Mirumoto)."""

    def test_freeraise_on_parry_removed_after_negation(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        # Pre: a FreeRaise modifier on "parry" was installed.
        free_raises_pre = [
            m for m in mirumoto._modifiers
            if isinstance(m, FreeRaise) and "parry" in m.skills()
        ]
        self.assertEqual(1, len(free_raises_pre))
        # Negate.
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        # Post: the FreeRaise on parry is gone.
        free_raises_post = [
            m for m in mirumoto._modifiers
            if isinstance(m, FreeRaise) and "parry" in m.skills()
        ]
        self.assertEqual(0, len(free_raises_post))

    def test_school_negated_by_set(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        self.assertIs(ishi, mirumoto._school_negated_by)
        self.assertEqual(0, mirumoto.school_rank())


class TestNegateSchoolRevertsExtraRolled(unittest.TestCase):
    """rules/04-schools.md "Isawa Ishi School: 5th Dan": school-installed
    extra_rolled bonuses (1st Dan +1 die) must be reverted on negation."""

    def test_extra_rolled_parry_reverted(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        # Pre: Mirumoto's 1st Dan gave +1 to parry.
        self.assertEqual(1, mirumoto.extra_rolled("parry"))
        # Negate.
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        # Post: the bonus is gone.
        self.assertEqual(0, mirumoto.extra_rolled("parry"))
        self.assertEqual(0, mirumoto.extra_rolled("double attack"))
        self.assertEqual(0, mirumoto.extra_rolled("wound check"))


class TestNegateSchoolRevertsProviders(unittest.TestCase):
    """rules/04-schools.md "Isawa Ishi School: 5th Dan": school-installed
    providers (action factory, roll parameter provider, etc.) must be
    reverted to the engine default on negation."""

    def test_mirumoto_action_factory_reverted(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        # Pre: Mirumoto's 4th Dan installed MIRUMOTO_ACTION_FACTORY.
        self.assertIs(mirumoto_school.MIRUMOTO_ACTION_FACTORY, mirumoto.action_factory())
        # Negate.
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        # Post: the engine default is restored.
        self.assertIs(DEFAULT_ACTION_FACTORY, mirumoto.action_factory())

    def test_max_vp_provider_reverted_on_ishi(self) -> None:
        ishi = _build_fifth_dan_ishi()
        # Pre: Ishi has the custom max_vp_provider installed.
        self.assertIsNotNone(ishi._max_vp_provider)
        # Negate.
        ishi.negate_school(Character("OtherIshi"))
        # Post: the engine default (None) is restored.
        self.assertIsNone(ishi._max_vp_provider)


class TestNegateSchoolKeepsPermanentStatMods(unittest.TestCase):
    """rules/04-schools.md "Isawa Ishi School: 5th Dan": permanent stat
    modifications (e.g. the 4th Dan ring +1 from
    apply_school_ring_raise_and_discount) are not reverted by negation."""

    def test_void_bumped_by_4th_dan_stays(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        # 4th Dan raised Void to 3 (base 2 + 1).
        self.assertEqual(3, mirumoto.ring("void"))
        # Negate.
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        # Permanent ring bump remains.
        self.assertEqual(3, mirumoto.ring("void"))


class TestNegateSchoolClearsListenerSlots(unittest.TestCase):
    """rules/04-schools.md "Isawa Ishi School: 5th Dan": school-owned
    listeners must be removed from ``_listeners`` on negation so they
    do not fire."""

    def test_parry_failed_listener_removed(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        # Pre: parry_failed listener installed by special ability.
        self.assertIn("parry_failed", mirumoto._listeners)
        # Negate.
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        # Post: the listener is gone.
        self.assertNotIn("parry_failed", mirumoto._listeners)

    def test_no_tvp_event_yielded_on_parry_failed_after_negation(self) -> None:
        from simulation.actions import AttackAction, ParryAction
        from simulation.mechanics.initiative_actions import InitiativeAction
        mirumoto = _build_fourth_dan_mirumoto()
        attacker = Character("Attacker")
        groups = [Group("Dragon", mirumoto), Group("Other", attacker)]
        context = EngineContext(groups)
        ia = InitiativeAction([1], 1)
        attack_action = AttackAction(attacker, mirumoto, "attack", ia, context)
        parry_action = ParryAction(mirumoto, attacker, "parry", ia, context, attack_action)
        parry_failed = events.ParryFailedEvent(parry_action)
        # Sanity pre-negation: TVP is yielded.
        pre = list(mirumoto.event(parry_failed, context))
        self.assertTrue(
            any(isinstance(ev, events.GainTemporaryVoidPointsEvent) for ev in pre),
        )
        # Negate.
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        # Post-negation: no TVP yielded (listener was removed).
        post = list(mirumoto.event(parry_failed, context))
        self.assertFalse(
            any(isinstance(ev, events.GainTemporaryVoidPointsEvent) for ev in post),
        )


class TestResetRestoresSchoolMutations(unittest.TestCase):
    """rules/04-schools.md "Isawa Ishi School: 5th Dan" -- negation is
    for the duration of a fight; ``Character.reset()`` must restore
    the school's mutations for the next combat."""

    def test_reset_restores_modifiers(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        # Sanity: FreeRaise on parry is removed.
        self.assertFalse(any(
            isinstance(m, FreeRaise) and "parry" in m.skills()
            for m in mirumoto._modifiers
        ))
        # Reset.
        mirumoto.reset()
        # Post: FreeRaise on parry is restored.
        self.assertTrue(any(
            isinstance(m, FreeRaise) and "parry" in m.skills()
            for m in mirumoto._modifiers
        ))

    def test_reset_restores_extra_rolled(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        self.assertEqual(0, mirumoto.extra_rolled("parry"))
        mirumoto.reset()
        self.assertEqual(1, mirumoto.extra_rolled("parry"))

    def test_reset_restores_listener(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        self.assertNotIn("parry_failed", mirumoto._listeners)
        mirumoto.reset()
        self.assertIn("parry_failed", mirumoto._listeners)

    def test_reset_restores_action_factory(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        self.assertIs(DEFAULT_ACTION_FACTORY, mirumoto.action_factory())
        mirumoto.reset()
        self.assertIs(mirumoto_school.MIRUMOTO_ACTION_FACTORY, mirumoto.action_factory())

    def test_reset_restores_school_rank(self) -> None:
        mirumoto = _build_fourth_dan_mirumoto()
        ishi = Character("Ishi")
        mirumoto.negate_school(ishi)
        self.assertEqual(0, mirumoto.school_rank())
        mirumoto.reset()
        self.assertEqual(4, mirumoto.school_rank())
        self.assertIsNone(mirumoto._school_negated_by)


class TestEagerNegationStrategyUsesNewMethod(unittest.TestCase):
    """rules/04-schools.md "Isawa Ishi School: 5th Dan": the strategy must
    call ``target.negate_school(character)`` so the active revert runs."""

    def test_strategy_actively_reverts_target(self) -> None:
        from simulation.strategies.ishi_dan_abilities import EagerNegationStrategy
        ishi = _build_fifth_dan_ishi()
        mirumoto = _build_fourth_dan_mirumoto()
        groups = [Group("Phoenix", ishi), Group("Dragon", mirumoto)]
        ctx = EngineContext(groups)
        # Sanity: Mirumoto has the FreeRaise modifier installed.
        self.assertTrue(any(
            isinstance(m, FreeRaise) and "parry" in m.skills()
            for m in mirumoto._modifiers
        ))
        # Fire the negation strategy directly.
        event = events.YourMoveEvent(ishi)
        list(EagerNegationStrategy().recommend(ishi, event, ctx))
        # Both the negation flag AND the active revert happened.
        self.assertIs(ishi, mirumoto._school_negated_by)
        self.assertEqual(0, mirumoto.school_rank())
        self.assertFalse(any(
            isinstance(m, FreeRaise) and "parry" in m.skills()
            for m in mirumoto._modifiers
        ))


if __name__ == "__main__":
    unittest.main()
