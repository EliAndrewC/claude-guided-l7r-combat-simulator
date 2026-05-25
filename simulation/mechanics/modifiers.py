#!/usr/bin/env python3

#
# modifiers.py
#
# Implement modifiers (flat bonuses or penalties to rolls) that can expire in response to events.
#

import uuid
from collections.abc import Iterator
from typing import Any

from simulation.mechanics.skills import ATTACK_SKILLS


class Modifier:
    """
    Class for modifiers (bonuses or penalties) that are specific to
    a skill or a specific target, or that have an expiration.
    """

    def __init__(self, subject: Any, target: Any, skills: str | list[str], adjustment: int) -> None:
        self._id = uuid.uuid4().hex
        self._subject = subject
        self._target = target
        if isinstance(skills, str):
            self._skills: list[str] = [skills]
        elif isinstance(skills, list):
            for skill in skills:
                if not isinstance(skill, str):
                    raise ValueError("Modifier skills parameter must be str or list of str")
            self._skills = skills
        else:
            raise ValueError("Modifier skills parameter must be str or list of str")
        self._adjustment = adjustment
        self._listeners: dict[str, Any] = {}

    def apply(self, target: Any, skill: str) -> int:
        if skill in self.skills():
            if target is None or self.target() is None or self.target() == target:
                return self.adjustment()
        return 0

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if event.name in self._listeners.keys():
            yield from self._listeners[event.name].handle(character, event, self, context)

    def adjustment(self) -> int:
        return self._adjustment

    def register_listener(self, event_name: str, listener: Any) -> None:
        if not isinstance(event_name, str):
            raise ValueError("Modifier register_listener event_name parameter must be str")
        self._listeners[event_name] = listener

    def skills(self) -> list[str]:
        return self._skills

    def subject(self) -> Any:
        return self._subject

    def target(self) -> Any:
        return self._target

    def __eq__(self, other: Any) -> bool:
        if self is other:
            return True
        elif not isinstance(other, Modifier):
            return False
        else:
            return self._id == other._id


class AnyAttackModifier(Modifier):
    """
    A Modifier that applies to any attack skill.
    """

    def __init__(self, subject: Any, target: Any, adjustment: int) -> None:
        super().__init__(subject, target, ATTACK_SKILLS, adjustment)


class FreeRaise(Modifier):
    """
    A modifier that grants a +5 bonus to a skill, does not have restrictions on the target, and never expires.
    """

    def __init__(self, subject: Any, skill: str) -> None:
        super().__init__(subject, None, skill, 5)

    def apply(self, target: Any, skill: str) -> int:
        if skill in self.skills():
            return 5
        return 0

    def register_listener(self, event_name: str, listener: Any) -> None:
        pass
