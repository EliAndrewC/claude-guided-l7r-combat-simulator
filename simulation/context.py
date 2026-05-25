#!/usr/bin/env python3

#
# context.py
#
# Context class for L7R combat simulator.
#

from typing import Any

from simulation import events
from simulation.exceptions import CombatEnded
from simulation.features import TrialFeatures
from simulation.formation import Formation, NullFormation
from simulation.optimizers.probability_provider import DefaultProbabilityProvider


class EngineContext:
    """
    Portable context for simulator engines.
    """

    def __init__(self, groups: list[Any] = [], round: int = 0, phase: int = 0, formation: Formation | None = None) -> None:
        self._formation: Formation = formation if formation is not None else NullFormation()
        self._groups = groups
        if len(self._groups) < 2:
            raise ValueError("Must have at least two groups")
        self._characters: list[Any] = []
        for group in groups:
            if len(group) < 1:
                raise ValueError("A group must contain at least one character")
            for character in group:
                self._characters.append(character)
        if len(self._characters) < 2:
            raise ValueError("Must have at least two characters")
        self._still_moving: list[Any] = []
        self._features = TrialFeatures()
        self._probability_provider = DefaultProbabilityProvider()
        self._round = round
        self._phase = phase

    def characters(self) -> list[Any]:
        return self._characters

    def groups(self) -> list[Any]:
        return self._groups

    def features(self) -> TrialFeatures:
        return self._features

    def formation(self) -> Formation:
        return self._formation

    def initialize(self) -> None:
        self.probability_provider().initialize()
        for character in self._characters:
            group = character.group()
            if group is None:
                continue
            for other in self._characters:
                if other not in group:
                    character.knowledge().observe_tn_to_hit(other, other.tn_to_hit())

    def is_anybody_still_moving(self) -> bool:
        return len(self._still_moving) > 0

    def is_still_moving(self, character: Any) -> bool:
        return character in self._still_moving

    def mean_roll(self, rolled: int, kept: int, explode: bool = True) -> float:
        result: float = self.probability_provider().mean_roll(rolled, kept, explode)
        return result

    def next_phase(self) -> None:
        if self._phase == 10:
            raise RuntimeError("Cannot go to next phase after 10")
        self._phase += 1

    def next_round(self) -> None:
        self._round += 1
        self._phase = 0

    def phase(self) -> int:
        return self._phase

    def p(self, x: int, rolled: int, kept: int, explode: bool = True) -> float:
        result: float = self.probability_provider().p(x, rolled, kept, explode)
        return result

    def probability_provider(self) -> DefaultProbabilityProvider:
        return self._probability_provider

    def reevaluate_initiative(self) -> None:
        max_actions = max([len(character.actions()) for character in self._characters if character.is_fighting()])
        self._characters.sort(key=lambda character: character.initiative_priority(max_actions))

    def reset(self) -> None:
        self._features.clear()
        self._phase = 0
        self._round = 0
        for character in self._characters:
            character.reset()
        self._still_moving.clear()
        self._formation.reset()

    def reset_still_moving(self) -> None:
        self._still_moving.clear()
        for character in self._characters:
            if character.is_fighting():
                self._still_moving.append(character)

    def round(self) -> int:
        return self._round

    def stop_moving(self, character: Any) -> None:
        if character in self._still_moving:
            self._still_moving.remove(character)

    def test_group(self) -> Any:
        return self._groups[1]

    def time(self) -> tuple[int, int]:
        return (self._round, self._phase)

    def update_status(self, event: events.Event) -> None:
        if isinstance(event, events.NotMovingEvent):
            self.stop_moving(event.subject)
        elif isinstance(event, events.DefeatEvent):
            self.stop_moving(event.subject)
            self._formation.remove(event.subject)
            for i, group in enumerate(self._groups):
                fighting = False
                for character in group:
                    if character.is_fighting():
                        fighting = True
                        break
                if not fighting:
                    if i == 0:
                        self.features().observe_winner(1)
                    else:
                        self.features().observe_winner(-1)
                    raise CombatEnded("Combat is over")
