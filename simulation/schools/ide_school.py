#!/usr/bin/env python3

#
# ide_school.py
#
# Implement Ide Diplomat School.
#
# School Ring: Water
# School Knacks: double attack, feint, worldliness
#
# Special Ability: After a feint hits TN, lower target's TN by 10
#                  for the Ide's next attack (even if parried).
# 1st Dan: Extra rolled on wound check, initiative, precepts
# 2nd Dan: Free raise on attack
# 3rd Dan: Spend 1 VP to subtract Xk1 from enemy's attack roll (X = tact skill)
# 4th Dan: Ring+1/discount (+ extra VP per night, no-op in combat)
# 5th Dan: Gain 1 TVP when spending VP (not from 3rd dan tact usage)
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.modifiers import AnyAttackModifier
from simulation.modifier_listeners import ExpireAfterNextAttackByCharacterListener, ExpireAtEndOfRoundListener
from simulation.schools.base import BaseSchool


class IdeDiplomatSchool(BaseSchool):
    """Ide Diplomat School.

    Accepted school_choices (overrideable via YAML, per specs/003-school-choices):
      - first_dan_extra_rolled: list[str] (length 2) of skill names the 1st Dan
        +1-die applies to, alongside the mandatory "precepts". Default:
        ["wound check", "initiative"]. Rules: "Roll one extra die on precepts
        and any two rolls of your choice."
      - second_dan_free_raise: str skill name for the 2nd Dan free raise.
        Default: "attack". Rules: "You get a free raise on any type of roll
        of your choice."
      - school_ring: str, any non-Void ring ("air", "earth", "fire", "water").
        Default: "water". Rules: "School Ring: Any non-Void". The 4th Dan
        Ring+1/discount targets this chosen ring.
    """

    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        self._set_school_listener(character, "attack_succeeded", IdeFeintSucceededListener())
        self._set_school_listener(character, "attack_failed", IdeFeintFailedListener())

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_listener(character, "attack_rolled", IdeTactSubtractListener())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_listener(character, "spend_vp", IdeSpendVPListener())

    def extra_rolled(self) -> list[str]:
        # rules/04-schools.md "Ide Diplomat School: 1st Dan": "Roll one extra
        # die on precepts and any two rolls of your choice."  Precepts is
        # mandatory and is always prepended; the two choice-skills come from
        # the ``first_dan_extra_rolled`` choice, defaulting to
        # ["wound check", "initiative"] (specs/003-school-choices FR-006).
        default: list[str] = ["wound check", "initiative"]
        chosen = self.choice("first_dan_extra_rolled", default)
        # FR-007: validate shape (list[str] of length 2); warn + fallback.
        if not (
            isinstance(chosen, list)
            and len(chosen) == 2
            and all(isinstance(s, str) for s in chosen)
        ):
            logger.warning(
                f"Ide Diplomat: invalid 'first_dan_extra_rolled' choice "
                f"(expected list of 2 skill names; got {chosen!r}). Using default.",
            )
            chosen = default
        return ["precepts"] + list(chosen)

    def free_raise_skills(self) -> list[str]:
        # rules/04-schools.md "Ide Diplomat School: 2nd Dan": "You get a free
        # raise on any type of roll of your choice."  Default is ``attack``
        # (the Ide's original hardcoded default; distinct from Ishi's
        # ``precepts``).  The ``second_dan_free_raise`` choice overrides per
        # specs/003-school-choices/spec.md FR-006.
        default = "attack"
        chosen = self.choice("second_dan_free_raise", default)
        # FR-007: validate shape (str); warn + fallback.
        if not isinstance(chosen, str):
            logger.warning(
                f"Ide Diplomat: invalid 'second_dan_free_raise' choice "
                f"(expected string skill name; got {chosen!r}). Using default.",
            )
            chosen = default
        return [chosen]

    def name(self) -> str:
        return "Ide Diplomat School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "feint", "worldliness"]

    def school_ring(self) -> str:
        # rules/04-schools.md "Ide Diplomat School: School Ring: Any non-Void".
        # The ``school_ring`` choice overrides the default ``water`` per
        # specs/003-school-choices/spec.md FR-006.  The 4th Dan Ring+1/discount
        # in ``apply_school_ring_raise_and_discount`` reads this method, so
        # choosing a non-default ring redirects the 4th Dan bump as well
        # (verified by test_fourth_dan_raises_chosen_ring).
        default = "water"
        valid_rings = {"air", "earth", "fire", "water"}
        chosen = self.choice("school_ring", default)
        # FR-007: validate (must be a non-Void ring); warn + fallback.
        if not isinstance(chosen, str) or chosen not in valid_rings:
            logger.warning(
                f"Ide Diplomat: invalid 'school_ring' choice "
                f"(expected one of {sorted(valid_rings)}; got {chosen!r}). "
                f"Using default.",
            )
            chosen = default
        return chosen


class IdeFeintSucceededListener(Listener):
    """
    After a successful feint, lower target's TN by 10 for the Ide's next attack.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackSucceededEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    target = event.action.target()
                    modifier = AnyAttackModifier(character, target, -10)
                    attack_listener = ExpireAfterNextAttackByCharacterListener(character)
                    end_of_round_listener = ExpireAtEndOfRoundListener()
                    modifier.register_listener("attack_failed", attack_listener)
                    modifier.register_listener("attack_succeeded", attack_listener)
                    modifier.register_listener("end_of_round", end_of_round_listener)
                    yield events.AddModifierEvent(target, modifier)


class IdeFeintFailedListener(Listener):
    """
    Even on a failed feint (hit TN but parried), lower target's TN by 10.
    AttackFailedEvent fires both when missing TN and when parried.
    We apply the bonus regardless since the rules say "after a feint hits TN".
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackFailedEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    # Only apply if the feint was parried (hit TN but was blocked)
                    if event.action.parried():
                        target = event.action.target()
                        modifier = AnyAttackModifier(character, target, -10)
                        attack_listener = ExpireAfterNextAttackByCharacterListener(character)
                        end_of_round_listener = ExpireAtEndOfRoundListener()
                        modifier.register_listener("attack_failed", attack_listener)
                        modifier.register_listener("attack_succeeded", attack_listener)
                        modifier.register_listener("end_of_round", end_of_round_listener)
                        yield events.AddModifierEvent(target, modifier)


class IdeTactSubtractListener(Listener):
    """
    3rd Dan: When this character is the target of an attack, spend 1 VP
    to roll Xk1 (X = tact skill) and subtract from attacker's roll.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackRolledEvent):
            if event.action.target() == character:
                tact = character.skill("tact")
                if tact > 0 and character.vp() >= 1:
                    yield events.SpendVoidPointsEvent(character, "tact", 1)
                    penalty = character.roll_provider().get_skill_roll("tact", tact, 1, True)
                    new_roll = max(0, event.roll - penalty)
                    event.action.set_skill_roll(new_roll)
                    yield events.AttackRolledEvent(event.action, new_roll)
            elif character != event.action.subject():
                # Default behavior: observe and consider interrupt
                character.knowledge().observe_attack_roll(event.action.subject(), event.roll)
                yield from character.interrupt_strategy().recommend(character, event, context)


class IdeSpendVPListener(Listener):
    """
    5th Dan: Gain 1 TVP when spending VP (not from 3rd dan tact usage).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.SpendVoidPointsEvent):
            if event.subject == character:
                character.spend_vp(event.amount)
                if event.skill != "tact":
                    yield events.GainTemporaryVoidPointsEvent(character, 1)
