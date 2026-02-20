#!/usr/bin/env python3

#
# wound_check_optimizer_factory.py
#
# Factories to get wound check optimizer instances for a character.

from abc import ABC, abstractmethod

from simulation.wound_check_optimizers import DefaultWoundCheckOptimizer

class WoundCheckOptimizerFactory(ABC):
  @abstractmethod
  def get_wound_check_optimizer(self, subject, event, context, max_vp=None, max_ap=None):
    pass


class DefaultWoundCheckOptimizerFactory(WoundCheckOptimizerFactory):
  def get_wound_check_optimizer(self, subject, event, context, max_vp=None, max_ap=None):
    return DefaultWoundCheckOptimizer(subject, event, context, max_vp, max_ap)

DEFAULT_WOUND_CHECK_OPTIMIZER_FACTORY = DefaultWoundCheckOptimizerFactory()

