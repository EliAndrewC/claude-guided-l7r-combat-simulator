#!/usr/bin/env python3

#
# ishi_dan_abilities.py
#
# Pluggable decision strategies for the Isawa Ishi School's 3rd Dan ally-boost
# and 5th Dan school-negation abilities. Per Constitution Principle V (pluggable
# decisions), the strategy is a separate class so playtesters can swap it
# without touching the combat loop or the Listener.
#
# References (all from ``rules/04-schools.md``):
#   * Isawa Ishi School Third Dan: "Spend 1 Void Point to add Xk1 to another
#     character's roll, where X is your Precepts skill. May only be done once
#     per roll."
#     -> implemented as ``IshiAllyBoostStrategy`` ABC + concrete
#        ``EagerAllyBoostStrategy``. Operates on combat roll events
#        (AttackRolled, ParryRolled, CounterattackRolled, WoundCheckRolled).
#   * Isawa Ishi School Fifth Dan: "Spend Void Points equal to 2 times your
#     opponent's school rank, or 1 point per 50 XP for a schoolless opponent,
#     to negate their school/profession for the duration of a fight."
#     -> implemented as ``IshiNegateSchoolStrategy`` ABC + concrete
#        ``EagerNegationStrategy``. Operates on ``YourMoveEvent`` once per
#        combat (per OPEN_QUESTIONS.md Q5b).
#
# Mirumoto's third_dan module is the reference pattern for this style.
#

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.log import logger
from simulation.strategies.base import Strategy


def _already_boosted(action: Any) -> bool:
    """Return True iff the given action has already been boosted by an Ishi
    3rd Dan ally boost on this roll.

    Per rules/04-schools.md "Isawa Ishi School: 3rd Dan" the ability may only
    be used once per roll. We tag the action with ``_ishi_boosted_by`` at the
    time of boost so subsequent listeners observing the same roll can detect
    this and abstain.
    """
    return getattr(action, "_ishi_boosted_by", None) is not None


def _event_action(event: events.Event) -> Any:
    """Return the action attached to the event, or None if the event has none.

    The combat roll events all expose ``event.action`` (ActionEvent) except
    WoundCheckRolledEvent which has no action. Returns None for the latter.
    """
    return getattr(event, "action", None)


def _event_subject(event: events.Event) -> Any:
    """Return the subject who performed the rolled action.

    For ActionEvent-derived rolls (Attack/Parry/Counterattack), this is
    ``event.action.subject()``. For WoundCheckRolledEvent it is
    ``event.subject`` (the character making the wound check).
    """
    action = _event_action(event)
    if action is not None:
        return action.subject()
    return getattr(event, "subject", None)


def _event_tn(event: events.Event) -> int | None:
    """Return the TN that the rolled total is being compared against.

    For ActionEvent-derived rolls this is ``action.tn()``. For
    WoundCheckRolledEvent it is ``event.tn``. Returns None if the event
    type does not expose a TN.
    """
    action = _event_action(event)
    if action is not None:
        return int(action.tn())
    tn = getattr(event, "tn", None)
    if tn is None:
        return None
    return int(tn)


def _event_roll(event: events.Event) -> int | None:
    """Return the rolled total on the event, or None if the event has none."""
    roll = getattr(event, "roll", None)
    if roll is None:
        return None
    return int(roll)


def _is_supported_roll_event(event: events.Event) -> bool:
    """Whether ``event`` is a combat-roll event the 3rd Dan boost can target.

    Per rules/04-schools.md "Isawa Ishi School: 3rd Dan" the ability adds Xk1
    to "another character's roll". The supported roll-event surface in this
    engine is: AttackRolledEvent (covers attack/double attack/iaijutsu/feint/
    lunge — all via the attack-action subclasses), ParryRolledEvent,
    CounterattackRolledEvent, and WoundCheckRolledEvent.
    """
    return isinstance(
        event,
        (
            events.AttackRolledEvent,
            events.ParryRolledEvent,
            events.CounterattackRolledEvent,
            events.WoundCheckRolledEvent,
        ),
    )


class IshiAllyBoostStrategy(Strategy):
    """ABC for Isawa Ishi 3rd Dan ally-boost decisions.

    Per rules/04-schools.md "Isawa Ishi School: 3rd Dan": the Ishi may spend
    1 VP to add Xk1 (X = precepts skill) to another character's roll, once
    per roll.

    Concrete subclasses implement the per-call spending policy (eager,
    conservative, etc.). They are invoked from ``IshiAllyBoostListener``
    whenever an in-group ally's combat roll resolves.
    """

    def recommend(
        self, character: Any, event: events.Event, context: Any,
    ) -> Iterator[events.Event]:
        raise NotImplementedError()


