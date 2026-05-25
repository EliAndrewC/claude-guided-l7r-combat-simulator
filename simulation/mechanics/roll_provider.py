#!/usr/bin/env python3

#
# roll_provider.py
#
# Alternate roll providers for L7R combat simulations.
#

from abc import ABC, abstractmethod
from typing import Any

from simulation.mechanics.ninja_rolls import NinjaDamageReductionRoll
from simulation.mechanics.roll import DieProvider, InitiativeRoll, Roll


class RollProvider(ABC):
    @abstractmethod
    def die_provider(self) -> Any:
        pass

    @abstractmethod
    def get_damage_reduction_roll(self, rolled: int, kept: int, reduction: int) -> int:
        pass

    @abstractmethod
    def get_damage_roll(self, rolled: int, kept: int) -> int:
        pass

    @abstractmethod
    def get_initiative_roll(self, rolled: int, kept: int) -> list[int]:
        pass

    @abstractmethod
    def get_skill_roll(self, skill: str, rolled: int, kept: int, explode: bool = True) -> int:
        pass

    @abstractmethod
    def get_wound_check_roll(self, rolled: int, kept: int, explode: bool = True) -> int:
        pass

    @abstractmethod
    def set_die_provider(self, die_provider: DieProvider) -> None:
        pass


class DefaultRollProvider(RollProvider):
    def __init__(self, die_provider: Any = None) -> None:
        self._die_provider = die_provider
        self._last_skill_roll: Any = None
        self._last_damage_roll: Any = None
        self._last_wound_check_roll: Any = None
        self._last_initiative_roll: Any = None
        self._last_skill_info: dict[str, Any] | None = None
        self._last_damage_info: dict[str, Any] | None = None
        self._last_wound_check_info: dict[str, Any] | None = None
        self._last_initiative_info: dict[str, Any] | None = None

    def die_provider(self) -> Any:
        return self._die_provider

    def get_damage_reduction_roll(self, rolled: int, kept: int, reduction: int) -> int:
        roll = NinjaDamageReductionRoll(rolled, kept, reduction=reduction, die_provider=self.die_provider())
        result = roll.roll()
        self._last_damage_roll = roll
        self._last_damage_info = {"rolled": rolled, "kept": kept, "dice": list(roll.dice())}
        return result

    def get_damage_roll(self, rolled: int, kept: int) -> int:
        roll = Roll(rolled, kept, die_provider=self.die_provider())
        result = roll.roll()
        self._last_damage_roll = roll
        self._last_damage_info = {"rolled": rolled, "kept": kept, "dice": list(roll.dice())}
        return result

    def get_initiative_roll(self, rolled: int, kept: int) -> list[int]:
        roll = InitiativeRoll(rolled, kept, die_provider=self.die_provider())
        result = roll.roll()
        self._last_initiative_roll = roll
        self._last_initiative_info = {"rolled": rolled, "kept": kept, "all_dice": list(roll.all_dice())}
        return result

    def get_skill_roll(self, skill: str, rolled: int, kept: int, explode: bool = True) -> int:
        roll = Roll(rolled, kept, die_provider=self.die_provider(), explode=explode)
        result = roll.roll()
        self._last_skill_roll = roll
        self._last_skill_info = {"rolled": rolled, "kept": kept, "dice": list(roll.dice())}
        return result

    def get_wound_check_roll(self, rolled: int, kept: int, explode: bool = True) -> int:
        roll = Roll(rolled, kept, die_provider=self.die_provider(), explode=explode)
        result = roll.roll()
        self._last_wound_check_roll = roll
        self._last_wound_check_info = {"rolled": rolled, "kept": kept, "dice": list(roll.dice())}
        return result

    def last_damage_roll(self) -> Any:
        return self._last_damage_roll

    def last_damage_info(self) -> dict[str, Any] | None:
        return self._last_damage_info

    def last_initiative_roll(self) -> Any:
        return self._last_initiative_roll

    def last_initiative_info(self) -> dict[str, Any] | None:
        return self._last_initiative_info

    def last_skill_roll(self) -> Any:
        return self._last_skill_roll

    def last_skill_info(self) -> dict[str, Any] | None:
        return self._last_skill_info

    def last_wound_check_roll(self) -> Any:
        return self._last_wound_check_roll

    def last_wound_check_info(self) -> dict[str, Any] | None:
        return self._last_wound_check_info

    def set_die_provider(self, die_provider: DieProvider) -> None:
        if not isinstance(die_provider, DieProvider):
            raise ValueError("set_die_provider requires DieProvider")
        self._die_provider = die_provider


DEFAULT_ROLL_PROVIDER = DefaultRollProvider()


