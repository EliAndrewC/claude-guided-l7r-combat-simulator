#!/usr/bin/env python3

#
# test_professions.py
#
# Unit tests for L7R combat simulator professions module
#

import logging
import sys
import unittest

from simulation import professions
from simulation.actions import AttackAction
from simulation.character import Character
from simulation.context import EngineContext
from simulation.events import AddModifierEvent, AttackSucceededEvent, LightWoundsDamageEvent
from simulation.groups import Group
from simulation.initiative_actions import InitiativeAction
from simulation.log import logger
from simulation.roll import TestDice
from simulation.roll_provider import TestRollProvider
from simulation.weapons import KATANA, TANTO, UNARMED, YARI

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestWaveManAttackAction(unittest.TestCase):
  '''
  Unit tests for the WaveManAttackAction class, which implements
  several Wave Man profession abilities.
  '''
  def setUp(self):
    attacker = Character('Wave Man')
    attacker.set_ring('fire', 3)
    attacker.set_skill('attack', 3)
    attacker.set_profession(professions.Profession())
    # create target with TN to be hit 25
    target = Character('target')
    target.set_skill('parry', 4)
    # give attacker knowledge of target's TN to be hit
    attacker.knowledge().observe_tn_to_hit(target, target.tn_to_hit())
    # context
    groups = [Group('Wave Man', attacker), Group('Generic Dudes', target)]
    context = EngineContext(groups)
    # set instances
    self.attacker = attacker
    self.target = target
    self.context = context
    self.initiative_action = InitiativeAction([1], 1)

  def test_miss_no_abilities(self):
    # rig attack roll to miss
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('attack', 24)
    self.attacker.set_roll_provider(roll_provider)
    # set up attack
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.roll_skill()
    # attack should get expected roll and miss
    self.assertEqual(24, attack.skill_roll())
    self.assertFalse(attack.is_hit())
    self.assertFalse(attack.used_missed_attack_bonus())

  def test_failed_parry_damage_bonus_level_one(self):
    self.attacker.profession().take_ability(professions.FAILED_PARRY_DAMAGE_BONUS)
    # set up attack with failed parry attempt
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_parry_attempted()
    # attack that barely hit should get no extra damage dice
    attack.set_skill_roll(25)
    self.assertEqual(0, attack.calculate_extra_damage_dice())
    # attack that hit by 5 should get one extra die
    attack.set_skill_roll(30)
    self.assertEqual(1, attack.calculate_extra_damage_dice())
    # attack that hit by 15 should only get two extra rolled dice
    attack.set_skill_roll(40)
    self.assertEqual(2, attack.calculate_extra_damage_dice())

  def test_failed_parry_damage_bonus_level_two(self):
    self.attacker.profession().take_ability(professions.FAILED_PARRY_DAMAGE_BONUS)
    self.attacker.profession().take_ability(professions.FAILED_PARRY_DAMAGE_BONUS)
    # set up attack with failed parry attempt
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_parry_attempted()
    # attack that barely hit should get no extra damage dice
    attack.set_skill_roll(25)
    self.assertEqual(0, attack.calculate_extra_damage_dice())
    # attack that hit by 5 should get one extra die
    attack.set_skill_roll(30)
    self.assertEqual(1, attack.calculate_extra_damage_dice())
    # attack that hit by 15 should only get three extra rolled dice
    attack.set_skill_roll(40)
    self.assertEqual(3, attack.calculate_extra_damage_dice())
    # attack that hit by 25 should only get four extra rolled dice
    attack.set_skill_roll(45)
    self.assertEqual(4, attack.calculate_extra_damage_dice())

  def test_missed_attack_bonus_level_one_hit_with_ability(self):
    self.attacker.profession().take_ability(professions.MISSED_ATTACK_BONUS)
    # rig attack roll to miss by five
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('attack', 20)
    self.attacker.set_roll_provider(roll_provider)
    # set up attack
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.roll_skill()
    # attack roll should get a bonus of +5
    self.assertEqual(25, attack.skill_roll())
    self.assertTrue(attack.is_hit())
    self.assertTrue(attack.used_missed_attack_bonus())
    self.assertEqual(0, attack.parry_tn())
    
  def test_missed_attack_bonus_level_one_miss_with_ability(self):
    self.attacker.profession().take_ability(professions.MISSED_ATTACK_BONUS)
    # rig attack roll to miss by six
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('attack', 19)
    self.attacker.set_roll_provider(roll_provider)
    # set up attack
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.roll_skill()
    # attack roll should get a bonus of +5 but still miss
    self.assertEqual(24, attack.skill_roll())
    self.assertFalse(attack.is_hit())
    self.assertTrue(attack.used_missed_attack_bonus())
    self.assertEqual(0, attack.parry_tn())

  def test_missed_attack_bonus_level_two_hit_with_ability(self):
    self.attacker.profession().take_ability(professions.MISSED_ATTACK_BONUS)
    self.attacker.profession().take_ability(professions.MISSED_ATTACK_BONUS)
    # rig attack roll to miss by ten
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('attack', 15)
    self.attacker.set_roll_provider(roll_provider)
    # set up attack
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.roll_skill()
    # attack roll should get a bonus of +10
    self.assertEqual(25, attack.skill_roll())
    self.assertTrue(attack.is_hit())
    self.assertTrue(attack.used_missed_attack_bonus())
    self.assertEqual(0, attack.parry_tn())
    
  def test_missed_attack_bonus_level_two_miss_with_ability(self):
    self.attacker.profession().take_ability(professions.MISSED_ATTACK_BONUS)
    self.attacker.profession().take_ability(professions.MISSED_ATTACK_BONUS)
    # rig attack roll to miss by eleven
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('attack', 14)
    self.attacker.set_roll_provider(roll_provider)
    # set up attack
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.roll_skill()
    # attack roll should get a bonus of +5 but still miss
    self.assertEqual(24, attack.skill_roll())
    self.assertFalse(attack.is_hit())
    self.assertTrue(attack.used_missed_attack_bonus())
    self.assertEqual(0, attack.parry_tn())

  def test_parry_penalty_level_one(self):
    self.attacker.profession().take_ability(professions.PARRY_PENALTY)
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(25)
    # parry TN should be +5
    self.assertEqual(25, attack.skill_roll())
    self.assertTrue(attack.is_hit())
    self.assertEqual(30, attack.parry_tn())

  def test_parry_penalty_level_two(self):
    self.attacker.profession().take_ability(professions.PARRY_PENALTY)
    self.attacker.profession().take_ability(professions.PARRY_PENALTY)
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(25)
    # parry TN should be +10
    self.assertEqual(25, attack.skill_roll())
    self.assertTrue(attack.is_hit())
    self.assertEqual(35, attack.parry_tn())

  def test_parry_penalty_with_missed_attack_bonus(self):
    self.attacker.profession().take_ability(professions.MISSED_ATTACK_BONUS)
    self.attacker.profession().take_ability(professions.PARRY_PENALTY)
    # rig attack roll to miss by five
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('attack', 20)
    self.attacker.set_roll_provider(roll_provider)
    # set up attack
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.roll_skill()
    # attack roll should get a bonus of +5
    self.assertEqual(25, attack.skill_roll())
    self.assertTrue(attack.is_hit())
    self.assertTrue(attack.used_missed_attack_bonus())
    # parry tn should be zero instead of 30
    self.assertEqual(0, attack.parry_tn())

  def test_rolled_damage_bonus_level_one(self):
    self.attacker.profession().take_ability(professions.ROLLED_DAMAGE_BONUS)
    # first try a roll with a remainder divided by five
    roll_provider = TestRollProvider()
    roll_provider.put_damage_roll(16)
    self.attacker.set_roll_provider(roll_provider)
    # set up attack and make it a hit
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(25)
    attack.roll_damage()
    # damage should be increased to nearest multiple of five
    self.assertEqual(20, attack.damage_roll())
    #
    # now try a multiple of five
    roll_provider.put_damage_roll(15)
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(25)
    attack.roll_damage()
    # damage should be increased by three
    self.assertEqual(18, attack.damage_roll())

  def test_damage_bonus_level_two(self):
    self.attacker.profession().take_ability(professions.ROLLED_DAMAGE_BONUS)
    self.attacker.profession().take_ability(professions.ROLLED_DAMAGE_BONUS)
    # first try a roll with a remainder divided by five
    roll_provider = TestRollProvider()
    roll_provider.put_damage_roll(16)
    self.attacker.set_roll_provider(roll_provider)
    # set up attack and make it a hit
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(25)
    attack.roll_damage()
    # damage should be increased by +5 and then +3
    self.assertEqual(23, attack.damage_roll())
    #
    # now try a multiple of five
    roll_provider.put_damage_roll(15)
    attack = professions.WaveManAttackAction(self.attacker, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(25)
    attack.roll_damage()
    # damage should be increased by +3 and then bumped to nearest five
    self.assertEqual(20, attack.damage_roll())


class TestWaveManAttackSucceededListener(unittest.TestCase):
  def setUp(self):
    attacker = Character('attacker')
    attacker.set_ring('fire', 5)
    attacker.set_skill('attack', 4)
    wave_man = Character('Wave Man')
    wave_man.set_skill('parry', 4)
    wave_man.set_profession(professions.Profession())
    wave_man.set_listener('attack_succeeded', professions.WAVE_MAN_ATTACK_SUCCEEDED_LISTENER)
    # context
    groups = [Group('Wave Man', wave_man), Group('Internationals', attacker)]
    context = EngineContext(groups)
    # set instances
    self.attacker = attacker
    self.wave_man = wave_man
    self.context = context
    self.initiative_action = InitiativeAction([1], 1)

  def test_level_zero(self):
    # attack succeeded event
    attack = AttackAction(self.attacker, self.wave_man, 'attack', \
      self.initiative_action, self.context)
    attack.set_skill_roll(35)
    attack.set_damage_roll(27)
    attack_succeeded = AttackSucceededEvent(attack)
    # play attack succeeded event on Wave Man
    responses = [response for response in self.wave_man.event(attack_succeeded, self.context)]
    self.assertEqual(0, len(responses))

  def test_level_one(self):
    self.wave_man.profession().take_ability(professions.DAMAGE_PENALTY)
    # attack succeeded event
    attack = AttackAction(self.attacker, self.wave_man, 'attack', \
      self.initiative_action, self.context)
    attack.set_skill_roll(35)
    attack.set_damage_roll(27)
    attack_succeeded = AttackSucceededEvent(attack)
    # play attack succeeded event on Wave Man
    responses = [response for response in self.wave_man.event(attack_succeeded, self.context)]
    # response should be a -5 modifier on damage from the attacker on the wave man
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, AddModifierEvent))
    self.assertEqual(self.attacker, response.subject)
    self.assertEqual(self.attacker, response.modifier.subject())
    self.assertEqual(self.wave_man, response.modifier.target())
    self.assertTrue('damage' in response.modifier.skills())
    self.assertEqual(-5, response.modifier.adjustment())

  def test_level_two(self):
    self.wave_man.profession().take_ability(professions.DAMAGE_PENALTY)
    self.wave_man.profession().take_ability(professions.DAMAGE_PENALTY)
    # attack succeeded event
    attack = AttackAction(self.attacker, self.wave_man, 'attack', \
      self.initiative_action, self.context)
    attack.set_skill_roll(35)
    attack.set_damage_roll(27)
    attack_succeeded = AttackSucceededEvent(attack)
    # play attack succeeded event on Wave Man
    responses = [response for response in self.wave_man.event(attack_succeeded, self.context)]
    # response should be a -5 modifier on damage from the attacker on the wave man
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, AddModifierEvent))
    self.assertEqual(self.attacker, response.subject)
    self.assertEqual(self.attacker, response.modifier.subject())
    self.assertEqual(self.wave_man, response.modifier.target())
    self.assertTrue('damage' in response.modifier.skills())
    self.assertEqual(-10, response.modifier.adjustment())


