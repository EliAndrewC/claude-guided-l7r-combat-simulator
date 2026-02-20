#!/usr/bin/env python3

#
# test_target_finders.py
#
# Unit tests for target_finders classes.
#

import logging
import sys
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.initiative_actions import InitiativeAction
from simulation.log import logger
from simulation.target_finders import TargetFinder

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestTargetFinder(unittest.TestCase):
  def setUp(self):
    akodo = Character('Akodo')
    akodo.set_skill('parry', 4)
    doji = Character('Doji')
    doji.set_skill('parry', 5)
    bayushi = Character('Bayushi')
    bayushi.set_skill('parry', 4)
    hida = Character('Hida')
    hida.set_skill('parry', 5)
    groups = [Group('East', [akodo, doji]), Group('West', [bayushi, hida])]
    self.akodo = akodo
    self.doji = doji
    self.bayushi = bayushi
    self.hida = hida
    self.initiative_action = InitiativeAction([4], 4)
    self.context = EngineContext(groups)
    self.context.initialize()

  def test_find_enemies(self):
    finder = TargetFinder()
    self.assertEqual([self.bayushi, self.hida], finder.find_enemies(self.akodo, self.context))
    self.assertEqual([self.akodo, self.doji], finder.find_enemies(self.bayushi, self.context))

  def test_find_easiest_target(self):
    finder = TargetFinder()
    # initial knowledge should find hida easier to hit, because the default tn to hit is 20
    self.akodo.knowledge().observe_tn_to_hit(self.bayushi, 25)
    self.assertEqual(self.hida, finder.find_easiest_target(self.akodo, 'attack', self.initiative_action, self.context))
    # with fuller knowledge, bayushi is the best target
    self.akodo.knowledge().observe_tn_to_hit(self.hida, 30)
    self.assertEqual(self.bayushi, finder.find_easiest_target(self.akodo, 'attack', self.initiative_action, self.context))
  
