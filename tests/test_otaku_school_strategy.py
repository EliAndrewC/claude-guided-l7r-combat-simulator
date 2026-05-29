#!/usr/bin/env python3

#
# test_otaku_school_strategy.py
#
# Unit tests for OtakuInterruptLungeStrategy decline-gate behavior.
# Per spec 014 (Otaku Bushi School Special Ability) Q1 / T-B1.
#
# rules/04-schools.md "Otaku Bushi School: Special Ability":
# "After an attack against you is completely resolved, you may make
# a lunge attack at your attacker as an interrupt action at the cost
# of one action die."
#

import unittest
from typing import Any

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.schools import otaku_school


def _build_otaku(name: str = "Otaku", lunge_skill: int = 3, sw_taken: int = 0) -> Character:
    """Build a minimal Otaku character with the strategy installed."""
    otaku = Character(name)
    school = otaku_school.OtakuBushiSchool()
    otaku.set_school(school)
    otaku.set_skill("lunge", lunge_skill)
    otaku.set_skill("attack", 3)
    otaku.set_ring("fire", 4)
    otaku.set_actions([5, 7, 9])
    # Wire the school's special ability (installs interrupt strategy).
    school.apply_special_ability(otaku)
    if sw_taken > 0:
        otaku.take_sw(sw_taken)
    return otaku


def _build_attacker(name: str = "Attacker") -> Character:
    attacker = Character(name)
    attacker.set_skill("attack", 3)
    attacker.set_actions([5])
    return attacker


def _make_resolved_event(
    attacker: Character,
    target: Character,
    skill: str = "attack",
    is_interrupt: bool = False,
    succeeded: bool = True,
) -> events.Event:
    """Build a real AttackSucceededEvent / AttackFailedEvent wrapped
    around a real action, ready to feed to the strategy."""
    from simulation.actions import AttackAction
    ia = InitiativeAction([5], 5, is_interrupt=is_interrupt)
    groups = [Group("A", attacker), Group("B", target)]
    ctx = EngineContext(groups)
    action = AttackAction(attacker, target, skill, ia, ctx)
    if succeeded:
        return events.AttackSucceededEvent(action)
    else:
        return events.AttackFailedEvent(action)


def _setup_context(otaku: Character, attacker: Character) -> Any:
    groups = [Group("Otaku-side", otaku), Group("Attacker-side", attacker)]
    ctx = EngineContext(groups, phase=5)
    ctx.initialize()
    return ctx


class TestOtakuInterruptLungeStrategyFires(unittest.TestCase):
    """Verify the strategy actually produces a lunge interrupt in the
    happy path — the spec 014 Q1 identity bug was that
    ``add_interrupt_skill("lunge")`` was wired but no strategy ever
    fired the interrupt."""

    def test_fires_on_attack_succeeded_against_otaku(self) -> None:
        otaku = _build_otaku()
        attacker = _build_attacker()
        ctx = _setup_context(otaku, attacker)
        event = _make_resolved_event(attacker, otaku, succeeded=True)

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        emitted = list(strategy.recommend(otaku, event, ctx))
        # At least a SpendActionEvent + TakeAttackActionEvent must fire.
        self.assertGreaterEqual(len(emitted), 2)
        # The take-attack-action event must carry the trace attribution tag.
        from simulation.events import TakeAttackActionEvent
        take_attack = [e for e in emitted if isinstance(e, TakeAttackActionEvent)]
        self.assertEqual(1, len(take_attack))
        self.assertTrue(
            getattr(take_attack[0].action, "_otaku_special_ability_interrupt", False),
            "T-C4: interrupt-lunge action must be tagged for trace attribution",
        )

    def test_fires_on_attack_failed_against_otaku(self) -> None:
        """Per rules: "after an attack against you is completely
        resolved" — this includes the failed-to-hit case."""
        otaku = _build_otaku()
        attacker = _build_attacker()
        ctx = _setup_context(otaku, attacker)
        event = _make_resolved_event(attacker, otaku, succeeded=False)

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        emitted = list(strategy.recommend(otaku, event, ctx))
        self.assertGreaterEqual(len(emitted), 2)


