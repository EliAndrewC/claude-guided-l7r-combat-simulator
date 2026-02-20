#!/usr/bin/env python3

#
# test_attack_optimizers.py
#
# Unit tests for attack_optimizers classes.
#

import logging
import sys
import unittest

from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.initiative_actions import InitiativeAction
from simulation.log import logger
from simulation.attack_optimizers import AttackOptimizer, DamageOptimizer

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestAttackOptimizer(unittest.TestCase):
  def setUp(self):
    # weak starting character
    taro = Character('Taro')
    taro.set_actions([1])
    taro.set_skill('attack', 3)
    taro.set_skill('double attack', 3)
    taro.set_skill('parry', 3)
    taro.set_ring('fire', 3)
    # midlevel character with medium skills
    jiro = Character('Jiro')
    jiro.set_actions([1])
    jiro.set_ring('fire', 4)
    jiro.set_skill('attack', 3)
    jiro.set_skill('double attack', 3)
    jiro.set_skill('parry', 4)
    # strong character with high fire
    bayushi = Character('Bayushi')
    bayushi.set_actions([1])
    bayushi.set_ring('fire', 6)
    bayushi.set_skill('attack', 4)
    bayushi.set_skill('double attack', 5)
    bayushi.set_skill('parry', 5)
    # give characters knowledge of each others' TN to hit
    taro.knowledge().observe_tn_to_hit(jiro, jiro.tn_to_hit())
    taro.knowledge().observe_tn_to_hit(bayushi, bayushi.tn_to_hit())
    jiro.knowledge().observe_tn_to_hit(taro, taro.tn_to_hit())
    jiro.knowledge().observe_tn_to_hit(bayushi, bayushi.tn_to_hit())
    bayushi.knowledge().observe_tn_to_hit(taro, taro.tn_to_hit())
    bayushi.knowledge().observe_tn_to_hit(jiro, jiro.tn_to_hit())
    # groups and context
    groups = [Group('Scorpion', bayushi), Group('Ronin', [jiro, taro])]
    context = EngineContext(groups, round=1, phase=1)
    context.initialize()
    # initiative action in phase one
    self.initiative_action = InitiativeAction([1], 1)
    # set instances
    self.taro = taro
    self.jiro = jiro
    self.bayushi = bayushi
    self.context = context    

  def test_cannot_reach_threshold(self):
    #
    # test case where the character can't reach the desired
    # probability of success, even by spending all resources
    #
    # Taro double attacking Jiro has TN 45
    # Taro's base attack roll is 6k3, spending 2 VP would reach 8k5
    # P(45|8k5) = 0.31
    # Recommendation for threshold 0.5 should be None
    optimizer = AttackOptimizer(self.taro, self.jiro, \
      'double attack', self.initiative_action, self.context)
    self.assertEqual(None, optimizer.optimize(0.5))
    #
    # Jiro double attacking Bayushi has TN 50
    # Jiro's base attack roll is 7k4, spending 2 VP would reach 9k6
    # P(50|9k6) = 0.38
    # Recommendation for threshold 0.5 should be None
    optimizer = AttackOptimizer(self.jiro, self.bayushi, \
      'double attack', self.initiative_action, self.context)
    self.assertEqual(None, optimizer.optimize(0.5))

  def test_spend_no_resources(self):
    #
    # test case where a character should spend no resources
    # because the threshold is met with no resources
    #
    # Bayushi double attacking Jiro has TN 40
    # Bayushi's base attack roll is 10k5
    # P(40|10k5) = 0.65 
    # Recommendation for threshold 0.6 should be (0, 0)
    optimizer = AttackOptimizer(self.bayushi, self.taro, \
      'double attack', self.initiative_action, self.context)
    attack = optimizer.optimize(0.6)
    self.assertEqual(0, attack.vp())
    #
    # Bayushi attacking Taro has TN 20
    # Bayushi's base attack roll is 9k5
    # P(20|9k5) = 1.0 
    # should recommend (0, 0) to attack Taro with probability of 0.9
    optimizer = AttackOptimizer(self.bayushi, self.taro, 'attack', \
      self.initiative_action, self.context)
    attack = optimizer.optimize(0.9)
    self.assertEqual(0, attack.vp())

  def test_spend_some_resources(self):
    #
    # test case where a character should only spend 1 VP
    # because the threshold is met without spending more
    #
    # Taro attacking Jiro has TN 25
    # Taro's base attack roll is 6k3, spending 1 VP would make it 7k4
    # P(25|7k4) = 0.85
    # should recommend (1, 0) at threshold 0.8
    optimizer = AttackOptimizer(self.taro, self.jiro, 'attack', \
      self.initiative_action, self.context)
    attack = optimizer.optimize(0.8)
    self.assertEqual(1, attack.vp())
    #
    # Taro attacking Bayushi has TN 30
    # Taro's base attack roll is 6k3, spending 1 VP would make it 7k4
    # P(30|7k4) = 0.64
    # should recommend (1, 0) at threshold 0.6
    optimizer = AttackOptimizer(self.taro, self.bayushi, 'attack', \
      self.initiative_action, self.context)
    attack = optimizer.optimize(0.6)
    self.assertEqual(1, attack.vp())

  def test_spend_all_resources(self):
    #
    # test case where a character can reach the threshold
    # by spending the maximum resources
    #
    # Jiro double attacking Bayushi has TN 50
    # Jiro's base attack roll is 7k4, spending 2 VP would make it 9k6
    # P(50|9k6) = 0.38
    # should recommend (2,0) at threshold 0.3 
    optimizer = AttackOptimizer(self.jiro, self.bayushi, \
      'double attack', self.initiative_action, self.context)
    attack = optimizer.optimize(0.3)
    self.assertEqual(2, attack.vp())


