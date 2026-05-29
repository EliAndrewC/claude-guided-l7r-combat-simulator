#!/usr/bin/env python3

#
# courtier_school.py
#
# Implement Courtier School.
#
# School Ring: Air
# School Knacks: discern honor, oppose social, worldliness
#
# Special Ability: Add Air to all attack and damage rolls.
# 1st Dan: Extra rolled on tact, manipulation, wound check
# 2nd Dan: Free raise on manipulation
# 3rd Dan: AP system — ap_base_skill = "tact", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; TVP on successful attack (once per target per fight)
# 5th Dan: Add Air to all TN and contested rolls (stacks with special for attack)
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.schools.base import BaseSchool


class CourtierSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return "tact"

    def ap_skills(self) -> list[str]:
        return ["attack", "wound check"]

    def apply_special_ability(self, character: Any) -> None:
        self._set_school_roll_parameter_provider(character, CourtierRollParameterProvider())

    def apply_rank_three_ability(self, character: Any) -> None:
        self.apply_ap(character)

    def apply_rank_four_ability(self, character: Any) -> None:
        # Spec 026 Q2 MINOR fix: rules say "once per target per
        # **conversation or fight**" — the once-per-target set MUST
        # reset between fights.  Build a paired listener: the
        # AttackSucceededListener tracks per-target firing; the
        # NewRoundListener wraps both the engine default
        # (roll_initiative + status) AND a round==1 reset of the
        # AttackSucceededListener's set.  Single-combat simulators
        # never re-use the same character across fights so this is
        # an edge-case guard, but it's the rules-correct shape.
        self.apply_school_ring_raise_and_discount(character)
        attack_listener = CourtierAttackSucceededListener()
        self._set_school_listener(character, "attack_succeeded", attack_listener)
        self._set_school_listener(
            character, "new_round",
            CourtierNewRoundListener(attack_listener),
        )

    def apply_rank_five_ability(self, character: Any) -> None:
        # Upgrade provider to 5th Dan version which adds Air to ALL TN/contested rolls
        self._set_school_roll_parameter_provider(character, CourtierFifthDanRollParameterProvider())

    def extra_rolled(self) -> list[str]:
        return ["manipulation", "tact", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["manipulation"]

    def name(self) -> str:
        return "Courtier School"

    def school_knacks(self) -> list[str]:
        return ["discern honor", "oppose social", "worldliness"]

    def school_ring(self) -> str:
        return "air"


class CourtierRollParameterProvider(DefaultRollParameterProvider):
    """Add Air to all attack and damage roll modifiers (special ability)."""

    def get_skill_roll_params(self, character: Any, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        if skill in ATTACK_SKILLS:
            modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)

    def get_damage_roll_params(self, character: Any, target: Any, skill: str, attack_extra_rolled: int, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_damage_roll_params(character, target, skill, attack_extra_rolled, vp)
        modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)


class CourtierFifthDanRollParameterProvider(CourtierRollParameterProvider):
    """rules/04-schools.md "Courtier School: Fifth Dan":

    "Add your Air to all TN and contested rolls.  This stacks with
    your Special Ability for attack rolls."

    Spec 026 Q3 MINOR refactor: previously had an ``if skill not in
    ATTACK_SKILLS`` branch whose ``else`` arm also added Air —
    behavior was unconditional, just split awkwardly.  Collapsed
    to a single unconditional add.

    Q4 interpretation (deferred): "all TN and contested rolls" is
    read as "all skill rolls" (every roll has a TN).  The
    alternative reading — that the courtier's TN-to-be-hit stat
    gets +Air — is not implemented.  Defensible because the
    rules-text clause "stacks with Special Ability for attack
    rolls" only makes sense if 5th Dan affects attack rolls (the
    skill-rolls interpretation).
    """

    def get_skill_roll_params(self, character: Any, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        # Q3 refactor: 5th Dan adds Air to every skill roll
        # unconditionally.  On attack rolls this stacks with the
        # Special Ability's +Air (super already applied it), so
        # attack rolls get +2*Air total.
        modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character: Any, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_wound_check_roll_params(character, vp)
        modifier += character.ring("air")
        return normalize_roll_params(rolled, kept, modifier)


class CourtierAttackSucceededListener(Listener):
    """rules/04-schools.md "Courtier School: Fourth Dan":

    "Once per target per conversation or fight, you get a temporary
    void point after a successful attack or manipulation roll."

    Tracks per-target firing in ``_targets_triggered``.  Reset
    between fights via ``CourtierNewRoundListener`` (spec 026 Q2
    fix).
    """

    def __init__(self) -> None:
        self._targets_triggered: set[Any] = set()

    def reset(self) -> None:
        """Reset the once-per-target set — called at start of each
        new combat by ``CourtierNewRoundListener``."""
        self._targets_triggered = set()

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackSucceededEvent):
            if event.action.subject() == character:
                target_id = event.action.target().character_id()
                if target_id not in self._targets_triggered:
                    self._targets_triggered.add(target_id)
                    tvp_event = events.GainTemporaryVoidPointsEvent(character, 1)
                    # Trace attribution tag for future renderer work.
                    tvp_event._courtier_4th_dan = True  # type: ignore[attr-defined]
                    yield tvp_event
                    return
        yield from ()


class CourtierNewRoundListener(Listener):
    """Spec 026 Q2 fix: at the start of each fight (round 1), reset
    the 4th Dan once-per-target set so the TVP gain fires anew
    against each target in each fight (rules-text "once per target
    per conversation or **fight**").

    Replaces the engine's default ``new_round`` listener slot so it
    owns the new-round flow: ``roll_initiative`` for the character,
    AND reset the 4th Dan tracker on round 1 only.
    """

    def __init__(self, attack_listener: CourtierAttackSucceededListener) -> None:
        self._attack_listener = attack_listener

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            if event.round == 1:
                self._attack_listener.reset()
        yield from ()
