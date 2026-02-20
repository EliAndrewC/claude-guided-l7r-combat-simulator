#!/usr/bin/env python3

#
# test_akodo_school.py
#
# Unit tests for the Akodo Bushi School.
#

import logging
import sys
import unittest

from simulation import actions, akodo_school, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.initiative_actions import InitiativeAction
from simulation.log import logger
 
# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestAkodoAttackFailedListener(unittest.TestCase):
  def setUp(self):
    self.akodo = Character('Akodo')
    self.akodo.set_actions([1,])
    self.bayushi = Character('Bayushi')
    groups = [Group('Lion', self.akodo), Group('Scorpion', self.bayushi)]
    self.context = EngineContext(groups)
    self.initiative_action = InitiativeAction([1], 1)

  def test_feint_failed(self):
    action = actions.FeintAction(self.akodo, self.bayushi, 'feint', \
      self.initiative_action, self.context)
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
    self.akodo = Character('Akodo')
    self.akodo.set_actions([1,])
    self.bayushi = Character('Bayushi')
    groups = [Group('Lion', self.akodo), Group('Scorpion', self.bayushi)]
    self.context = EngineContext(groups)
    self.initiative_action = InitiativeAction([1], 1)

  def test_feint_succeeded(self):
    action = actions.FeintAction(self.akodo, self.bayushi, 'feint', \
      self.initiative_action, self.context)
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
    self.akodo = Character('Akodo')
    self.bayushi = Character('Bayushi')
    groups = [Group('Lion', self.akodo), Group('Scorpion', self.bayushi)]
    self.context = EngineContext(groups)

  def test_inflict_lw(self):
    event = events.LightWoundsDamageEvent(self.bayushi, self.akodo, 7)
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

  def test_no_vp(self):
    self.akodo.spend_vp(2)
    self.bayushi = Character('Bayushi')
    event = events.LightWoundsDamageEvent(self.bayushi, self.akodo, 7)
    strategy = akodo_school.AkodoFifthDanStrategy()
    responses = list(strategy.recommend(self.akodo, event, self.context))
    self.assertEqual([], responses)

