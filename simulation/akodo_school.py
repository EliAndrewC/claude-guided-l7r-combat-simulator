#!/usr/bin/env python3

#
# akodo_school.py
#
# Implement Akodo Bushi School.
#

from simulation import events
from simulation.floating_bonuses import AnyAttackFloatingBonus
from simulation.listeners import Listener
from simulation.schools import BaseSchool
from simulation.strategies import Strategy


class AkodoBushiSchool(BaseSchool):
  def ap_base_skill(self):
    return None

  def apply_rank_five_ability(self, character):
    character.set_listener('lw_damage', AkodoLightWoundsDamageListener())

  def apply_rank_four_ability(self, character):
    self.apply_school_ring_raise_and_discount(character)
    character.set_listener('wound_check_declared', AkodoWoundCheckDeclaredListener())

  def apply_rank_three_ability(self, character):
    character.set_listener('wound_check_succeeded', AkodoWoundCheckSucceededListener())

  def apply_special_ability(self, character):
    character.set_listener('attack_failed', AkodoAttackFailedListener())
    character.set_listener('attack_succeeded', AkodoAttackSucceededListener())

  def extra_rolled(self):
    return ['double attack', 'feint', 'wound check']

  def free_raise_skills(self):
    return [ 'wound check' ]

  def name(self):
    return 'Akodo Bushi School'

  def school_knacks(self):
    return ['double attack', 'feint', 'iaijutsu']

  def school_ring(self):
    return 'water'


class AkodoAttackFailedListener(Listener):
  '''
  Listener to implement the Akodo special ability
  to gain 1 TVP on a failed feint.
  '''
  def handle(self, character, event, context):
    if isinstance(event, events.AttackFailedEvent):
      if event.action.subject() == character:
        if event.action.skill() == 'feint':
          yield events.GainTemporaryVoidPointsEvent(character, 1)


class AkodoAttackSucceededListener(Listener):
  '''
  Listener to implement the Akodo special ability
  to gain 4 TVP on a successful feint.
  '''
  def handle(self, character, event, context):
    if isinstance(event, events.AttackSucceededEvent):
      if event.action.subject() == character:
        if event.action.skill() == 'feint':
          yield events.GainTemporaryVoidPointsEvent(character, 4)


class AkodoLightWoundsDamageListener(Listener):
  '''
  Listener to implement the Akodo 5th Dan technique.
  '''
  def __init__(self):
    self._strategy = AkodoFifthDanStrategy()

  def handle(self, character, event, context):
    if isinstance(event, events.LightWoundsDamageEvent):
      if event.subject != character:
        # observe another character's damage roll
        character.knowledge().observe_damage_roll(event.subject, event.damage)
      if event.target == character:
        character.take_lw(event.damage)
        yield from character.wound_check_strategy().recommend(character, event, context)
        yield from self._strategy.recommend(character, event, context)


class AkodoFifthDanStrategy(Strategy):
  '''
  Strategy to decide how to use the Akodo 5th Dan technique
  to spend VP after taking damage to directly inflict 10 LW
  per VP spent to the attacker.
  '''
  def recommend(self, character, event, context):
    if isinstance(event, events.LightWoundsDamageEvent):
      if event.target == character:
        # calculate max vp spendable on damage
        available_vp = character.void_point_manager().vp('damage')
        max_vp = min(available_vp, character.max_vp_per_roll())
        # TODO: implement a little more intelligence
        if max_vp > 0:
          yield events.SpendVoidPointsEvent(character, 'damage', max_vp)
          yield events.LightWoundsDamageEvent(character, event.subject, 10 * max_vp)


class AkodoWoundCheckSucceededListener(Listener):
  '''
  Listener to implement the Akodo 3rd Dan technique
  to gain a floating bonus after a successful Wound Check.
  '''
  def handle(self, character, event, context):
    if isinstance(event, events.WoundCheckSucceededEvent):
      if event.subject == character:
        bonus = ((event.roll - event.damage) // 5) * character.skill('attack')
        character.gain_floating_bonus(AnyAttackFloatingBonus(bonus))
        # if the character may keep LW, consult the character's light wounds strategy
        yield from character.light_wounds_strategy().recommend(character, event, context)


class AkodoWoundCheckDeclaredListener(Listener):
  '''
  Listener to implement the Akodo 4th Dan technique
  to spend Void Points after a Wound Check roll to
  apply Free Raises to the roll.
  '''
  def __init__(self):
    self._strategy = AkodoWoundCheckRolledStrategy()

  def handle(self, character, event, context):
    if isinstance(event, events.WoundCheckDeclaredEvent):
      if event.subject == character:
        roll = character.roll_wound_check(event.damage, event.vp)
        event = events.WoundCheckRolledEvent(character, event.attacker, event.damage, roll)
        yield from self._strategy.recommend(character, event, context)


class AkodoWoundCheckRolledStrategy(Strategy):
  '''
  Strategy for the Akodo 4th Dan technique to decide
  whether to spend VP to improve a wound check roll.
  '''
  def recommend(self, character, event, context):
    if isinstance(event, events.WoundCheckRolledEvent):
      if event.subject == character:
        # how many wounds can I tolerate?
        tolerable_sw = min(1, character.sw_remaining())
        # how many wounds would I take?
        expected_sw = character.wound_check(event.roll)
        if expected_sw <= tolerable_sw:
          # ignore if the result is tolerable
          yield event
        else:
          # spend VP to reduce SW
          available_vp = character.void_point_manager().vp('wound check')
          max_spend = min(available_vp, character.max_vp_per_roll())
          prev_expected_sw = expected_sw
          chosen_spend = 0
          for vp in range(1, max_spend):
            new_roll = event.roll + (5 * vp)
            expected_sw = character.wound_check(new_roll)
            if expected_sw < prev_expected_sw:
              chosen_spend = vp
            prev_expected_sw = expected_sw
            if expected_sw <= tolerable_sw:
              break
          # spend chosen amount of VP
          new_roll = event.roll + (5 * chosen_spend)
          if (chosen_spend > 0):
            yield events.SpendVoidPointsEvent(character, 'wound check', chosen_spend)
          # yield adjusted wound check roll
          yield events.WoundCheckRolledEvent(character, event.attacker, event.damage, new_roll)

