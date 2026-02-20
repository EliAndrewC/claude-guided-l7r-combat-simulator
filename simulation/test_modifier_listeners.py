#!/usr/bin/env python3

#
# test_modifier_listeners.py
#
# Unit tests for modifier_listeners module.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.initiative_actions import InitiativeAction
from simulation.listeners import Listener
from simulation.log import logger
from simulation.modifiers import Modifier
from simulation.modifier_listeners import ExpireAfterNextAttackListener, ExpireAfterNextAttackByCharacterListener, ExpireAfterNextDamageByCharacterListener, ModifierListener

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestExpireAfterNextAttackListener(unittest.TestCase):
  def setUp(self):
    self.kakita = Character('Kakita')
    self.matsu = Character('Matsu')
    self.matsu.set_skill('parry', 3)
    self.shiba = Character('Shiba')
    groups = [Group('Lion', [self.matsu]), Group('Crane-Phoenix', [self.kakita, self.shiba])]
    self.context = EngineContext(groups)
    self.initiative_action = InitiativeAction([1], 1)

  def test_expire_after_failed_attack(self):
    modifier = Modifier(self.matsu, None, 'tn to hit', -5)
    listener = ExpireAfterNextAttackListener()
    modifier.register_listener('attack_failed', listener)
    modifier.register_listener('attack_succeeded', listener)
    self.matsu.add_modifier(modifier)
    # Matsu's TN to be hit to should be 15
    self.assertEqual(-5, self.matsu.modifier(None, 'tn to hit'))
    self.assertEqual(15, self.matsu.tn_to_hit())
    # should expire after Kakita attacks Matsu
    kakita_attack = actions.AttackAction(self.kakita, self.matsu, \
      'attack', self.initiative_action, self.context)
    kakita_attack_failed = events.AttackFailedEvent(kakita_attack)
    responses = [response for response in modifier.handle(self.matsu, kakita_attack_failed, self.context)]
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, events.RemoveModifierEvent))
    self.assertEqual(modifier, response.modifier)

  def test_expire_after_successful_attack(self):
    modifier = Modifier(self.matsu, None, 'tn to hit', -5)
    listener = ExpireAfterNextAttackListener()
    modifier.register_listener('attack_failed', listener)
    modifier.register_listener('attack_succeeded', listener)
    self.matsu.add_modifier(modifier)
    # Matsu's TN to be hit to should be 15
    self.assertEqual(-5, self.matsu.modifier(None, 'tn to hit'))
    self.assertEqual(15, self.matsu.tn_to_hit())
    # should expire after Kakita attacks Matsu
    kakita_attack = actions.AttackAction(self.kakita, self.matsu, \
      'attack', self.initiative_action, self.context)
    kakita_attack_succeeded = events.AttackSucceededEvent(kakita_attack)
    responses = [response for response in modifier.handle(self.matsu, kakita_attack_succeeded, self.context)]
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, events.RemoveModifierEvent))
    self.assertEqual(modifier, response.modifier)

  def test_do_not_expire_after_irrelevant_attack(self):
    modifier = Modifier(self.matsu, None, 'tn to hit', -5)
    listener = ExpireAfterNextAttackListener()
    modifier.register_listener('attack_failed', listener)
    modifier.register_listener('attack_succeeded', listener)
    self.matsu.add_modifier(modifier)
    # Matsu's TN to be hit to should be 15
    self.assertEqual(-5, self.matsu.modifier(None, 'tn to hit'))
    self.assertEqual(15, self.matsu.tn_to_hit())
    # should not expire if Matsu attacks Shiba
    matsu_attack = actions.AttackAction(self.matsu, self.shiba, \
      'attack', self.initiative_action, self.context)
    matsu_attack_failed = events.AttackFailedEvent(matsu_attack)
    responses = [response for response in modifier.handle(self.matsu, matsu_attack_failed, self.context)]
    self.assertEqual(0, len(responses))


