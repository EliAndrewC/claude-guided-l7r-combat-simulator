#!/usr/bin/env python3

#
# void_point_manager.py
#
# Class to help characters reserve Void Points for future use.
#

from typing import Any

from simulation.mechanics.skills import EXTENDED_SKILLS


class VoidPointManager:
    """
    Class to reserve Void Points for future use for a specific skill.

    The usual reason to do this is when a character keeps a large
    number of Light Wounds because they can handle a future Wound
    Check by spending Void Points. This class makes it possible to
    reserve Void Points for that future Wound Check, so the character
    won't spend them on something else like an attack roll or a
    special ability.
    """

    def __init__(self, character: Any) -> None:
        self._character = character
        self._reservations: dict[str, int] = {}

    def cancel(self, skill: str) -> None:
        """
        cancel(skill)
          skill (str): skill for which the reservation is being cancelled

        Removes any existing reservations for the indicated skill.
        """
        if not isinstance(skill, str):
            raise ValueError("cancel skill must be str")
        if skill not in EXTENDED_SKILLS:
            raise ValueError(f"Invalid skill: {skill}")
        self._reservations.pop(skill)

    def clear(self) -> None:
        """
        clear()

        Clears all reservations.
        """
        self._reservations.clear()

    def reserve(self, skill: str, vp: int) -> None:
        """
        reserve(skill, vp)
          skill (str): skill that the Void Points will be used for
          vp (int): number of Void Points to reserve

        Reserves void points for future use for the chosen skill.
        Reservations are not additive, so a new reservation overwrites
        any previous reservation for the same skill.
        """
        if not isinstance(skill, str):
            raise ValueError("reserve skill must be str")
        if skill not in EXTENDED_SKILLS:
            raise ValueError(f"Invalid skill: {skill}")
        if not isinstance(vp, int):
            raise ValueError("reserve vp must be int")
        self._reservations[skill] = vp

    def reserved(self, skill: str) -> int:
        """
        reserved(skill) -> int
          skill (str): skill of interest

        Returns the number of Void Points reserved for use for the given skill.
        """
        if not isinstance(skill, str):
            raise ValueError("reserved skill must be str")
        if skill not in EXTENDED_SKILLS:
            raise ValueError(f"Invalid skill: {skill}")
        return self._reservations.get(skill, 0)

    def vp(self, skill: str) -> int:
        """
        vp(skill) -> int
          skill (str): skill of interest

        Returns the number of Void Points the character has available
        for the given skill: the character's available VP, minus any VP
        reserved for other skills.
        """
        if not isinstance(skill, str):
            raise ValueError("reserve skill must be str")
        if skill not in EXTENDED_SKILLS:
            raise ValueError(f"Invalid skill: {skill}")
        available = self._character.vp() - sum([v for (k, v) in self._reservations.items() if k != skill])
        result: int = max(available, 0)
        return result
