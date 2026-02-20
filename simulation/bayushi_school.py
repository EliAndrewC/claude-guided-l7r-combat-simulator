#!/usr/bin/env python3

#
# bayushi_school.py
# Implement Bayushi Bushi School.
#

from simulation import events
from simulation.actions import FeintAction
from simulation.action_factory import DefaultActionFactory
from simulation.character import Character
from simulation.floating_bonuses import AnyAttackFloatingBonus
from simulation.listeners import Listener
from simulation.log import logger
from simulation.roll_params import DefaultRollParameterProvider, RollParameterProvider, normalize_roll_params
from simulation.schools import BaseSchool
from simulation.strategies import BaseAttackStrategy, Strategy, UniversalAttackStrategy
from simulation.wound_check_provider import DEFAULT_WOUND_CHECK_PROVIDER, WoundCheckProvider


class BayushiBushiSchool(BaseSchool):
  def ap_base_skill(self):
    return None

  def apply_rank_five_ability(self, character):
    character.set_wound_check_provider(BayushiWoundCheckProvider())

  def apply_rank_four_ability(self, character):
    self.apply_school_ring_raise_and_discount(character)
    character.set_listener('attack_failed', BayushiAttackFailedListener())
    character.set_listener('attack_succeeded', BayushiAttackSucceededListener())

  def apply_rank_three_ability(self, character):
    character.set_action_factory(BAYUSHI_ACTION_FACTORY)

  def apply_special_ability(self, character):
    character.set_roll_parameter_provider(BAYUSHI_ROLL_PARAMETER_PROVIDER)

  def extra_rolled(self):
    return ['double attack', 'iaijutsu', 'wound check']

  def free_raise_skills(self):
    return [ 'double attack' ]

  def name(self):
    return 'Bayushi Bushi School'

  def school_knacks(self):
    return ['double attack', 'feint', 'iaijutsu']

  def school_ring(self):
    return 'fire'


class BayushiRollParameterProvider(DefaultRollParameterProvider):
  '''
  Custom RollParameterProvider to implement the Bayushi special ability
  to apply Void Points spent on attack rolls to damage rolls.
  '''
  def get_damage_roll_params(self, character, target, skill, attack_extra_rolled, vp=0):
    # calculate extra rolled dice
    ring = character.ring(character.get_skill_ring('damage'))
    my_extra_rolled = character.extra_rolled('damage')
    rolled = ring + my_extra_rolled + attack_extra_rolled + character.weapon().rolled() + vp
    # calculate extra kept dice
    kept = character.weapon().kept() + character.extra_kept('damage') + vp
    # calculate modifier
    mod = character.modifier('damage', None)
    return normalize_roll_params(rolled, kept, mod)

BAYUSHI_ROLL_PARAMETER_PROVIDER = BayushiRollParameterProvider()


class BayushiWoundCheckProvider(WoundCheckProvider):
  '''
  WoundCheckProvider to implement the Bayushi 5th Dan ability
  to take Serious Wounds as if the character had half as many light wounds.
  '''
  def wound_check(self, roll, lw=None):
    lw = lw // 2
    return DEFAULT_WOUND_CHECK_PROVIDER.wound_check(roll, lw)


class BayushiFeintAction(FeintAction):
  def damage_roll_params(self):
    rolled = self.subject().skill('attack') + self.vp()
    kept = 1 + self.vp()
    modifier = self.subject().modifier(self.target(), self.skill())
    return (rolled, kept, modifier)

  def roll_damage(self):
    (rolled, kept, modifier) = self.damage_roll_params()
    damage_roll = self.subject().roll_provider().get_damage_roll(rolled, kept) + modifier
    self.set_damage_roll(damage_roll)
    return damage_roll


class BayushiActionFactory(DefaultActionFactory):
  def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
    if skill == 'feint':
      return BayushiFeintAction(subject, target, skill, initiative_action, context, vp=vp)
    else:
      return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)

BAYUSHI_ACTION_FACTORY = BayushiActionFactory()


class BayushiAttackFailedListener(Listener):
  '''
  Listener to implement the Bayushi 4th Dan ability
  to gain a floating bonus to any attack after a Feint.
  '''
  def handle(self, character, event, context):
    if isinstance(event, events.AttackFailedEvent):
      if event.action.subject() == character:
        if event.action.skill() == 'feint':
          character.gain_floating_bonus(AnyAttackFloatingBonus(5))
    yield from ()


class BayushiAttackSucceededListener(Listener):
  '''
  Listener to implement the Bayushi 4th Dan ability
  to gain a floating bonus to any attack after a Feint.
  '''
  def handle(self, character, event, context):
    if isinstance(event, events.AttackSucceededEvent):
      if event.action.subject() == character:
        if event.action.skill() == 'feint':
          character.gain_floating_bonus(AnyAttackFloatingBonus(5))
    yield from ()

