#!/usr/bin/env python3

#
# test_kakita_school.py
#
# Unit tests for the Kakita Duelist School.
#

import unittest

from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.events import LightWoundsDamageEvent, NewPhaseEvent
from simulation.groups import Group
from simulation.initiative_actions import InitiativeAction
from simulation.kakita_school import ContestedIaijutsuAttackAction, \
    ContestedIaijutsuAttackDeclaredEvent, \
    ContestedIaijutsuAttackRolledEvent, \
    KakitaAttackAction, KakitaBushiSchool, \
    KakitaNewPhaseListener, KakitaRollParameterProvider, \
    TakeContestedIaijutsuAttackAction
from simulation.roll_provider import TestRollProvider


class TestContestedIaijutsuAttackAction(unittest.TestCase):
  '''
  Test the Kakita ContestedIaijutsuAttackAction used for context
  and mechanics for the Kakita 5th Dan ability.
  '''
  def setUp(self):
    # set characters
    kakita = CharacterBuilder(xp=9001) \
      .with_name('Kakita') \
      .with_school(KakitaBushiSchool()) \
      .buy_skill('double attack', 5) \
      .buy_skill('iaijutsu', 5) \
      .buy_skill('lunge', 5) \
      .build()
    matsu = CharacterBuilder(xp=9001) \
      .with_name('Matsu') \
      .generic() \
      .buy_skill('iaijutsu', 5) \
      .build()
    # set context
    groups = [Group('Crane', kakita), Group('Lion', matsu)]
    context = EngineContext(groups)
    # set instances
    self.kakita = kakita
    self.matsu = matsu
    self.context = context
    self.initiative_action = InitiativeAction([], 0)

  def test_calculate_extra_damage_dice_outroll(self):
    # test extra damage dice when kakita outrolls opponent
    action = ContestedIaijutsuAttackAction(self.kakita, self.matsu, \
      self.kakita, 'iaijutsu', 'iaijutsu', self.initiative_action, \
      self.context)
    # kakita outrolls matsu by 10
    action.set_skill_roll(45)
    action.set_opponent_skill_roll(35)
    # should receive two extra rolled dice
    self.assertEqual(2, action.calculate_extra_damage_dice())
    self.assertEqual(2, action.calculate_extra_damage_dice(opponent_skill_roll=35, skill_roll=45))

  def test_calculate_extra_damage_dice_outrolled(self):
    # test extra damage dice when kakita is outrolled by opponent
    action = ContestedIaijutsuAttackAction(self.kakita, self.matsu, \
      self.kakita, 'iaijutsu', 'iaijutsu', self.initiative_action, \
      self.context)
    # matsu outrolls kakita by 10
    action.set_skill_roll(35)
    action.set_opponent_skill_roll(45)
    # should receive two extra rolled dice
    self.assertEqual(-2, action.calculate_extra_damage_dice())
    self.assertEqual(-2, action.calculate_extra_damage_dice(opponent_skill_roll=45, skill_roll=35))

  def test_is_hit(self):
    # test hit when kakita wins
    action = ContestedIaijutsuAttackAction(self.kakita, self.matsu, \
      self.kakita, 'iaijutsu', 'iaijutsu', self.initiative_action, \
      self.context)
    action.set_skill_roll(45)
    action.set_opponent_skill_roll(35)
    self.assertTrue(action.is_hit())

  def test_is_hit_outrolled(self):
    # test hit when kakita is outrolled by opponent
    action = ContestedIaijutsuAttackAction(self.kakita, self.matsu, \
      self.kakita, 'iaijutsu', 'iaijutsu', self.initiative_action, \
      self.context)
    action.set_skill_roll(35)
    action.set_opponent_skill_roll(45)
    self.assertTrue(action.is_hit())

  def test_miss(self): 
    # test "miss"
    # this happens when opponent outrolls by so much that there is no damage
    action = ContestedIaijutsuAttackAction(self.kakita, self.matsu, \
      self.kakita, 'iaijutsu', 'iaijutsu', self.initiative_action, \
      self.context)
    action.set_skill_roll(5)
    action.set_opponent_skill_roll(105)
    self.assertFalse(action.is_hit())

  def test_penalize_no_iaijutsu(self):
    # test penalty for using attack instead of iaijutsu
    action = ContestedIaijutsuAttackAction(self.kakita, self.matsu, \
      self.kakita, 'attack', 'iaijutsu', self.initiative_action, \
      self.context)
    (rolled, kept, modifier) = action.skill_roll_params()
    self.assertEqual(-5, modifier)


