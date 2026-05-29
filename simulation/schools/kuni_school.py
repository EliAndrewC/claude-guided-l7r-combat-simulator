#!/usr/bin/env python3

#
# kuni_school.py
#
# Implement Kuni Witch Hunter School.
#
# School Ring: Earth
# School Knacks: detect taint, iaijutsu, presence
#
# Special Ability: Extra 1k1 on wound checks (Taint=0 is always true
#                  in simulator).  Spec 020 Q1 fix — +1 rolled AND
#                  +1 kept (previously only +1 kept).
# 1st Dan: Extra rolled on damage, interrogation, wound check.
#          Spec 020 Q2 fix — added missing "interrogation".
# 2nd Dan: Free raise on interrogation (no-op in combat).
# 3rd Dan: AP system — ap_base_skill = "investigation",
#          ap_skills = ["attack", "wound check"].  Also installs
#          WoundCheckStrategy04 per strategy-designer (the deep WC
#          pool with AP raises calls for an aggressive threshold).
# 4th Dan: Ring+1/discount; extra action die DEFERRED (needs
#          per-die usage restrictions infrastructure).
# 5th Dan: After WC succeeds, reflect LW on attacker AND take half
#          that amount as backlash on the Kuni (spec 020 Q4 fix —
#          previously the Kuni took NO backlash, over-powering the
#          ability).
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.schools.base import BaseSchool
from simulation.strategies.base import WoundCheckStrategy04


class KuniWitchHunterSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return "investigation"

    def ap_skills(self) -> list[str]:
        return ["attack", "wound check"]

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Kuni Witch Hunter School: Special
        # Ability": "Roll an extra (X+1)k(X+1) on wound checks, where
        # X is the Shadowlands Taint of the attacker".
        #
        # Taint=0 is always true in the simulator → X=0 → 1k1 = +1
        # rolled AND +1 kept.  Spec 020 Q1 BLOCKING fix: the previous
        # skeleton only added +1 kept, missing the +1 rolled.
        self._set_school_extra_rolled(character, "wound check", 1)
        self._set_school_extra_kept(character, "wound check", 1)

    def apply_rank_one_ability(self, character: Any) -> None:
        # Standard 1st Dan: extra rolled on damage, wound check
        super().apply_rank_one_ability(character)
        # The special ability already adds +1 kept to wound check.
        # The 1st Dan extra_rolled for wound check stacks with the special.

    def apply_rank_three_ability(self, character: Any) -> None:
        self.apply_ap(character)
        # rules/04-schools.md Kuni 3rd Dan grants 2X AP raises usable
        # on attack and WC rolls (X = investigation skill).  The
        # default WoundCheckStrategy (0.6 threshold) under-utilizes
        # this deep AP pool.  ``WoundCheckStrategy04`` (0.4 threshold)
        # spends AP raises more aggressively on WCs, matching the
        # school's WC-tank identity (Hida/Otaku/Shiba/Shinjo/Daidoji
        # precedent).  Spec 020 strategy-designer recommendation.
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # TODO: extra action die restricted to non-Tainted targets (useless without Taint system)

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_listener(character, "wound_check_succeeded", KuniWoundCheckSucceededListener())

    def extra_rolled(self) -> list[str]:
        # rules/04-schools.md "Kuni Witch Hunter School: First Dan":
        # "Roll one extra die on damage, interrogation, and wound
        # checks."  Spec 020 Q2 BLOCKING fix: skeleton previously
        # returned ``["damage", "wound check"]``, omitting the
        # rules-text "interrogation" skill.
        return ["damage", "interrogation", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["interrogation"]

    def name(self) -> str:
        return "Kuni Witch Hunter School"

    def school_knacks(self) -> list[str]:
        return ["detect taint", "iaijutsu", "presence"]

    def school_ring(self) -> str:
        return "earth"


class KuniWoundCheckSucceededListener(Listener):
    """rules/04-schools.md "Kuni Witch Hunter School: Fifth Dan":

    "After you take light wounds and resolve your wound check, you
    may choose to inflict that number of light wounds on the opponent
    who dealt them and take half that amount yourself.  If the
    opponent has the Shadowlands Taint, then you may also use an
    attack in the current phase to add to that damage."

    Spec 020 Q4 BLOCKING fix: the skeleton reflected the FULL LW
    amount to the attacker but the Kuni took NO backlash, making the
    ability strictly over-powered.  Now also emits a half-damage
    ``LightWoundsDamageEvent`` from the attacker to the Kuni.

    Q5 deferral: the "may choose" strategic gate is DEFERRED —
    listener fires unconditionally on every successful WC with
    damage > 0.  The reflection IS the school's signature mechanic;
    gating it suppresses identity.

    Tainted-attacker bonus attack: OUT OF SCOPE (no Taint system).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.WoundCheckSucceededEvent):
            if event.subject == character:
                # Spec 020 mirror anti-recursion gate (Principle IX):
                # if this WC is itself the result of a reflection
                # from a previous Kuni's listener, skip reflection to
                # break the infinite Kuni-vs-Kuni reflection chain
                # (mirror combat seeds 4 + 5 hit RecursionError without
                # this gate).  Marker is set on the attacker by the
                # previous Kuni's listener before yielding the
                # reflect_lw event.
                if getattr(character, "_kuni_in_reflection_chain", False):
                    character._kuni_in_reflection_chain = False
                    yield from character.light_wounds_strategy().recommend(character, event, context)
                    return
                damage = event.damage
                if damage > 0:
                    # Mark the attacker so their WC-success listener
                    # (if they're also a Kuni 5th Dan) sees the
                    # reflection-chain flag and skips re-reflection.
                    event.attacker._kuni_in_reflection_chain = True
                    # Reflect LW to the attacker.
                    reflect = events.LightWoundsDamageEvent(character, event.attacker, damage)
                    reflect._kuni_5th_dan_reflection = True  # type: ignore[attr-defined]
                    yield reflect
                    # Take half that amount as backlash (rounded
                    # down) — spec 020 Q4 fix.
                    backlash_damage = damage // 2
                    if backlash_damage > 0:
                        backlash = events.LightWoundsDamageEvent(
                            event.attacker, character, backlash_damage,
                        )
                        backlash._kuni_5th_dan_backlash = True  # type: ignore[attr-defined]
                        yield backlash
                # Continue with normal wound check succeeded
                # behavior (keep LW decision).
                yield from character.light_wounds_strategy().recommend(character, event, context)