class TestExpireAfterNextAttackByCharacterListener(unittest.TestCase):
  def setUp(self):
    self.kakita = Character('Kakita')
    self.matsu = Character('Matsu')
    self.matsu.set_skill('parry', 3)
    self.shiba = Character('Shiba')
    groups = [Group('Lion', [self.matsu]), Group('Crane-Phoenix', [self.kakita, self.shiba])]
    self.context = EngineContext(groups)
    self.initiative_action = InitiativeAction([1], 1)

  def test_expire_after_failed_attack(self):
    modifier = Modifier(self.matsu, None, 'tn to hit', -5)
    listener = ExpireAfterNextAttackByCharacterListener(self.kakita)
    modifier.register_listener('attack_failed', listener)
    modifier.register_listener('attack_succeeded', listener)
    self.matsu.add_modifier(modifier)
    # Matsu's TN to be hit to should be 15
    self.assertEqual(-5, self.matsu.modifier(None, 'tn to hit'))
    self.assertEqual(15, self.matsu.tn_to_hit())
    # should expire after Kakita attacks Matsu
    kakita_attack = actions.AttackAction(self.kakita, self.matsu, \
      'attack', self.initiative_action, self.context)
    kakita_attack_failed = events.AttackFailedEvent(kakita_attack)
    responses = [response for response in modifier.handle(self.matsu, kakita_attack_failed, self.context)]
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, events.RemoveModifierEvent))
    self.assertEqual(modifier, response.modifier)

  def test_expire_after_successful_attack(self):
    modifier = Modifier(self.matsu, None, 'tn to hit', -5)
    listener = ExpireAfterNextAttackByCharacterListener(self.kakita)
    modifier.register_listener('attack_failed', listener)
    modifier.register_listener('attack_succeeded', listener)
    self.matsu.add_modifier(modifier)
    # Matsu's TN to be hit to should be 15
    self.assertEqual(-5, self.matsu.modifier(None, 'tn to hit'))
    self.assertEqual(15, self.matsu.tn_to_hit())
    # should expire after Kakita attacks Matsu
    kakita_attack = actions.AttackAction(self.kakita, self.matsu, \
      'attack', self.initiative_action, self.context)
    kakita_attack_succeeded = events.AttackSucceededEvent(kakita_attack)
    responses = [response for response in modifier.handle(self.matsu, kakita_attack_succeeded, self.context)]
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, events.RemoveModifierEvent))
    self.assertEqual(modifier, response.modifier)

  def test_do_not_expire_after_attack_by_other_character(self):
    modifier = Modifier(self.matsu, None, 'tn to hit', -5)
    listener = ExpireAfterNextAttackByCharacterListener(self.kakita)
    modifier.register_listener('attack_failed', listener)
    modifier.register_listener('attack_succeeded', listener)
    self.matsu.add_modifier(modifier)
    # Matsu's TN to be hit to should be 15
    self.assertEqual(-5, self.matsu.modifier(None, 'tn to hit'))
    self.assertEqual(15, self.matsu.tn_to_hit())
    # should not expire if Shiba attacks Matsu
    shiba_attack = actions.AttackAction(self.shiba, self.matsu, \
      'attack', self.initiative_action, self.context)
    shiba_attack_failed = events.AttackSucceededEvent(shiba_attack)
    responses = [response for response in modifier.handle(self.matsu, shiba_attack_failed, self.context)]
    self.assertEqual(0, len(responses))

class TestExpireAfterNextDamageByCharacterListener(unittest.TestCase):
  def test_expire_after_light_wounds(self):
    # set up characters and context
    kakita = Character('Kakita')
    kakita.set_ring('fire', 5)
    wave_man = Character('Wave Man')
    groups = [Group('Frat Boys', kakita), Group('Plague', wave_man)]
    context = EngineContext(groups)
    modifier = Modifier(kakita, wave_man, 'damage', -5)
    listener = ExpireAfterNextDamageByCharacterListener(kakita, wave_man)
    modifier.register_listener('lw_damage', listener)
    kakita.add_modifier(modifier)
    # Get Kakita's damage roll params
    # There should be a -5 penalty
    (rolled, kept, mod) = kakita.get_damage_roll_params(wave_man, 'attack', 1)
    self.assertEqual(10, rolled)
    self.assertEqual(2, kept)
    self.assertEqual(-5, mod)
    # play LightWoundsDamageEvent on Kakita
    event = events.LightWoundsDamageEvent(kakita, wave_man, 19)
    responses = [response for response in modifier.handle(kakita, event, context)]
    # should be an expiration event
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, events.RemoveModifierEvent))
    self.assertEqual(modifier, response.modifier)

