#!/usr/bin/env python3

#
# actions.py
#
# Classes for combat actions in the L7R combat simulator.
#

from simulation.events import SeriousWoundsDamageEvent
from simulation.initiative_actions import InitiativeAction

class Action(object):
  '''
  Action classes implement the details of making characters roll for
  an action, determining whether the action was successful, and
  providing a context for combat actions.

  Actions are played out using Event classes with play methods that
  generate events for the action. An Action class is set on the
  generated events, which is how it can serve as a context to
  coordinate between the characters and the playable event.
  '''
  def __init__(self, subject, target, skill, initiative_action, context, ring=None, vp=0):
    '''
    __init__(subject, target, skill, initiative_action, context, vp=0)
      subject (Character): character taking the action
      target (Character): target of the action
      skill (str): skill being used
      initiative_action (InitiativeAction): initiative action being used
      context (EngineContext): context for timing
      ring (str): ring used for skill roll. Defaults to None, which
        means the character's default skill ring is used.
      vp (int): Void Points spent on this action
    '''
    self._subject = subject
    self._target = target
    if not isinstance(skill, str):
      raise ValueError('skill must be str')
    self._skill = skill
    if not isinstance(initiative_action, InitiativeAction):
      raise ValueError('initiative_action must be InitiativeAction')
    self._initiative_action = initiative_action
    self._context = context
    if ring is not None:
      if not isinstance(ring, str):
        raise ValueError('ring must be str')
    self._ring = ring
    if not isinstance(vp, int):
      raise ValueError('vp must be int')
    self._vp = vp
    self._skill_roll = None

  def context(self):
    return self._context

  def damage_roll_params(self):
    raise NotImplementedError()

  def initiative_action(self):
    return self._initiative_action

  def ring(self):
    return self._ring

  def roll_skill(self):
    self.set_skill_roll(self.subject().roll_skill(self.target(), self.skill(), ring=self.ring(), vp=self.vp()))
    return self.skill_roll()

  def set_skill_roll(self, roll):
    if not isinstance(roll, int):
      raise ValueError('set_skill_roll requires int')
    self._skill_roll = roll

  def set_vp(self, vp):
    self._vp = vp

  def skill(self):
    return self._skill

  def skill_roll(self):
    return self._skill_roll

  def skill_roll_params(self):
    return self.subject().get_skill_roll_params(self.target(), self.skill(), vp=self.vp())

  def subject(self):
    return self._subject

  def target(self):
    return self._target

  def vp(self):
    return self._vp


class AttackAction(Action):
  def __init__(self, subject, target, skill, initiative_action, context, ring=None, vp=0):
    super().__init__(subject, target, skill, initiative_action, context, ring=ring, vp=vp)
    self._damage_roll = None
    self._damage_roll_params = None
    self._parries_declared = []
    self._parries_declined = []
    self._parries_predeclared = []
    self._parried = False
    self._parry_attempted = False

  def add_parry_declared(self, event):
    self._parries_declared.append(event)

  def add_parry_predeclared(self, event):
    self._parries_predeclared.append(event)
    self.add_parry_declared(event)

  def add_parry_declined(self, character):
    self._parries_declined.append(character)

  def calculate_extra_damage_dice(self, skill_roll=None, tn=None):
    if skill_roll is None:
      skill_roll = self.skill_roll()
    if tn is None:
      tn = self.tn()
    if self.parry_attempted():
      return 0
    else:
      return (skill_roll - self.tn()) // 5

  def damage_roll(self):
    return self._damage_roll

  def damage_roll_params(self):
    if self.skill_roll() is None:
      return None
    extra_rolled = self.calculate_extra_damage_dice()
    rolled, kept, mod = self.subject().get_damage_roll_params(self.target(), self.skill(), extra_rolled, self.vp())
    return (rolled, kept, mod)

  def direct_damage(self):
    return None

  def is_hit(self):
    return self.skill_roll() >= self.tn() and not self.parried()

  def parried(self):
    return self._parried

  def parry_attempted(self):
    return self._parry_attempted

  def parries_declared(self):
    return self._parries_declared

  def parries_declined(self):
    return self._parries_declined

  def parries_predeclared(self):
    return self._parries_predeclared

  def parry_tn(self):
    return self.skill_roll()

  def roll_damage(self):
    extra_rolled = self.calculate_extra_damage_dice()
    damage_roll = self.subject().roll_damage(self.target(), self.skill(), extra_rolled, self.vp())
    damage_roll = max(0, damage_roll)
    self.set_damage_roll(damage_roll)
    return damage_roll

  def set_damage_roll(self, damage):
    if not isinstance(damage, int):
      raise ValueError('set_damage_roll requires int')
    self._damage_roll = damage

  def set_parry_attempted(self):
    self._parry_attempted = True

  def set_parried(self):
    self._parried = True

  def tn(self):
    return self.target().tn_to_hit()


class CounterattackAction(AttackAction):
  def __init__(self, subject, target, skill, initiative_action, context, attack, ring=None, vp=0):
    super().__init__(subject, target, skill, initiative_action, context, ring=ring, vp=vp)
    self._original_attack = attack

  def attack(self):
    return self._original_attack

  def tn(self):
    penalty = 0 if self.attack().target() == self.subject() else 5 * self.attack().subject().skill('attack')
    return self.target().tn_to_hit() + penalty 
    

class DoubleAttackAction(AttackAction):
  def calculate_extra_damage_dice(self, skill_roll=None, tn=None):
    if skill_roll is None:
      skill_roll = self.skill_roll()
    if tn is None:
      tn = self.tn() - 20
    penalty = 0
    if self.parry_attempted():
      for parry_event in self.parries_declared():
        if parry_event.action.subject() == self.target():
          # if the target attempts to parry,
          # double attack does 4 fewer dice of damage
          penalty = 4
          break
        else:
          # if a third character parries on behalf of the target,
          # double attack does 2 fewer dice of damage
          penalty = 2
    return ((skill_roll - self.tn()) // 5) - penalty

  def direct_damage(self):
    return SeriousWoundsDamageEvent(self.subject(), self.target(), 1)

  def tn(self):
    return self.target().tn_to_hit() + 20


class FeintAction(AttackAction):
  def calculate_extra_damage_dice(self, skill_roll=None, tn=None):
    return 0

  def damage_roll_params(self):
    return (0, 0, 0)

  def roll_damage(self):
    self.set_damage_roll(0)
    return 0


class LungeAction(AttackAction):
  def calculate_extra_damage_dice(self, skill_roll=None, tn=None):
    return super().calculate_extra_damage_dice(skill_roll, tn) + 1


class ParryAction(Action):
  def __init__(self, subject, target, skill, initiative_action, context, attack, predeclared=False, ring=None, vp=0):
    super().__init__(subject, target, skill, initiative_action, context, ring=ring, vp=vp)
    self._attack = attack
    self._predeclared = predeclared

  def attack(self):
    return self._attack

  def is_success(self):
    return self.skill_roll() >= self.tn()

  def roll_skill(self):
    penalty = 0
    if self._attack.target() != self.subject():
      # parry on behalf of others has a penalty
      penalty = 10
    # roll parry
    self.set_skill_roll(self.subject().roll_skill(self.target(), self.skill(), ring=self.ring(), vp=self.vp()) - penalty)
    return self.skill_roll()

  def set_attack_parry_declared(self, event):
    self._attack.add_parry_declared(event)

  def set_attack_parried(self):
    self._attack.set_parried()

  def set_attack_parry_attempted(self):
    self._attack.set_parry_attempted()

  def tn(self):
    return self._attack.parry_tn()

