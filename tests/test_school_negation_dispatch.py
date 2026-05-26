#!/usr/bin/env python3

#
# test_school_negation_dispatch.py
#
# Tests for the engine-side dispatch gate that ensures the Isawa Ishi 5th
# Dan school-negation ability (rules/04-schools.md "Isawa Ishi School:
# 5th Dan") actually disables already-installed school-owned listeners
# and strategies at dispatch time.
#
# Without this gate the negation flag (`_school_negated_by`) would only
# short-circuit FUTURE `apply_*_ability` calls; the listeners installed
# at character-build time would continue to fire.  See SC-2 in
# specs/002-isawa-ishi-school/OPEN_QUESTIONS.md.
#

import unittest
from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.listeners import Listener
from simulation.schools.akodo_school import AkodoBushiSchool
from simulation.schools.base import BaseSchool
from simulation.schools.mirumoto_school import MirumotoBushiSchool
from simulation.strategies.base import Strategy


class _RecordingListener(Listener):
    """Test double: records that it fired and how many times."""

    def __init__(self) -> None:
        self.calls = 0

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        self.calls += 1
        yield from ()


class _RecordingStrategy(Strategy):
    """Test double: records that it was consulted and how many times."""

    def __init__(self) -> None:
        self.calls = 0

    def recommend(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        self.calls += 1
        yield from ()


class _TestSchool(BaseSchool):
    """A minimal school that exercises both `_set_school_listener` and
    `_set_school_strategy` helpers for the dispatch-gate tests.

    rules/04-schools.md "Isawa Ishi School: 5th Dan" — the school-owned
    listeners installed here must be skipped when the character is
    school-negated; the helpers tag the slots so the engine can find
    them.
    """

    def __init__(self) -> None:
        super().__init__()
        self.test_listener = _RecordingListener()
        self.test_strategy = _RecordingStrategy()

    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # Install a listener on an engine-default slot (`sw_damage`) so we
        # can check that school-installed listeners are gated.
        self._set_school_listener(character, "sw_damage", self.test_listener)
        # Install a strategy on the engine-default `attack` slot so we can
        # check that school-installed strategies are gated.
        self._set_school_strategy(character, "attack", self.test_strategy)

    def apply_rank_three_ability(self, character: Any) -> None:
        pass

    def apply_rank_four_ability(self, character: Any) -> None:
        pass

    def apply_rank_five_ability(self, character: Any) -> None:
        pass

    def extra_rolled(self) -> list[str]:
        return []

    def free_raise_skills(self) -> list[str]:
        return []

    def name(self) -> str:
        return "Test School"

    def school_knacks(self) -> list[str]:
        return ["attack", "parry"]

    def school_ring(self) -> str:
        return "fire"


class TestSchoolOwnedListenerGating(unittest.TestCase):
    """rules/04-schools.md "Isawa Ishi School: 5th Dan" — school-installed
    listeners must NOT fire when the character is school-negated."""

    def setUp(self) -> None:
        self.character = Character("Target")
        self.attacker = Character("Attacker")
        groups = [Group("A", self.character), Group("B", self.attacker)]
        self.context = EngineContext(groups)
        self.school = _TestSchool()
        self.school.apply_special_ability(self.character)

    def test_school_listener_fires_when_not_negated(self) -> None:
        """Sanity: the school-installed listener fires under normal conditions."""
        event = events.SeriousWoundsDamageEvent(self.attacker, self.character, 1)
        list(self.character.event(event, self.context))
        self.assertEqual(1, self.school.test_listener.calls)

    def test_school_listener_does_not_fire_when_negated(self) -> None:
        """When `_school_negated_by` is set, the school-installed listener
        is skipped at dispatch time."""
        negator = Character("Ishi")
        self.character._school_negated_by = negator
        event = events.SeriousWoundsDamageEvent(self.attacker, self.character, 1)
        list(self.character.event(event, self.context))
        self.assertEqual(0, self.school.test_listener.calls)

    def test_school_listener_fires_again_after_reset(self) -> None:
        """`Character.reset()` clears the negation flag so the listener
        fires again on the next combat."""
        negator = Character("Ishi")
        self.character._school_negated_by = negator
        # negated -- no fire
        list(self.character.event(
            events.SeriousWoundsDamageEvent(self.attacker, self.character, 1),
            self.context,
        ))
        self.assertEqual(0, self.school.test_listener.calls)
        # reset clears negation
        self.character.reset()
        self.assertIsNone(self.character._school_negated_by)
        list(self.character.event(
            events.SeriousWoundsDamageEvent(self.attacker, self.character, 1),
            self.context,
        ))
        self.assertEqual(1, self.school.test_listener.calls)


class TestEngineDefaultListenerStillFires(unittest.TestCase):
    """Engine-default listeners (not installed by the school) must
    continue firing even when the character is school-negated."""

    def test_engine_default_listener_unaffected(self) -> None:
        """A listener installed at Character.__init__ (not via the school
        helper) is NOT in `_school_owned_listener_slots` and must
        continue to fire when negation is active."""
        character = Character("Target")
        attacker = Character("Attacker")
        groups = [Group("A", character), Group("B", attacker)]
        context = EngineContext(groups)
        # Replace the engine-default sw_damage listener with our recorder
        # by calling `set_listener` directly (NOT via a school helper) --
        # this simulates an engine default and must remain un-gated.
        recorder = _RecordingListener()
        character.set_listener("sw_damage", recorder)
        # Mark character as negated
        character._school_negated_by = Character("Ishi")
        # Dispatch the event
        event = events.SeriousWoundsDamageEvent(attacker, character, 1)
        list(character.event(event, context))
        # The engine-default listener fires; only school-owned slots are gated.
        self.assertEqual(1, recorder.calls)


class TestSchoolOwnedStrategyGating(unittest.TestCase):
    """When a school replaces an engine-default strategy slot (e.g.,
    Daidoji replacing `interrupt`, Mirumoto replacing `attack_rolled`),
    the accessor must return the engine default while the character is
    negated."""

    def setUp(self) -> None:
        self.character = Character("Target")
        self.school = _TestSchool()
        self.school.apply_special_ability(self.character)

    def test_strategy_accessor_returns_school_strategy_when_not_negated(self) -> None:
        self.assertIs(self.school.test_strategy, self.character.attack_strategy())

    def test_strategy_accessor_returns_engine_default_when_negated(self) -> None:
        """The accessor returns the cached engine default while
        `_school_negated_by` is set (rules-text "completely negate")."""
        self.character._school_negated_by = Character("Ishi")
        returned = self.character.attack_strategy()
        # Not the school strategy
        self.assertIsNot(self.school.test_strategy, returned)
        # And it is the engine default (a UniversalAttackStrategy by default)
        from simulation.strategies.base import UniversalAttackStrategy
        self.assertIsInstance(returned, UniversalAttackStrategy)

    def test_strategy_accessor_returns_school_strategy_after_reset(self) -> None:
        """Reset clears negation so the school strategy is back in play."""
        self.character._school_negated_by = Character("Ishi")
        self.character.reset()
        self.assertIs(self.school.test_strategy, self.character.attack_strategy())


class TestMirumotoParryListenerNegatedByIshi(unittest.TestCase):
    """End-to-end SC-2 verification: a 4th-dan Mirumoto's
    `MirumotoParryTVPListener` (installed at Special Ability) MUST stop
    firing after an Ishi has negated the Mirumoto's school."""

    def test_mirumoto_parry_tvp_does_not_fire_when_negated(self) -> None:
        mirumoto = Character("Mirumoto")
        attacker = Character("Other")
        groups = [Group("Dragon", mirumoto), Group("Other", attacker)]
        context = EngineContext(groups)
        school = MirumotoBushiSchool()
        school.apply_special_ability(mirumoto)
        # Build a parry action targeting the Mirumoto.  We construct the
        # underlying attack first so the ParryAction signature is satisfied.
        from simulation.actions import AttackAction, ParryAction
        from simulation.mechanics.initiative_actions import InitiativeAction
        ia = InitiativeAction([1], 1)
        attack_action = AttackAction(attacker, mirumoto, "attack", ia, context)
        parry_action = ParryAction(mirumoto, attacker, "parry", ia, context, attack_action)
        parry_failed = events.ParryFailedEvent(parry_action)
        # Sanity: pre-negation, the school listener yields a TVP event
        pre = list(mirumoto.event(parry_failed, context))
        self.assertTrue(
            any(isinstance(ev, events.GainTemporaryVoidPointsEvent) for ev in pre),
            "Pre-negation parry_failed should yield a GainTemporaryVoidPointsEvent",
        )
        # Now negate the school
        ishi = Character("Ishi")
        mirumoto._school_negated_by = ishi
        # Post-negation: no TVP-gain events from the school listener
        post = list(mirumoto.event(parry_failed, context))
        self.assertFalse(
            any(isinstance(ev, events.GainTemporaryVoidPointsEvent) for ev in post),
            "MirumotoParryTVPListener should be gated when school is negated",
        )


class TestSchoolHelperTracksSlots(unittest.TestCase):
    """The `_set_school_listener` / `_set_school_strategy` helpers must
    populate `_school_owned_*_slots` so the dispatch gate can find
    school-installed slots."""

    def test_helper_tracks_listener_slot(self) -> None:
        character = Character("X")
        school = _TestSchool()
        school._set_school_listener(character, "sw_damage", _RecordingListener())
        self.assertIn("sw_damage", character._school_owned_listener_slots)

    def test_helper_tracks_strategy_slot(self) -> None:
        character = Character("X")
        school = _TestSchool()
        school._set_school_strategy(character, "attack", _RecordingStrategy())
        self.assertIn("attack", character._school_owned_strategy_slots)


class TestAkodoSchoolNegationEndToEnd(unittest.TestCase):
    """End-to-end: an Akodo's `AkodoAttackFailedListener` (installed at
    Special Ability) MUST stop firing after the school is negated."""

    def test_akodo_attack_failed_listener_gated_when_negated(self) -> None:
        from simulation import actions
        from simulation.mechanics.initiative_actions import InitiativeAction
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        groups = [Group("Lion", akodo), Group("Scorpion", bayushi)]
        context = EngineContext(groups)
        school = AkodoBushiSchool()
        school.apply_special_ability(akodo)
        ia = InitiativeAction([1], 1)
        action = actions.FeintAction(akodo, bayushi, "feint", ia, context)
        event = events.AttackFailedEvent(action)
        # Pre-negation: 1 TVP gain event yielded
        pre = list(akodo.event(event, context))
        self.assertEqual(1, len(pre))
        self.assertIsInstance(pre[0], events.GainTemporaryVoidPointsEvent)
        # Negate
        akodo._school_negated_by = Character("Ishi")
        post = list(akodo.event(event, context))
        self.assertEqual(0, len(post),
                         "AkodoAttackFailedListener should be gated when school is negated")


if __name__ == "__main__":
    unittest.main()
