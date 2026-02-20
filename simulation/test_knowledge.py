#!/usr/bin/env python3

#
# test_knowledge.py
#
# Unit tests for L7R combat simulator knowledge module
#

import unittest

from simulation.character import Character
from simulation.knowledge import Knowledge, TheoreticalCharacter
from simulation.modifiers import Modifier


class TestKnowledge(unittest.TestCase):
  def test_actions_per_round(self):
    knowledge = Knowledge()
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    # akodo acts twice
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    # bayushi acts three times
    knowledge.observe_action(bayushi)
    knowledge.observe_action(bayushi)
    knowledge.observe_action(bayushi)
    # so far we know akodo acts 2 times per round,
    # bayushi acts 3 times per round
    self.assertEqual(2, knowledge.actions_per_round(akodo))
    self.assertEqual(3, knowledge.actions_per_round(bayushi))
    # akodo acts two more times
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    # now akodo acts 4 times per round
    self.assertEqual(4, knowledge.actions_per_round(akodo))
    # observe end of round
    knowledge.end_of_round()
    # assert akodo:4, bayushi:3
    self.assertEqual(4, knowledge.actions_per_round(akodo))
    self.assertEqual(3, knowledge.actions_per_round(bayushi))
    
  def test_actions_per_round_default(self):
    self.assertEqual(2, Knowledge().actions_per_round(Character()))

  def test_actions_remaining(self):
    knowledge = Knowledge()
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    # akodo acts four times
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    # bayushi acts three times
    knowledge.observe_action(bayushi)
    knowledge.observe_action(bayushi)
    knowledge.observe_action(bayushi)
    # end of round
    knowledge.end_of_round()
    # actions remaining should be akodo:4, bayushi:3
    self.assertEqual(4, knowledge.actions_remaining(akodo))
    self.assertEqual(3, knowledge.actions_remaining(bayushi))
    # akodo acts once
    knowledge.observe_action(akodo)
    # akodo should have 3 actions remaining
    self.assertEqual(3, knowledge.actions_remaining(akodo))
    # akodo acts three more times
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    # akodo should have 0 actions remaining, bayushi should have 3
    self.assertEqual(0, knowledge.actions_remaining(akodo))
    self.assertEqual(3, knowledge.actions_remaining(bayushi))

  def test_average_attack_roll(self):
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    knowledge = Knowledge()
    # observe some big attacks by Akodo
    knowledge.observe_attack_roll(akodo, 50)
    knowledge.observe_attack_roll(akodo, 60)
    # observe some small attacks by Bayushi
    knowledge.observe_attack_roll(bayushi, 20)
    knowledge.observe_attack_roll(bayushi, 30)
    # expected attack roll should be akodo:55, bayushi:65
    self.assertEqual(55, knowledge.average_attack_roll(akodo))
    self.assertEqual(25, knowledge.average_attack_roll(bayushi))

  def test_average_attack_roll_default(self):
    self.assertEqual(27, Knowledge().average_attack_roll(Character()))

  def test_average_damage_roll(self):
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    knowledge = Knowledge()
    # observe some big damage rolls by Akodo
    knowledge.observe_damage_roll(akodo, 30)
    knowledge.observe_damage_roll(akodo, 40)
    # observe some bigger damage rolls by Bayushi
    knowledge.observe_damage_roll(bayushi, 60)
    knowledge.observe_damage_roll(bayushi, 70)
    # expected damage roll should be akodo:35, bayushi:65
    self.assertEqual(35, knowledge.average_damage_roll(akodo))
    self.assertEqual(65, knowledge.average_damage_roll(bayushi))

  def test_average_damage_roll_default(self):
    self.assertEqual(18, Knowledge().average_damage_roll(Character()))

  def test_end_of_round(self):
    knowledge = Knowledge()
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    # akodo acts four times
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    knowledge.observe_action(akodo)
    # bayushi acts three times
    knowledge.observe_action(bayushi)
    knowledge.observe_action(bayushi)
    knowledge.observe_action(bayushi)
    # actions taken should be akodo:4, bayushi:3
    self.assertEqual(4, knowledge.actions_taken(akodo))
    self.assertEqual(3, knowledge.actions_taken(bayushi))
    # actions remaining should be zero
    self.assertEqual(0, knowledge.actions_remaining(akodo))
    self.assertEqual(0, knowledge.actions_remaining(bayushi))
    # end of round
    knowledge.end_of_round()
    # actions taken should be zero
    self.assertEqual(0, knowledge.actions_taken(akodo))
    self.assertEqual(0, knowledge.actions_taken(bayushi))
    # actions remaining should be akodo:4, bayushi:3
    self.assertEqual(4, knowledge.actions_remaining(akodo))
    self.assertEqual(3, knowledge.actions_remaining(bayushi))

  def test_tn_to_hit(self):
    akodo = Character('Akodo')
    bayushi = Character('Bayushi')
    knowledge = Knowledge()
    # observe TN to hit
    knowledge.observe_tn_to_hit(akodo, 15)
    knowledge.observe_tn_to_hit(bayushi, 30)
    # assert akodo:15, bayushi:30
    self.assertEqual(15, knowledge.tn_to_hit(akodo))
    self.assertEqual(30, knowledge.tn_to_hit(bayushi))

  def test_tn_to_hit_default(self):
    self.assertEqual(20, Knowledge().tn_to_hit(Character()))

  def test_wounds(self):
    akagi = Character('Akagi')
    knowledge = Knowledge()
    # Should return 0 for character's wounds with no observations
    self.assertEqual(0, knowledge.wounds(akagi))
    # observe wounds for character
    knowledge.observe_wounds(akagi, 3)
    # Should return 3 character's new wounds
    self.assertEqual(3, knowledge.wounds(akagi))


class TestTheoreticalCharacter(unittest.TestCase):
  def test_tn_to_hit(self):
    target = Character('target')
    target.set_skill('parry', 5)
    knowledge = Knowledge()
    knowledge.observe_tn_to_hit(target, 30)
    theoretical_target = TheoreticalCharacter(knowledge, target)
    self.assertEqual(30, theoretical_target.tn_to_hit())

  def test_modifiers(self):
    subject = Character('subject')
    target = Character('target')
    target.set_skill('parry', 5)
    knowledge = Knowledge()
    knowledge.observe_tn_to_hit(target, 30)
    modifier = Modifier(target, None, 'tn to hit', -5)
    knowledge.observe_modifier_added(target, modifier)
    # knowledge should give 25 for target's TN to be hit
    theoretical_target = TheoreticalCharacter(knowledge, target)
    self.assertEqual(25, theoretical_target.tn_to_hit())

if (__name__ == '__main__'):
  unittest.main()

