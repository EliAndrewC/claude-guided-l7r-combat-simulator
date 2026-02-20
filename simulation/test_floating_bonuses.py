#!/usr/bin/env python3

#
# test_floating_bonuses.py
#
# Unit tests for floating_bonuses module.
#

import unittest

from simulation.floating_bonuses import AnyAttackFloatingBonus, FloatingBonus
from simulation.skills import ATTACK_SKILLS, EXTENDED_SKILLS


class TestAnyAttackFloatingBonus(unittest.TestCase):
  def test_bonus(self):
    bonus = AnyAttackFloatingBonus(4)
    self.assertEqual(4, bonus.bonus())

  def test_is_applicable(self):
    bonus = AnyAttackFloatingBonus(4)
    for skill in EXTENDED_SKILLS:
      if skill in ATTACK_SKILLS:
        self.assertTrue(bonus.is_applicable(skill))
      else:
        self.assertFalse(bonus.is_applicable(skill))


class TestFloatingBonus(unittest.TestCase):
  def test_bonus(self):
    bonus = FloatingBonus('wound check', 5)
    self.assertEqual(5, bonus.bonus())

  def test_is_applicable(self):
    bonus = FloatingBonus('wound check', 5)
    for skill in EXTENDED_SKILLS:
      if skill == 'wound check':
        self.assertTrue(bonus.is_applicable(skill))
      else:
        self.assertFalse(bonus.is_applicable(skill))