class EagerAllyBoostStrategy(IshiAllyBoostStrategy):
    """Default 3rd Dan policy: spend 1 VP whenever the precepts boost will
    push an in-group ally's failing roll over the TN.

    Triggers when ALL of these hold (per rules/04-schools.md "Isawa Ishi
    School: 3rd Dan" + specs/002 OPEN_QUESTIONS Q3):

      * The event is a supported combat-roll event (Attack/Parry/
        Counterattack/WoundCheck Rolled).
      * The event subject is an in-group ally of the Ishi (not the Ishi
        themselves; "another character" per rules-text, restricted to
        in-group per Q3).
      * The Ishi has at least 1 VP available.
      * The Ishi's precepts skill > 0 (the Xk1 boost requires X >= 1).
      * The roll is below the TN (margin > 0): no point boosting a roll
        that already succeeded.
      * The action has NOT already been boosted by this or another Ishi on
        this roll (once-per-roll guard via ``_ishi_boosted_by``).

    When firing:

      1. Rolls precepts.k1 via the Ishi's ``roll_provider().get_skill_roll``
         (so the dice flow through the injectable roll providers per
         Constitution Principle IV).
      2. Yields ``SpendVoidPointsEvent(character, "ishi_3rd_dan_ally_boost",
         1)``.
      3. Mutates the rolled-event total in-place so downstream listeners
         see the bonused roll. For ActionEvent-derived rolls this also
         calls ``action.set_skill_roll(new_total)``.
      4. Tags ``event.action._ishi_boosted_by = character`` and
         ``event.action._ishi_boost_value = bonus`` so the once-per-roll
         guard and trace attribution (web/adapters/modifier_breakdown.py)
         can read them. For WoundCheckRolledEvent (no action), the tags
         are attached to the event itself.
      5. Logs a ``[Ishi 3rd Dan]`` debug marker.
    """

    def recommend(
        self, character: Any, event: events.Event, context: Any,
    ) -> Iterator[events.Event]:
        del context  # not used; kept for interface uniformity
        # Wrong-event guard: only fire on supported combat roll events.
        if not _is_supported_roll_event(event):
            return
        subject = _event_subject(event)
        if subject is None:
            return
        # Subject guard: must be an in-group ally, never the Ishi themselves.
        if subject is character:
            return
        group = character.group()
        if group is None or subject not in group:
            return
        # Resource guards: need 1 VP and a positive precepts skill.
        if character.vp() < 1:
            return
        precepts = character.skill("precepts")
        if precepts <= 0:
            return
        # Roll-state guards: need a valid roll and TN.
        current_roll = _event_roll(event)
        tn = _event_tn(event)
        if current_roll is None or tn is None:
            return
        margin = tn - current_roll
        if margin <= 0:
            # Roll already meets/exceeds TN; no need to boost.
            return
        # Once-per-roll guard: check tag on action (or event for wound check).
        action = _event_action(event)
        guard_owner: Any = action if action is not None else event
        if _already_boosted(guard_owner):
            return
        # Fire: compute Xk1 bonus via injectable roll provider so the dice
        # flow through TrackingRollProvider / CalvinistRollProvider, etc.
        # (Constitution Principle IV: never call random.* directly.)
        bonus = character.roll_provider().get_skill_roll(
            "precepts", precepts, 1, True,
        )
        # Spend the VP via the event so the standard listeners decrement.
        yield events.SpendVoidPointsEvent(
            character, "ishi_3rd_dan_ally_boost", 1,
        )
        # Mutate the rolled total. For ActionEvent-derived rolls, also
        # update the action's stored skill_roll so downstream consumers
        # (hit/miss checks, damage scaling) see the bonused total. The
        # event's ``roll`` field is mirrored on WoundCheckRolledEvent too.
        new_total = current_roll + bonus
        event.roll = new_total  # type: ignore[attr-defined]
        if action is not None:
            action.set_skill_roll(new_total)
        # Tag for once-per-roll guard and trace attribution.
        guard_owner._ishi_boosted_by = character
        guard_owner._ishi_boost_value = bonus
        # SC-006-style trace marker so a reviewer can map this spend to
        # rules/04-schools.md "Isawa Ishi School: 3rd Dan".
        logger.debug(
            f"[Ishi 3rd Dan] {character.name()} spent 1 VP to add "
            f"{precepts}k1={bonus} to {subject.name()}'s "
            f"{event.name} roll ({current_roll}->{new_total}, TN {tn})",
        )


# ---------------------------------------------------------------------------
# 5th Dan: school negation
# ---------------------------------------------------------------------------


def _school_rank_of(character: Any) -> int:
    """Return ``character``'s school rank, computed as ``min(skill rank)``
    across the school's knacks.

    Mirrors ``simulation/character_file.py::CharacterFile.school_rank`` and
    ``web/adapters/modifier_breakdown.py::_school_rank_of``.  Returns 0 when
    the character has no school or the school exposes no knacks.
    """
    school = character.school() if hasattr(character, "school") else None
    if school is None:
        return 0
    knacks = school.school_knacks()
    if not knacks:
        return 0
    result: int = min(character.skill(s) for s in knacks)
    return result


