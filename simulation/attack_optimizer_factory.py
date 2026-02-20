#!/usr/bin/env python3

#
# attack_optimizer_factory.py
#
# Factory class to provide AttackOptimizer instances.
#

from abc import ABC, abstractmethod

from simulation.attack_optimizers import AttackOptimizer, DamageOptimizer


class AttackOptimizerFactory(ABC):
  @abstractmethod
  def get_optimizer(self, character, target, skill, initiative_action, context):
    pass


class DefaultAttackOptimizerFactory(object):
  def get_optimizer(self, character, target, skill, initiative_action, context):
    if skill == 'feint':
      # since feint gets you 1 TVP, you should not spend VP on it
      return AttackOptimizer(character, target, skill, \
        initiative_action, context, max_vp=0, max_ap=2)
    elif skill == 'double attack':
      # double attacks might be worth 2 VP
      return DamageOptimizer(character, target, skill, \
        initiative_action, context, max_vp=2, max_ap=2)
    else:
      # otherwise, don't spend more than 1 VP on an attack roll
      return DamageOptimizer(character, target, skill, \
        initiative_action, context, max_vp=1, max_ap=2)

DEFAULT_ATTACK_OPTIMIZER_FACTORY = DefaultAttackOptimizerFactory()

