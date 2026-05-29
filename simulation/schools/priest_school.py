#!/usr/bin/env python3

#
# priest_school.py
#
# Implement Priest School.
#
# School Ring: Any non-Void (player choice via school_choices)
# School Knacks: conviction, otherworldliness, pontificate
#
# Special Ability: Has all 10 rituals — no combat effect.
# 1st Dan: Extra rolled on precepts + any one skill (default
#          initiative) + any one combat roll (default wound check).
#          Player choices via school_choices.
# 2nd Dan: Free raise on bragging, precepts, sincerity (ally
#          version deferred — non-combat skills).
# 3rd Dan: Roll X dice ONCE at combat start (X = precepts). Store
#          as floating-bonus pool that persists for the combat.
#          Each die can be spent as a flat bonus to attack/parry/WC
#          /damage rolls.  Spec 025 Q4 BLOCKING fix: previously
#          rolled per-round (over-powered).  Now uses a per-listener
#          ``_pool_rolled`` flag to fire ONCE on the first
#          NewRoundEvent.
# 4th Dan: Ring+1/discount on the chosen school_ring.
#          Contested-roll Honor free raise DEFERRED.
# 5th Dan: DEFERRED.  Conviction-on-allies + action-die lowering
#          for counterattack/parry — entirely ally-buff mechanics
#          moot in 1v1 simulator.
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.floating_bonuses import FloatingBonus
from simulation.schools.base import BaseSchool

PRIEST_POOL_SKILLS = ["attack", "parry", "wound check", "damage",
                      "double attack", "feint", "iaijutsu", "lunge",
                      "counterattack"]


VALID_NON_VOID_RINGS = {"air", "earth", "fire", "water"}
# Combat-roll skill list for the 1st Dan "any one type of combat
# roll" choice (validation set).
VALID_COMBAT_ROLLS = {
    "attack", "counterattack", "double attack", "feint", "iaijutsu",
    "lunge", "damage", "parry", "wound check",
}


class PriestSchool(BaseSchool):
    """rules/04-schools.md "Priest School".

    Accepted school_choices (overrideable via YAML, per
    specs/003-school-choices precedent):

    * ``school_ring`` — str, any non-Void ring ("air", "earth",
      "fire", "water"). Defaults to "water" if unset.
    * ``first_dan_extra_skill`` — str, the "any one skill" the 1st
      Dan grants an extra die on. Defaults to "initiative".
    * ``first_dan_extra_combat`` — str, the "any one type of combat
      roll" the 1st Dan grants an extra die on. Defaults to "wound
      check". Validated against ``VALID_COMBAT_ROLLS``.
    """

    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # All 10 rituals — no combat effect
        pass

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_listener(character, "new_round", PriestNewRoundListener())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # TODO: free raise on contested rolls vs equal/higher skill (self + allies)

    def apply_rank_five_ability(self, character: Any) -> None:
        # TODO: conviction on allies' rolls + refresh each round + lower action dice
        pass

    def extra_rolled(self) -> list[str]:
        # rules/04-schools.md "Priest School: First Dan": "Roll one
        # extra die on precepts, any one skill, and any one type of
        # combat roll."  Spec 025 Q2 fix — precepts is fixed; the
        # two "any one" slots are player choices via school_choices.
        chosen_skill = self.choice("first_dan_extra_skill", "initiative")
        if not isinstance(chosen_skill, str):
            logger.warning(
                f"Priest: invalid 'first_dan_extra_skill' choice "
                f"(expected str; got {chosen_skill!r}). Using default."
            )
            chosen_skill = "initiative"
        chosen_combat = self.choice("first_dan_extra_combat", "wound check")
        if not isinstance(chosen_combat, str) or chosen_combat not in VALID_COMBAT_ROLLS:
            logger.warning(
                f"Priest: invalid 'first_dan_extra_combat' choice "
                f"(expected one of {sorted(VALID_COMBAT_ROLLS)}; got "
                f"{chosen_combat!r}). Using default."
            )
            chosen_combat = "wound check"
        return ["precepts", chosen_skill, chosen_combat]

    def free_raise_skills(self) -> list[str]:
        return ["bragging", "precepts", "sincerity"]

    def name(self) -> str:
        return "Priest School"

    def school_knacks(self) -> list[str]:
        return ["conviction", "otherworldliness", "pontificate"]

    def school_ring(self) -> str:
        # rules/04-schools.md "Priest School: School Ring: Any
        # non-Void".  Player choice via ``school_choices["school_ring"]``,
        # default "water" — Monk/Ide/Ise Zumi precedent.  Spec 025
        # Q1 fix.  The 4th Dan +1 Ring bump in
        # ``apply_school_ring_raise_and_discount`` reads this method,
        # so the choice also redirects the 4th Dan bump.
        default = "water"
        chosen = self.choice("school_ring", default)
        if not isinstance(chosen, str) or chosen not in VALID_NON_VOID_RINGS:
            logger.warning(
                f"Priest: invalid 'school_ring' choice (expected one "
                f"of {sorted(VALID_NON_VOID_RINGS)}; got {chosen!r}). "
                f"Using default."
            )
            chosen = default
        return chosen


class PriestNewRoundListener(Listener):
    """rules/04-schools.md "Priest School: Third Dan":

    "Roll X dice **at the beginning of combat**, where X is equal to
    your precepts skill.  You may swap any of these dice for any
    rolled die on any attack, parry, wound check, or damage roll."

    Spec 025 Q4 BLOCKING fix: previously fired on EVERY
    ``NewRoundEvent`` so the priest accumulated X new floating
    bonuses every round (combat-simulator pre-fix measured 5 dice/
    round at precepts=5 — over-powered).  Now uses a per-listener
    ``_pool_rolled`` flag to roll ONCE at the first NewRoundEvent
    of the combat, then defers to rolling initiative only.

    Q5 swap vs add — DEFERRED: rules say "swap any of these dice
    for any rolled die" (REPLACE).  ``FloatingBonus.bonus`` is ADDED
    to the roll total — different semantics that approximate the
    swap.  Full swap semantics would require engine-level changes.

    The Q6 ally-swap on lower dice is DEFERRED — moot in 1v1.
    """

    def __init__(self) -> None:
        # Per-combat pool initialization flag.  ``_set_school_listener``
        # creates ONE listener instance per character at build time
        # which persists for the character's lifetime — this flag
        # therefore tracks "has the pool been rolled THIS COMBAT"
        # but does not reset between combats (acceptable for the
        # simulator's single-combat usage; multi-combat campaigns
        # are out of scope per Constitution Principle III).
        self._pool_rolled = False

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            if not self._pool_rolled:
                precepts = character.skill("precepts")
                if precepts > 0:
                    for _ in range(precepts):
                        die_value = character.roll_provider().get_skill_roll(
                            "precepts", 1, 1, True,
                        )
                        bonus = FloatingBonus(PRIEST_POOL_SKILLS, die_value)
                        # Trace attribution tag for future renderer work.
                        bonus._priest_3rd_dan_pool_die = True  # type: ignore[attr-defined]
                        character.gain_floating_bonus(bonus)
                self._pool_rolled = True
            yield from ()
