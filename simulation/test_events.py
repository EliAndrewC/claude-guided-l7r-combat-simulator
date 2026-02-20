#!/usr/bin/env python3

#
# test_events.py
#
# Unit tests for L7R combat simulator events module
#

import logging
import sys
import unittest

from simulation import events
from simulation.actions import AttackAction, ParryAction
from simulation.character import Character
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.groups import Group
from simulation.initiative_actions import InitiativeAction
from simulation.log import logger
from simulation.roll_provider import TestRollProvider
from simulation.strategies import AlwaysParryStrategy, NeverParryStrategy, PlainAttackStrategy, ReluctantParryStrategy, StingyPlainAttackStrategy


# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestTakeAttackActionEvent(unittest.TestCase):
  def setUp(self):
    # set up attacker character
    attacker = Character('attacker')
    attacker.set_ring('fire', 5)
    attacker.set_skill('attack', 4)
    attacker.set_strategy('attack', StingyPlainAttackStrategy())
    attacker.set_actions([1])
    self.attacker = attacker
    # set up target character
    target = Character('target')
    target.set_parry_strategy(NeverParryStrategy())
    target.set_ring('air', 5)
    target.set_skill('parry', 5)
    target.set_actions([1])
    self.target = target
    # set up groups
    groups = [Group('attacker', attacker), Group('target', target)]
    # set up context
    self.context = EngineContext(groups, round=1, phase=1)
    self.context.initialize()
    self.initiative_action = InitiativeAction([1], 1)

  def test_run_hit(self):
    # rig the attack roll to hit by 1
    attacker_roll_provider = TestRollProvider()
    attacker_roll_provider.put_skill_roll('attack', 31)
    attacker_roll_provider.put_damage_roll(15)
    self.attacker.set_roll_provider(attacker_roll_provider)
    # rig the wound check to succeed
    target_roll_provider = TestRollProvider()
    target_roll_provider.put_wound_check_roll(25)
    self.target.set_roll_provider(target_roll_provider)
    # set up attack
    attack = AttackAction(self.attacker, self.target, 'attack', self.initiative_action, self.context)
    # set up engine
    engine = CombatEngine(self.context)
    # run the event
    event = events.TakeAttackActionEvent(attack)
    # run the attack
    engine.event(event)
    # assert expected attack action state
    self.assertEqual(31, attack.skill_roll())
    self.assertEqual([], attack.parries_declared())
    self.assertFalse(attack.parried())
    self.assertTrue(attack.is_hit())
    self.assertEqual(0, attack.calculate_extra_damage_dice())
    self.assertEqual(15, attack._damage_roll)
    # assert expected event history
    history = engine.history()
    first_event = history.pop(0)
    self.assertTrue(isinstance(first_event, events.TakeAttackActionEvent))
    second_event = history.pop(0)
    self.assertTrue(isinstance(second_event, events.AttackDeclaredEvent))
    third_event = history.pop(0)
    self.assertTrue(isinstance(third_event, events.AttackRolledEvent))
    self.assertEqual(31, third_event.roll)
    fourth_event = history.pop(0)
    self.assertTrue(isinstance(fourth_event, events.AttackSucceededEvent))
    fifth_event = engine.history().pop(0)
    self.assertTrue(isinstance(fifth_event, events.LightWoundsDamageEvent))
    self.assertEqual(self.target, fifth_event.target)
    self.assertEqual(15, fifth_event.damage)

  def test_run_miss(self):
    # rig the attack roll to miss by 1
    attacker_roll_provider = TestRollProvider()
    attacker_roll_provider.put_skill_roll('attack', 29)
    self.attacker.set_roll_provider(attacker_roll_provider)
    # set up attack
    attack = AttackAction(self.attacker, self.target, 'attack', self.initiative_action, self.context)
    # set up engine
    engine = CombatEngine(self.context)
    # run the event
    event = events.TakeAttackActionEvent(attack)
    # run the attack
    engine.event(event)
    # assert expected attack action state
    self.assertEqual(29, attack.skill_roll())
    self.assertEqual([], attack.parries_declared())
    self.assertFalse(attack.parried())
    self.assertFalse(attack.is_hit())
    self.assertEqual
    # assert expected event history
    history = engine.history()
    first_event = history.pop(0)
    self.assertTrue(isinstance(first_event, events.TakeAttackActionEvent))
    second_event = history.pop(0)
    self.assertTrue(isinstance(second_event, events.AttackDeclaredEvent))
    third_event = history.pop(0)
    self.assertTrue(isinstance(third_event, events.AttackRolledEvent))
    self.assertEqual(29, third_event.roll)
    fourth_event = history.pop(0)
    self.assertTrue(isinstance(fourth_event, events.AttackFailedEvent))

  def test_run_failed_parry(self):
    # make target parry attacks
    self.target.set_strategy('parry', AlwaysParryStrategy())
    # rig the attack roll to hit by 20 and the damage roll to be small
    attacker_roll_provider = TestRollProvider()
    attacker_roll_provider.put_skill_roll('attack', 50)
    attacker_roll_provider.put_damage_roll(15)
    self.attacker.set_roll_provider(attacker_roll_provider)
    # rig the parry to fail and the wound check to succeed
    target_roll_provider = TestRollProvider()
    target_roll_provider.put_skill_roll('parry', 49)
    target_roll_provider.put_wound_check_roll(25)
    self.target.set_roll_provider(target_roll_provider)
    # set up engine and context
    engine = CombatEngine(self.context)
    # set up an attack action
    attack = AttackAction(self.attacker, self.target, 'attack', self.initiative_action, self.context)
    # run the event
    event = events.TakeAttackActionEvent(attack)
    engine.event(event)
    # assert expected attack action state
    self.assertEqual(50, attack.skill_roll())
    self.assertEqual(1, len(attack.parries_declared()))
    self.assertEqual([], attack.parries_predeclared())
    self.assertFalse(attack.parried())
    self.assertTrue(attack.parry_attempted())
    self.assertTrue(attack.is_hit())
    self.assertEqual(0, attack.calculate_extra_damage_dice())
    self.assertEqual(15, attack._damage_roll)
    # assert expected event history
    history = engine.history()
    # take_attack
    first_event = history.pop(0)
    self.assertTrue(isinstance(first_event, events.TakeAttackActionEvent))
    # attack_declared
    second_event = history.pop(0)
    self.assertTrue(isinstance(second_event, events.AttackDeclaredEvent))
    # attack_rolled
    third_event = history.pop(0)
    self.assertTrue(isinstance(third_event, events.AttackRolledEvent))
    self.assertEqual(50, third_event.roll)
    # spend_action
    fourth_event = history.pop(0)
    self.assertTrue(isinstance(fourth_event, events.SpendActionEvent))
    # take_parry
    fifth_event = history.pop(0)
    self.assertTrue(isinstance(fifth_event, events.TakeParryActionEvent))
    # parry_declared
    sixth_event = history.pop(0)
    self.assertTrue(isinstance(sixth_event, events.ParryDeclaredEvent))
    self.assertEqual(self.target, sixth_event.action.subject())
    self.assertEqual(self.attacker, sixth_event.action.target())
    # parry_rolled
    seventh_event = history.pop(0)
    self.assertTrue(isinstance(seventh_event, events.ParryRolledEvent))
    self.assertEqual(self.target, seventh_event.action.subject())
    self.assertEqual(self.attacker, seventh_event.action.target())
    self.assertEqual(49, seventh_event.roll)
    self.assertFalse(seventh_event.action.is_success())
    # parry_failed
    eighth_event = history.pop(0)
    self.assertTrue(isinstance(eighth_event, events.ParryFailedEvent))
    # attack_succeeded
    ninth_event = history.pop(0)
    self.assertTrue(isinstance(ninth_event, events.AttackSucceededEvent))
    # lw_damage
    tenth_event = engine.history().pop(0)
    self.assertTrue(isinstance(tenth_event, events.LightWoundsDamageEvent))
    self.assertEqual(self.target, tenth_event.target)
    self.assertEqual(15, tenth_event.damage)
    # wound_check_declared
    # wound_check_rolled
    # wound_check_succeeded
    # keep_lw

  def test_run_successful_parry(self):
    # make target parry attacks
    self.target.set_strategy('parry', AlwaysParryStrategy())
    # rig the attack roll to hit by 20
    attacker_roll_provider = TestRollProvider()
    attacker_roll_provider.put_skill_roll('attack', 50)
    self.attacker.set_roll_provider(attacker_roll_provider)
    # rig the parry roll to succeed by 1
    target_roll_provider = TestRollProvider()
    target_roll_provider.put_skill_roll('parry', 51)
    self.target.set_roll_provider(target_roll_provider)
    # set up engine and context
    engine = CombatEngine(self.context)
    # set up an attack action
    attack = AttackAction(self.attacker, self.target, 'attack', self.initiative_action, self.context)
    # run the event
    event = events.TakeAttackActionEvent(attack)
    engine.event(event)
    # assert expected attack action state
    self.assertEqual(50, attack.skill_roll())
    self.assertTrue(attack.parried())
    self.assertTrue(attack.parry_attempted())
    self.assertFalse(attack.is_hit())
    # assert expected event history
    history = engine.history()
    # take_attack
    first_event = history.pop(0)
    self.assertTrue(isinstance(first_event, events.TakeAttackActionEvent))
    # attack_declared
    second_event = history.pop(0)
    self.assertTrue(isinstance(second_event, events.AttackDeclaredEvent))
    # attack_rolled
    third_event = history.pop(0)
    self.assertTrue(isinstance(third_event, events.AttackRolledEvent))
    self.assertEqual(50, third_event.roll)
    # spend_action
    fourth_event = history.pop(0)
    self.assertTrue(isinstance(fourth_event, events.SpendActionEvent))
    # take_parry
    fifth_event = history.pop(0)
    self.assertTrue(isinstance(fifth_event, events.TakeParryActionEvent))
    # parry_declared
    sixth_event = history.pop(0)
    self.assertTrue(isinstance(sixth_event, events.ParryDeclaredEvent))
    self.assertEqual(self.target, sixth_event.action.subject())
    self.assertEqual(self.attacker, sixth_event.action.target())
    # parry_rolled
    seventh_event = history.pop(0)
    self.assertTrue(isinstance(seventh_event, events.ParryRolledEvent))
    self.assertEqual(self.target, seventh_event.action.subject())
    self.assertEqual(self.attacker, seventh_event.action.target())
    self.assertEqual(51, seventh_event.roll)
    self.assertTrue(seventh_event.action.is_success())
    # parry_succeeded
    eighth_event = history.pop(0)
    self.assertTrue(isinstance(eighth_event, events.ParrySucceededEvent))
    # attack_failed
    ninth_event = history.pop(0)
    self.assertTrue(isinstance(ninth_event, events.AttackFailedEvent))
    # no more events
    self.assertEqual(0, len(history))


