#!/usr/bin/env python3

#
# test_listeners.py
#
# Unit tests for L7R combat simulator Listener classes
#

import logging
import sys
import unittest

from simulation.actions import AttackAction
from simulation.character import Character
from simulation.context import EngineContext
from simulation.events import DeathEvent, NewRoundEvent, LightWoundsDamageEvent, SeriousWoundsDamageEvent, TakeSeriousWoundEvent, UnconsciousEvent, WoundCheckDeclaredEvent, WoundCheckFailedEvent, WoundCheckRolledEvent, WoundCheckSucceededEvent
from simulation.groups import Group
from simulation.listeners import NewRoundListener, LightWoundsDamageListener, SeriousWoundsDamageListener, TakeSeriousWoundListener, WoundCheckDeclaredListener, WoundCheckFailedListener, WoundCheckRolledListener
from simulation.log import logger
from simulation.roll_provider import TestRollProvider


# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestNewRoundListener(unittest.TestCase):
  def test_new_round(self):
    character = Character()
    context = EngineContext([Group('1', character), Group('2', Character())])
    # rig an initiative roll
    roll_provider = TestRollProvider()
    roll_provider.put_initiative_roll([1, 2])
    character.set_roll_provider(roll_provider)
    event = NewRoundEvent(1)
    listener = NewRoundListener()
    responses = list(listener.handle(character, event, context))
    self.assertTrue(responses == [])
    self.assertEqual([1, 2], character.actions())


class TestLightWoundsDamageListener(unittest.TestCase):
  def setUp(self):
    self.attacker = Character('attacker')
    self.target = Character('target')
    self.context = EngineContext([Group('attacker', self.attacker), Group('target', self.target)])
    self.context.initialize()

  def test_light_wounds(self):
    damage = 20
    event = LightWoundsDamageEvent(self.attacker, self.target, damage)
    listener = LightWoundsDamageListener()
    responses = list(listener.handle(self.target, event, self.context))
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, WoundCheckDeclaredEvent))
    self.assertEqual(damage, response.damage)
    self.assertEqual(damage, self.target.lw())

  def test_additive_light_wounds(self):
    self.target.take_lw(5)
    damage = 20
    event = LightWoundsDamageEvent(self.attacker, self.target, damage)
    listener = LightWoundsDamageListener()
    responses = list(listener.handle(self.target, event, self.context))
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, WoundCheckDeclaredEvent))
    self.assertEqual(damage, response.damage)
    # character should now have 25 LW
    self.assertEqual(25, self.target.lw())


class TestSeriousWoundsDamageListener(unittest.TestCase):
  def setUp(self):
    self.attacker = Character('attacker')
    self.target = Character('target')
    self.context = EngineContext([Group('attacker', self.attacker), Group('target', self.target)])

  def test_die(self):
    damage = 5
    event = SeriousWoundsDamageEvent(self.attacker, self.target, damage)
    listener = SeriousWoundsDamageListener()
    responses = list(listener.handle(self.target, event, self.context))
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, DeathEvent))
    self.assertEqual(self.target, response.subject)

  def test_unconscious(self):
    damage = 4
    event = SeriousWoundsDamageEvent(self.attacker, self.target, damage)
    listener = SeriousWoundsDamageListener()
    responses = list(listener.handle(self.target, event, self.context))
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, UnconsciousEvent))
    self.assertEqual(self.target, response.subject)

  def test_wounds(self):
    damage = 2
    event = SeriousWoundsDamageEvent(self.attacker, self.target, damage)
    listener = SeriousWoundsDamageListener()
    responses = list(listener.handle(self.target, event, self.context))
    self.assertEqual([], responses)
    self.assertEqual(damage, self.target.sw())


class TestTakeSeriousWoundListener(unittest.TestCase):
  def test_take_sw(self):
    attacker = Character('attacker')
    target = Character('target')
    context = EngineContext([Group('attacker', attacker), Group('target', target)])
    target.take_lw(9001)
    event = TakeSeriousWoundEvent(target, attacker, 1)
    listener = TakeSeriousWoundListener()
    responses = list(listener.handle(target, event, context))
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, SeriousWoundsDamageEvent))
    self.assertEqual(target, response.target)
    self.assertEqual(1, response.damage) 
    # the target's lw should be reset, but the sw is not taken until the serious wound event is handled
    self.assertEqual(0, target.lw())
    self.assertEqual(0, target.sw())


class TestWoundCheckDeclaredListener(unittest.TestCase):
  def test_roll(self):
    # set up character with rigged wound check
    attacker = Character('attacker')
    target = Character('target')
    context = EngineContext([Group('attacker', attacker), Group('target', target)])
    roll_provider = TestRollProvider()
    roll_provider.put_wound_check_roll(50)
    target.set_roll_provider(roll_provider)
    damage = 20
    vp = 0
    event = WoundCheckDeclaredEvent(target, attacker, damage, vp)
    listener = WoundCheckDeclaredListener()
    responses = list(listener.handle(target, event, context))
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, WoundCheckRolledEvent))
    self.assertEqual(20, response.damage)
    self.assertEqual(50, response.roll)


class TestWoundCheckRolledListener(unittest.TestCase):
  def setUp(self):
    attacker = Character('attacker')
    self.attacker = attacker
    target = Character('target')
    self.target = target
    self.context = EngineContext([Group('attacker', attacker), Group('target', target)])

  def test_fail(self):
    damage = 20
    roll = 10
    event = WoundCheckRolledEvent(self.target, self.attacker, damage, roll)
    listener = WoundCheckRolledListener()
    responses = list(listener.handle(self.target, event, self.context))
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, WoundCheckFailedEvent))
    self.assertEqual(damage, response.damage)
    self.assertEqual(roll, response.roll)

  def test_succeed(self):
    damage = 10
    roll = 20
    event = WoundCheckRolledEvent(self.target, self.attacker, damage, roll)
    listener = WoundCheckRolledListener()
    responses = list(listener.handle(self.target, event, self.context))
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, WoundCheckSucceededEvent))
    self.assertEqual(damage, response.damage)
    self.assertEqual(roll, response.roll)


class TestWoundCheckFailedListener(unittest.TestCase):
  def test_fail(self):
    attacker = Character('attacker')
    target = Character('target')
    target.take_lw(29)
    context = EngineContext([Group('attacker', attacker), Group('target', target)])
    damage = 20
    roll = 10
    event = WoundCheckFailedEvent(target, attacker, damage, roll)
    listener = WoundCheckFailedListener()
    responses = list(listener.handle(target, event, context))
    self.assertEqual(1, len(responses))
    response = responses[0]
    # missing a wound check by 19 means 2 SW
    self.assertTrue(isinstance(response, SeriousWoundsDamageEvent))
    self.assertEqual(2, response.damage)
    # character's lw should be reset
    self.assertEqual(0, target.lw())


# TODO: test wound check succeeded listener


if (__name__ == '__main__'):
  unittest.main()

