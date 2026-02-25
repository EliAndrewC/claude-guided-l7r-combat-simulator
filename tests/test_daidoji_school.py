#!/usr/bin/env python3

#
# test_daidoji_school.py
#
# Unit tests for the Daidoji Yojimbo School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import TestRollProvider
from simulation.schools import daidoji_school
from simulation.strategies.base import CounterattackInterruptStrategy

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestDaidojiYojimboSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual("Daidoji Yojimbo School", school.name())

    def test_school_ring(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual(["counterattack", "double attack", "iaijutsu"], school.school_knacks())

    def test_extra_rolled(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual(["attack", "counterattack", "wound check"], school.extra_rolled())

    def test_free_raise_skills(self):
        school = daidoji_school.DaidojiYojimboSchool()
        self.assertEqual(["counterattack"], school.free_raise_skills())


class TestDaidojiSpecialAbility(unittest.TestCase):
    """The Daidoji special ability sets counterattack interrupt cost to 1,
    installs counterattack interrupt strategy, and the custom action factory."""

    def test_interrupt_cost(self):
        school = daidoji_school.DaidojiYojimboSchool()
        builder = CharacterBuilder(9001).with_name("Daidoji").with_school(school)
        daidoji = builder.build()
        enemy = Character("Enemy")
        context = EngineContext([Group("Crane", daidoji), Group("Enemy", enemy)])
        self.assertEqual(1, daidoji.interrupt_cost("counterattack", context))

    def test_interrupt_strategy_is_counterattack(self):
        school = daidoji_school.DaidojiYojimboSchool()
        builder = CharacterBuilder(9001).with_name("Daidoji").with_school(school)
        daidoji = builder.build()
        self.assertIsInstance(daidoji.interrupt_strategy(), CounterattackInterruptStrategy)


class TestDaidojiCounterattackAction(unittest.TestCase):
    """Test the Daidoji counterattack has no penalty for counterattacking
    on behalf of others."""

    def setUp(self):
        self.daidoji = Character("Daidoji")
        self.daidoji.set_skill("counterattack", 3)
        self.daidoji.set_skill("parry", 3)
        self.daidoji.set_actions([1, 5])
        self.ally = Character("Ally")
        self.ally.set_skill("parry", 3)
        self.attacker = Character("Attacker")
        self.attacker.set_skill("parry", 3)
        self.attacker.set_actions([1])
        groups = [
            Group("Crane", [self.daidoji, self.ally]),
            Group("Enemy", self.attacker),
        ]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_no_penalty_for_others(self):
        """Daidoji counterattacking on behalf of an ally has no TN penalty."""
        # attack targets the ally, not the daidoji
        attack = actions.AttackAction(
            self.attacker, self.ally, "attack", self.initiative_action, self.context,
        )
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            self.initiative_action, self.context, attack,
        )
        # TN should be just the attacker's tn_to_hit, no penalty
        expected_tn = self.attacker.tn_to_hit()
        self.assertEqual(expected_tn, counterattack.tn())

    def test_standard_counterattack_has_penalty(self):
        """Regular CounterattackAction for comparison: has penalty when counterattacking for others."""
        attack = actions.AttackAction(
            self.attacker, self.ally, "attack", self.initiative_action, self.context,
        )
        counterattack = actions.CounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            self.initiative_action, self.context, attack,
        )
        # Standard counterattack has penalty of 5 * attacker's parry
        expected_tn = self.attacker.tn_to_hit() + 5 * self.attacker.skill("parry")
        self.assertEqual(expected_tn, counterattack.tn())

    def test_no_penalty_for_self(self):
        """Counterattacking on your own behalf has no penalty (same as standard)."""
        attack = actions.AttackAction(
            self.attacker, self.daidoji, "attack", self.initiative_action, self.context,
        )
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            self.initiative_action, self.context, attack,
        )
        expected_tn = self.attacker.tn_to_hit()
        self.assertEqual(expected_tn, counterattack.tn())


class TestDaidojiActionFactory(unittest.TestCase):
    def test_returns_daidoji_counterattack_action(self):
        daidoji = Character("Daidoji")
        attacker = Character("Attacker")
        groups = [Group("Crane", daidoji), Group("Enemy", attacker)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, daidoji, "attack", initiative_action, context)
        factory = daidoji_school.DaidojiActionFactory()
        counterattack = factory.get_counterattack_action(
            daidoji, attacker, attack, "counterattack", initiative_action, context,
        )
        self.assertIsInstance(counterattack, daidoji_school.DaidojiCounterattackAction)


