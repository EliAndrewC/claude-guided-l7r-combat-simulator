#!/usr/bin/env python3

#
# shiba_school.py
# Author: Patrick Bannister (ptbannister@gmail.com)
#
#

from simulation.actions import ParryAction
from simulation.action_factory import DefaultActionFactory
from simulation.events import AddModifierEvent, LightWoundsDamageEvent, ParrySucceededEvent, TakeParryActionEvent
from simulation.listeners import Listener
from simulation.modifiers import Modifier
from simulation.modifier_listeners import ExpireAfterNextAttackListener
from simulation.schools import BaseSchool
from simulation.take_action_event_factory import DefaultTakeActionEventFactory


class ShibaBushiSchool(BaseSchool):
  def ap_base_skill(self):
    pass

  def apply_special_ability(self, character):
    character.set_interrupt_cost('parry', 1)
    character.set_action_factory(SHIBA_ACTION_FACTORY)

  def apply_rank_three_ability(self, character):
    character.set_take_action_event_factory(SHIBA_TAKE_ACTION_EVENT_FACTORY)

  def apply_rank_four_ability(self, character):
    self.apply_school_ring_raise_and_discount(character)
    character.set_extra_rolled('wound check', 3)
    character.set_extra_kept('wound check', 1)

  def apply_rank_five_ability(self, character):
    character.set_listener('parry_succeeded', ShibaParrySucceededListener())

  def extra_rolled(self):
    return ['double attack', 'parry', 'wound check']

  def free_raise_skills(self):
    return [ 'parry' ]

  def name(self):
    return 'Shiba Bushi School'

  def school_knacks(self):
    return ['counterattack', 'double attack', 'iaijutsu']

  def school_ring(self):
    return 'air' 


class ShibaActionFactory(DefaultActionFactory):
  '''
  ActionFactory that returns the ShibaParryAction for parries.
  '''
  def get_parry_action(self, subject, target, attack, skill, initiative_action, context, vp=0):
    return ShibaParryAction(subject, target, skill, initiative_action, context, attack, vp=vp)

SHIBA_ACTION_FACTORY = ShibaActionFactory()


class ShibaParryAction(ParryAction):
  '''
  Implement the Shiba Bushi School special ability that parries on
  behalf of others do not suffer the standard -10 penalty.
  '''
  def roll_parry(self):
    # roll parry
    self.set_skill_roll(self.subject().roll_skill(self.target(), self.skill(), vp=self.vp()))
    return self.skill_roll()


class ShibaParrySucceededListener(Listener):
  '''
  Implement the Shiba Bushi School 5th Dan technique
  to impose an expiring modifier on the TN to be hit
  on the target of a successful parry.
  '''
  def handle(self, character, event, context):
    if isinstance(event, ParrySucceededEvent):
      penalty = -1 * (event.action.skill_roll() - event.action.attack().skill_roll())
      modifier = Modifier(event.action.target(), None, 'tn to hit', penalty)
      listener = ExpireAfterNextAttackListener()
      modifier.register_listener('attack_failed', listener)
      modifier.register_listener('attack_succeeded', listener)
      yield AddModifierEvent(event.action.target(), modifier)


class ShibaTakeActionEventFactory(DefaultTakeActionEventFactory):
  '''
  Custom TakeActionEventFactory to help implement Shiba Bushi School 3rd Dan technique
  to do damage with parries.
  '''
  def get_take_parry_action_event(self, parry):
    if isinstance(parry, ParryAction):
      return ShibaTakeParryEvent(parry)
    else:
      raise ValueError('get_take_parry_action_event requires a ParryAction')

SHIBA_TAKE_ACTION_EVENT_FACTORY = ShibaTakeActionEventFactory()


class ShibaTakeParryEvent(TakeParryActionEvent):
  '''
  Custom TakeParryActionEvent to implement the Shiba Bushi School 3rd Dan technique
  to do damage with parries.
  '''
  def play(self, context):
    yield self._declare_parry()
    yield from self._roll_parry(context)
    if self.action.is_success():
      yield self._succeeded()
    else:
      yield self._failed()
    yield self._roll_damage()

  def _roll_damage(self):
    '''
    _roll_damage() -> int

    Returns a damage roll for this parry.
    '''
    rolled = 2 * self.action.subject().skill('attack')
    damage_roll = self.action.subject().roll_provider().get_damage_roll(rolled, 1)
    return LightWoundsDamageEvent(self.action.subject(), self.action.target(), damage_roll)