class TestWaveManRoll(unittest.TestCase):
  '''
  Unit tests for the WaveManRoll class, which implements the
  "crippled bonus" ability to reroll some tens.
  '''
  def test_normal_roll(self):
    # test case for WaveManRoll that acts like a normal roll
    test_dice = TestDice()
    test_dice.extend([1, 1, 3, 5, 7, 9])
    roll = professions.WaveManRoll(6, 3, die_provider=test_dice)
    self.assertEqual(21, roll.roll())

  def test_no_tens_reroll_one(self):
    # test case for WaveManRoll that could reroll one die, but got no tens 
    test_dice = TestDice()
    test_dice.extend([1, 1, 3, 5, 7, 9, 1, 2])
    roll = professions.WaveManRoll(6, 3, always_explode=1, die_provider=test_dice, explode=False)
    self.assertEqual(21, roll.roll())

  def test_no_tens_reroll_two(self):
    # test case for WaveManRoll that could reroll two dice, but got no tens 
    test_dice = TestDice()
    test_dice.extend([1, 1, 3, 5, 7, 9, 1, 2])
    roll = professions.WaveManRoll(6, 3, always_explode=2, die_provider=test_dice, explode=False)
    self.assertEqual(21, roll.roll())

  def test_tens_no_reroll(self):
    # test case for WaveManRoll that got tens but cannot reroll them
    test_dice = TestDice()
    test_dice.extend([1, 3, 5, 7, 10, 10, 1, 2])
    roll = professions.WaveManRoll(6, 3, die_provider=test_dice, explode=False)
    self.assertEqual(27, roll.roll())

  def test_tens_reroll_one(self):
    # test case for WaveManRoll that got tens and can reroll one of them
    test_dice = TestDice()
    test_dice.extend([1, 3, 5, 7, 10, 10, 1, 2])
    roll = professions.WaveManRoll(6, 3, always_explode=1, die_provider=test_dice, explode=False)
    self.assertEqual(28, roll.roll())

  def test_tens_reroll_two(self):
    # test case for WaveManRoll that got tens and can reroll two of them
    test_dice = TestDice()
    test_dice.extend([1, 3, 5, 7, 10, 10, 1, 2])
    roll = professions.WaveManRoll(6, 3, always_explode=2, die_provider=test_dice, explode=False)
    self.assertEqual(30, roll.roll())

  def test_tens_continue_exploding(self):
    # test case for WaveManRoll with tens exploding to tens
    test_dice = TestDice()
    test_dice.extend([1, 1, 3, 5, 7, 10, 10, 1, 2])
    roll = professions.WaveManRoll(6, 3, always_explode=2, die_provider=test_dice, explode=False)
    self.assertEqual(33, roll.roll())