class TestDaidojiTakeCounterattackActionEvent(unittest.TestCase):
    """Test the Daidoji-specific counterattack event that gives the opponent
    a free raise on wound check when used as an interrupt."""

    def setUp(self):
        self.daidoji = Character("Daidoji")
        self.daidoji.set_skill("counterattack", 3)
        self.daidoji.set_actions([5, 8])
        self.attacker = Character("Attacker")
        self.attacker.set_actions([1])
        groups = [Group("Crane", self.daidoji), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        # original attack: attacker attacks daidoji
        self.attack_initiative = InitiativeAction([1], 1)
        self.attack = actions.AttackAction(
            self.attacker, self.daidoji, "attack", self.attack_initiative, self.context,
        )
        self.attack.set_skill_roll(25)

    def test_interrupt_gives_opponent_wound_check_bonus(self):
        """When counterattacking as interrupt and hitting, opponent gets -5 TN on wound check."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: counterattack succeeds, damage = 20
        roll_provider = TestRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(20)
        self.daidoji.set_roll_provider(roll_provider)
        # rig attacker's wound check
        attacker_rp = TestRollProvider()
        attacker_rp.put_wound_check_roll(18)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # Find the LW damage event in history
        history = engine.history()
        lw_events = [e for e in history if isinstance(e, events.LightWoundsDamageEvent)]
        self.assertEqual(1, len(lw_events))
        lw_event = lw_events[0]
        # Damage is 20, but wound check TN should be 20 - 5 = 15 (free raise)
        self.assertEqual(20, lw_event.damage)
        self.assertEqual(15, lw_event.wound_check_tn)

    def test_non_interrupt_no_wound_check_bonus(self):
        """When counterattacking with a regular action, no wound check bonus."""
        regular_action = InitiativeAction([5], 5)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            regular_action, self.context, self.attack,
        )
        # rig rolls
        roll_provider = TestRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(20)
        self.daidoji.set_roll_provider(roll_provider)
        # rig attacker's wound check
        attacker_rp = TestRollProvider()
        attacker_rp.put_wound_check_roll(18)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        lw_events = [e for e in history if isinstance(e, events.LightWoundsDamageEvent)]
        self.assertEqual(1, len(lw_events))
        lw_event = lw_events[0]
        # No bonus: wound check TN should equal damage
        self.assertEqual(20, lw_event.damage)
        self.assertEqual(20, lw_event.wound_check_tn)

    def test_counterattack_miss_no_damage(self):
        """A missed counterattack deals no damage."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: miss
        roll_provider = TestRollProvider()
        roll_provider.put_skill_roll("counterattack", 5)
        self.daidoji.set_roll_provider(roll_provider)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        self.assertEqual(0, self.attacker.lw())

    def test_event_history(self):
        """Verify the correct event sequence for a successful Daidoji counterattack."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            self.daidoji, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        roll_provider = TestRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.daidoji.set_roll_provider(roll_provider)
        attacker_rp = TestRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = daidoji_school.DaidojiTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        self.assertIsInstance(history[0], daidoji_school.DaidojiTakeCounterattackActionEvent)
        self.assertIsInstance(history[1], events.CounterattackDeclaredEvent)
        self.assertIsInstance(history[2], events.CounterattackRolledEvent)
        self.assertIsInstance(history[3], events.CounterattackSucceededEvent)
        self.assertIsInstance(history[4], events.LightWoundsDamageEvent)


class TestDaidojiFourthDan(unittest.TestCase):
    """4th Dan raises the school ring (Water)."""

    def test_fourth_dan_raises_water(self):
        school = daidoji_school.DaidojiYojimboSchool()
        builder = (
            CharacterBuilder(9001)
            .with_name("Daidoji")
            .with_school(school)
            .buy_skill("counterattack", 4)
            .buy_skill("double attack", 4)
            .buy_skill("iaijutsu", 4)
        )
        daidoji = builder.build()
        # School ring starts at 3, 4th Dan raises it to 4
        self.assertEqual(4, daidoji.ring("water"))


class TestDaidojiTakeActionEventFactory(unittest.TestCase):
    def test_returns_daidoji_counterattack_event(self):
        daidoji = Character("Daidoji")
        attacker = Character("Attacker")
        groups = [Group("Crane", daidoji), Group("Enemy", attacker)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, daidoji, "attack", initiative_action, context)
        counterattack = daidoji_school.DaidojiCounterattackAction(
            daidoji, attacker, "counterattack", initiative_action, context, attack,
        )
        factory = daidoji_school.DaidojiTakeActionEventFactory()
        event = factory.get_take_counterattack_action_event(counterattack)
        self.assertIsInstance(event, daidoji_school.DaidojiTakeCounterattackActionEvent)
