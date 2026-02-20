#!/usr/bin/env python3

#
# test_groups.py
#
# Unit tests for L7R combat simulator Group classes
#

import unittest

from simulation.character import Character
from simulation.groups import Group


class TestGroup(unittest.TestCase):
  def test_contains(self):
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    doji = Character('Doji')
    group = Group('G.R.O.S.S.', [akodo, bayushi])
    self.assertTrue(akodo in group)
    self.assertTrue(bayushi in group)
    self.assertFalse(doji in group)

  def test_equals(self):
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    doji = Character('Doji')
    hida = Character('Hida')
    group1 = Group('East', [akodo, doji])
    group2 = Group('West', [bayushi, hida])
    self.assertTrue(group1 == group1)
    self.assertFalse(group1 == group2)
    self.assertFalse(group1 is group2)
    self.assertTrue(group2 == group2)

  def test_len(self):
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    doji = Character('Doji')
    group1 = Group('Rough', [akodo])
    group2 = Group('Refined', [bayushi, doji])
    self.assertEqual(1, len(group1))
    self.assertEqual(2, len(group2))

