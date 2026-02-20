#!/usr/bin/env python3

#
# action_factory.py
#
# Factory to get attacks.
# This is used to deal with schools that have custom actions that break the usual rules of how actions work.
#

from abc import ABC, abstractmethod

from simulation import actions
from simulation.initiative_actions import InitiativeAction


class ActionFactory(ABC):
  def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
    '''
    get_attack_action(subject, target, skill, vp=0) -> AttackAction
      subject (Character): attacker
      target (Character): target of the attack
      skill (str): skill being used to attack
      initiative_action (InitiativeAction): initiative action being used for the attack
      context (EngineContext): context
      vp (int): Void Points declared for for the skill roll

    Returns an attack action using the chosen skill.
    '''
    pass

  def get_counterattack_action(self, subject, target, attack, skill, initiative_action, context, vp=0):
    '''
    get_counterattack_action(subject, target, attack, skill, vp=0) -> CounterattackAction
      subject (Character): attacker
      target (Character): target of the attack
      attack (AttackAction): attack being countered
      skill (str): skill being used to attack
      initiative_action (InitiativeAction): initiative action being used for the attack
      context (EngineContext): context
      vp (int): Void Points declared for for the skill roll

    Returns a counterattack action against the given attack action using the chosen skill.
    '''
    pass

  def get_parry_action(self, subject, target, attack, skill, initiative_action, context, vp=0):
    '''
    get_parry_action(subject, target, attack, skill, initiative_action, context, vp=0) -> ParryAction
      subject (Character): attacker
      target (Character): target of the attack
      attack (AttackAction): attack being parried
      skill (str): skill being used to attack
      initiative_action (InitiativeAction): initiative action being used for the attack
      context (EngineContext): context
      vp (int): Void Points declared for for the skill roll

    Returns a parry action against the given attack action using the chosen skill.
    '''
    pass


class DefaultActionFactory(ActionFactory):
  '''
  ActionFactory used by characters who do not have special abilities that modify these skills.
  '''
  def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
    if skill == 'attack':
      return actions.AttackAction(subject, target, skill, initiative_action, context, vp=vp)
    elif skill == 'double attack':
      return actions.DoubleAttackAction(subject, target, skill, initiative_action, context, vp=vp)
    elif skill == 'feint':
      return actions.FeintAction(subject, target, skill, initiative_action, context, vp=vp)
    elif skill == 'lunge':
      return actions.LungeAction(subject, target, skill, initiative_action, context, vp=vp)
    else:
      raise ValueError('Invalid attack skill: {}'.format(skill))

  def get_counterattack_action(self, subject, target, attack, skill, initiative_action, context, vp=0):
    return actions.CounterattackAction(subject, target, skill, initiative_action, context, attack, vp=vp)

  def get_parry_action(self, subject, target, attack, skill, initiative_action, context, vp=0):
    return actions.ParryAction(subject, target, skill, initiative_action, context, attack, vp=vp)

DEFAULT_ACTION_FACTORY = DefaultActionFactory()

