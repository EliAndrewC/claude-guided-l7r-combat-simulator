#!/usr/bin/env python3

#
# test_actions.py
#
# Unit tests for L7R combat simulator actions module
#

import unittest

from simulation.actions import AttackAction
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.initiative_actions import InitiativeAction
from simulation.roll_provider import TestRollProvider


class TestAttackAction(unittest.TestCase):
  def setUp(self):
    attacker = Character('attacker')
    attacker.set_actions([1,])
    target = Character('target')
    groups = [Group('attacker', attacker), Group('target', target)]
    context = EngineContext(groups)
    self.attacker = attacker
    self.target = target
    self.context = context

  def test_calculate_extra_damage_dice(self):
    self.target.set_skill('parry', 5)
    # rig the attack roll to hit by 1
    # attack should get no extra damage dice
    initiative_action = InitiativeAction([1], 1)
    attack = AttackAction(self.attacker, self.target, 'attack', \
      initiative_action, self.context)
    attack.set_skill_roll(31)
    self.assertEqual(0, attack.calculate_extra_damage_dice())
    # rig the attack roll to hit by 5
    # expect one extra damage die
    attack.set_skill_roll(35)
    self.assertEqual(1, attack.calculate_extra_damage_dice())
    # rig the attack roll to hit by 9
    # expect one extra damage die
    attack.set_skill_roll(39)
    self.assertEqual(1, attack.calculate_extra_damage_dice())
    # rig the attack roll to hit by 21
    # expect four extra damage dice
    attack.set_skill_roll(51)
    self.assertEqual(4, attack.calculate_extra_damage_dice())
    
  def test_calculate_extra_damage_dice_parried(self):
    self.target.set_skill('parry', 5)
    # set up an attack with a parry attempted
    initiative_action = InitiativeAction([1], 1)
    attack = AttackAction(self.attacker, self.target, 'attack', \
      initiative_action, self.context)
    attack.set_parry_attempted()
    # rig the attack roll to hit by 1
    # attack should get no extra damage dice
    attack.set_skill_roll(31)
    self.assertEqual(0, attack.calculate_extra_damage_dice())
    # rig the attack roll to hit by 21
    # expect four extra damage dice
    attack.set_skill_roll(51)
    self.assertEqual(0, attack.calculate_extra_damage_dice())
  
  def test_hit(self):
    self.target.set_skill('parry', 5)
    # target's TN to hit should be 30
    # set attack roll to 31
    # attack should hit
    initiative_action = InitiativeAction([1], 1)
    attack = AttackAction(self.attacker, self.target, 'attack', \
      initiative_action, self.context)
    attack.set_skill_roll(31)
    self.assertTrue(attack.is_hit())

  def test_hit_parried(self):
    self.target.set_skill('parry', 5)
    # target's TN to hit should be 30
    # set attack roll to 31 so it would have been good enough to hit
    initiative_action = InitiativeAction([1], 1)
    attack = AttackAction(self.attacker, self.target, 'attack', \
      initiative_action, self.context)
    attack.set_skill_roll(31)
    self.assertTrue(attack.is_hit())
    # now set attack to be parried - it is no longer a hit
    attack.set_parried()
    self.assertFalse(attack.is_hit())

  def test_miss(self):
    self.target.set_skill('parry', 5)
    # target's TN to hit should be 30
    # set attack roll to 29
    # attack should miss
    initiative_action = InitiativeAction([1], 1)
    attack = AttackAction(self.attacker, self.target, 'attack', \
      initiative_action, self.context)
    attack.set_skill_roll(29)
    self.assertFalse(attack.is_hit())


if (__name__ == '__main__'):
  unittest.main()