class TestDamageOptimizer(unittest.TestCase):
  def setUp(self):
    # weak starting character
    taro = Character('Taro')
    taro.set_actions([1])
    taro.set_skill('attack', 3)
    taro.set_skill('double attack', 3)
    taro.set_skill('parry', 3)
    taro.set_ring('fire', 3)
    # midlevel character with medium skills
    jiro = Character('Jiro')
    jiro.set_actions([1])
    jiro.set_ring('fire', 4)
    jiro.set_skill('attack', 3)
    jiro.set_skill('double attack', 3)
    jiro.set_skill('parry', 4)
    # strong character with high fire
    bayushi = Character('Bayushi')
    bayushi.set_actions([1])
    bayushi.set_ring('fire', 6)
    bayushi.set_skill('attack', 4)
    bayushi.set_skill('double attack', 5)
    bayushi.set_skill('parry', 5)
    # give characters knowledge of each others' TN to hit
    taro.knowledge().observe_tn_to_hit(jiro, jiro.tn_to_hit())
    taro.knowledge().observe_tn_to_hit(bayushi, bayushi.tn_to_hit())
    jiro.knowledge().observe_tn_to_hit(taro, taro.tn_to_hit())
    jiro.knowledge().observe_tn_to_hit(bayushi, bayushi.tn_to_hit())
    bayushi.knowledge().observe_tn_to_hit(taro, taro.tn_to_hit())
    bayushi.knowledge().observe_tn_to_hit(jiro, jiro.tn_to_hit())
    # groups and context
    groups = [Group('Scorpion', bayushi), Group('Ronin', [jiro, taro])]
    context = EngineContext(groups, round=1, phase=1)
    context.initialize()
    # initiative action in phase one
    self.initiative_action = InitiativeAction([1], 1)
    # set instances
    self.taro = taro
    self.jiro = jiro
    self.bayushi = bayushi
    self.context = context    

  def test_cannot_reach_threshold(self):
    #
    # test case where the character can't reach the desired
    # probability of success, even by spending all resources
    #
    # Taro double attacking Jiro has TN 45
    # Taro's base attack roll is 6k3, spending 2 VP would reach 8k5
    # P(45|8k5) = 0.31
    # Recommendation for threshold 0.5 should be None
    optimizer = DamageOptimizer(self.taro, self.jiro, \
      'double attack', self.initiative_action, self.context)
    self.assertEqual(None, optimizer.optimize(0.5))
    #
    # Jiro double attacking Bayushi has TN 50
    # Jiro's base attack roll is 7k4, spending 2 VP would reach 9k6
    # P(50|9k6) = 0.38
    # Recommendation for threshold 0.5 should be None
    optimizer = DamageOptimizer(self.jiro, self.bayushi, \
      'double attack', self.initiative_action, self.context)
    self.assertEqual(None, optimizer.optimize(0.5))

  def test_spend_no_resources(self):
    #
    # test cases where the character should spend no resources
    #
    # Taro attacking Jiro has TN 25
    # Taro's base damage is 7k2, so Taro needs 4 extra rolled dice to keep 3 damage dice
    # Taro would need to roll 45 to keep 3 damage dice
    # Taro's base attack roll is 6k3, spending 2 VP would reach 8k5
    # P(25|6k3) = 0.52
    # P(45|8k5) = 0.03
    # Recommendation should be (0, 0) at threshold 0.5 
    optimizer = DamageOptimizer(self.taro, self.jiro, 'attack', \
      self.initiative_action, self.context)
    attack = optimizer.optimize(0.5)
    self.assertEqual(0, attack.vp())
    #
    # Bayushi's base attack damage is 10k2, needs 4 extra rolled dice
    # to reach the max of 6 kept dice
    # Attacking a character with 2 Parry, Bayushi needs to roll 35
    # Bayushi P(35|(0,0)) = 0.94
    # So Bayushi should spend no resources to optimize damage against this character
    exploding_mook = Character('Exploding Mook')
    exploding_mook.set_skill('parry', 2)
    self.bayushi.knowledge().observe_tn_to_hit(exploding_mook, 15)
    optimizer = DamageOptimizer(self.bayushi, \
      exploding_mook, 'attack', self.initiative_action, self.context)
    attack = optimizer.optimize(0.9)
    self.assertEqual(0, attack.vp())

  def test_spend_all_resources(self):
    #
    # test case for a character who can reach 3 or more kept damage
    # dice by spending all resources
    #
    # Jiro attacking Bayushi has TN 30
    # Jiro's base damage is 8k2, so Jiro needs 3 extra rolled dice to keep 3 damage dice
    # Jiro would need to roll 45 to keep 3 damage dice
    # Jiro's base attack roll is 7k4, so spending 2 VP would reach 9k6
    # P(30|7k4) = 0.64
    # P(45|7k4) = 0.13
    # P(45|8k5) = 0.31
    # P(45|9k6) = 0.56
    # Recommendation should be (2, 0) at threshold of 0.5
    optimizer = DamageOptimizer(self.jiro, self.bayushi, 'attack', \
      self.initiative_action, self.context)
    attack = optimizer.optimize(0.5)
    self.assertEqual(2, attack.vp())

