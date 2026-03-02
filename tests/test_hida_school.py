#!/usr/bin/env python3

#
# test_hida_school.py
#
# Unit tests for the Hida Bushi School.
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
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import hida_school
from simulation.strategies.base import CounterattackInterruptStrategy

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestHidaBushiSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = hida_school.HidaBushiSchool()
        self.assertEqual("Hida Bushi School", school.name())

    def test_school_ring(self):
        school = hida_school.HidaBushiSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = hida_school.HidaBushiSchool()
        self.assertEqual(["counterattack", "iaijutsu", "lunge"], school.school_knacks())

    def test_extra_rolled(self):
        school = hida_school.HidaBushiSchool()
        extra = school.extra_rolled()
        self.assertEqual(["attack", "counterattack", "wound check"], extra)

    def test_free_raise_skills(self):
        school = hida_school.HidaBushiSchool()
        self.assertEqual(["counterattack"], school.free_raise_skills())


class TestHidaSpecialAbility(unittest.TestCase):
    """The Hida special ability sets counterattack interrupt cost to 1
    and installs the counterattack interrupt strategy."""

    def test_interrupt_cost(self):
        school = hida_school.HidaBushiSchool()
        builder = CharacterBuilder(9001).with_name("Hida").with_school(school)
        hida = builder.build()
        enemy = Character("Enemy")
        context = EngineContext([Group("Crab", hida), Group("Enemy", enemy)])
        self.assertEqual(1, hida.interrupt_cost("counterattack", context))

    def test_interrupt_strategy_is_counterattack(self):
        school = hida_school.HidaBushiSchool()
        builder = CharacterBuilder(9001).with_name("Hida").with_school(school)
        hida = builder.build()
        self.assertIsInstance(hida.interrupt_strategy(), CounterattackInterruptStrategy)


class TestHidaTakeCounterattackActionEvent(unittest.TestCase):
    """Test the Hida-specific counterattack event that applies +5 to
    the original attacker's roll when used as an interrupt."""

    def setUp(self):
        self.hida = Character("Hida")
        self.hida.set_skill("counterattack", 3)
        self.hida.set_actions([5, 8])
        self.attacker = Character("Attacker")
        self.attacker.set_actions([1])
        groups = [Group("Crab", self.hida), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        # original attack: attacker attacks hida
        self.attack_initiative = InitiativeAction([1], 1)
        self.attack = actions.AttackAction(
            self.attacker, self.hida, "attack", self.attack_initiative, self.context,
        )
        self.attack.set_skill_roll(25)

    def test_interrupt_applies_plus_five(self):
        """When counterattacking as interrupt, a pending +5 bonus is stored."""
        # counterattack as interrupt (is_interrupt=True)
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.hida.set_roll_provider(roll_provider)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # a pending +5 bonus should be stored on the original attack
        self.assertEqual(5, getattr(self.attack, '_counterattack_roll_bonus', 0))

    def test_non_interrupt_no_penalty(self):
        """When counterattacking with a regular action, no pending bonus is stored."""
        # counterattack as regular action (is_interrupt=False)
        regular_action = InitiativeAction([5], 5)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            regular_action, self.context, self.attack,
        )
        # rig rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.hida.set_roll_provider(roll_provider)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # no pending bonus should be stored
        self.assertEqual(0, getattr(self.attack, '_counterattack_roll_bonus', 0))

    def test_counterattack_hit_deals_damage(self):
        """A successful counterattack deals damage to the original attacker."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: counterattack succeeds (roll 30 >= tn 10)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.hida.set_roll_provider(roll_provider)
        # rig attacker's wound check to succeed
        attacker_roll_provider = CalvinistRollProvider()
        attacker_roll_provider.put_wound_check_roll(20)
        self.attacker.set_roll_provider(attacker_roll_provider)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # attacker took 15 LW, wound check succeeded, chose to take SW
        # (KeepLightWoundsStrategy decided to take SW since next check might be bad)
        self.assertEqual(1, self.attacker.sw())

    def test_counterattack_miss_no_damage(self):
        """A missed counterattack deals no damage."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls: counterattack misses (roll 5 < tn 10)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 5)
        self.hida.set_roll_provider(roll_provider)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        # attacker should have no damage
        self.assertEqual(0, self.attacker.lw())

    def test_event_history(self):
        """Verify the correct sequence of events for a successful counterattack."""
        interrupt_action = InitiativeAction([5, 8], 1, is_interrupt=True)
        counterattack = actions.CounterattackAction(
            self.hida, self.attacker, "counterattack",
            interrupt_action, self.context, self.attack,
        )
        # rig rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("counterattack", 30)
        roll_provider.put_damage_roll(15)
        self.hida.set_roll_provider(roll_provider)
        # rig attacker wound check
        attacker_rp = CalvinistRollProvider()
        attacker_rp.put_wound_check_roll(50)
        self.attacker.set_roll_provider(attacker_rp)

        take_event = hida_school.HidaTakeCounterattackActionEvent(counterattack)
        engine = CombatEngine(self.context)
        engine.event(take_event)

        history = engine.history()
        # take_counterattack
        self.assertIsInstance(history[0], hida_school.HidaTakeCounterattackActionEvent)
        # counterattack_declared
        self.assertIsInstance(history[1], events.CounterattackDeclaredEvent)
        # counterattack_rolled
        self.assertIsInstance(history[2], events.CounterattackRolledEvent)
        # counterattack_succeeded
        self.assertIsInstance(history[3], events.CounterattackSucceededEvent)
        # lw_damage
        self.assertIsInstance(history[4], events.LightWoundsDamageEvent)


class TestHidaFourthDan(unittest.TestCase):
    """4th Dan raises the school ring (Water)."""

    def test_fourth_dan_raises_water(self):
        school = hida_school.HidaBushiSchool()
        builder = (
            CharacterBuilder(9001)
            .with_name("Hida")
            .with_school(school)
            .buy_skill("counterattack", 4)
            .buy_skill("iaijutsu", 4)
            .buy_skill("lunge", 4)
        )
        hida = builder.build()
        # School ring starts at 3, 4th Dan raises it to 4
        self.assertEqual(4, hida.ring("water"))


class TestHidaTakeActionEventFactory(unittest.TestCase):
    def test_returns_hida_counterattack_event(self):
        hida = Character("Hida")
        hida.set_skill("counterattack", 3)
        attacker = Character("Attacker")
        groups = [Group("Crab", hida), Group("Enemy", attacker)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, hida, "attack", initiative_action, context)
        counterattack = actions.CounterattackAction(
            hida, attacker, "counterattack", initiative_action, context, attack,
        )
        factory = hida_school.HidaTakeActionEventFactory()
        event = factory.get_take_counterattack_action_event(counterattack)
        self.assertIsInstance(event, hida_school.HidaTakeCounterattackActionEvent)
