#!/usr/bin/env python3

#
# test_counterattack_timing.py
#
# Integration tests for counterattack timing: counterattacks should
# happen before the attack roll, not after.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import daidoji_school, hida_school
from simulation.strategies.base import CounterattackInterruptStrategy

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestCounterattackBeforeRoll(unittest.TestCase):
    """Counterattack events should appear before the AttackRolledEvent in history."""

    def setUp(self):
        self.defender = Character("Defender")
        self.defender.set_skill("counterattack", 3)
        self.defender.set_actions([3, 5])
        self.defender.set_strategy("interrupt", CounterattackInterruptStrategy())

        self.attacker = Character("Attacker")
        self.attacker.set_actions([3])

        groups = [
            Group("Heroes", self.defender),
            Group("Villains", self.attacker),
        ]
        self.context = EngineContext(groups, round=1, phase=5)
        self.context.initialize()

        # rig defender's rolls: counterattack misses, wound check succeeds
        defender_rp = CalvinistRollProvider()
        defender_rp.put_skill_roll("counterattack", 5)
        defender_rp.put_wound_check_roll(50)
        self.defender.set_roll_provider(defender_rp)

        # rig attacker's attack roll (hit) and damage
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll("attack", 20)
        attacker_rp.put_damage_roll(10)
        self.attacker.set_roll_provider(attacker_rp)

    def test_counterattack_before_attack_roll(self):
        """Counterattack events should appear before AttackRolledEvent."""
        initiative_action = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            self.attacker, self.defender, "attack", initiative_action, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        counterattack_indices = [
            i for i, e in enumerate(history)
            if isinstance(e, events.CounterattackRolledEvent)
        ]
        attack_rolled_indices = [
            i for i, e in enumerate(history)
            if isinstance(e, events.AttackRolledEvent)
        ]
        self.assertTrue(len(counterattack_indices) > 0, "Should have a counterattack")
        self.assertTrue(len(attack_rolled_indices) > 0, "Should have an attack roll")
        self.assertLess(
            counterattack_indices[0], attack_rolled_indices[0],
            "Counterattack should happen before the attack roll",
        )

    def test_event_ordering(self):
        """Verify the full event sequence: declare → counterattack → roll attack."""
        initiative_action = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            self.attacker, self.defender, "attack", initiative_action, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        event_types = [type(e) for e in history]

        declared_idx = event_types.index(events.AttackDeclaredEvent)
        spend_idx = next(
            i for i, e in enumerate(history)
            if isinstance(e, events.SpendActionEvent) and e.skill == "counterattack"
        )
        counter_rolled_idx = event_types.index(events.CounterattackRolledEvent)
        attack_rolled_idx = event_types.index(events.AttackRolledEvent)

        self.assertLess(declared_idx, spend_idx)
        self.assertLess(spend_idx, counter_rolled_idx)
        self.assertLess(counter_rolled_idx, attack_rolled_idx)


class TestCounterattackKillsAttacker(unittest.TestCase):
    """When counterattack kills the attacker, the attack should not proceed."""

    def test_dead_attacker_no_attack_roll(self):
        """If counterattack kills the attacker, no AttackRolledEvent should appear."""
        defender = Character("Defender")
        defender.set_skill("counterattack", 3)
        defender.set_actions([3, 5])
        defender.set_strategy("interrupt", CounterattackInterruptStrategy())

        attacker = Character("Attacker")
        attacker.set_actions([3])
        # Set attacker to 3 SW (one more = unconscious with Earth 2, max_sw 4)
        attacker.take_sw(3)

        # Add a dummy ally so CombatEnded is not raised
        dummy = Character("Dummy")
        groups = [
            Group("Heroes", defender),
            Group("Villains", [attacker, dummy]),
        ]
        context = EngineContext(groups, round=1, phase=5)
        context.initialize()

        # rig defender's counterattack roll (hit with high damage)
        defender_rp = CalvinistRollProvider()
        defender_rp.put_skill_roll("counterattack", 30)
        defender_rp.put_damage_roll(20)
        defender.set_roll_provider(defender_rp)

        # rig attacker's wound check to fail (low roll)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(5)
        attacker.set_roll_provider(attacker_rp)

        initiative_action = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            attacker, defender, "attack", initiative_action, context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(context)
        engine.event(take_event)

        history = engine.history()
        # The attacker should no longer be fighting
        self.assertFalse(attacker.is_fighting())
        # There should be no AttackRolledEvent since the attacker was killed
        attack_rolled = [e for e in history if isinstance(e, events.AttackRolledEvent)]
        self.assertEqual(0, len(attack_rolled), "Attack should not proceed after attacker is killed")
        # There should be a defeat event (death or unconscious) for the attacker
        defeat = [e for e in history if isinstance(e, events.DefeatEvent) and e.subject == attacker]
        self.assertTrue(len(defeat) > 0, "Attacker should be defeated")


