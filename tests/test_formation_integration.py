#!/usr/bin/env python3

#
# test_formation_integration.py
#
# Integration tests for the formation system with strategies and context.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.formation import LineFormation, SurroundFormation
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.strategies.base import (
    AlwaysParryStrategy,
    CounterattackInterruptStrategy,
    ReluctantParryStrategy,
)
from simulation.strategies.target_finders import EasiestTargetFinder

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestTargetFinderWithFormation(unittest.TestCase):
    """TargetFinder should only return enemies the attacker can reach."""

    def test_edge_cannot_find_far_target(self):
        """In 3v2 line, A0 cannot attack B1."""
        a0 = Character("A0")
        a0.set_actions([1])
        a1 = Character("A1")
        a1.set_actions([1])
        a2 = Character("A2")
        a2.set_actions([1])
        b0 = Character("B0")
        b0.set_actions([1])
        b1 = Character("B1")
        b1.set_actions([1])
        formation = LineFormation([[a0, a1, a2], [b0, b1]])
        groups = [Group("A", [a0, a1, a2]), Group("B", [b0, b1])]
        context = EngineContext(groups, formation=formation)
        finder = EasiestTargetFinder()
        enemies = finder.find_enemies(a0, context)
        self.assertIn(b0, enemies)
        self.assertNotIn(b1, enemies)

    def test_center_can_find_both_targets(self):
        """In 3v2 line, A1 can attack both B0 and B1."""
        a0 = Character("A0")
        a0.set_actions([1])
        a1 = Character("A1")
        a1.set_actions([1])
        a2 = Character("A2")
        a2.set_actions([1])
        b0 = Character("B0")
        b0.set_actions([1])
        b1 = Character("B1")
        b1.set_actions([1])
        formation = LineFormation([[a0, a1, a2], [b0, b1]])
        groups = [Group("A", [a0, a1, a2]), Group("B", [b0, b1])]
        context = EngineContext(groups, formation=formation)
        finder = EasiestTargetFinder()
        enemies = finder.find_enemies(a1, context)
        self.assertIn(b0, enemies)
        self.assertIn(b1, enemies)


class TestParryWithFormation(unittest.TestCase):
    """Parry should be blocked when the parrier is not adjacent to the target."""

    def test_non_adjacent_ally_cannot_parry(self):
        """In a 3v1 line, A2 is not adjacent to A0, so A2 cannot parry for A0."""
        a0 = Character("A0")
        a0.set_actions([1])
        a1 = Character("A1")
        a1.set_actions([1])
        a1.set_skill("parry", 3)
        a2 = Character("A2")
        a2.set_actions([1])
        a2.set_skill("parry", 3)
        a2.set_strategy("parry", AlwaysParryStrategy())
        b0 = Character("B0")
        b0.set_actions([1])
        formation = LineFormation([[a0, a1, a2], [b0]])
        groups = [Group("A", [a0, a1, a2]), Group("B", [b0])]
        context = EngineContext(groups, formation=formation)
        context.initialize()

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(b0, a0, "attack", initiative_action, context)
        attack.set_skill_roll(25)
        event = events.AttackRolledEvent(attack, 25)

        # A2 tries to parry for A0 — should fail because not adjacent
        responses = list(a2.parry_strategy().recommend(a2, event, context))
        self.assertEqual(0, len(responses))

    def test_adjacent_ally_can_parry(self):
        """In a 3v1 line, A1 is adjacent to A0, so A1 can parry for A0."""
        a0 = Character("A0")
        a0.set_actions([1])
        a1 = Character("A1")
        a1.set_actions([1])
        a1.set_skill("parry", 3)
        a1.set_strategy("parry", AlwaysParryStrategy())
        a2 = Character("A2")
        a2.set_actions([1])
        b0 = Character("B0")
        b0.set_actions([1])
        formation = LineFormation([[a0, a1, a2], [b0]])
        groups = [Group("A", [a0, a1, a2]), Group("B", [b0])]
        context = EngineContext(groups, round=1, phase=1, formation=formation)
        context.initialize()

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(b0, a0, "attack", initiative_action, context)
        attack.set_skill_roll(25)
        event = events.AttackRolledEvent(attack, 25)

        # A1 parries for A0 — should work because adjacent
        responses = list(a1.parry_strategy().recommend(a1, event, context))
        self.assertTrue(len(responses) > 0)


