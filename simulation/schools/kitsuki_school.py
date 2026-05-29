#!/usr/bin/env python3

#
# kitsuki_school.py
#
# Implement Kitsuki Magistrate School.
#
# School Ring: Water
# School Knacks: discern honor, iaijutsu, presence
#
# Special Ability: Add 2*Water to all attack rolls.
# 1st Dan: Extra rolled on investigation, interrogation, wound check
# 2nd Dan: Free raise on interrogation
# 3rd Dan: AP system — ap_base_skill = "investigation", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; know Void, parry, and phase of next action (knowledge)
# 5th Dan: Reduce Air, Fire, Water of chosen characters by 1.
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.schools.base import BaseSchool
from simulation.strategies.base import NeverParryStrategy, WoundCheckStrategy04


class KitsukiMagistrateSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return "investigation"

    def ap_skills(self) -> list[str]:
        return ["attack", "wound check"]

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Kitsuki Magistrate School: Special Ability":
        # "you add twice your Water to all attack rolls."
        #
        # Identity bindings (spec 030, strategy-designer):
        # - ``NeverParryStrategy`` — the SA does not boost parry and
        #   the school lacks a parry-favoring knack; every action is
        #   better spent carrying the +2*Water hammer than burned on
        #   defense. The 5th Dan ring-debuff carries the defensive
        #   side instead.
        self._set_school_roll_parameter_provider(character, KitsukiRollParameterProvider())
        self._set_school_strategy(character, "parry", NeverParryStrategy())

    def apply_rank_three_ability(self, character: Any) -> None:
        # ``WoundCheckStrategy04`` (0.4 confidence threshold) — 3rd Dan
        # AP raises feed into wound checks, so the structurally larger
        # WC pool justifies an earlier VP-spend threshold (vs the
        # engine default of 0.6).
        self.apply_ap(character)
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # TODO: automatically know Void, parry, and phase of each character's next action

    def apply_rank_five_ability(self, character: Any) -> None:
        # Reduce Air, Fire, Water of all opponents by 1 on the first round.
        existing_listener = character._listeners.get("new_round")
        self._set_school_listener(
            character,
            "new_round",
            KitsukiFifthDanNewRoundListener(existing_listener),
        )

    def extra_rolled(self) -> list[str]:
        return ["interrogation", "investigation", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["interrogation"]

    def name(self) -> str:
        return "Kitsuki Magistrate School"

    def school_knacks(self) -> list[str]:
        return ["discern honor", "iaijutsu", "presence"]

    def school_ring(self) -> str:
        return "water"


class KitsukiRollParameterProvider(DefaultRollParameterProvider):
    """Add 2*Water to all attack roll modifiers."""

    def get_skill_roll_params(self, character: Any, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        if skill in ATTACK_SKILLS:
            modifier += 2 * character.ring("water")
        return normalize_roll_params(rolled, kept, modifier)


class KitsukiFifthDanNewRoundListener(Listener):
    """5th Dan: On the first round of combat, reduce a single chosen
    opponent's Air, Fire, and Water rings by 1 (minimum 1).

    Rules text (spec 030): "Your presence is so overwhelming that the
    Air, Fire and Water rings of chosen characters are reduced by one.
    You may do this to any one character... it does not stack with
    other Kitsuki Magistrates targeting the same character."

    Implementation choices (spec 030 Q3/Q4):
    - Target selection: highest-XP opponent that has not already been
      reduced by a Kitsuki. Ties broken by first-encountered (groups
      then within-group iteration order) for determinism. The single-
      target case is the rules floor; the multi-target XP-budget
      branch is an optimization deferred for now.
    - Stacking guard: a ``_kitsuki_5th_dan_applied`` flag is stamped on
      the target; if the highest-XP candidate already carries the flag,
      this Kitsuki falls through to the next-highest unflagged opponent
      (per rules-auditor: do not silently no-op, re-run target select).

    Wraps an existing ``new_round`` listener so initiative is still rolled.
    """

    def __init__(self, wrapped_listener: Any) -> None:
        self._wrapped = wrapped_listener
        self._applied = False

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if self._wrapped is not None:
            yield from self._wrapped.handle(character, event, context)
        else:  # pragma: no cover  # defensive: an unwrapped instance never reaches play; school always wraps the existing new_round listener
            if isinstance(event, events.NewRoundEvent):
                character.roll_initiative()
                yield from ()

        if isinstance(event, events.NewRoundEvent) and not self._applied:
            self._applied = True
            target = self._select_target(character, context)
            if target is None:  # pragma: no cover  # defensive: combat always has at least one opponent
                return
            target._kitsuki_5th_dan_applied = True
            for ring_name in ("air", "fire", "water"):
                current = target.ring(ring_name)
                target.set_ring(ring_name, max(1, current - 1))
            logger.info(
                f"{character.name()} (Kitsuki 5th Dan) reduces "
                f"{target.name()}'s Air, Fire, and Water by 1"
            )

    @staticmethod
    def _select_target(character: Any, context: Any) -> Any:
        """Return the highest-XP opponent not already targeted by a Kitsuki.

        Deterministic tiebreak: first encountered in ``context.characters()``.
        Returns ``None`` if no eligible target exists.
        """
        kitsuki_group = character.group()
        eligible: list[Any] = []
        for other in context.characters():
            if other in kitsuki_group:
                continue
            if getattr(other, "_kitsuki_5th_dan_applied", False):
                continue
            eligible.append(other)
        if not eligible:
            return None
        # max() with key= preserves insertion order on ties.
        return max(eligible, key=lambda c: getattr(c, "xp", lambda: 0)())