class TestKakitaAttackAction(unittest.TestCase):
  '''
  Test the tempo bonus from the Kakita 3rd Dan technique.
  '''
  def setUp(self):
    # set characters
    kakita = CharacterBuilder(xp=9001) \
      .with_name('Kakita') \
      .with_school(KakitaBushiSchool()) \
      .buy_ring('fire', 4) \
      .buy_skill('attack', 3) \
      .buy_skill('double attack', 3) \
      .buy_skill('iaijutsu', 3) \
      .buy_skill('lunge', 3) \
      .build()
    target = Character('target')
    # set context
    groups = [Group('Crane', kakita), Group('Awful Zombies', target)]
    # set instances
    self.kakita = kakita
    self.target = target
    self.groups = groups

  def test_equal_tempo(self):
    self.kakita.set_actions([1,2,3])
    self.target.set_actions([1,2,3])
    context = EngineContext(self.groups, round=1, phase=1)
    # if target has action in same phase, there is no tempo bonus
    # roll params should be base roll of 8k4+5
    initiative_action = InitiativeAction([1], 1)
    attack = KakitaAttackAction(self.kakita, self.target, \
      'iaijutsu', initiative_action, context)
    self.assertEqual((8, 4, 5), attack.skill_roll_params())

  def test_negative_tempo(self):
    self.kakita.set_actions([4,5,6])
    self.target.set_actions([1,2,3])
    context = EngineContext(self.groups, round=1, phase=4)
    # if target has the earlier action, there is no tempo bonus
    # tempo bonus cannot become a penalty
    # roll params should be base roll of 8k4+5
    initiative_action = InitiativeAction([4], 4)
    attack = KakitaAttackAction(self.kakita, self.target, \
      'iaijutsu', initiative_action, context)
    self.assertEqual((8, 4, 5), attack.skill_roll_params())

  def test_no_target_actions(self):
    self.kakita.set_actions([3])
    context = EngineContext(self.groups, round=1, phase=3)
    # kakita acts in Phase 3, target has no actions
    # Kakita's base roll is 8k4+5
    # should receive a tempo bonus of +24
    # roll params should be 8k4+29
    initiative_action = InitiativeAction([3], 3)
    attack = KakitaAttackAction(self.kakita, self.target, \
      'iaijutsu', initiative_action, context)
    self.assertEqual((8, 4, 29), attack.skill_roll_params())

  def test_tempo_bonus(self):
    self.kakita.set_actions([0,1,2,3])
    self.target.set_actions([4,5,6,7])
    context = EngineContext(self.groups, round=1, phase=0)
    # kakita acts in Phase 0, target's first action is in Phase 4
    # Kakita's base roll is 8k4+5
    # should receive a tempo bonus of +12
    # roll params should be 8k4+17
    initiative_action = InitiativeAction([0], 0)
    attack = KakitaAttackAction(self.kakita, self.target, \
      'iaijutsu', initiative_action, context)
    self.assertEqual((8, 4, 17), attack.skill_roll_params())


class TestKakitaNewPhaseListener(unittest.TestCase):
  '''
  Test that KakitaNewPhaseListener response to Phase 0 with a
  TakeContestedIaijutsuAttackAction (playable event for Kakita
  5th Dan ability).
  '''
  def setUp(self):
    # characters
    kakita = CharacterBuilder(xp=9001) \
      .with_name('Kakita') \
      .with_school(KakitaBushiSchool()) \
      .buy_ring('fire', 5) \
      .buy_skill('double attack', 5) \
      .buy_skill('iaijutsu', 5) \
      .buy_skill('lunge', 5) \
      .build()
    target = Character('target')
    # context
    groups = [Group('Crane', kakita), Group('target', target)]
    context = EngineContext(groups)
    # instances
    self.kakita = kakita
    self.target = target
    self.context = context

  def test_phase_zero(self):
    # Kakita should respond to phase zero with TakeContestedIaijutsuAttackAction
    listener = KakitaNewPhaseListener()
    event = NewPhaseEvent(0)
    responses = [e for e in listener.handle(self.kakita, event, self.context)]
    self.assertEqual(1, len(responses))
    response = responses[0]
    self.assertTrue(isinstance(response, TakeContestedIaijutsuAttackAction))
    self.assertEqual(self.kakita, response.challenger())
    self.assertEqual(self.target, response.defender())

  def test_phase_one(self):
    # Kakita should respond to phase one with nothing
    listener = KakitaNewPhaseListener()
    event = NewPhaseEvent(1)
    responses = [e for e in listener.handle(self.kakita, event, self.context)]
    self.assertEqual(0, len(responses))


