#!/usr/bin/env python3

#
# ise_zumi_school.py
#
# Implement Togashi Ise Zumi School.
#
# School Ring: Void
# School Knacks: athletics, conviction, dragon tattoo
#
# Special Ability: Roll extra action dice per round (1 or 3, athletics-only).
#   Simplified: add 1 extra action die each round (Q1/Q2 DEFERRED — the
#   1-or-3 choice and athletics-only restriction are meaningless in a
#   simulator without combat athletics actions).
# 1st Dan: Extra rolled on athletics, initiative, and wound checks.
#   Spec 024 Q3 BLOCKING fix — skeleton previously returned
#   ["attack", "parry", "athletics"] which omitted initiative and WC
#   and included attack/parry (NOT in the rules clause).
# 2nd Dan: Free raise on athletics
# 3rd Dan: 4X daily free raises for athletics (X = precepts). Max X per roll.
#   Uses AP system with 4× multiplier, ap_base_skill = "precepts", ap_skills = ["athletics"]
# 4th Dan: Raise current and maximum rank of any Ring by 1 + discount.
#   Spec 024 Q4 fix — school_choices["school_ring"] (Monk/Ide precedent;
#   "any Ring" per rules text includes Void).
#   Contested-roll reroll DEFERRED (rarely encountered in combat).
# 5th Dan: Spend 1 VP to heal 2 SW after a wound check failure.
#   ("at any time" Q6 DEFERRED to a proactive-heal strategy follow-up.)
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.log import logger
from simulation.schools.base import BaseSchool


class TogashiIseZumiSchool(BaseSchool):
    def __init__(self) -> None:
        super().__init__()
        self._ap_base_skill = "precepts"
        self._ap_skills = ["athletics"]

    def ap_base_skill(self) -> str | None:
        return "precepts"

    def ap_skills(self) -> list[str]:
        return ["athletics"]

    def apply_special_ability(self, character: Any) -> None:
        self._set_school_listener(character, "new_round", IseZumiNewRoundListener())

    def apply_rank_three_ability(self, character: Any) -> None:
        self.apply_ap(character)
        character.set_ap_multiplier(4)

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # Contested roll reroll is a social ability, not applicable in combat simulation

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_listener(character, "wound_check_failed", IseZumiWoundCheckFailedListener())

    def extra_rolled(self) -> list[str]:
        # rules/04-schools.md "Togashi Ise Zumi School: First Dan":
        # "Roll one extra die on athletics, initiative, and wound
        # checks."  Spec 024 Q3 BLOCKING fix — the previous skeleton
        # returned ``["attack", "parry", "athletics"]`` which omitted
        # initiative and wound check and included attack/parry
        # (NOT in the rules clause).
        return ["athletics", "initiative", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["athletics"]

    def name(self) -> str:
        return "Togashi Ise Zumi School"

    def school_knacks(self) -> list[str]:
        return ["athletics", "conviction", "dragon tattoo"]

    def school_ring(self) -> str:
        # rules/04-schools.md "Togashi Ise Zumi School: School Ring: Void"
        # — the BASE school ring is Void.
        #
        # 4th Dan: "Raise the current and maximum rank of any Ring
        # by 1.  Raising that Ring now costs 5 fewer XP."  The
        # ``apply_school_ring_raise_and_discount`` helper reads
        # ``school_ring()`` for the 4th Dan bump target.  Per the
        # rules-text "any Ring", the choice MAY be Void.  Apply
        # ``school_choices["school_ring"]`` per the Monk/Ide
        # precedent — spec 024 Q4 fix.
        default = "void"
        valid_rings = {"air", "earth", "fire", "water", "void"}
        chosen = self.choice("school_ring", default)
        if not isinstance(chosen, str) or chosen not in valid_rings:
            logger.warning(
                f"Togashi Ise Zumi: invalid 'school_ring' choice "
                f"(expected one of {sorted(valid_rings)}; got "
                f"{chosen!r}). Using default."
            )
            chosen = default
        return chosen


class IseZumiNewRoundListener(Listener):
    """
    Special ability: Roll initiative and gain 1 extra action die.
    The extra die is placed at a random phase (rolled as 1d10).
    TODO: athletics-only restriction on extra action dice.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            # Roll 1 extra action die (1d10)
            extra_actions = character.roll_provider().get_initiative_roll(1, 1)
            if extra_actions:
                for phase in extra_actions:
                    character.gain_action(phase)
            yield from ()


class IseZumiWoundCheckFailedListener(Listener):
    """rules/04-schools.md "Togashi Ise Zumi School: Fifth Dan":

    "At any time, you may spend 1 void point to heal 2 serious
    wounds."

    Currently restricted to post-WC-failure (Q6 deferred — proactive
    heal-strategy is a follow-up).  Replaces the engine default
    ``WoundCheckFailedListener`` so this listener owns the SW
    application AND the heal — no double-handling.

    The engine processes yielded events synchronously
    (``engine.py:23-47``), so after yielding ``SeriousWoundsDamage
    Event`` the SW is fully applied before the heal check runs.

    Spec 024 ``is_alive()`` gate (rules-auditor recommendation): if
    the SW killed the character outright, the heal is moot.  Skip to
    avoid emitting a phantom ``SpendVoidPointsEvent`` against a
    corpse.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.WoundCheckFailedEvent):
            if event.subject == character:
                sw = character.wound_check(event.roll)
                character.reset_lw()
                yield events.SeriousWoundsDamageEvent(event.attacker, character, sw)
                # Spec 024 ``is_alive()`` gate per rules-auditor.
                if not character.is_alive():
                    return
                # After taking the SW, if character has VP and SW,
                # heal 2 SW.
                if character.vp() >= 1 and character.sw() >= 2:
                    yield events.SpendVoidPointsEvent(character, "wound check", 1)
                    character.take_sw(-2)
                    # Trace attribution tag for future renderer work.
                    character._ise_zumi_5th_dan_last_heal = 2