class CalvinistRollProvider(RollProvider):
    """
    Roll provider whose results are predestined, not random.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[Any]] = {"damage": [], "initiative": [], "wound_check": []}
        self._observed_params: dict[str, list[tuple[int, int]]] = {"damage": [], "initiative": [], "wound_check": []}
        self._last_skill_info: dict[str, Any] | None = None
        self._last_wound_check_info: dict[str, Any] | None = None
        self._last_damage_info: dict[str, Any] | None = None

    def die_provider(self) -> Any:
        return None

    def get_damage_reduction_roll(self, rolled: int, kept: int, reduction: int) -> int:
        if len(self._queues["damage"]) == 0:
            raise IndexError("No roll queued for damage")
        self._observed_params["damage"].append((rolled, kept))
        entry = self._queues["damage"].pop(0)
        result: int = self._pop_entry(entry, "damage", rolled, kept)
        return result

    def get_damage_roll(self, rolled: int, kept: int) -> int:
        if len(self._queues["damage"]) == 0:
            raise IndexError("No roll queued for damage")
        self._observed_params["damage"].append((rolled, kept))
        entry = self._queues["damage"].pop(0)
        result: int = self._pop_entry(entry, "damage", rolled, kept)
        return result

    def get_initiative_roll(self, rolled: int, kept: int) -> list[int]:
        if len(self._queues["initiative"]) == 0:
            raise IndexError("No roll queued for initiative")
        self._observed_params["initiative"].append((rolled, kept))
        result: list[int] = self._queues["initiative"].pop(0)
        return result

    def get_skill_roll(self, skill: str, rolled: int, kept: int, explode: bool = True) -> int:
        if skill not in self._queues.keys():
            raise KeyError("No roll queued for " + skill)
        elif len(self._queues[skill]) == 0:
            raise IndexError("No roll queued for " + skill)
        if skill not in self._observed_params.keys():
            self._observed_params[skill] = []
        self._observed_params[skill].append((rolled, kept))
        entry = self._queues[skill].pop(0)
        result: int = self._pop_entry(entry, "skill", rolled, kept)
        return result

    def get_wound_check_roll(self, rolled: int, kept: int, explode: bool = True) -> int:
        if len(self._queues["wound_check"]) == 0:
            raise IndexError("No roll queued for wound_check")
        self._observed_params["wound_check"].append((rolled, kept))
        entry = self._queues["wound_check"].pop(0)
        result: int = self._pop_entry(entry, "wound_check", rolled, kept)
        return result

    def last_damage_info(self) -> dict[str, Any] | None:
        return self._last_damage_info

    def last_skill_info(self) -> dict[str, Any] | None:
        return self._last_skill_info

    def last_wound_check_info(self) -> dict[str, Any] | None:
        return self._last_wound_check_info

    def pop_observed_params(self, roll_type: str) -> tuple[int, int]:
        return self._observed_params[roll_type].pop(0)

    def put_damage_roll(self, result: int) -> None:
        self._queues["damage"].append(result)

    def put_damage_roll_with_dice(self, result: int, dice: list[int]) -> None:
        self._queues["damage"].append((result, list(dice)))

    def put_initiative_roll(self, result: list[int]) -> None:
        if isinstance(result, list):
            self._queues["initiative"].append(result)
        else:
            raise ValueError("Initiative rolls should be sequences of ints")

    def put_skill_roll(self, skill: str, result: int) -> None:
        if skill in self._queues.keys():
            self._queues[skill].append(result)
        else:
            self._queues[skill] = [result]

    def put_skill_roll_with_dice(self, skill: str, result: int, dice: list[int]) -> None:
        entry = (result, list(dice))
        if skill in self._queues.keys():
            self._queues[skill].append(entry)
        else:
            self._queues[skill] = [entry]

    def put_wound_check_roll(self, result: int) -> None:
        self._queues["wound_check"].append(result)

    def put_wound_check_roll_with_dice(self, result: int, dice: list[int]) -> None:
        self._queues["wound_check"].append((result, list(dice)))

    def set_die_provider(self, die_provider: DieProvider) -> None:
        raise NotImplementedError()

    def _pop_entry(self, entry: Any, roll_type: str, rolled: int, kept: int) -> Any:
        if isinstance(entry, tuple):
            total, dice = entry
        else:
            total = entry
            dice = None
        info = {"rolled": rolled, "kept": kept, "dice": dice}
        if roll_type == "skill":
            self._last_skill_info = info
        elif roll_type == "wound_check":
            self._last_wound_check_info = info
        elif roll_type == "damage":
            self._last_damage_info = info
        return total