class TestKakitaRollParameterProvider(unittest.TestCase):
  '''
  Test that KakitaRollParameterProvider gives the Kakita 4th Dan
  ability of a Free Raise to damage rolls with iaijutsu.
  '''
  def setUp(self):
    kakita = CharacterBuilder(xp=9001) \
      .with_name('Kakita') \
      .with_school(KakitaBushiSchool()) \
      .buy_skill('double attack', 4) \
      .buy_skill('iaijutsu', 4) \
      .buy_skill('lunge', 4) \
      .buy_ring('fire', 5) \
      .build()
    target = Character('target')
    self.kakita = kakita
    self.target = target

  def test_iaijutsu_damage_bonus(self):
    provider = KakitaRollParameterProvider()
    (rolled, kept, bonus) = provider.get_damage_roll_params( \
      self.kakita, self.target, 'iaijutsu', 0)
    self.assertEqual(9, rolled)
    self.assertEqual(2, kept)
    self.assertEqual(5, bonus)

  def test_other_skill_no_damage_bonus(self):
    provider = KakitaRollParameterProvider()
    (rolled, kept, bonus) = provider.get_damage_roll_params( \
      self.kakita, self.target, 'attack', 0)
    self.assertEqual(9, rolled)
    self.assertEqual(2, kept)
    self.assertEqual(0, bonus)


