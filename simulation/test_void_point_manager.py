#!/usr/bin/env python3

#
# test_void_point_manager.py
#
# Unit tests for void_point_manager class.
#

import unittest

from simulation.character import Character
from simulation.void_point_manager import VoidPointManager

class TestVoidPointManager(unittest.TestCase):
  def setUp(self):
    # create character with 3 VP
    character = Character()
    character.set_ring('air', 3)
    character.set_ring('earth', 3)
    character.set_ring('fire', 3)
    character.set_ring('water', 3)
    character.set_ring('void', 3)
    self.character = character
    self.assertEqual(3, self.character.vp())

  def test_cancel(self):
    manager = VoidPointManager(self.character)
    manager.reserve('attack', 1)
    manager.reserve('wound check', 2)
    # reservations should be in effect
    self.assertEqual(1, manager.reserved('attack'))
    self.assertEqual(2, manager.reserved('wound check'))
    self.assertEqual(0, manager.vp('parry'))
    # cancel wound check reservation
    manager.cancel('wound check')
    self.assertEqual(1, manager.reserved('attack'))
    self.assertEqual(0, manager.reserved('wound check'))
    self.assertEqual(2, manager.vp('parry'))
    self.assertEqual(2, manager.vp('wound check'))

  def test_clear(self):
    manager = VoidPointManager(self.character)
    manager.reserve('wound check', 1)
    manager.clear()
    # after clearing reservations, should be nothing reserved for wound checks and 3 avaiable for attack
    self.assertEqual(0, manager.reserved('wound check'))
    self.assertEqual(3, manager.vp('attack'))

  def test_reserve(self):
    manager = VoidPointManager(self.character)
    manager.reserve('wound check', 2)
    self.assertEqual(2, manager.reserved('wound check'))
    self.assertEqual(0, manager.reserved('attack'))
 
  def test_vp(self):
    manager = VoidPointManager(self.character)
    self.assertEqual(3, manager.vp('attack'))
    manager.reserve('wound check', 3)
    self.assertEqual(0, manager.vp('parry'))
    self.assertEqual(3, manager.vp('wound check'))

