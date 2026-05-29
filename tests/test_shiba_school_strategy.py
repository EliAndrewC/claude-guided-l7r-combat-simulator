#!/usr/bin/env python3

#
# test_shiba_school_strategy.py
#
# Unit tests for ShibaInterruptParryStrategy decline-gate behavior.
# Per spec 016 (Shiba Bushi School Special Ability) Q1+Q2 / T-B1.
#

import unittest
from typing import Any

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.schools import shiba_school


def _build_shiba(
    name: str = "Shiba",
    parry_skill: int = 4,
    actions: list[int] | None = None,
    sw_taken: int = 0,
) -> Character:
    """Build a minimal Shiba character with the strategy installed."""
    shiba = Character(name)
    school = shiba_school.ShibaBushiSchool()
    shiba.set_school(school)
    shiba.set_skill("parry", parry_skill)
    shiba.set_skill("attack", 4)
    shiba.set_ring("air", 4)
    shiba.set_actions(actions if actions is not None else [3, 5, 7])
    school.apply_special_ability(shiba)
    if sw_taken > 0:
        shiba.take_sw(sw_taken)
    return shiba


def _build_attacker(name: str = "Attacker") -> Character:
    attacker = Character(name)
    attacker.set_skill("attack", 3)
    attacker.set_actions([5])
    return attacker


def _make_attack_rolled_event(
    attacker: Character,
    target: Character,
    skill: str = "attack",
    hit: bool = True,
) -> events.AttackRolledEvent:
    """Build a real AttackRolledEvent around a real action."""
    from simulation.actions import AttackAction
    ia = InitiativeAction([5], 5)
    groups = [Group("A", attacker), Group("B", target)]
    ctx = EngineContext(groups)
    action = AttackAction(attacker, target, skill, ia, ctx)
    # AttackRolledEvent's is_hit() check requires the action's roll
    # vs TN.  Set a roll high enough to hit.
    action.set_skill_roll(50 if hit else 1)
    return events.AttackRolledEvent(action, roll=50 if hit else 1)


def _setup_context(shiba: Character, attacker: Character) -> Any:
    groups = [Group("Phoenix", shiba), Group("Attacker-side", attacker)]
    ctx = EngineContext(groups, phase=5)
    ctx.initialize()
    return ctx


class TestShibaInterruptParryStrategyFires(unittest.TestCase):
    """Happy-path: strategy produces a parry interrupt."""

    def test_fires_on_attack_against_shiba(self) -> None:
        shiba = _build_shiba()
        attacker = _build_attacker()
        ctx = _setup_context(shiba, attacker)
        event = _make_attack_rolled_event(attacker, shiba)

        strategy = shiba_school.ShibaInterruptParryStrategy()
        emitted = list(strategy.recommend(shiba, event, ctx))
        # At least SpendActionEvent + take-parry-action event.
        self.assertGreaterEqual(len(emitted), 2)
        # The take-parry event must wrap a ShibaParryAction (so the
        # parry-other no-penalty + 3rd Dan damage logic fires).
        from simulation.events import TakeParryActionEvent
        take_parry = [e for e in emitted if isinstance(e, TakeParryActionEvent)]
        self.assertEqual(1, len(take_parry))

    def test_lowest_die_selection(self) -> None:
        """rules text — "spending your **lowest** 1 action die".
        Standard BaseAttackStrategy / BaseParryStrategy pick MAX.
        Shiba MUST pick MIN.  Q2 BLOCKING fix."""
        shiba = _build_shiba(actions=[2, 7])
        attacker = _build_attacker()
        ctx = _setup_context(shiba, attacker)
        event = _make_attack_rolled_event(attacker, shiba)

        strategy = shiba_school.ShibaInterruptParryStrategy()
        emitted = list(strategy.recommend(shiba, event, ctx))
        # First emitted event is SpendActionEvent — inspect its dice.
        spend_events = [
            e for e in emitted if isinstance(e, events.SpendActionEvent)
        ]
        self.assertEqual(1, len(spend_events))
        ia = spend_events[0].initiative_action
        # MUST consume the LOWEST die (2), NOT the highest (7).
        self.assertEqual([2], ia.dice())


