#!/usr/bin/env python3

#
# test_character.py
#
# Unit tests for L7R combat simulator Character classes
#

import unittest

from simulation.actions import AttackAction
from simulation.character import Character
from simulation.context import EngineContext
from simulation.events import AttackDeclaredEvent, NewPhaseEvent
from simulation.groups import Group
from simulation.roll_provider import TestRollProvider


class TestCharacter(unittest.TestCase):
  def test_base_to_hit_tn(self):
    akagi = Character('Akagi')
    shiba = Character('Shiba')
    shiba.set_skill('parry', 5)
    self.assertEqual(10, akagi.tn_to_hit())
    self.assertEqual(30, shiba.tn_to_hit())

  def test_has_action(self):
    kakita = Character('Kakita')
    kakita._actions = []
    akodo = Character('Akodo')
    akodo._actions = [2, 3, 4]
    shinjo = Character('Shinjo')
    shinjo._actions = [1, 1, 1, 1, 1]
    groups = [Group('Hurry Up and Wait', [kakita, shinjo]), Group('Lion', akodo)]
    context = EngineContext(groups, round=1, phase=1)
    # akodo has actions but they are not current actions
    self.assertFalse(akodo.has_action(context))
    # kakita has no actions at all 
    self.assertFalse(kakita.has_action(context))
    # shinjo has lots of actions
    self.assertTrue(shinjo.has_action(context))

  def test_has_interrupt_action(self):
    # set up characters
    hida = Character('Hida')
    hida._actions = [4]
    hida.set_interrupt_cost('counterattack', 1)
    kakita = Character('Kakita')
    kakita._actions = [4]
    mirumoto = Character('Mirumoto')
    mirumoto._actions = [2, 3, 4, 5, 6, 7]
    shiba = Character('Shiba')
    shiba.set_interrupt_cost('parry', 1)
    shiba._actions = [4]
    # set up context
    groups = [Group('Crab Stabs', [hida, kakita]), Group('Brass Men of the Shaolin Temple', [mirumoto, shiba])]
    context = EngineContext(groups, round=1, phase=1)
    # Hida has an interrupt action to counterattack but not to parry
    self.assertTrue(hida.has_interrupt_action('counterattack', context))
    self.assertFalse(hida.has_interrupt_action('parry', context))
    # Kakita does not have an interrupt action
    self.assertFalse(kakita.has_interrupt_action('counterattack', context))
    self.assertFalse(kakita.has_interrupt_action('parry', context))
    # Mirumoto has interrupt actions because he has many actions
    self.assertTrue(mirumoto.has_interrupt_action('counterattack', context))
    self.assertTrue(mirumoto.has_interrupt_action('parry', context))
    # Shiba has an interrupt action to parry but not to counterattack
    self.assertFalse(shiba.has_interrupt_action('counterattack', context))
    self.assertTrue(shiba.has_interrupt_action('parry', context))

  def test_interrupt_cost(self):
    # set up characters
    hida = Character('Hida')
    hida._actions = [4]
    hida.set_interrupt_cost('counterattack', 1)
    kakita = Character('Kakita')
    kakita._actions = [4]
    mirumoto = Character('Mirumoto')
    mirumoto._actions = [4]
    shiba = Character('Shiba')
    shiba.set_interrupt_cost('parry', 1)
    shiba._actions = [4]
    # set up context
    groups = [Group('Crab Stabs', [hida, kakita]), Group('Brass Men of the Shaolin Temple', [mirumoto, shiba])]
    context = EngineContext(groups, round=1, phase=1)
    # Hida's interrupt cost is 1 to counterattack, 2 to parry
    self.assertEqual(1, hida.interrupt_cost('counterattack', context))
    self.assertEqual(2, hida.interrupt_cost('parry', context))
    # Kakita's interrupt cost is 2 actions for counterattack and parry.
    self.assertEqual(2, kakita.interrupt_cost('counterattack', context))
    self.assertEqual(2, kakita.interrupt_cost('parry', context))
    # Shiba's interrupt cost is 2 actions for counterattack, 1 for parry.
    self.assertEqual(2, shiba.interrupt_cost('counterattack', context))
    self.assertEqual(1, shiba.interrupt_cost('parry', context))

  def test_roll_skill(self):
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('attack', 1)
    roll_provider.put_skill_roll('attack', 2)
    roll_provider.put_skill_roll('parry', 3)
    roll_provider.put_skill_roll('double attack', 4)
    akodo = Character('Akodo')
    akodo.set_skill('attack', 5)
    akodo.set_skill('parry', 5)
    akodo.set_skill('double attack', 5)
    akodo.set_roll_provider(roll_provider)
    target = Character('target')
    self.assertEqual(1, akodo.roll_skill(target, 'attack'))
    self.assertEqual(3, akodo.roll_skill(target, 'parry'))
    self.assertEqual(4, akodo.roll_skill(target, 'double attack'))
    self.assertEqual(2, akodo.roll_skill(target, 'attack'))

  def test_speculative_wound_check(self):
    '''
    A "speculative" wound check is one where the LW are specified, instead of defaulting to the character's current LW total.
    '''
    akodo = Character('Akodo')
    # wound check exceeds LW: 0 SW
    self.assertEqual(0, akodo.wound_check(10, 9))
    # wound check misses by less than 10: 1 SW
    self.assertEqual(1, akodo.wound_check(5, 10))
    # wound check misses by 10: 2 SW
    self.assertEqual(2, akodo.wound_check(10, 20))
    # wound check misses by 19: 2 SW
    self.assertEqual(2, akodo.wound_check(10, 29))
    # wound check misses by 20: 3 SW
    self.assertEqual(3, akodo.wound_check(10, 30))

  def test_vp(self):
    character = Character()
    # character with all 2s has 2 VP to spend
    self.assertEqual(2, character.max_vp())
    self.assertEqual(2, character.vp())
    # raise some rings but leave a ring at 2
    character.set_ring('air', 2)
    character.set_ring('earth', 3)
    character.set_ring('fire', 4)
    character.set_ring('water', 3)
    character.set_ring('void', 3)
    # character with high rings but one ring at 2 still has 2 VP to spend
    self.assertEqual(2, character.max_vp())
    self.assertEqual(2, character.vp())
    # raise lowest ring to 3
    character.set_ring('air', 3)
    # character should have 3 VP
    self.assertEqual(3, character.max_vp())
    self.assertEqual(3, character.vp())
    # give the character 3 worldliness
    character.set_skill('worldliness', 3)
    # character should have 6 VP
    self.assertEqual(6, character.max_vp())
    self.assertEqual(6, character.vp())
    # spend some vp
    character.spend_vp(2)
    # character's max should be unchanged, but available should be lower
    self.assertEqual(6, character.max_vp())
    self.assertEqual(4, character.vp())
    # spend down to zero
    character.spend_vp(4)
    self.assertEqual(6, character.max_vp())
    self.assertEqual(0, character.vp())
    # try to spend more, it should crash
    with self.assertRaises(ValueError):
      character.spend_vp(1)

  def test_wound_check(self):
    akodo = Character('Akodo')
    akodo.take_lw(30)
    # wound check exceeds LW: 0 SW
    self.assertEqual(0, akodo.wound_check(31))
    # wound check misses by less than 10: 1 SW
    self.assertEqual(1, akodo.wound_check(25))
    # wound check misses by 10: 2 SW
    self.assertEqual(2, akodo.wound_check(20))
    # wound check misses by 19: 2 SW
    self.assertEqual(2, akodo.wound_check(19))
    # wound check misses by 20: 3 SW
    self.assertEqual(3, akodo.wound_check(10))


if (__name__ == '__main__'):
  unittest.main()

