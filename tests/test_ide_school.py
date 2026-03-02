#!/usr/bin/env python3

#
# test_ide_school.py
#
# Unit tests for the Ide Diplomat School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import ide_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestIdeDiplomatSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual("Ide Diplomat School", school.name())

    def test_extra_rolled(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual(["wound check", "initiative", "precepts"], school.extra_rolled())

    def test_school_ring(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual(["double attack", "feint", "worldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual(["attack"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertIsNone(school.ap_base_skill())


class TestIdeFeintSucceededListener(unittest.TestCase):
    def setUp(self):
        self.ide = Character("Ide")
        self.ide.set_actions([1])
        self.target = Character("Target")
        groups = [Group("Unicorn", self.ide), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_feint_succeeded_adds_modifier(self):
        action = actions.FeintAction(self.ide, self.target, "feint", self.initiative_action, self.context)
        event = events.AttackSucceededEvent(action)
        listener = ide_school.IdeFeintSucceededListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(1, len(responses))
        response = responses[0]
        self.assertIsInstance(response, events.AddModifierEvent)
        self.assertEqual(self.target, response.subject)
        # Modifier should reduce TN by 10
        self.assertEqual(-10, response.modifier.adjustment())

    def test_non_feint_attack_no_effect(self):
        action = actions.AttackAction(self.ide, self.target, "attack", self.initiative_action, self.context)
        event = events.AttackSucceededEvent(action)
        listener = ide_school.IdeFeintSucceededListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(0, len(responses))


class TestIdeFeintFailedListener(unittest.TestCase):
    def setUp(self):
        self.ide = Character("Ide")
        self.ide.set_actions([1])
        self.target = Character("Target")
        groups = [Group("Unicorn", self.ide), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_parried_feint_adds_modifier(self):
        action = actions.FeintAction(self.ide, self.target, "feint", self.initiative_action, self.context)
        action.set_parried()  # Simulate being parried
        event = events.AttackFailedEvent(action)
        listener = ide_school.IdeFeintFailedListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(1, len(responses))
        response = responses[0]
        self.assertIsInstance(response, events.AddModifierEvent)
        self.assertEqual(-10, response.modifier.adjustment())

    def test_missed_feint_no_modifier(self):
        action = actions.FeintAction(self.ide, self.target, "feint", self.initiative_action, self.context)
        # Not parried, just missed
        event = events.AttackFailedEvent(action)
        listener = ide_school.IdeFeintFailedListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(0, len(responses))


class TestIdeTactSubtractListener(unittest.TestCase):
    def setUp(self):
        self.ide = Character("Ide")
        self.ide.set_skill("tact", 3)
        self.ide.set_actions([1])
        self.attacker = Character("Attacker")
        self.attacker.set_actions([1])
        groups = [Group("Unicorn", self.ide), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_subtract_from_enemy_attack(self):
        # Use CalvinistRollProvider so tact roll is predictable
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("tact", 7)
        self.ide.set_roll_provider(roll_provider)
        action = actions.AttackAction(self.attacker, self.ide, "attack", self.initiative_action, self.context)
        action.set_skill_roll(30)
        event = events.AttackRolledEvent(action, 30)
        listener = ide_school.IdeTactSubtractListener()
        responses = list(listener.handle(self.ide, event, self.context))
        # Should spend VP, then yield new AttackRolledEvent
        self.assertEqual(2, len(responses))
        self.assertIsInstance(responses[0], events.SpendVoidPointsEvent)
        self.assertEqual(1, responses[0].amount)
        self.assertEqual("tact", responses[0].skill)
        self.assertIsInstance(responses[1], events.AttackRolledEvent)
        self.assertEqual(23, responses[1].roll)  # 30 - 7 = 23

    def test_no_subtract_when_no_vp(self):
        self.ide.spend_vp(self.ide.vp())  # Spend all VP
        action = actions.AttackAction(self.attacker, self.ide, "attack", self.initiative_action, self.context)
        action.set_skill_roll(30)
        event = events.AttackRolledEvent(action, 30)
        listener = ide_school.IdeTactSubtractListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(0, len(responses))

    def test_no_subtract_when_no_tact(self):
        self.ide.set_skill("tact", 0)
        action = actions.AttackAction(self.attacker, self.ide, "attack", self.initiative_action, self.context)
        action.set_skill_roll(30)
        event = events.AttackRolledEvent(action, 30)
        listener = ide_school.IdeTactSubtractListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(0, len(responses))


class TestIdeSpendVPListener(unittest.TestCase):
    def setUp(self):
        self.ide = Character("Ide")
        self.ide.set_actions([1])
        self.target = Character("Target")
        groups = [Group("Unicorn", self.ide), Group("Enemy", self.target)]
        self.context = EngineContext(groups)

    def test_gain_tvp_on_non_tact_vp_spend(self):
        event = events.SpendVoidPointsEvent(self.ide, "attack", 1)
        listener = ide_school.IdeSpendVPListener()
        responses = list(listener.handle(self.ide, event, self.context))
        # Should yield GainTemporaryVoidPointsEvent
        tvp_events = [r for r in responses if isinstance(r, events.GainTemporaryVoidPointsEvent)]
        self.assertEqual(1, len(tvp_events))
        self.assertEqual(1, tvp_events[0].amount)

    def test_no_tvp_on_tact_vp_spend(self):
        event = events.SpendVoidPointsEvent(self.ide, "tact", 1)
        listener = ide_school.IdeSpendVPListener()
        responses = list(listener.handle(self.ide, event, self.context))
        # Should NOT yield GainTemporaryVoidPointsEvent
        tvp_events = [r for r in responses if isinstance(r, events.GainTemporaryVoidPointsEvent)]
        self.assertEqual(0, len(tvp_events))


class TestIdeFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        ide = Character("Ide")
        ide.set_ring("water", 3)
        school = ide_school.IdeDiplomatSchool()
        school.apply_rank_four_ability(ide)
        self.assertEqual(4, ide.ring("water"))
