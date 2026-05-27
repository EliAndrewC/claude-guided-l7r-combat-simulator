#!/usr/bin/env python3

#
# wound_check_optimizer_factory.py
#
# Factories to get wound check optimizer instances for a character.

from abc import ABC, abstractmethod
from typing import Any

from simulation.optimizers.wound_check_optimizers import DefaultWoundCheckOptimizer


class WoundCheckOptimizerFactory(ABC):
    @abstractmethod
    def get_wound_check_optimizer(self, subject: Any, event: Any, context: Any, max_vp: int | None = None, max_ap: int | None = None) -> Any:
        pass  # pragma: no cover  # abstract method; subclasses must override


class DefaultWoundCheckOptimizerFactory(WoundCheckOptimizerFactory):
    def get_wound_check_optimizer(self, subject: Any, event: Any, context: Any, max_vp: int | None = None, max_ap: int | None = None) -> Any:
        return DefaultWoundCheckOptimizer(subject, event, context, max_vp, max_ap)


DEFAULT_WOUND_CHECK_OPTIMIZER_FACTORY = DefaultWoundCheckOptimizerFactory()
