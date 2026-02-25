#!/usr/bin/env python3

#
# test_akodo_school.py
#
# Unit tests for the Akodo Bushi School.
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
from simulation.schools import akodo_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestAkodoBushiSchoolExtraRolled(unittest.TestCase):
    def test_extra_rolled_returns_correct_skills(self):
        school = akodo_school.AkodoBushiSchool()
        extra = school.extra_rolled()
        self.assertEqual(["attack", "double attack", "wound check"], extra)
        self.assertNotIn("feint", extra)


class TestAkodoAttackFailedListener(unittest.TestCase):
    def setUp(self):
        self.akodo = Character("Akodo")
        self.akodo.set_actions(
            [
                1,
            ]
        )
        self.bayushi = Character("Bayushi")
        groups = [Group("Lion", self.akodo), Group("Scorpion", self.bayushi)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_feint_failed(self):
        action = actions.FeintAction(self.akodo, self.bayushi, "feint", self.initiative_action, self.context)
        event = events.AttackFailedEvent(action)
        listener = akodo_school.AkodoAttackFailedListener()
        responses = list(listener.handle(self.akodo, event, self.context))
        self.assertEqual(1, len(responses))
        response = responses[0]
        self.assertTrue(isinstance(response, events.GainTemporaryVoidPointsEvent))
        self.assertEqual(self.akodo, response.subject)
        self.assertEqual(1, response.amount)


class TestAkodoAttackSucceededListener(unittest.TestCase):
    def setUp(self):
        self.akodo = Character("Akodo")
        self.akodo.set_actions(
            [
                1,
            ]
        )
        self.bayushi = Character("Bayushi")
        groups = [Group("Lion", self.akodo), Group("Scorpion", self.bayushi)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_feint_succeeded(self):
        action = actions.FeintAction(self.akodo, self.bayushi, "feint", self.initiative_action, self.context)
        event = events.AttackSucceededEvent(action)
        listener = akodo_school.AkodoAttackSucceededListener()
        responses = list(listener.handle(self.akodo, event, self.context))
        self.assertEqual(1, len(responses))
        response = responses[0]
        self.assertTrue(isinstance(response, events.GainTemporaryVoidPointsEvent))
        self.assertEqual(self.akodo, response.subject)
        self.assertEqual(4, response.amount)


class TestAkodoFifthDanStrategy(unittest.TestCase):
    def setUp(self):
        self.akodo = Character("Akodo")
        self.bayushi = Character("Bayushi")
        groups = [Group("Lion", self.akodo), Group("Scorpion", self.bayushi)]
        self.context = EngineContext(groups)

    def test_inflict_lw(self):
        event = events.LightWoundsDamageEvent(self.bayushi, self.akodo, 25)
        strategy = akodo_school.AkodoFifthDanStrategy()
        responses = list(strategy.recommend(self.akodo, event, self.context))
        self.assertEqual(2, len(responses))
        first_event = responses[0]
        self.assertTrue(isinstance(first_event, events.SpendVoidPointsEvent))
        self.assertEqual(self.akodo, first_event.subject)
        self.assertEqual(2, first_event.amount)
        second_event = responses[1]
        self.assertTrue(isinstance(second_event, events.LightWoundsDamageEvent))
        self.assertEqual(self.akodo, second_event.subject)
        self.assertEqual(self.bayushi, second_event.target)
        self.assertEqual(20, second_event.damage)

    def test_damage_caps_vp(self):
        """Counter-damage (10 * VP) must not exceed damage taken."""
        # damage=15 means max_vp_for_damage = 15//10 = 1
        # character has 2 VP available and max_vp_per_roll=2, but cap limits to 1
        event = events.LightWoundsDamageEvent(self.bayushi, self.akodo, 15)
        strategy = akodo_school.AkodoFifthDanStrategy()
        responses = list(strategy.recommend(self.akodo, event, self.context))
        self.assertEqual(2, len(responses))
        first_event = responses[0]
        self.assertTrue(isinstance(first_event, events.SpendVoidPointsEvent))
        self.assertEqual(1, first_event.amount)
        second_event = responses[1]
        self.assertTrue(isinstance(second_event, events.LightWoundsDamageEvent))
        self.assertEqual(10, second_event.damage)

    def test_no_counter_when_damage_too_low(self):
        """When damage < 10, no VP can be spent on counter-damage."""
        event = events.LightWoundsDamageEvent(self.bayushi, self.akodo, 7)
        strategy = akodo_school.AkodoFifthDanStrategy()
        responses = list(strategy.recommend(self.akodo, event, self.context))
        self.assertEqual([], responses)

    def test_no_vp(self):
        self.akodo.spend_vp(2)
        self.bayushi = Character("Bayushi")
        event = events.LightWoundsDamageEvent(self.bayushi, self.akodo, 25)
        strategy = akodo_school.AkodoFifthDanStrategy()
        responses = list(strategy.recommend(self.akodo, event, self.context))
        self.assertEqual([], responses)