class TestWaveManRollParameterProvider(unittest.TestCase):
  '''
  Unit tests for the WaveManRollParameterProvider, which implements
  the "weapon damage bonus" ability with its get_damage_roll_params
  function.
  '''
  def setUp(self):
    self.target = Character('target')

  def test_katana(self):
    # test case for a 4k2 weapon, which receives no bonus
    character = Character(name='Wave Man')
    character.set_weapon(KATANA)
    character.set_profession(professions.Profession())
    provider = professions.WaveManRollParameterProvider()
    character.set_roll_parameter_provider(provider)
    # ability level zero
    self.assertEqual((6,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((6,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((9,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((9,2,0), character.get_damage_roll_params(self.target, 'attack', 3))
    # ability level two
    character.profession().take_ability(professions.WEAPON_DAMAGE_BONUS)
    character.profession().take_ability(professions.WEAPON_DAMAGE_BONUS)
    self.assertEqual((6,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((6,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((9,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((9,2,0), character.get_damage_roll_params(self.target, 'attack', 3))

  def test_tanto(self):
    # test case for a 2k2 weapon, which should receive up to two extra dice
    character = Character(name='Wave Man')
    character.set_weapon(TANTO)
    character.set_profession(professions.Profession())
    provider = professions.WaveManRollParameterProvider()
    character.set_roll_parameter_provider(provider)
    # ability level zero
    self.assertEqual((4,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((4,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((7,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((7,2,0), character.get_damage_roll_params(self.target, 'attack', 3))
    # ability level one
    character.profession().take_ability(professions.WEAPON_DAMAGE_BONUS)
    self.assertEqual((5,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((5,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((8,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((8,2,0), character.get_damage_roll_params(self.target, 'attack', 3))
    # ability level two
    character.profession().take_ability(professions.WEAPON_DAMAGE_BONUS)
    self.assertEqual((6,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((6,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((9,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((9,2,0), character.get_damage_roll_params(self.target, 'attack', 3))

  def test_unarmed(self):
    # test case for a 0k2 weapon, which should receive up to two extra dice
    character = Character(name='Wave Man')
    character.set_weapon(UNARMED)
    character.set_profession(professions.Profession())
    provider = professions.WaveManRollParameterProvider()
    character.set_roll_parameter_provider(provider)
    # ability level zero
    self.assertEqual((2,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((2,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((5,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((5,2,0), character.get_damage_roll_params(self.target, 'attack', 3))
    # ability level one
    character.profession().take_ability(professions.WEAPON_DAMAGE_BONUS)
    self.assertEqual((3,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((3,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((6,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((6,2,0), character.get_damage_roll_params(self.target, 'attack', 3))
    # ability level two
    character.profession().take_ability(professions.WEAPON_DAMAGE_BONUS)
    self.assertEqual((4,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((4,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((7,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((7,2,0), character.get_damage_roll_params(self.target, 'attack', 3))

  def test_yari(self):
    # test case for a 3k2 weapon, which should receive up to one extra die
    character = Character(name='Wave Man')
    character.set_weapon(YARI)
    character.set_profession(professions.Profession())
    provider = professions.WaveManRollParameterProvider()
    character.set_roll_parameter_provider(provider)
    # ability level zero
    self.assertEqual((5,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((5,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((8,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((8,2,0), character.get_damage_roll_params(self.target, 'attack', 3))
    # ability level one
    character.profession().take_ability(professions.WEAPON_DAMAGE_BONUS)
    self.assertEqual((6,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((6,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((9,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((9,2,0), character.get_damage_roll_params(self.target, 'attack', 3))
    # ability level two (no additional bonus)
    character.profession().take_ability(professions.WEAPON_DAMAGE_BONUS)
    self.assertEqual((6,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 0))
    self.assertEqual((6,2,0), character.get_damage_roll_params(self.target, 'attack', 0))
    self.assertEqual((9,2,0), provider.get_damage_roll_params(character, self.target, 'attack', 3))
    self.assertEqual((9,2,0), character.get_damage_roll_params(self.target, 'attack', 3))


class TestWaveManRollProvider(unittest.TestCase):
  '''
  Unit tests for the WaveManRollProvider class, which
  implements the "crippled_bonus" ability to reroll some tens.
  '''
  def setUp(self):
    # set up a crippled character who rolls 6k3 on attack
    character = Character('Wave Man')
    character.set_ring('fire', 3)
    character.set_skill('attack', 3)
    character.take_sw(2)
    character.set_profession(professions.Profession())
    self.character = character
    # set up a target
    self.target = Character('target')
    
  def test_ability_level_zero(self):
    self.assertTrue(self.character.crippled())
    test_dice = TestDice()
    provider = professions.WaveManRollProvider(self.character.profession(), die_provider=test_dice)
    self.character.set_roll_provider(provider)
    # test a roll with no tens directly through the roll provider
    test_dice.extend([1, 1, 3, 5, 7, 9])
    roll = provider.get_skill_roll('attack', 6, 3, explode=False)
    self.assertEqual(21, roll)
    # test a roll with no tens through the character
    test_dice.clear()
    test_dice.extend([1, 1, 3, 5, 7, 9])
    roll = self.character.roll_skill(self.target, 'attack')
    self.assertEqual(21, roll)
    # test a roll with tens directly through the roll provider
    test_dice.clear()
    test_dice.extend([1, 3, 5, 7, 10, 10, 1, 2])
    roll = provider.get_skill_roll('attack', 6, 3, explode=False)
    self.assertEqual(27, roll)
    # test a roll with tens through the character
    test_dice.clear()
    test_dice.extend([1, 3, 5, 7, 10, 10, 1, 2])
    roll = self.character.roll_skill(self.target, 'attack')
    self.assertEqual(27, roll)

  def test_ability_level_one(self):
    self.assertTrue(self.character.crippled())
    self.character.profession().take_ability(professions.CRIPPLED_BONUS)
    test_dice = TestDice()
    provider = professions.WaveManRollProvider(self.character.profession(), die_provider=test_dice)
    self.character.set_roll_provider(provider)
    # test a roll with no tens directly through the roll provider
    test_dice.extend([1, 1, 3, 5, 7, 9])
    roll = provider.get_skill_roll('attack', 6, 3, explode=False)
    self.assertEqual(21, roll)
    # test a roll with no tens through the character
    test_dice.clear()
    test_dice.extend([1, 1, 3, 5, 7, 9])
    roll = self.character.roll_skill(self.target, 'attack')
    self.assertEqual(21, roll)
    # test a roll with tens directly through the roll provider
    test_dice.clear()
    test_dice.extend([1, 3, 5, 7, 10, 10, 1, 2])
    roll = provider.get_skill_roll('attack', 6, 3, explode=False)
    self.assertEqual(28, roll)
    # test a roll with tens through the character
    test_dice.clear()
    test_dice.extend([1, 3, 5, 7, 10, 10, 1, 2])
    roll = self.character.roll_skill(self.target, 'attack')
    self.assertEqual(28, roll)

  def test_ability_level_two(self):
    self.assertTrue(self.character.crippled())
    self.character.profession().take_ability(professions.CRIPPLED_BONUS)
    self.character.profession().take_ability(professions.CRIPPLED_BONUS)
    test_dice = TestDice()
    provider = professions.WaveManRollProvider(self.character.profession(), die_provider=test_dice)
    self.character.set_roll_provider(provider)
    # test a roll with no tens directly through the roll provider
    test_dice.extend([1, 1, 3, 5, 7, 9])
    roll = provider.get_skill_roll('attack', 6, 3, explode=False)
    self.assertEqual(21, roll)
    # test a roll with no tens through the character
    test_dice.clear()
    test_dice.extend([1, 1, 3, 5, 7, 9])
    roll = self.character.roll_skill(self.target, 'attack')
    self.assertEqual(21, roll)
    # test a roll with tens directly through the roll provider
    test_dice.clear()
    test_dice.extend([1, 3, 5, 7, 10, 10, 1, 2])
    roll = provider.get_skill_roll('attack', 6, 3, explode=False)
    self.assertEqual(30, roll)
    # test a roll with tens through the character
    test_dice.clear()
    test_dice.extend([1, 3, 5, 7, 10, 10, 1, 2])
    roll = self.character.roll_skill(self.target, 'attack')
    self.assertEqual(30, roll)
    # test a roll with three tens, only two should reroll
    self.character.set_ring('fire', 4)
    self.character.set_skill('attack', 4)
    test_dice.clear()
    test_dice.extend([1, 1, 3, 5, 7, 10, 10, 10, 1, 2, 3, 4])
    roll = provider.get_skill_roll('attack', 8, 4, explode=False)
    self.assertEqual(40, roll)
    test_dice.clear()
    test_dice.extend([1, 1, 3, 5, 7, 10, 10, 10, 1, 2, 3, 4])
    roll = self.character.roll_skill(self.target, 'attack')
    self.assertEqual(40, roll)


class TestWaveManTakeAttackActionEvent(unittest.TestCase):
  def setUp(self):
    character = Character('Wave Man')
    character.set_profession(professions.Profession())
    self.character = character
    # rig the character's damage roll
    roll_provider = TestRollProvider()
    roll_provider.put_skill_roll('damage', 17)
    self.character.set_roll_provider(roll_provider)
    # set up a target
    self.target = Character('target')
    # set up context
    groups = [Group('Wave Man', character), Group('target', self.target)]
    self.context = EngineContext(groups)
    # initiative action
    self.initiative_action = InitiativeAction([1], 1)
    
  def test_level_zero(self):
    # set up an attack
    attack = professions.WaveManAttackAction(self.character, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(30)
    # set up take attack action event
    take_attack_event = professions.WaveManTakeAttackActionEvent(attack)
    damage_event = take_attack_event._roll_damage()
    self.assertEqual(17, damage_event.damage)
    self.assertEqual(17, damage_event.wound_check_tn)

  def test_level_one(self):
    self.character.profession().take_ability(professions.WOUND_CHECK_PENALTY)
    # set up an attack
    attack = professions.WaveManAttackAction(self.character, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(30)
    # set up take attack action event
    take_attack_event = professions.WaveManTakeAttackActionEvent(attack)
    damage_event = take_attack_event._roll_damage()
    self.assertEqual(17, damage_event.damage)
    self.assertEqual(22, damage_event.wound_check_tn)

  def test_level_two(self):
    self.character.profession().take_ability(professions.WOUND_CHECK_PENALTY)
    self.character.profession().take_ability(professions.WOUND_CHECK_PENALTY)
    # set up an attack
    attack = professions.WaveManAttackAction(self.character, \
      self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(30)
    # set up take attack action event
    take_attack_event = professions.WaveManTakeAttackActionEvent(attack)
    damage_event = take_attack_event._roll_damage()
    self.assertEqual(17, damage_event.damage)
    self.assertEqual(27, damage_event.wound_check_tn)