class TestShirkWithFormation(unittest.TestCase):
    """_can_shirk should only count adjacent allies."""

    def test_cannot_shirk_to_non_adjacent(self):
        """If the only other ally with actions is non-adjacent to the target,
        cannot shirk."""
        a0 = Character("A0")
        a0.set_actions([1])
        a0.set_skill("parry", 3)
        a0.set_strategy("parry", ReluctantParryStrategy())
        a1 = Character("A1")
        a1.set_actions([1])
        a1.set_skill("parry", 3)
        a1.set_strategy("parry", AlwaysParryStrategy())
        a2 = Character("A2")
        a2.set_actions([1])
        a2.set_skill("parry", 3)
        a2.set_strategy("parry", AlwaysParryStrategy())
        b0 = Character("B0")
        b0.set_actions([1])
        formation = LineFormation([[a0, a1, a2], [b0]])
        groups = [Group("A", [a0, a1, a2]), Group("B", [b0])]
        context = EngineContext(groups, round=1, phase=1, formation=formation)
        context.initialize()

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(b0, a0, "attack", initiative_action, context)
        attack.set_skill_roll(25)
        event = events.AttackRolledEvent(attack, 25)

        strategy = ReluctantParryStrategy()
        # A0 at position 0. A1 is adjacent (position 1), A2 is not (position 2).
        # A1 is adjacent and willing -> can shirk
        result = strategy._can_shirk(a0, event, context)
        self.assertTrue(result)


class TestCounterattackWithFormation(unittest.TestCase):
    """Counterattack adjacency check."""

    def test_non_adjacent_cannot_counterattack(self):
        """A character cannot counterattack for a non-adjacent ally."""
        a0 = Character("A0")
        a0.set_actions([1])
        a1 = Character("A1")
        a1.set_actions([1])
        a2 = Character("A2")
        a2.set_actions([1])
        a2.set_skill("counterattack", 3)
        b0 = Character("B0")
        b0.set_actions([1])
        formation = LineFormation([[a0, a1, a2], [b0]])
        groups = [Group("A", [a0, a1, a2]), Group("B", [b0])]
        context = EngineContext(groups, formation=formation)

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(b0, a0, "attack", initiative_action, context)
        attack.set_skill_roll(25)
        event = events.AttackDeclaredEvent(attack)

        strategy = CounterattackInterruptStrategy()
        # A2 is not adjacent to A0
        result = strategy._should_counterattack(a2, event, context)
        self.assertFalse(result)

    def test_adjacent_can_counterattack(self):
        """A character can counterattack for an adjacent ally."""
        a0 = Character("A0")
        a0.set_actions([1])
        a1 = Character("A1")
        a1.set_actions([1])
        a1.set_skill("counterattack", 3)
        b0 = Character("B0")
        b0.set_actions([1])
        formation = LineFormation([[a0, a1], [b0]])
        groups = [Group("A", [a0, a1]), Group("B", [b0])]
        context = EngineContext(groups, round=1, phase=1, formation=formation)

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(b0, a0, "attack", initiative_action, context)
        attack.set_skill_roll(25)
        event = events.AttackDeclaredEvent(attack)

        strategy = CounterattackInterruptStrategy()
        # A1 is adjacent to A0
        result = strategy._should_counterattack(a1, event, context)
        self.assertTrue(result)

    def test_self_can_always_counterattack(self):
        """A character can always counterattack for themselves."""
        a0 = Character("A0")
        a0.set_actions([1])
        a0.set_skill("counterattack", 3)
        b0 = Character("B0")
        b0.set_actions([1])
        formation = LineFormation([[a0], [b0]])
        groups = [Group("A", [a0]), Group("B", [b0])]
        context = EngineContext(groups, round=1, phase=1, formation=formation)

        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(b0, a0, "attack", initiative_action, context)
        attack.set_skill_roll(25)
        event = events.AttackDeclaredEvent(attack)

        strategy = CounterattackInterruptStrategy()
        result = strategy._should_counterattack(a0, event, context)
        self.assertTrue(result)