class TestTakeContestedIaijutsuAttackAction(unittest.TestCase):
  def setUp(self):
    kakita = CharacterBuilder(xp=9001) \
      .with_name('Kakita') \
      .with_school(KakitaBushiSchool()) \
      .buy_skill('double attack', 5) \
      .buy_skill('iaijutsu', 5) \
      .buy_skill('lunge', 5) \
      .buy_ring('fire', 5) \
      .build()
    target = Character('target')
    target.set_ring('earth', 5)
    target.set_ring('fire', 3)
    target.set_ring('water', 5)
    target.set_skill('attack', 4)
    # context
    groups = [Group('Crane', kakita), Group('target', target)]
    context = EngineContext(groups)
    # engine
    engine = CombatEngine(context)
    # instances
    self.kakita = kakita
    self.target = target
    self.context = context
    self.engine = engine

  def test_play(self):
    self.context.initialize()
    phase_zero = NewPhaseEvent(0)
    # rig the rolls
    challenger_skill_roll = 50
    defender_skill_roll = 30
    challenger_damage_roll = 1
    defender_wound_check_roll = 100
    challenger_roll_provider = TestRollProvider()
    challenger_roll_provider \
      .put_skill_roll('iaijutsu', challenger_skill_roll)
    challenger_roll_provider \
      .put_damage_roll(challenger_damage_roll)
    self.kakita.set_roll_provider(challenger_roll_provider)
    defender_roll_provider = TestRollProvider()
    defender_roll_provider \
      .put_skill_roll('attack', defender_skill_roll)
    defender_roll_provider \
      .put_wound_check_roll(defender_wound_check_roll)
    self.target.set_roll_provider(defender_roll_provider)
    self.engine.event(phase_zero)
    # assert expected event history:
    #  1. NewPhaseEvent
    #  2. TakeContestedIaijutsuAttackAction
    #  3. ContestedIaijutsuAttackDeclaredEvent(challenger, defender)
    #  4. ContestedIaijutsuAttackDeclaredEvent(defender, challenger)
    #  5. ContestedIaijutsuAttackRolledEvent(challenger, defender)
    #  6. ContestedIaijutsuAttackRolledEvent(defender, challenger)
    #  7. LightWoundsDamageEvent
    #  8. WoundCheckDeclaredEvent
    #  9. WoundCheckRolledEvent
    # 10. KeepLightWoundsEvent
    history = self.engine.history()
    #  1. NewPhaseEvent
    self.assertTrue(isinstance(history[0], \
      NewPhaseEvent))
    #  2. TakeContestedIaijutsuAttackAction
    take_attack_event = history[1]
    self.assertTrue(isinstance(take_attack_event, \
      TakeContestedIaijutsuAttackAction))
    #  3. ContestedIaijutsuDeclaredEvent(challenger, defender)
    challenger_declared_event = history[2]
    self.assertTrue(isinstance(challenger_declared_event, \
      ContestedIaijutsuAttackDeclaredEvent))
    self.assertEqual(self.kakita, \
      challenger_declared_event.action.subject())
    self.assertEqual(self.target, \
      challenger_declared_event.action.target())
    self.assertEqual(self.kakita, \
      challenger_declared_event.action.challenger())
    self.assertEqual('iaijutsu', \
      challenger_declared_event.action.skill())
    self.assertEqual('attack', \
      challenger_declared_event.action.contested_skill())
    #  4. ContestedIaijutsuDeclaredEvent(defender, challenger)
    defender_declared_event = history[3]
    self.assertTrue(isinstance(defender_declared_event, \
      ContestedIaijutsuAttackDeclaredEvent))
    self.assertEqual(self.target, \
      defender_declared_event.action.subject())
    self.assertEqual(self.kakita, \
      defender_declared_event.action.target())
    self.assertEqual(self.kakita, \
      defender_declared_event.action.challenger())
    self.assertEqual('attack', \
      defender_declared_event.action.skill())
    self.assertEqual('iaijutsu', \
      defender_declared_event.action.contested_skill())
    #  5. ContestedIaijutsuRolledEvent(challenger, defender)
    challenger_rolled_event = history[4]
    self.assertTrue(isinstance(challenger_rolled_event, \
      ContestedIaijutsuAttackRolledEvent))
    self.assertEqual(self.kakita, \
      challenger_rolled_event.action.subject())
    self.assertEqual(self.target, \
      challenger_rolled_event.action.target())
    self.assertEqual(self.kakita, \
      challenger_rolled_event.action.challenger())
    self.assertEqual('iaijutsu', \
      challenger_rolled_event.action.skill())
    self.assertEqual('attack', \
      challenger_rolled_event.action.contested_skill())
    self.assertEqual(challenger_skill_roll + 5, \
      challenger_rolled_event.action.skill_roll())
    self.assertEqual(defender_skill_roll, \
      challenger_rolled_event.action.opponent_skill_roll())
    #  6. ContestedIaijutsuRolledEvent(defender, challenger)
    defender_rolled_event = history[5]
    self.assertTrue(isinstance(defender_rolled_event, \
      ContestedIaijutsuAttackRolledEvent))
    self.assertEqual(self.target, \
      defender_rolled_event.action.subject())
    self.assertEqual(self.kakita, \
      defender_rolled_event.action.target())
    self.assertEqual(self.kakita, \
      defender_rolled_event.action.challenger())
    self.assertEqual('attack', \
      defender_rolled_event.action.skill())
    self.assertEqual('iaijutsu', \
      defender_rolled_event.action.contested_skill())
    self.assertEqual(defender_skill_roll, \
      defender_rolled_event.action.skill_roll())
    self.assertEqual(challenger_skill_roll + 5, \
      defender_rolled_event.action.opponent_skill_roll())
    #  7. LightWoundsDamageEvent
    damage_event = history[6]
    self.assertTrue(isinstance(damage_event, \
      LightWoundsDamageEvent))
    self.assertEqual(self.kakita, damage_event.subject)
    self.assertEqual(self.target, damage_event.target)
    self.assertEqual(challenger_damage_roll + 5, damage_event.damage)
    #  8. WoundCheckDeclaredEvent
    #  9. WoundCheckRolledEvent
    # 10. KeepLightWoundsEvent
    
