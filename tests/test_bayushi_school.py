#!/usr/bin/env python3

#
# test_bayushi_school.py
#
# Unit tests for Bayushi Bushi School classes.
#

import logging
import sys
import unittest

from simulation import actions
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import TestRollProvider
from simulation.schools import bayushi_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestBayushiActionFactory(unittest.TestCase):
    def setUp(self):
        bayushi = Character("Bayushi")
        target = Character("target")
        groups = [Group("Scorpion", bayushi), Group("target", target)]
        context = EngineContext(groups)
        self.bayushi = bayushi
        self.target = target
        self.context = context
        self.initiative_action = InitiativeAction([1], 1)

    def test_get_attack(self):
        factory = bayushi_school.BayushiActionFactory()
        action = factory.get_attack_action(self.bayushi, self.target, "attack", self.initiative_action, self.context)
        self.assertTrue(isinstance(action, actions.AttackAction))
        self.assertEqual(self.bayushi, action.subject())
        self.assertEqual(self.target, action.target())
        self.assertEqual("attack", action.skill())

    def test_get_feint(self):
        factory = bayushi_school.BayushiActionFactory()
        action = factory.get_attack_action(self.bayushi, self.target, "feint", self.initiative_action, self.context)
        self.assertTrue(isinstance(action, bayushi_school.BayushiFeintAction))
        self.assertEqual(self.bayushi, action.subject())
        self.assertEqual(self.target, action.target())
        self.assertEqual("feint", action.skill())


class TestBayushiWoundCheckProvider(unittest.TestCase):
    def test_halved_lw_still_fails(self):
        # 50 LW, roll 30: check fails (30 < 50).
        # Halved LW = 25, so default provider would say 0 SW (30 >= 25).
        # But a failed check always results in at least 1 SW.
        provider = bayushi_school.BayushiWoundCheckProvider()
        self.assertEqual(1, provider.wound_check(30, 50))
        # same test using a character with the provider
        bayushi = Character("Bayushi")
        bayushi.set_wound_check_provider(provider)
        bayushi.take_lw(50)
        self.assertEqual(1, bayushi.wound_check(30))

    def test_large_damage(self):
        # 100 LW, roll 30: check fails badly (30 < 100).
        # Halved LW = 50, default provider: 1 + ((50 - 30) // 10) = 3 SW.
        provider = bayushi_school.BayushiWoundCheckProvider()
        self.assertEqual(3, provider.wound_check(30, 100))
        # same test using a character with the provider
        bayushi = Character("Bayushi")
        bayushi.set_wound_check_provider(provider)
        bayushi.take_lw(100)
        # Normal would be 8 SW, Bayushi takes 3 SW
        self.assertEqual(3, bayushi.wound_check(30))

    def test_roll_between_halved_and_actual_lw(self):
        # 58 LW, roll 32: check fails (32 < 58).
        # Halved LW = 29, default provider would say 0 SW (32 >= 29).
        # But a failed check always results in at least 1 SW.
        provider = bayushi_school.BayushiWoundCheckProvider()
        self.assertEqual(1, provider.wound_check(32, 58))

    def test_successful_wound_check(self):
        # 20 LW, roll 25: check succeeds (25 >= 20), 0 SW.
        # Halving doesn't matter here since the check passed.
        provider = bayushi_school.BayushiWoundCheckProvider()
        self.assertEqual(0, provider.wound_check(25, 20))

    def test_example_from_rules(self):
        # 58 LW, roll 22: check fails badly (22 < 58).
        # Normal: 1 + ((58 - 22) // 10) = 4 SW.
        # Halved LW = 29: 1 + ((29 - 22) // 10) = 1 SW.
        provider = bayushi_school.BayushiWoundCheckProvider()
        self.assertEqual(1, provider.wound_check(22, 58))

    def test_specified_lw(self):
        bayushi = Character("Bayushi")
        bayushi.set_wound_check_provider(bayushi_school.BayushiWoundCheckProvider())
        # 50 LW, roll 30: fails (30 < 50), at least 1 SW
        self.assertEqual(1, bayushi.wound_check(30, lw=50))


class TestBayushiFeintAction(unittest.TestCase):
    def test_roll_damage(self):
        bayushi = Character("Bayushi")
        bayushi.set_skill("attack", 4)
        bayushi.set_skill("feint", 1)
        target = Character("target")
        groups = [Group("Scorpion", bayushi), Group("target", target)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        # set Bayushi school roll parameter provider
        bayushi.set_roll_parameter_provider(bayushi_school.BayushiRollParameterProvider())
        # set test roll provider to rig damage roll
        roll_provider = TestRollProvider()
        roll_provider.put_damage_roll(9)
        bayushi.set_roll_provider(roll_provider)
        # set up Bayushi school Feint attack action
        action = bayushi_school.BayushiFeintAction(bayushi, target, "feint", initiative_action, context)
        action._attack_roll = 9001
        # assert expected behavior
        self.assertEqual(9, action.roll_damage())
        self.assertEqual((4, 1), roll_provider.pop_observed_params("damage"))
