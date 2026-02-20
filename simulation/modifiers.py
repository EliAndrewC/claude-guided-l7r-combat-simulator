#!/usr/bin/env python3

#
# modifiers.py
#
# Implement modifiers (flat bonuses or penalties to rolls) that can expire in response to events.
#

import uuid


class Modifier(object):
  '''
  Class for modifiers (bonuses or penalties) that are specific to
  a skill or a specific target, or that have an expiration.

  Examples of modifiers:
  * Free raises to specific skills from School 2nd Dan techniques
  * Penalties to TN to be hit from Lunge or the Shiba 5th Dan
    technique

  Some modifiers, such as Free Raises granted by school, do not
  expire.

  Expiring modifiers are implemented by using a ModifierListener.
  Write a ModifierListener that 
  TODO: finish this documentation
  '''
  def __init__(self, subject, target, skills, adjustment):
    self._id = uuid.uuid4().hex
    self._subject = subject
    self._target = target
    if isinstance(skills, str):
      self._skills = [skills]
    elif isinstance(skills, list):
      for skill in skills:
        if not isinstance(skill, str):
          raise ValueError('Modifier skills parameter must be str or list of str')
      self._skills = skills
    else:
      raise ValueError('Modifier skills parameter must be str or list of str')
    self._adjustment = adjustment
    self._listeners = {}

  def apply(self, target, skill):
    '''
    apply(subject, target, skill) -> int
      target (Character): character who is the target of the skill
      skill (str): skill being used

    Returns the effect of this modifier on a skill or thing,
    or zero if it doesn't apply.
    '''
    if skill in self.skills():
      if target is None or self.target() is None or self.target() == target:
        return self.adjustment()
    return 0

  def handle(self, character, event, context):
    if event.name in self._listeners.keys():
      yield from self._listeners[event.name].handle(character, event, self, context)

  def adjustment(self):
    return self._adjustment

  def register_listener(self, event_name, listener):
    if not isinstance(event_name, str):
      raise ValueError('Modifier register_listener event_name parameter must be str')
    self._listeners[event_name] = listener

  def skills(self):
    return self._skills

  def subject(self):
    return self._subject

  def target(self):
    return self._target

  def __eq__(self, other):
    if self is other:
      return True
    elif not isinstance(other, Modifier):
      return False
    else:
      return self._id == other._id


class AnyAttackModifier(Modifier):
  '''
  A Modifier that applies to any attack skill.
  '''
  def __init__(self, subject, target, adjustment):
    super().__init__(subject, target, ATTACK_SKILLS, adjustment)


class FreeRaise(Modifier):
  '''
  A modifier that grants a +5 bonus to a skill, does not have restrictions on the target, and never expires.
  '''
  def __init__(self, subject, skill):
    super().__init__(subject, None, skill, 5)

  def apply(self, target, skill):
    if skill in self.skills():
      return 5
    return 0

  def register_listener(self, event_name, listener):
    pass

