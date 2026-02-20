#!/usr/bin/env python3

#
# modifier_listeners.py
#
# A class that can respond to events to expire modifiers.
# These are a completely separate object from Listener.
# With normal Listeners, the handle method is a generator.
# With ModifierListeners, the handle method determines whether or not to remove the modifier.
#

from abc import ABC, abstractmethod

from simulation.events import AttackFailedEvent, AttackSucceededEvent, EndOfRoundEvent, LightWoundsDamageEvent, RemoveModifierEvent
from simulation.log import logger
from simulation.modifiers import Modifier
from simulation.skills import ATTACK_SKILLS


class ModifierListener(ABC):
  '''
  An observer that may be registered on a Modifier to make it expire in response to some event.
  '''
  @abstractmethod
  def handle(self, character, event, modifier, context):
    '''
    Evaluate whether the modifier should expire, and remove it from the character if so.
    '''
    pass


class ExpireAfterNextAttackListener(ModifierListener):
  '''
  Expire a modifier after the next attack against the character.
  '''
  def handle(self, character, event, modifier, context):
    if isinstance(event, AttackFailedEvent) or isinstance(event, AttackSucceededEvent):
      if character == event.action.target():
        yield RemoveModifierEvent(character, modifier)


class ExpireAfterNextAttackByCharacterListener(ModifierListener):
  '''
  Expire a modifier after the next attack by a specific attacker against the character.
  '''
  def __init__(self, attacker):
    super().__init__()
    self._attacker = attacker

  def handle(self, character, event, modifier, context):
    if isinstance(event, AttackFailedEvent) or isinstance(event, AttackSucceededEvent):
      if character == event.action.target() and self._attacker == event.action.subject():
        yield RemoveModifierEvent(character, modifier)


class ExpireAfterNextDamageByCharacterListener(ModifierListener):
  '''
  Expire a modifier after a character's next damage roll.
  Used for expiring modifiers that affect a character's damage roll.
  '''
  def __init__(self, subject, target):
    super().__init__()
    self._subject = subject
    self._target = target

  def handle(self, character, event, modifier, context):
    if isinstance(event, LightWoundsDamageEvent):
      if character == event.subject and self._target == event.target:
        yield RemoveModifierEvent(character, modifier)


class ExpireAtEndOfRoundListener(ModifierListener):
  '''
  Expire a modifier at the end of the current round.
  '''
  def handle(self, character, event, modifier, context):
    if isinstance(event, EndOfRoundEvent):
      yield RemoveModifierEvent(character, modifier)