class TestShibaInterruptParryStrategyDeclines(unittest.TestCase):
    def test_declines_when_no_parry_skill(self) -> None:
        shiba = _build_shiba(parry_skill=0)
        attacker = _build_attacker()
        ctx = _setup_context(shiba, attacker)
        event = _make_attack_rolled_event(attacker, shiba)
        strategy = shiba_school.ShibaInterruptParryStrategy()
        self.assertEqual([], list(strategy.recommend(shiba, event, ctx)))

    def test_declines_when_no_interrupt_action_available(self) -> None:
        shiba = _build_shiba(actions=[])
        attacker = _build_attacker()
        ctx = _setup_context(shiba, attacker)
        event = _make_attack_rolled_event(attacker, shiba)
        strategy = shiba_school.ShibaInterruptParryStrategy()
        self.assertEqual([], list(strategy.recommend(shiba, event, ctx)))

    def test_declines_when_attack_missed(self) -> None:
        shiba = _build_shiba()
        attacker = _build_attacker()
        ctx = _setup_context(shiba, attacker)
        event = _make_attack_rolled_event(attacker, shiba, hit=False)
        strategy = shiba_school.ShibaInterruptParryStrategy()
        self.assertEqual([], list(strategy.recommend(shiba, event, ctx)))

    def test_declines_when_already_parried(self) -> None:
        shiba = _build_shiba()
        attacker = _build_attacker()
        ctx = _setup_context(shiba, attacker)
        event = _make_attack_rolled_event(attacker, shiba)
        # Mark the attack as already parried.
        event.action.set_parried()
        strategy = shiba_school.ShibaInterruptParryStrategy()
        self.assertEqual([], list(strategy.recommend(shiba, event, ctx)))

    def test_declines_at_sw_saturation(self) -> None:
        shiba = _build_shiba()
        shiba.take_sw(shiba.max_sw() - 1)
        self.assertEqual(1, shiba.sw_remaining())
        attacker = _build_attacker()
        ctx = _setup_context(shiba, attacker)
        event = _make_attack_rolled_event(attacker, shiba)
        strategy = shiba_school.ShibaInterruptParryStrategy()
        self.assertEqual([], list(strategy.recommend(shiba, event, ctx)))

    def test_declines_when_target_is_enemy(self) -> None:
        """Don't parry FOR an enemy.

        Build the enemy in a SEPARATE group from the attacker so the
        attacker is attacking inside their own faction (target not in
        Shiba's group)."""
        shiba = _build_shiba()
        attacker = _build_attacker()
        enemy_target = Character("Enemy")
        groups = [
            Group("Phoenix", shiba),
            Group("Attacker-side", [attacker, enemy_target]),
        ]
        ctx = EngineContext(groups, phase=5)
        ctx.initialize()
        from simulation.actions import AttackAction
        ia = InitiativeAction([5], 5)
        action = AttackAction(attacker, enemy_target, "attack", ia, ctx)
        action.set_skill_roll(50)
        event = events.AttackRolledEvent(action, roll=50)
        strategy = shiba_school.ShibaInterruptParryStrategy()
        self.assertEqual([], list(strategy.recommend(shiba, event, ctx)))

    def test_does_not_fire_on_unrelated_events(self) -> None:
        shiba = _build_shiba()
        attacker = _build_attacker()
        ctx = _setup_context(shiba, attacker)
        from simulation.actions import AttackAction
        ia = InitiativeAction([5], 5)
        action = AttackAction(attacker, shiba, "attack", ia, ctx)
        # AttackDeclaredEvent is NOT what Shiba's interrupt-parry reacts to.
        unrelated = events.AttackDeclaredEvent(action)
        strategy = shiba_school.ShibaInterruptParryStrategy()
        self.assertEqual([], list(strategy.recommend(shiba, unrelated, ctx)))


class TestShibaSpecialAbilityWiring(unittest.TestCase):
    def test_apply_special_ability_installs_interrupt_strategy(self) -> None:
        shiba = _build_shiba()
        self.assertIsInstance(
            shiba.interrupt_strategy(),
            shiba_school.ShibaInterruptParryStrategy,
        )

    def test_apply_special_ability_installs_wound_check_strategy_04(self) -> None:
        from simulation.strategies.base import WoundCheckStrategy04
        shiba = _build_shiba()
        self.assertIsInstance(
            shiba.wound_check_strategy(), WoundCheckStrategy04,
        )

    def test_apply_special_ability_installs_action_factory(self) -> None:
        shiba = _build_shiba()
        self.assertIs(
            shiba.action_factory(),
            shiba_school.SHIBA_ACTION_FACTORY,
        )

    def test_apply_special_ability_sets_interrupt_cost(self) -> None:
        shiba = _build_shiba()
        # Cost of parry interrupt is 1 die (rules text).
        attacker = Character("Atk")
        ctx = EngineContext([Group("Phoenix", shiba), Group("Foe", attacker)], phase=5)
        self.assertEqual(1, shiba.interrupt_cost("parry", ctx))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