class TestDaidojiAlwaysCounterattacks(unittest.TestCase):
    """Daidoji should counterattack on every incoming attack when actions are available."""

    def setUp(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.daidoji = Character("Daidoji")
        self.daidoji.set_skill("counterattack", 3)
        self.daidoji.set_actions([3, 5])
        school.apply_special_ability(self.daidoji)

        self.attacker = Character("Attacker")
        self.attacker.set_actions([3])

        groups = [
            Group("Crane", self.daidoji),
            Group("Enemy", self.attacker),
        ]
        self.context = EngineContext(groups, round=1, phase=5)
        self.context.initialize()

    def test_counterattacks_on_hit(self):
        """Daidoji counterattacks even when we don't know if the attack will hit."""
        # rig daidoji's counterattack (miss) and wound check
        daidoji_rp = CalvinistRollProvider()
        daidoji_rp.put_skill_roll("counterattack", 5)
        daidoji_rp.put_wound_check_roll(50)
        self.daidoji.set_roll_provider(daidoji_rp)

        # rig attacker's attack (hit) and damage
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll("attack", 20)
        attacker_rp.put_damage_roll(10)
        self.attacker.set_roll_provider(attacker_rp)

        initiative_action = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            self.attacker, self.daidoji, "attack", initiative_action, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        counterattacks = [e for e in history if isinstance(e, events.CounterattackRolledEvent)]
        self.assertEqual(1, len(counterattacks), "Daidoji should counterattack")

    def test_counterattacks_on_miss(self):
        """Daidoji counterattacks even when the attack will miss."""
        # rig daidoji's counterattack
        daidoji_rp = CalvinistRollProvider()
        daidoji_rp.put_skill_roll("counterattack", 5)
        self.daidoji.set_roll_provider(daidoji_rp)

        # rig attacker's attack (miss)
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll("attack", 3)
        self.attacker.set_roll_provider(attacker_rp)

        initiative_action = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            self.attacker, self.daidoji, "attack", initiative_action, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        counterattacks = [e for e in history if isinstance(e, events.CounterattackRolledEvent)]
        self.assertEqual(1, len(counterattacks), "Daidoji should counterattack even on a miss")

    def test_no_counterattack_without_actions(self):
        """Daidoji should not counterattack if no actions are available."""
        self.daidoji.set_actions([])

        # rig attacker's attack
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll("attack", 3)
        self.attacker.set_roll_provider(attacker_rp)

        initiative_action = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            self.attacker, self.daidoji, "attack", initiative_action, self.context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        counterattacks = [e for e in history if isinstance(e, events.CounterattackRolledEvent)]
        self.assertEqual(0, len(counterattacks), "Daidoji should not counterattack without actions")


class TestHidaBonusAppliedToAttackRoll(unittest.TestCase):
    """Hida's +5 bonus should be applied to the attacker's roll after counterattack."""

    def test_hida_interrupt_adds_five_to_attack_roll(self):
        """When Hida counterattacks as interrupt, the attacker's roll gets +5."""
        school = hida_school.HidaBushiSchool()
        hida = Character("Hida")
        hida.set_skill("counterattack", 3)
        # Actions at phases 7 and 9 — not available at phase 5 as regular actions
        # but Hida's interrupt cost is 1, so interrupt is possible
        hida.set_actions([7, 9])
        school.apply_special_ability(hida)

        attacker = Character("Attacker")
        attacker.set_actions([3])

        groups = [
            Group("Crab", hida),
            Group("Enemy", attacker),
        ]
        context = EngineContext(groups, round=1, phase=5)
        context.initialize()

        # rig hida's counterattack (miss) and wound check
        hida_rp = CalvinistRollProvider()
        hida_rp.put_skill_roll("counterattack", 5)
        hida_rp.put_wound_check_roll(50)
        hida.set_roll_provider(hida_rp)

        # rig attacker's attack roll to exactly 10 (base)
        # After Hida's +5 bonus, the recorded roll should be 15
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_skill_roll("attack", 10)
        attacker_rp.put_damage_roll(10)
        attacker.set_roll_provider(attacker_rp)

        initiative_action = InitiativeAction([3], 3)
        attack = actions.AttackAction(
            attacker, hida, "attack", initiative_action, context,
        )
        take_event = events.TakeAttackActionEvent(attack)
        engine = CombatEngine(context)
        engine.event(take_event)

        history = engine.history()
        attack_rolled = [e for e in history if isinstance(e, events.AttackRolledEvent)]
        self.assertEqual(1, len(attack_rolled))
        # The roll should be 10 (base) + 5 (Hida bonus) = 15
        self.assertEqual(15, attack_rolled[0].roll)
        self.assertEqual(15, attack.skill_roll())


if __name__ == "__main__":
    unittest.main()
