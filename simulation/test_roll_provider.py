#!/usr/bin/env python3

#
# test_roll_provider.py
#
# Unit tests for L7R combat simulator roll_provider module
#

import unittest

from simulation.roll_provider import TestRollProvider


class TestTestRollProvider(unittest.TestCase):
  def test_fifo(self):
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('attack', 37)
    roll_provider.put_skill_roll('attack', 9001)
    # first Attack roll should be 37
    self.assertEqual(37, roll_provider.get_skill_roll('attack', 6, 3))
    # second Attack roll should be 9001
    self.assertEqual(9001, roll_provider.get_skill_roll('attack', 10, 10))

  def test_get_initiative_roll(self):
    roll_provider = TestRollProvider()
    roll_provider.put_initiative_roll([1, 2, 3]) 
    roll_provider.put_initiative_roll([1, 5, 10])
    self.assertEqual([1, 2, 3], roll_provider.get_initiative_roll(4, 3))
    self.assertEqual([1, 5, 10], roll_provider.get_initiative_roll(7, 5))

  def test_get_skill_roll(self):
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('attack', 37)
    roll_provider.put_skill_roll('parry', 59009)
    # should get different results for Attack and Parry
    self.assertEqual(37, roll_provider.get_skill_roll('attack', 6, 3))
    self.assertEqual(59009, roll_provider.get_skill_roll('parry', 10, 10))

  def test_get_wound_check_roll(self):
    roll_provider = TestRollProvider()
    roll_provider.put_wound_check_roll(5)
    roll_provider.put_wound_check_roll(50)
    self.assertEqual(5, roll_provider.get_wound_check_roll(4, 3))
    self.assertEqual(50, roll_provider.get_wound_check_roll(6, 5))

  def test_no_roll_queued(self):
    roll_provider = TestRollProvider()
    with self.assertRaises(KeyError):
      roll_provider.get_skill_roll('attack', 6, 3)

  def test_pop_observed_params(self):
    roll_provider = TestRollProvider()
    roll_provider.put_damage_roll(9001)
    roll_provider.put_initiative_roll([1, 2, 3])
    roll_provider.put_skill_roll('attack', 50)
    roll_provider.put_wound_check_roll(30)
    roll_provider.get_damage_roll(4, 1)
    self.assertEqual((4, 1), roll_provider.pop_observed_params('damage'))
    roll_provider.get_initiative_roll(4, 3)
    self.assertEqual((4, 3), roll_provider.pop_observed_params('initiative'))
    

if (__name__ == '__main__'):
  unittest.main()