class TestOtakuInterruptLungeStrategyDeclines(unittest.TestCase):
    """Verify the strategy declines under the documented gates."""

    def test_declines_when_otaku_not_target(self) -> None:
        otaku = _build_otaku()
        attacker = _build_attacker()
        bystander = Character("Bystander")
        ctx = _setup_context(otaku, attacker)
        # Attack against bystander, NOT the Otaku — must not fire.
        event = _make_resolved_event(attacker, bystander)

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        emitted = list(strategy.recommend(otaku, event, ctx))
        self.assertEqual([], emitted)

    def test_declines_when_no_lunge_skill(self) -> None:
        otaku = _build_otaku(lunge_skill=0)
        attacker = _build_attacker()
        ctx = _setup_context(otaku, attacker)
        event = _make_resolved_event(attacker, otaku)

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        emitted = list(strategy.recommend(otaku, event, ctx))
        self.assertEqual([], emitted)

    def test_declines_when_no_interrupt_action_available(self) -> None:
        """Otaku with empty action dice cannot pay the 1-die interrupt cost."""
        otaku = _build_otaku()
        otaku.set_actions([])  # No dice → has_interrupt_action returns False.
        attacker = _build_attacker()
        ctx = _setup_context(otaku, attacker)
        event = _make_resolved_event(attacker, otaku)

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        emitted = list(strategy.recommend(otaku, event, ctx))
        self.assertEqual([], emitted)

    def test_declines_at_sw_saturation(self) -> None:
        """SW-saturation gate: don't burn interrupt dice when the next
        damage will defeat us. Otaku with max_sw - 1 SW remaining
        declines so the wound-check strategy can manage the situation."""
        otaku = _build_otaku()
        # Push Otaku to sw_remaining() == 1.
        otaku.take_sw(otaku.max_sw() - 1)
        self.assertEqual(1, otaku.sw_remaining())
        attacker = _build_attacker()
        ctx = _setup_context(otaku, attacker)
        event = _make_resolved_event(attacker, otaku)

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        emitted = list(strategy.recommend(otaku, event, ctx))
        self.assertEqual([], emitted)

    def test_declines_against_incoming_interrupt_lunge(self) -> None:
        """Mirror-recursion gate: if the incoming attack is itself an
        interrupt-lunge, decline — otherwise two Otakus ricochet
        interrupt-lunges into each other forever."""
        otaku = _build_otaku()
        attacker = _build_attacker()
        ctx = _setup_context(otaku, attacker)
        # The incoming attack is a LUNGE that is an INTERRUPT.
        event = _make_resolved_event(
            attacker, otaku, skill="lunge", is_interrupt=True,
        )

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        emitted = list(strategy.recommend(otaku, event, ctx))
        self.assertEqual([], emitted)

    def test_fires_against_incoming_non_interrupt_lunge(self) -> None:
        """The mirror-recursion gate is conditional on is_interrupt —
        a normal-action lunge should still trigger the interrupt
        response (we want to lunge back at lunge attackers, just not
        recurse on their interrupt-lunge)."""
        otaku = _build_otaku()
        attacker = _build_attacker()
        ctx = _setup_context(otaku, attacker)
        # Incoming lunge, but NOT an interrupt.
        event = _make_resolved_event(
            attacker, otaku, skill="lunge", is_interrupt=False,
        )

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        emitted = list(strategy.recommend(otaku, event, ctx))
        self.assertGreaterEqual(len(emitted), 2)

    def test_does_not_fire_on_unrelated_events(self) -> None:
        """The strategy MUST only react to AttackSucceeded /
        AttackFailed events. Other events are no-ops."""
        otaku = _build_otaku()
        attacker = _build_attacker()
        ctx = _setup_context(otaku, attacker)
        # AttackDeclaredEvent is NOT the resolution event Otaku reacts to.
        from simulation.actions import AttackAction
        ia = InitiativeAction([5], 5)
        action = AttackAction(attacker, otaku, "attack", ia, ctx)
        unrelated = events.AttackDeclaredEvent(action)

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        emitted = list(strategy.recommend(otaku, unrelated, ctx))
        self.assertEqual([], emitted)


class TestOtakuInterruptLungeStrategyOptimizerDeclines(unittest.TestCase):
    """When the attack optimizer can't find a viable lunge at the
    strategy's THRESHOLD, the strategy yields no events."""

    def test_optimizer_returns_none_yields_nothing(self) -> None:
        """If ``optimizer.optimize(THRESHOLD)`` returns None (no viable
        attack at the confidence threshold), the strategy MUST yield
        nothing — even after passing all the _should_lunge gates."""
        from unittest.mock import patch
        otaku = _build_otaku()
        attacker = _build_attacker()
        ctx = _setup_context(otaku, attacker)
        event = _make_resolved_event(attacker, otaku)

        strategy = otaku_school.OtakuInterruptLungeStrategy()
        # Force the optimizer to return None.
        class _NullOptimizer:
            def optimize(self, threshold: float) -> Any:
                return None

        class _NullFactory:
            def get_optimizer(self, *args: Any, **kwargs: Any) -> Any:
                return _NullOptimizer()

        with patch.object(otaku, "attack_optimizer_factory", return_value=_NullFactory()):
            emitted = list(strategy.recommend(otaku, event, ctx))
        self.assertEqual([], emitted)


class TestOtakuSpecialAbilityWiring(unittest.TestCase):
    """Verify ``apply_special_ability`` installs both the new
    strategy and the aggressive WC strategy per spec 014 T-B2."""

    def test_apply_special_ability_installs_interrupt_lunge_strategy(self) -> None:
        otaku = _build_otaku()
        self.assertIsInstance(
            otaku.interrupt_strategy(),
            otaku_school.OtakuInterruptLungeStrategy,
        )

    def test_apply_special_ability_installs_wound_check_strategy_04(self) -> None:
        from simulation.strategies.base import WoundCheckStrategy04
        otaku = _build_otaku()
        self.assertIsInstance(
            otaku.wound_check_strategy(), WoundCheckStrategy04,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
