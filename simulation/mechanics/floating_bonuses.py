#!/usr/bin/env python3

#
# floating_bonuses.py
#
# A "floating bonus" is a bonus that a character may spend after
# making a roll to improve the roll.
#
# They are usually specific to a certain skill or group of skills.
#
# Unlike modifiers, they are a resource that a character uses at
# their discretion.
#

from typing import Any

from simulation.mechanics.skills import ATTACK_SKILLS


class FloatingBonus:
    """A floating bonus that may be applied to a roll after the fact.

    ``source`` is an optional human-readable attribution (e.g.
    ``"Akodo 3rd Dan"``) carried for trace observability per
    Constitution Principle VII.  When set, the user-facing combat
    trace can render the consumption with the source's name; when
    ``None``, the formatter falls back to a generic rendering.
    """

    def __init__(
        self,
        skills: str | list[str],
        bonus: int,
        source: str | None = None,
    ) -> None:
        if isinstance(skills, str):
            self._skills = [skills]
        elif isinstance(skills, list):
            for skill in skills:
                if not isinstance(skill, str):
                    raise ValueError("FloatingBonus skills must be str or list of str")
            self._skills = skills
        else:
            raise ValueError("FloatingBonus skills must be str or list of str")
        self._bonus = bonus
        self._source = source

    def bonus(self) -> int:
        return self._bonus

    def source(self) -> str | None:
        return self._source

    def is_applicable(self, skill: str) -> bool:
        return skill in self._skills

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        if not isinstance(other, FloatingBonus):
            return False
        return self.bonus() == other.bonus() and self._skills == other._skills

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, FloatingBonus):
            raise NotImplementedError("Cannot compare FloatingBonus to another type of object")
        if self is other:
            return False
        return self.bonus() < other.bonus()


class AnyAttackFloatingBonus(FloatingBonus):
    """
    A floating bonus that may be applied to any attack.

    Used by the Akodo and Bayushi schools.
    """

    def __init__(self, bonus: int, source: str | None = None) -> None:
        super().__init__(ATTACK_SKILLS, bonus, source=source)


class WoundCheckFloatingBonus(FloatingBonus):
    """
    A floating bonus that may be applied to wound checks.

    Used by the Isawa and Shinjo schools.
    """

    def __init__(self, bonus: int, source: str | None = None) -> None:
        super().__init__("wound check", bonus, source=source)
