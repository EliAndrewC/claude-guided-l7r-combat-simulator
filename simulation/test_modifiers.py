#!/usr/bin/env python3

#
# test_modifiers.py
#
# Unit tests for modifiers module.
#

import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.initiative_actions import InitiativeAction
from simulation.listeners import Listener
from simulation.modifiers import FreeRaise, Modifier
from simulation.modifier_listeners import ModifierListener


class TestCustomModifier(unittest.TestCase):
  def setUp(self):
    self.subject = Character('subject')
    self.target = Character('target')
    self.third_character = Character('third character')

  def test_penalty(self):
    modifier = Modifier(self.subject, None, 'tn to hit', -5)
    self.assertEqual(-5, modifier.apply(self.target, 'tn to hit'))
    self.assertEqual(-5, modifier.apply(self.third_character, 'tn to hit'))

  def test_specific_target(self):
    modifier = Modifier(self.subject, self.target, 'attack', 6)
    self.assertEqual(6, modifier.apply(self.target, 'attack'))
    self.assertEqual(0, modifier.apply(self.third_character, 'attack'))

  def test_unspecified_target(self):
    modifier = Modifier(self.subject, None, 'attack', 5)
    self.assertEqual(5, modifier.apply(self.target, 'attack'))
    self.assertEqual(5, modifier.apply(self.third_character, 'attack'))


class ExplodeOnAttackListener(ModifierListener):
  '''
  For testing purposes only: a listener that causes a character
  to take a million serious wounds if they successfully attack.
  '''
  def handle(self, character, event, modifier, context):
    if isinstance(event, events.AttackSucceededEvent):
      if character == event.action.subject():
        character.take_sw(1000000)
        yield from ()


class TestModifierEvents(unittest.TestCase):
  def setUp(self):
    self.subject = Character('subject')
    self.target = Character('target')
    groups = [Group('subject', self.subject), Group('target', self.target)]
    self.context = EngineContext(groups)
    self.initiative_action = InitiativeAction([1], 1)

  def test_listen_to_events(self):
    # set up the "explode on attack" modifier
    modifier = Modifier(self.subject, self.target, 'attack', 0)
    modifier.register_listener('attack_succeeded', ExplodeOnAttackListener())
    # play an irrelevant event on the listener
    irrelevant_attack = actions.AttackAction(self.target, \
      self.subject, 'attack', self.initiative_action, self.context)
    irrelevant_attack_event = events.AttackSucceededEvent(irrelevant_attack)
    responses = [response for response in modifier.handle(self.subject, irrelevant_attack_event, self.context)]
    # should have no effect
    self.assertEqual(0, self.subject.sw())
    self.assertEqual(0, self.target.sw())
    # play a relevant event on the listener
    relevant_attack = actions.AttackAction(self.subject, \
      self.target, 'attack', self.initiative_action, self.context)
    relevant_attack_event = events.AttackSucceededEvent(relevant_attack)
    responses = [response for response in modifier.handle(self.subject, relevant_attack_event, self.context)]
    # attacker should explode
    self.assertEqual(1000000, self.subject.sw())
    self.assertEqual(0, self.target.sw())
    

class TestFreeRaise(unittest.TestCase):
  def setUp(self):
    self.attacker = Character('attacker')
    self.target = Character('target')

  def test_free_raise(self):
    modifier = FreeRaise(self.attacker, 'attack')
    self.assertEqual(5, modifier.apply(self.target, 'attack'))

  def test_wrong_skill(self):
    modifier = FreeRaise(self.attacker, 'attack')
    self.assertEqual(0, modifier.apply(self.target, 'parry'))

  def test_no_target(self):
    modifier = FreeRaise(self.attacker, 'attack')
    self.assertEqual(5, modifier.apply(None, 'attack'))
    self.assertEqual(0, modifier.apply(None, 'parry'))

