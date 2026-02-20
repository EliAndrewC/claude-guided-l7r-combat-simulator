#!/usr/bin/env python3

#
# test_wound_check_optimizers.py
#
# Unit tests for wound_check_optimizers classes.
#

import logging
import sys
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.events import LightWoundsDamageEvent, WoundCheckDeclaredEvent, WoundCheckRolledEvent
from simulation.groups import Group
from simulation.log import logger
from simulation.wound_check_optimizers import DefaultWoundCheckOptimizer, DefaultKeepLightWoundsOptimizer

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestDefaultWoundCheckOptimizer(unittest.TestCase):
  def setUp(self):
    akagi = Character('Akagi')
    akagi.set_ring('water', 3)
    akodo = Character('Akodo')
    akodo.set_ring('water', 6)
    groups = [Group('Red Shirts', akagi), Group('Lion', akodo)]
    context = EngineContext(groups, round=1, phase=1)
    context.initialize()
    # set instances
    self.akagi = akagi
    self.akodo = akodo
    self.context = context

  def test_declare_none(self):
    #
    # test case where the character should spend 0 VP
    #
    # Akagi's base wound check is 4k3
    # P(15|4k3) = 0.85
    # P(20|4k3) = 0.57 
    # P(25|4k3) = 0.31
    # If Akagi has 17 LW and is willing to take 1 SW with probability 0.7, he should spend nothing.
    event = LightWoundsDamageEvent(self.akodo, self.akagi, 17)
    self.akagi.take_lw(17)
    optimizer = DefaultWoundCheckOptimizer(self.akagi, event, self.context)
    response = optimizer.declare(1, 0.7)
    self.assertTrue(isinstance(response, WoundCheckDeclaredEvent))
    self.assertEqual(response.subject, self.akagi)
    self.assertEqual(response.attacker, self.akodo)
    self.assertEqual(0, response.vp)
    #
    # Akodo's base wound check is 7k6
    # P(25|7k6) = 0.96
    # P(30|7k6) = 0.86
    # P(35|7k6) = 0.70
    # P(40|7k6) = 0.50
    # If Akodo has 44 LW and is willing to take 1 SW with probability 0.7, he should spend nothing.
    event = LightWoundsDamageEvent(self.akagi, self.akodo, 44)
    self.akodo.take_lw(44)
    optimizer = DefaultWoundCheckOptimizer(self.akodo, event, self.context)
    response = optimizer.declare(1, 0.7)
    self.assertTrue(isinstance(response, WoundCheckDeclaredEvent))
    self.assertEqual(response.subject, self.akodo)
    self.assertEqual(response.attacker, self.akagi)
    self.assertEqual(0, response.vp)

  def test_declare_one(self):
    #
    # test case where the character should spend 1 VP
    #
    # Akagi's base wound check is 4k3
    # P(15|4k3) = 0.85
    # P(20|4k3) = 0.57 
    # P(25|4k3) = 0.31
    # Akagi can get 5k4 by spending 1 VP
    # P(15|5k4) = 0.97
    # P(20|5k4) = 0.86
    # P(25|5k4) = 0.64
    # If Akagi has 35 LW and is willing to take 2 SW with probability 0.9, Akagi should spend 1 VP.
    event = LightWoundsDamageEvent(self.akodo, self.akagi, 35)
    self.akagi.take_lw(35)
    optimizer = DefaultWoundCheckOptimizer(self.akagi, event, self.context)
    response = optimizer.declare(2, 0.9)
    self.assertTrue(isinstance(response, WoundCheckDeclaredEvent))
    self.assertEqual(response.subject, self.akagi)
    self.assertEqual(response.attacker, self.akodo)
    self.assertEqual(1, response.vp)
    #
    # Akodo's base wound check is 7k6
    # P(25|7k6) = 0.96
    # P(30|7k6) = 0.86
    # P(35|7k6) = 0.70
    # P(40|7k6) = 0.50
    # Akodo can get 8k7 by spending 1 VP
    # P(30|8k7) = 0.96
    # P(35|8k7) = 0.87
    # P(40|8k7) = 0.72
    # P(45|8k7) = 0.55
    # If Akodo has 59 LW and is willing to take 2 SW with probability 0.7, he should spend 1 VP.
    event = LightWoundsDamageEvent(self.akagi, self.akodo, 59)
    self.akodo.take_lw(59)
    optimizer = DefaultWoundCheckOptimizer(self.akodo, event, self.context)
    response = optimizer.declare(2, 0.7)
    self.assertTrue(isinstance(response, WoundCheckDeclaredEvent))
    self.assertEqual(response.subject, self.akodo)
    self.assertEqual(response.attacker, self.akagi)
    self.assertEqual(1, response.vp)
   

class TestDefaultKeepLightWoundsOptimizer(unittest.TestCase):
  def test_two_water(self):
    #
    # test case with a character with 2 Water
    # characters like this can't keep light wounds
    character = Character('Glass Joe')
    character.take_lw(17)
    attacker = Character('Sid the Squid')
    groups = [Group('subject', character), Group('Squids', attacker)]
    context = EngineContext(groups)
    context.initialize()
    optimizer = DefaultKeepLightWoundsOptimizer(character, context)
    (should_keep, reserve_vp) = optimizer.should_keep(1, 0.6, max_vp=1)
    self.assertFalse(should_keep)
    self.assertEqual(0, reserve_vp)

  def test_four_water_keep_spend_zero(self):
    #
    # test case with a character with 4 Water
    # P(25|5k4) = 0.64
    # Should be willing to keep LW after taking 6 LW
    character = Character('Steel Josef')
    character.set_ring('water', 4)
    character.take_lw(6)
    attacker = Character('Sid the Squid')
    groups = [Group('subject', character), Group('Squids', attacker)]
    context = EngineContext(groups)
    context.initialize()
    optimizer = DefaultKeepLightWoundsOptimizer(character, context)
    (should_keep, reserve_vp) = optimizer.should_keep(1, 0.6, max_vp=1)
    self.assertTrue(should_keep)
    self.assertEqual(0, reserve_vp)

  def test_four_water_keep_spend_one(self):
    #
    # P(31|6k5) = 0.62
    # Should be willing to keep after taking 20 LW, with 1 VP
    character = Character('Steel Josef')
    character.set_ring('water', 4)
    character.take_lw(20)
    attacker = Character('Sid the Squid')
    groups = [Group('subject', character), Group('Squids', attacker)]
    context = EngineContext(groups)
    context.initialize()
    optimizer = DefaultKeepLightWoundsOptimizer(character, context)
    (should_keep, reserve_vp) = optimizer.should_keep(1, 0.6, max_vp=1)
    self.assertTrue(should_keep)
    self.assertEqual(1, reserve_vp)

class TestRiskyKeepLightWoundsOptimizer(unittest.TestCase):
  def test_six_water(self):
    #
    # test case for a character with 6 Water
    # P(33|8k7) = 0.91
    # this means that a character with 6 Water who plans to spend 1 VP
    # can face a 51 LW with a 9% chance of taking 3 SW
    # since an average damage roll is 19, you can risk this with 32 LW!
    character = Character('Bubble Man')
    character.set_ring('water', 6)
    attacker = Character('Blade')
    groups = [Group('subject', character), Group('Zombies', attacker)]
    

