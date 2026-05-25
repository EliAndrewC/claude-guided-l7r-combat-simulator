#!/usr/bin/env python3

#
# roll.py
#
# Class to roll dice using L7R homebrew rules.
#

import random
from abc import ABC, abstractmethod

from simulation.mechanics.roll_params import normalize_roll_params


class DieProvider(ABC):
    """
    Simulated dice for the L7R combat simulator.
    """

    @abstractmethod
    def roll_die(self, faces: int = 10, explode: bool = True) -> int:
        pass


class DefaultDieProvider(DieProvider):
    def roll_die(self, faces: int = 10, explode: bool = True) -> int:
        result = random.randint(1, faces)
        if explode and result == faces:
            return result + self.roll_die(faces, explode)
        else:
            return result


# singleton DefaultDieProvider instance
DEFAULT_DIE_PROVIDER = DefaultDieProvider()


class CalvinistDice(DieProvider):
    """
    Die source whose results are predestined, not random.
    """

    def __init__(self) -> None:
        self._dice: list[int] = []

    def clear(self) -> None:
        self._dice.clear()

    def extend(self, dice: list[int]) -> None:
        self._dice.extend(dice)

    def append(self, die: int) -> None:
        self._dice.append(die)

    def roll_die(self, faces: int = 10, explode: bool = True) -> int:
        die = self._dice.pop(0)
        if explode and die == faces:
            return die + self.roll_die(faces, explode)
        else:
            return die

    def __len__(self) -> int:
        return len(self._dice)


class BaseRoll:
    def __init__(self, rolled: int, kept: int, faces: int = 10, explode: bool = True, die_provider: DieProvider | None = None) -> None:
        # normalize roll parameters
        (self._rolled, self._kept, self._bonus) = normalize_roll_params(rolled, kept)
        # set die faces
        self._faces = faces
        # set exploding behavior
        self._explode = explode
        # set die source
        if die_provider is not None:
            if not isinstance(die_provider, DieProvider):
                raise ValueError("die_provider must be a DieProvider")
            self._die_provider: DieProvider = die_provider
        else:
            self._die_provider = DEFAULT_DIE_PROVIDER

    def die_provider(self) -> DieProvider:
        return self._die_provider

    def explode(self) -> bool:
        return self._explode

    def faces(self) -> int:
        return self._faces

    def roll_die(self, faces: int = 10, explode: bool = True) -> int:
        return self.die_provider().roll_die(faces, explode)

    def set_die_provider(self, die_provider: DieProvider) -> None:
        if not isinstance(die_provider, DieProvider):
            raise ValueError("set_die_provider requires a DieProvider")
        self._die_provider = die_provider


class Roll(BaseRoll):
    def __init__(self, rolled: int, kept: int, faces: int = 10, explode: bool = True, die_provider: DieProvider | None = None) -> None:
        super().__init__(rolled, kept, faces, explode, die_provider)
        self._dice: list[int] = []

    def dice(self) -> list[int]:
        return self._dice

    def roll(self) -> int:
        self._dice = [self.die_provider().roll_die(faces=self.faces(), explode=self.explode()) for n in range(self._rolled)]
        self._dice.sort(reverse=True)
        return sum(self._dice[: self._kept]) + self._bonus


class InitiativeRoll(BaseRoll):
    def __init__(self, rolled: int, kept: int, faces: int = 10, die_provider: DieProvider | None = None) -> None:
        super().__init__(rolled, kept, faces, False, die_provider)
        self._all_dice: list[int] = []

    def all_dice(self) -> list[int]:
        return self._all_dice

    def roll(self) -> list[int]:
        self._all_dice = sorted([self.roll_die(faces=self.faces(), explode=False) for n in range(self._rolled)])
        return self._all_dice[: self._kept]
