#!/usr/bin/env python3

#
# matsu_school.py
#
# Implement Matsu Bushi School.
#
# School Ring: Fire
# School Knacks: double attack, iaijutsu, lunge
#
# Special Ability: Always roll 10 dice on initiative.
# 1st Dan: Extra rolled on double attack, iaijutsu, wound check
# 2nd Dan: Free raise on iaijutsu
# 3rd Dan: On any VP spend, gain WoundCheckFloatingBonus(3 * attack_skill)
# 4th Dan: Ring+1/discount; custom MatsuDoubleAttackAction where is_hit()
#          returns True if within 20 of TN (near-miss), but
#          calculate_extra_damage_dice returns 0 for near-misses
# 5th Dan: When Matsu's attack causes a failed wound check,
#          set defender's LW to 15 instead of 0
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.actions import DoubleAttackAction
from simulation.listeners import Listener, SeriousWoundsDamageListener
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.mechanics.roll_provider import DefaultRollProvider
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import (
    DefaultInterruptStrategy,
    WoundCheckStrategy04,
)


class MatsuBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Matsu Bushi School: Special Ability":
        # "You always roll 10 dice when rolling initiative, keeping the
        #  usual number as action dice."
        #
        # Wiring per school-strategy-designer (specs/011 OPEN_QUESTIONS Q10):
        #   * ``MATSU_ROLL_PROVIDER`` — the always-10 initiative rule.
        #   * ``DefaultInterruptStrategy`` — Matsu has NO counterattack
        #     knack (school knacks are double attack / iaijutsu / lunge),
        #     so the engine default ``CounterattackInterruptStrategy``
        #     is identity-wrong even though it short-circuits at skill 0.
        #     Bind ``DefaultInterruptStrategy`` for identity clarity.
        #   * ``WoundCheckStrategy04`` — the 1st Dan +1 WC die calibrates
        #     a 0.4 confidence threshold (same precedent as Hida).  Also,
        #     every Matsu VP spend triggers the 3rd Dan +3X WC bonus, so
        #     earlier VP spends fund later WC rerolls — aggressive
        #     spending pays for itself.
        #
        # Per the strategy-designer's analysis, ``UniversalAttackStrategy``
        # (engine default) is acceptable for v1 — its first branch tries
        # double attack at threshold 0.6, which matches Matsu's identity.
        # A future ``MatsuAttackStrategy`` with attack_threshold = 0.4 and
        # the feint branch removed would more honestly express the 4th Dan
        # near-miss carve-out, but that's optional v2 polish.
        # ``ReluctantParryStrategy`` (engine default) is kept as a safety
        # valve — fires only on probably-fatal incoming attacks, which
        # prevents Matsu from suiciding into a Hida 5th-Dan counterattack.
        self._set_school_roll_provider(character, MATSU_ROLL_PROVIDER)
        self._set_school_strategy(
            character, "interrupt", DefaultInterruptStrategy(),
        )
        self._set_school_strategy(
            character, "wound_check", WoundCheckStrategy04(),
        )

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_listener(character, "spend_vp", MatsuSpendVoidPointsListener())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_action_factory(character, MATSU_ACTION_FACTORY)

    def apply_rank_five_ability(self, character: Any) -> None:
        # rules/04-schools.md "Matsu Bushi School: Fifth Dan":
        # "After you deal light wounds which result in the defender
        #  taking one or more serious wounds, their light wound total
        #  is reset to 15 instead of 0."
        #
        # Wiring (rules-auditor BLOCKING fix 2026-05-28): the prior
        # design slot-replaced the Matsu's own ``wound_check_failed``
        # listener AND emitted a ``SeriousWoundsDamageEvent`` from the
        # attacker side.  But the DEFENDER's default
        # ``WoundCheckFailedListener`` still fires (it's installed on
        # the defender, not the Matsu) — and the defender's default
        # also emits a SW event AND calls ``character.reset_lw()``,
        # producing (a) DOUBLE SW events and (b) a race on the LW
        # value (defender's reset_lw to 0 may execute before OR after
        # the Matsu's _lw = 15 set, depending on initiative iteration
        # order).
        #
        # The fix listens on the ``sw_damage`` slot (which fires AFTER
        # the defender's reset_lw has executed and AFTER the SW event
        # has been emitted exactly once).  ``MatsuSeriousWoundsDamageListener``
        # subclasses the default, calls super() for the standard
        # take_sw + status checks, and adds the LW=15 set when this
        # Matsu is the attacker AND the target is someone else.
        # No SW double-emission; no LW race.
        self._set_school_listener(
            character, "sw_damage", MatsuSeriousWoundsDamageListener(),
        )

    def extra_rolled(self) -> list[str]:
        return ["double attack", "iaijutsu", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["iaijutsu"]

    def name(self) -> str:
        return "Matsu Bushi School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "iaijutsu", "lunge"]

    def school_ring(self) -> str:
        return "fire"


class MatsuRollProvider(DefaultRollProvider):
    """
    RollProvider to implement the Matsu special ability:
    always roll EXACTLY 10 dice on initiative.

    rules/04-schools.md "Matsu Bushi School: Special Ability":
    "You always roll 10 dice when rolling initiative, keeping the
    usual number as action dice."  Per OPEN_QUESTIONS Q1 the strict
    rules-as-written reading is exactly 10 (not at-least-10): a
    high-XP Matsu whose base rolled count would exceed 10 clamps
    down to 10.  FR-001 / FR-002.
    """

    def get_initiative_roll(self, rolled: int, kept: int) -> list[int]:
        # Strict "always 10" semantics -- ignore the input ``rolled``
        # entirely; kept count is unchanged.
        return super().get_initiative_roll(10, kept)


MATSU_ROLL_PROVIDER = MatsuRollProvider()


class MatsuSpendVoidPointsListener(Listener):
    """
    Listener to implement the Matsu 3rd Dan technique:
    on any VP spend, gain WoundCheckFloatingBonus(3 * attack_skill).

    rules/04-schools.md "Matsu Bushi School: Third Dan".

    Slot-replaces the engine default ``SpendVoidPointsListener`` (so VP
    is debited exactly once -- regression-guarded by T013).  The
    granted ``WoundCheckFloatingBonus`` carries ``source="Matsu 3rd
    Dan"`` so the later ``SpendFloatingBonusEvent`` consumption surfaces
    the attribution in the trace.  A ``GainFloatingBonusEvent`` is
    yielded for trace observability per Constitution Principle VII
    (FR-013) -- the engine has no handler for this event; it exists
    solely so the formatter renders the gain with the source label.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.SpendVoidPointsEvent):
            if event.subject == character:
                character.spend_vp(event.amount)
                attack_skill = character.skill("attack")
                bonus_value = 3 * attack_skill
                bonus = WoundCheckFloatingBonus(
                    bonus_value, source="Matsu 3rd Dan",
                )
                character.gain_floating_bonus(bonus)
                # Emit the trace-observability event so the formatter
                # can attribute the gain to "Matsu 3rd Dan" (Principle
                # VII / FR-013).  The numeric breakdown surfaces the
                # rules-text formula 3 × attack_skill.
                if bonus_value > 0:
                    yield events.GainFloatingBonusEvent(
                        character,
                        bonus,
                        source="Matsu 3rd Dan",
                        breakdown=f"3 × attack {attack_skill}",
                    )


class MatsuDoubleAttackAction(DoubleAttackAction):
    """
    Custom DoubleAttackAction for Matsu 4th Dan:
    is_hit() returns True if within 20 of TN (near-miss),
    but calculate_extra_damage_dice returns 0 for near-misses.

    rules/04-schools.md "Matsu Bushi School: Fourth Dan".

    The ``_is_near_miss`` property exposes the near-miss state for
    trace-observability purposes (Constitution Principle VII / FR-021):
    the formatter reads this attribute on the action to populate the
    ``AttackEntry.matsu_4th_dan_near_miss_below_tn`` field, which both
    renderers surface as "Matsu 4th Dan: near-miss (N below TN)".
    A near-miss is ``tn - 20 <= skill_roll < tn``.
    """

    @property
    def _is_near_miss(self) -> bool:
        """True iff the action HIT via the 4th Dan carve-out rather
        than a clean roll >= TN.  Returns False for clean hits, misses,
        and parried attacks (where the 4th Dan carve-out does not
        apply).

        Boundary (rules-auditor #2, 2026-05-28): rules text says "by
        less than 20", which is strict ``<``.  A roll exactly 20 below
        TN is a MISS (``roll - tn == -20`` is "by 20", not "by less
        than 20"); a roll 19 below TN is a near-miss hit.
        """
        if self.parried():
            return False
        roll = self.skill_roll()
        if roll is None:
            return False  # pragma: no cover  # defensive: skill_roll() is set by roll_skill before is_hit/_is_near_miss are queried in any real combat path
        tn = self.tn()
        return tn - 20 < roll < tn

    def is_hit(self) -> bool:
        if self.parried():
            return False
        roll = self.skill_roll()
        assert roll is not None
        # Hit if skill roll is within < 20 below TN (near-miss) or above
        # TN.  Strict ``>`` per rules-text "by LESS THAN 20" (rules-
        # auditor #2 fix 2026-05-28; was ``>=`` which counted miss-by-
        # exactly-20 as a near-miss hit).
        return roll > self.tn() - 20

    def calculate_extra_damage_dice(self, skill_roll: int | None = None, tn: int | None = None) -> int:
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn()
        assert skill_roll is not None
        # Near-miss carve-out: hit but below actual TN -> no extra
        # damage dice per rules text "you deal no extra damage".
        if skill_roll < tn:
            return 0
        # Normal hit: delegate to the parent ``DoubleAttackAction``
        # WITHOUT passing the inflated DA TN (= base TN + 20) — the
        # parent's default for ``tn`` is ``self.tn() - 20`` (the base
        # hit TN), which is what the standard
        # ``(skill_roll - base_tn) // 5`` formula expects.  Passing
        # ``self.tn()`` instead under-counts the extra dice by 4
        # (rules-auditor #1 fix 2026-05-28).
        return super().calculate_extra_damage_dice(skill_roll)

    def direct_damage(self) -> Any:
        if self.parry_attempted():
            return None
        roll = self.skill_roll()
        assert roll is not None
        # Near-miss: no direct SW damage
        if roll < self.tn():
            return None
        return super().direct_damage()


class MatsuActionFactory(DefaultActionFactory):
    """
    ActionFactory to return Matsu-specific attack actions.
    """

    def get_attack_action(self, subject: Any, target: Any, skill: str, initiative_action: Any, context: Any, vp: int = 0) -> Any:
        if skill == "double attack":
            return MatsuDoubleAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


MATSU_ACTION_FACTORY = MatsuActionFactory()


class MatsuSeriousWoundsDamageListener(SeriousWoundsDamageListener):
    """Listener implementing the Matsu 5th Dan LW-floor.

    rules/04-schools.md "Matsu Bushi School: Fifth Dan":
      "After you deal light wounds which result in the defender taking
       one or more serious wounds, their light wound total is reset to
       15 instead of 0."

    Subclasses the default ``SeriousWoundsDamageListener`` to preserve
    the standard ``take_sw`` + death / unconscious / surrender status
    checks.  ADDS the 5th Dan LW-floor when this Matsu is the
    ``event.attacker`` AND the SW target is someone else.

    By the time ``SeriousWoundsDamageEvent`` fires, the defender's
    default ``WoundCheckFailedListener`` has already executed
    ``character.reset_lw()`` (LW=0), so this listener's ``_lw = 15``
    set is the last write — no race condition with the defender's
    reset_lw.

    Q3 (broad reading, revised 2026-05-28): the 5th Dan triggers on
    ANY SW the defender takes from a Matsu attack — including
    voluntary SW elected by the defender's ``KeepLightWoundsStrategy``.
    The rules text "result in the defender taking one or more SW"
    includes the defender's strategic choice to take SW from a
    Matsu-dealt LW pool.  This is the simpler reading AND the
    architecturally cleanest (no per-event flag needed to distinguish
    voluntary from involuntary).

    Q3 (narrow reading, prior to 2026-05-28): only involuntary SW
    from a failed WC triggered.  Revised when the rules-auditor
    flagged the double-SW + LW-race bug in the prior implementation
    (which slot-replaced ``wound_check_failed``).  Switching to the
    ``sw_damage`` slot resolves the bug, with the side effect of
    triggering on voluntary SW too — which is also rules-text-faithful.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.SeriousWoundsDamageEvent):
            # SeriousWoundsDamageEvent uses ``subject`` for the attacker
            # (per DamageEvent convention) and ``target`` for the
            # defender.  5th Dan LW-floor — only fires when this Matsu
            # is the attacker AND someone ELSE is the target (not when
            # the Matsu takes SW from another attacker).
            if event.subject == character and event.target != character:
                event.target._lw = 15
                yield events.MatsuLightWoundsFloorEvent(
                    character, event.target, lw_set_to=15,
                )
        # ALWAYS fall through to default behavior — the default
        # ``SeriousWoundsDamageListener`` handles ``take_sw`` on the
        # target and emits the death / unconscious / surrender status
        # events.  Without this delegation a 5th Dan Matsu would
        # silently fail to apply the SW.
        yield from super().handle(character, event, context)