class TestTakeParryActionEvent(unittest.TestCase):
  def setUp(self):
    # set up attacker character
    attacker = Character('attacker')
    attacker.set_ring('fire', 5)
    attacker.set_skill('attack', 4)
    attacker.set_strategy('attack', StingyPlainAttackStrategy())
    attacker.set_actions = ([1])
    self.attacker = attacker
    # set up target character
    target = Character('target')
    target.set_parry_strategy(AlwaysParryStrategy())
    target.set_ring('air', 5)
    target.set_skill('parry', 5)
    target.set_actions = ([1])
    self.target = target
    # set up groups
    groups = [Group('attacker', attacker), Group('target', target)]
    # set up context
    self.context = EngineContext(groups, round=1, phase=1)
    self.context.initialize()
    self.initiative_action = InitiativeAction([1], 1)

  def test_run_parry(self):
    # set up engine
    engine = CombatEngine(self.context)
    # set up an attack that hit by 20
    attack = AttackAction(self.attacker, self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(50)
    # set up the parry action
    parry = ParryAction(self.target, self.attacker, 'parry', self.initiative_action, self.context, attack)
    # rig the parry roll to succeed by 1
    target_roll_provider = TestRollProvider()
    target_roll_provider.put_skill_roll('parry', 51)
    self.target.set_roll_provider(target_roll_provider)
    # run the event
    event = events.TakeParryActionEvent(parry)
    engine.event(event)
    # assert expected parry action state
    self.assertEqual(51, parry.skill_roll())
    self.assertTrue(parry.is_success())
    # assert expected attack action state
    self.assertTrue(attack.parried())
    self.assertTrue(attack.parry_attempted())
    self.assertFalse(attack.is_hit())
    # assert expected event history
    history = engine.history()
    first_event = history.pop(0)
    self.assertTrue(isinstance(first_event, events.TakeParryActionEvent))
    second_event = history.pop(0)
    self.assertTrue(isinstance(second_event, events.ParryDeclaredEvent))
    third_event = history.pop(0)
    self.assertTrue(isinstance(third_event, events.ParryRolledEvent))
    self.assertEqual(self.target, third_event.action.subject())
    self.assertEqual(self.attacker, third_event.action.target())
    self.assertEqual(51, third_event.roll)
    fourth_event = history.pop(0)
    self.assertTrue(isinstance(fourth_event, events.ParrySucceededEvent))

  def test_run_failed_parry(self):
    # set up engine
    engine = CombatEngine(self.context)
    # set up an attack that hit by 20
    attack = AttackAction(self.attacker, self.target, 'attack', self.initiative_action, self.context)
    attack.set_skill_roll(50)
    # set up the parry action
    parry = ParryAction(self.target, self.attacker, 'parry', self.initiative_action, self.context, attack)
    # rig the parry roll to fail by 1
    target_roll_provider = TestRollProvider()
    target_roll_provider.put_skill_roll('parry', 49)
    self.target.set_roll_provider(target_roll_provider)
    # run the event
    event = events.TakeParryActionEvent(parry)
    engine.event(event)
    # assert expected parry action state
    self.assertEqual(49, parry.skill_roll())
    self.assertFalse(parry.is_success())
    # assert expected attack action state
    self.assertFalse(attack.parried())
    self.assertTrue(attack.parry_attempted())
    self.assertTrue(attack.is_hit())
    self.assertEqual(0, attack.calculate_extra_damage_dice())
    # assert expected event history
    history = engine.history()
    first_event = history.pop(0)
    self.assertTrue(isinstance(first_event, events.TakeParryActionEvent))
    second_event = history.pop(0)
    self.assertTrue(isinstance(second_event, events.ParryDeclaredEvent))
    third_event = history.pop(0)
    self.assertTrue(isinstance(third_event, events.ParryRolledEvent))
    self.assertEqual(self.target, third_event.action.subject())
    self.assertEqual(self.attacker, third_event.action.target())
    self.assertEqual(49, third_event.roll)
    fourth_event = history.pop(0)
    self.assertTrue(isinstance(fourth_event, events.ParryFailedEvent))