def _negation_cost(target: Any) -> int:
    """Compute the VP cost to negate ``target``'s school/profession per
    rules/04-schools.md "Isawa Ishi School: 5th Dan".

    Schooled opponent: ``2 * target.school_rank()``.
    Schoolless opponent: ``floor(target.xp / 50)`` (fallback for
    profession-only characters; single-combat sim usually has both sides
    schooled, so this path is rarely exercised).
    """
    school = target.school() if hasattr(target, "school") else None
    if school is not None:
        return 2 * _school_rank_of(target)
    xp_accessor = getattr(target, "xp", None)
    if xp_accessor is None:
        return 0
    xp = xp_accessor() if callable(xp_accessor) else int(xp_accessor)
    return int(xp) // 50


class IshiNegateSchoolStrategy(Strategy):
    """ABC for Isawa Ishi 5th Dan school-negation decisions.

    Per rules/04-schools.md "Isawa Ishi School: 5th Dan": the Ishi may spend
    VP equal to ``2 * opponent.school_rank()`` (or ``floor(opponent.xp/50)``
    for a schoolless opponent) to negate the opponent's school/profession
    for the duration of a fight.  The ability is instantaneous and does
    not consume an action.

    Concrete subclasses implement the spend policy (eager, reactive, etc.).
    They are invoked from ``IshiYourMoveListener`` (see ``simulation/
    schools/ishi_school.py``).
    """

    def recommend(
        self, character: Any, event: events.Event, context: Any,
    ) -> Iterator[events.Event]:
        raise NotImplementedError()


class EagerNegationStrategy(IshiNegateSchoolStrategy):
    """Default 5th Dan policy: on the Ishi's first ``YourMoveEvent`` of the
    combat, identify the highest-rank opposing schooled enemy and spend VP
    to negate if affordable.  Fires at most once per combat (guarded by the
    ``_ishi_negation_done`` flag on the Ishi, cleared by ``Character.reset()``).

    Trigger conditions (per OPEN_QUESTIONS.md Q5/Q5b):

      * The event is a ``YourMoveEvent`` (the natural earliest reactive
        point in a phase; the rules-text "instantaneous, no action
        consumed" implies the negation should fire as early as possible).
      * The Ishi's derived school rank is >= 5.
      * The Ishi has not already fired the negation this combat.
      * There is at least one opposing schooled enemy.
      * The VP cost (``2 * opponent.school_rank()`` or
        ``floor(opponent.xp/50)`` for schoolless) is affordable.

    When firing:

      1. Yields ``SpendVoidPointsEvent(character, "ishi_negate_school", cost)``.
      2. Sets ``target._school_negated_by = character`` (mutates the target;
         the engine's ``BaseSchool._is_school_negated`` helper consults this
         on subsequent ``apply_*_ability`` calls and short-circuits them).
      3. Yields ``SchoolNegatedEvent(character, target, cost, school_name)``
         for trace observability (Constitution Principle VII).
      4. Sets ``character._ishi_negation_done = True`` to lock further
         firings in this combat.
    """

    def recommend(
        self, character: Any, event: events.Event, context: Any,
    ) -> Iterator[events.Event]:
        # Wrong-event guard.
        if not isinstance(event, events.YourMoveEvent):
            return
        # The strategy only fires for the subject of the YourMoveEvent
        # (i.e., the Ishi whose move it is).  Defensive — the engine should
        # only dispatch YourMove to the subject's listener, but the
        # subject check guards against accidental cross-character firing.
        subject: Any = getattr(event, "subject", None)
        if subject is None or subject is not character:
            return
        # Rank guard: 5th Dan requires school_rank >= 5.
        if _school_rank_of(character) < 5:
            return
        # Once-per-combat guard.
        if getattr(character, "_ishi_negation_done", False):
            return
        # Find the highest-rank schooled enemy in opposing groups.
        target: Any = None
        target_rank: int = -1
        own_group = character.group()
        for group in context.groups():
            if group is own_group:
                continue
            for enemy in group:
                if not getattr(enemy, "is_fighting", lambda: True)():
                    continue
                if enemy.school() is None:
                    continue
                rank = _school_rank_of(enemy)
                if rank > target_rank:
                    target = enemy
                    target_rank = rank
        if target is None:
            return
        # Cost & affordability check.
        cost = _negation_cost(target)
        if character.vp() < cost:
            return
        # Fire: spend, mark, advertise.
        yield events.SpendVoidPointsEvent(
            character, "ishi_negate_school", cost,
        )
        target._school_negated_by = character
        target_school = target.school()
        target_school_name = (
            target_school.name() if target_school is not None else "(none)"
        )
        yield events.SchoolNegatedEvent(
            character, target, cost, target_school_name,
        )
        character._ishi_negation_done = True
        # SC-006-style trace marker.
        logger.debug(
            f"[Ishi 5th Dan] {character.name()} spent {cost} VP to negate "
            f"{target.name()}'s {target_school_name}",
        )