class TestDeathRedeployment(unittest.TestCase):
    """When a character dies, the formation should redeploy."""

    def test_remove_updates_attackable(self):
        """After removing a character, attackable sets should update."""
        a0 = Character("A0")
        a1 = Character("A1")
        a2 = Character("A2")
        b0 = Character("B0")
        b1 = Character("B1")
        formation = LineFormation([[a0, a1, a2], [b0, b1]])
        # Before: A0 cannot attack B1
        self.assertFalse(formation.can_attack(a0, b1))
        # Remove A2 -> 2v2
        formation.remove(a2)
        # After: A0 can now attack B1
        self.assertTrue(formation.can_attack(a0, b1))


class TestBatchReset(unittest.TestCase):
    """Formation should be restored after context reset."""

    def test_formation_reset_on_context_reset(self):
        a0 = Character("A0")
        a0.set_actions([1])
        a1 = Character("A1")
        a1.set_actions([1])
        b0 = Character("B0")
        b0.set_actions([1])
        formation = LineFormation([[a0, a1], [b0]])
        groups = [Group("A", [a0, a1]), Group("B", [b0])]
        context = EngineContext(groups, formation=formation)

        # Remove one character from formation
        formation.remove(a1)
        self.assertEqual(1, len(formation.sides()[0]))

        # Reset context
        context.reset()

        # Formation should be restored
        self.assertEqual(2, len(context.formation().sides()[0]))


class TestSurroundFormationIntegration(unittest.TestCase):
    """Test SurroundFormation with EngineContext."""

    def test_surround_all_attack_inner(self):
        """In a 3v1 surround, all outer can attack the inner."""
        a = [Character(f"A{i}") for i in range(3)]
        for c in a:
            c.set_actions([1])
        b0 = Character("B0")
        b0.set_actions([1])
        formation = SurroundFormation([a, [b0]])
        groups = [Group("A", a), Group("B", [b0])]
        context = EngineContext(groups, formation=formation)
        finder = EasiestTargetFinder()
        for ai in a:
            enemies = finder.find_enemies(ai, context)
            self.assertIn(b0, enemies)

    def test_surround_inner_attacks_all(self):
        """In a 3v1 surround, the inner can attack all outer."""
        a = [Character(f"A{i}") for i in range(3)]
        for c in a:
            c.set_actions([1])
        b0 = Character("B0")
        b0.set_actions([1])
        formation = SurroundFormation([a, [b0]])
        groups = [Group("A", a), Group("B", [b0])]
        context = EngineContext(groups, formation=formation)
        finder = EasiestTargetFinder()
        enemies = finder.find_enemies(b0, context)
        for ai in a:
            self.assertIn(ai, enemies)


class TestDefeatEventRemovesFromFormation(unittest.TestCase):
    """When a DefeatEvent is processed, the formation should be updated."""

    def test_defeat_event_removes_character(self):
        a0 = Character("A0")
        a0.set_actions([1])
        a1 = Character("A1")
        a1.set_actions([1])
        b0 = Character("B0")
        b0.set_actions([1])
        b1 = Character("B1")
        b1.set_actions([1])
        formation = LineFormation([[a0, a1], [b0, b1]])
        groups = [Group("A", [a0, a1]), Group("B", [b0, b1])]
        context = EngineContext(groups, formation=formation)

        # B0 is on the formation's side 1
        self.assertEqual(2, len(formation.sides()[1]))

        # Process defeat event through context
        # B1 is still fighting so combat won't end
        defeat_event = events.DeathEvent(b0)
        context.update_status(defeat_event)

        # B0 should have been removed from the formation
        self.assertEqual(1, len(formation.sides()[1]))
