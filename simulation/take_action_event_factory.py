#!/usr/bin/env python3

#
# take_action_event_factory.py
#
# Factory to get TakeActionEvents.
# This is used to deal with schools that have custom actions that break the usual rules of how actions work.
#
# Specifically, having this class means that schools can set a custom TakeActionEventFactory on a character
# instead of using custom strategies.
#

from abc import ABC, abstractmethod

from simulation.actions import AttackAction, ParryAction
from simulation.events import TakeAttackActionEvent, TakeParryActionEvent


class TakeActionEventFactory(ABC):
  '''
  Factory class to provide TakeActionEvents.

  Used to enable special abilities that alter the way events work.

  Encapsulates logic around special TakeActionEvents so we don't have to
  contaminate Strategy implementations with these features.
  '''
  @abstractmethod
  def get_take_attack_action_event(self, action):
    pass

  @abstractmethod
  def get_take_parry_action_event(self, action):
    pass


class DefaultTakeActionEventFactory(TakeActionEventFactory):
  '''
  Provider for standard TakeAttackActionEvent and TakeParryActionEvent.
  '''
  def get_take_attack_action_event(self, action):
    '''
    get_take_attack_action_event(action) -> TakeAttackActionEvent
      action (Action): an AttackAction

    Returns a TakeAttackActionEvent to run an attack.
    '''
    if isinstance(action, AttackAction):
      return TakeAttackActionEvent(action)
    else:
      raise ValueError('get_take_attack_action_event only supports TakeAttackAction')

  def get_take_parry_action_event(self, action):
    '''
    get_take_parry_action_event(action) -> TakeParryActionEvent
      action (Action): a ParryAction

    Returns a TakeParryActionEvent to run a parry.
    '''
    if isinstance(action, ParryAction):
      return TakeParryActionEvent(action)
    else:
      raise ValueError('get_take_parry_action_event only supports TakeParryAction')

DEFAULT_TAKE_ACTION_EVENT_FACTORY = DefaultTakeActionEventFactory()

