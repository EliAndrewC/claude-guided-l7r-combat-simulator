#!/usr/bin/env python3

#
# test_skills.py
#
# Unit tests for skills
#

import unittest

from simulation.skills import AdvancedSkill, BasicSkill, Skill

class TestGetSkill(unittest.TestCase):
  def test_advanced_skill(self):
    skill = Skill('attack').get() 
    self.assertTrue(isinstance(skill, AdvancedSkill))

  def test_basic_skill(self):
    skill = Skill('sincerity').get()
    self.assertTrue(isinstance(skill, BasicSkill))

  def test_invalid_skill(self):
    with self.assertRaises(ValueError):
      skill = Skill('tropical fish appreciation').get()

 
class TestAdvancedSkill(unittest.TestCase):
  def test_cost_from_zero(self):
    skill = Skill('attack').get()
    self.assertEqual(4, skill.cost(1))
    self.assertEqual(8, skill.cost(2))
    self.assertEqual(14, skill.cost(3))
    self.assertEqual(22, skill.cost(4))
    self.assertEqual(32, skill.cost(5))

  def test_cost_from_one(self):
    skill = Skill('attack').get()
    self.assertEqual(0, skill.cost(1, 1))
    self.assertEqual(4, skill.cost(2, 1))
    self.assertEqual(10, skill.cost(3, 1))
    self.assertEqual(18, skill.cost(4, 1))
    self.assertEqual(28, skill.cost(5, 1))

  def test_cost_from_previous_rank(self):
    skill = Skill('attack').get()
    self.assertEqual(4, skill.cost(1))
    self.assertEqual(4, skill.cost(1, 0))
    self.assertEqual(4, skill.cost(2, 1))
    self.assertEqual(6, skill.cost(3, 2))
    self.assertEqual(8, skill.cost(4, 3))
    self.assertEqual(10, skill.cost(5, 4))


class TestBasicSkill(unittest.TestCase):
  def test_cost_from_zero(self):
    skill = Skill('sincerity').get()
    self.assertEqual(2, skill.cost(1))
    self.assertEqual(4, skill.cost(2))
    self.assertEqual(7, skill.cost(3))
    self.assertEqual(10, skill.cost(4))
    self.assertEqual(13, skill.cost(5))

  def test_cost_from_one(self):
    skill = Skill('sincerity').get()
    self.assertEqual(0, skill.cost(1, 1))
    self.assertEqual(2, skill.cost(2, 1))
    self.assertEqual(5, skill.cost(3, 1))
    self.assertEqual(8, skill.cost(4, 1))
    self.assertEqual(11, skill.cost(5, 1))

  def test_cost_from_previous_rank(self):
    skill = Skill('sincerity').get()
    self.assertEqual(2, skill.cost(1))
    self.assertEqual(2, skill.cost(1, 0))
    self.assertEqual(2, skill.cost(2, 1))
    self.assertEqual(3, skill.cost(3, 2))
    self.assertEqual(3, skill.cost(4, 3))
    self.assertEqual(3, skill.cost(5, 4))

