#!/usr/bin/env python3

#
# yogo_school.py
#
# Implement Yogo Warden School.
#
# School Ring: Earth
# School Knacks: double attack, iaijutsu, feint
#
# Special Ability: Gain TVP when taking a serious wound.
#
# 1st Dan: Extra rolled on attack, damage, wound check
# 2nd Dan: Free raise on wound check
# 3rd Dan: SpendVoidPointsListener — on VP spend, reduce LW by
#          2*attack_skill PER VP SPENT (spec 021 Q2 BLOCKING fix —
#          previously applied once per event regardless of amount).
# 4th Dan: Ring+1/discount; +10 per VP on wound checks instead of +5
# 5th Dan: TBD per upstream rules text. Stubbed as no-op (spec 021
#          Q3 per user direction: school must function without 5th
#          Dan; never raise).
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.schools.base import BaseSchool


class YogoWardenSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Yogo Warden School: Special Ability":
        # "Gain a temporary void point every time you take a serious
        # wound."  Installed via a school-owned sw_damage listener
        # that replaces the engine default and adds TVP gain on the
        # alive-and-fighting branch.
        #
        # Spec 021 Q4 identity binding: WoundCheckStrategy04
        # (aggressive VP-spend threshold) was attempted but combined
        # with the Q2 per-VP scaling fix it made Yogos too durable
        # in mirror — two Yogos at 300 XP failed to terminate within
        # the 18-round Principle IX safety bound on 2 of 5 seeds.
        # DEFERRED to a follow-up branch that can co-tune the
        # threshold against the post-Q2-fix damage curve.
        self._set_school_listener(character, "sw_damage", YogoSeriousWoundsDamageListener())

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_listener(character, "spend_vp", YogoSpendVoidPointsListener())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_roll_parameter_provider(character, YOGO_ROLL_PARAMETER_PROVIDER)

    def apply_rank_five_ability(self, character: Any) -> None:
        # rules/04-schools.md "Yogo Warden School: Fifth Dan": TBD.
        # Stubbed as no-op per user direction (spec 021 Q3): "the
        # Yogo Warden does not have a 5th Dan so that will need to be
        # stubbed.  But we shouldn't raise NotImplemented anywhere
        # for it, since we want the school to function, just without
        # sa 5th Dan for now."
        pass

    def extra_rolled(self) -> list[str]:
        return ["attack", "damage", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["wound check"]

    def name(self) -> str:
        return "Yogo Warden School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "feint", "iaijutsu"]

    def school_ring(self) -> str:
        return "earth"


class YogoSeriousWoundsDamageListener(Listener):
    """
    Listener to implement the Yogo special ability
    to gain TVP when taking a serious wound.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.SeriousWoundsDamageEvent):
            if event.target == character:
                character.take_sw(event.damage)
                if not character.is_alive():
                    yield events.DeathEvent(character)
                elif not character.is_conscious():
                    yield events.UnconsciousEvent(character)
                elif not character.is_fighting():  # pragma: no cover  # defensive: is_fighting() == is_conscious() per character.py:369-370; this branch is dead code under the engine default but kept defensively against future is_fighting overrides
                    yield events.SurrenderEvent(character)
                else:
                    yield events.GainTemporaryVoidPointsEvent(character, 1)
            else:
                character.knowledge().observe_wounds(event.target, event.damage)


class YogoSpendVoidPointsListener(Listener):
    """rules/04-schools.md "Yogo Warden School: Third Dan":

    "Whenever you spend a void point, reduce your current light
    wound total by 2X, where X is your attack skill."

    Spec 021 Q2 BLOCKING fix: rules text "Whenever you spend **a**
    void point" implies PER-VP scaling.  The previous skeleton
    applied the reduction once per ``SpendVoidPointsEvent``
    regardless of ``event.amount``, so a 2-VP spend reduced LW by
    2X instead of 4X.  Now multiplies by ``event.amount``.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.SpendVoidPointsEvent):
            if event.subject == character:
                character.spend_vp(event.amount)
                # Per-VP scaling (Q2 fix).
                attack_skill = character.skill("attack")
                reduction = 2 * attack_skill * event.amount
                # Cap reduction at current LW so the trace's
                # ``lw_after`` reflects the actual mutation.
                effective_reduction = min(reduction, character.lw())
                new_lw = character.lw() - effective_reduction
                character._lw = new_lw
                # Trace attribution tag (kept for back-compat with
                # any external consumers).
                character._yogo_3rd_dan_last_reduction = effective_reduction
                if effective_reduction > 0:
                    # Trace-reader cat#10 fix (2026-05-30): emit a
                    # discrete event so the trace surfaces the LW
                    # reduction instead of a silent _lw mutation.
                    yield events.YogoThirdDanLwReductionEvent(
                        subject=character,
                        vp_spent=event.amount,
                        attack_skill=attack_skill,
                        reduction=effective_reduction,
                        lw_after=new_lw,
                    )


class YogoRollParameterProvider(DefaultRollParameterProvider):
    """
    RollParameterProvider to implement the Yogo 4th Dan ability:
    +10 per VP on wound checks instead of +5.
    """

    def get_wound_check_roll_params(self, character: Any, vp: int = 0) -> tuple[int, int, int]:
        ring = character.ring(character.get_skill_ring("wound check"))
        rolled = ring + 1 + character.extra_rolled("wound check") + vp
        kept = ring + character.extra_kept("wound check") + vp
        # +10 per VP instead of the normal +5
        modifier = character.modifier(None, "wound check") + (5 * vp)
        return normalize_roll_params(rolled, kept, modifier)


YOGO_ROLL_PARAMETER_PROVIDER = YogoRollParameterProvider()
