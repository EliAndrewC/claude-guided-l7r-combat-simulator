#!/usr/bin/env python3

#
# mirumoto_third_dan.py
#
# Decision strategies for the Mirumoto Bushi School Third Dan resource pool.
#
# Per rules/04-schools.md Mirumoto Bushi School Third Dan:
#     "At the beginning of each round, you get 2X points, where X is equal
#      to your attack skill. Each point may be spent to decrease the phase
#      of one of your actions by 1 in order to parry, or to provide a
#      bonus of +2 on any type of attack or parry after you have seen your
#      roll."
#
# The pool itself is allocated by ``MirumotoNewRoundListener`` in
# ``simulation/schools/mirumoto_school.py``; this module hosts the
# spend-decision logic (mode A: phase-lower; mode B: +2 after roll).
#
# Constitution Principle V (pluggable decisions): both spend modes are
# implemented as ``Strategy`` subclasses so playtesters can swap them
# without touching the combat loop. The concrete defaults provided here
# (``EagerPhaseLowerStrategy``, ``MarginalBonusStrategy``) are intentionally
# simple greedy baselines (see research.md R8) that more sophisticated
# strategies can be benchmarked against.
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.log import logger
from simulation.strategies.base import Strategy


def _pool_remaining(character: Any) -> int:
    """Return the character's current Third Dan pool size.

    Returns 0 if the character has no ``_mirumoto_pool`` attribute (e.g.,
    a non-3rd-dan character on whom the strategy was mistakenly invoked).
    Per contracts/interfaces.md.
    """
    value: int = getattr(character, "_mirumoto_pool", 0)
    return value


def _try_spend_pool_point(character: Any) -> bool:
    """Atomically attempt to spend one Third Dan pool point.

    Returns True and decrements ``character._mirumoto_pool`` by 1 if the
    pool currently has at least one point. Returns False otherwise (empty
    pool, or attribute missing entirely). Never lets the pool go negative
    and never creates the attribute as a side effect.

    Per contracts/interfaces.md.
    """
    if not hasattr(character, "_mirumoto_pool"):
        return False
    current: int = character._mirumoto_pool
    if current <= 0:
        return False
    character._mirumoto_pool = current - 1
    return True


class MirumotoPhaseLowerStrategy(Strategy):
    """Decides Third Dan mode-A (phase-lowering) spends.

    Invoked by the combat loop's strategy-dispatch on phase-related events
    (typically ``NewPhaseEvent``). Decision interface mirrors the spec's
    FR-008 + FR-009a:

      - May choose to lower one or more actions' phases by one or more steps.
      - Must never spend more points than ``_pool_remaining(character)``.
      - Must never lower an action below phase 1 (FR-008 floor).

    Per FR-008 / rules/04-schools.md Mirumoto Bushi School Third Dan:
    "Each point may be spent to decrease the phase of one of your actions
    by 1 in order to parry."

    Concrete subclasses implement the per-call spending policy.
    """

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        raise NotImplementedError()


class EagerPhaseLowerStrategy(MirumotoPhaseLowerStrategy):
    """Default mode-A strategy: spend just enough points in one call to
    make the soonest non-phase-1 action usable as a parry on the current
    combat phase.

    Per research.md R8: this is a deliberately simple greedy baseline so
    playtesters have a known reference policy to benchmark more
    sophisticated strategies against. Per the T010 fix-cycle-1
    parry-reservation gap fix, the strategy is TRANSACTIONAL: it spends
    pool points only if the spends actually enable a parry on the
    current phase. A partial lowering that leaves the action still
    unusable (phase > ``context.phase()``) is treated as a waste and
    refused entirely.

    Per FR-008 / rules/04-schools.md Mirumoto Bushi School Third Dan:
    "Each point may be spent to decrease the phase of one of your actions
    by 1 *in order to parry*". The "in order to parry" qualifier is the
    gating condition: spend only if a parry actually becomes possible.

    Each ``recommend(...)`` call:

      1. Returns immediately (no spend) on non-``NewPhaseEvent``s.
      2. Returns immediately if the pool is empty.
      3. Returns immediately if every scheduled action is already at the
         FR-008 phase-1 floor.
      4. Picks the soonest action with phase >= 2 (the candidate parry).
      5. Computes how many lowerings are needed to make that action's
         phase <= ``context.phase()``, capped at the pool size and the
         phase-1 floor.
      6. If the action is already usable (phase <= ``context.phase()``),
         no spend is needed -> returns.
      7. If the required lowering would either exceed the pool OR drop
         the action below phase 1 before reaching usability, refuses
         entirely (transactional: no partial spend that fails to reserve
         the parry -- this is the parry-reservation gap fix).
      8. Otherwise spends exactly N points and lowers the action by N
         to reach usability.

    Stacking (FR-009a-i): a single call MAY spend multiple points on the
    same action (each adding 1 step of phase reduction); repeated calls
    across successive phases stack further.

    No events are yielded: the spend is realized as a direct mutation of
    ``character._actions`` and ``character._mirumoto_pool``. The engine
    hook that invokes this strategy (T010) is responsible for any
    logging / trace events around the call.
    """

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        # Hook only on phase-boundary events.
        if not isinstance(event, events.NewPhaseEvent):
            return
        # Pool guard: no pool, no spend.
        pool = _pool_remaining(character)
        if pool <= 0:
            return
        # 2026-05-26 Fix-C condition (2): if the character already has
        # an action available at phase <= context.phase(), no mode-A
        # spend is needed -- the parry can happen with the
        # already-usable action. The rules clause "in order to parry"
        # gates the spend on the parry NOT otherwise being possible.
        # Without this guard, the strategy would burn pool points to
        # lower a future action even when a usable one exists right
        # now (the eager-spend regression that Fix-C corrects).
        combat_phase = context.phase()
        actions = character.actions()
        if any(p <= combat_phase for p in actions):
            return
        # Find the soonest action that is above the phase-1 floor (FR-008).
        spendable_indices = [i for i, phase in enumerate(actions) if phase >= 2]
        if not spendable_indices:
            # All actions at floor; FR-008 forbids further phase-lowering.
            return
        target_index = min(spendable_indices, key=lambda i: actions[i])
        original_phase = actions[target_index]
        # Parry-reservation gap fix: compute how many spends are needed
        # to make this action usable on the current combat phase. The
        # rules clause "in order to parry" gates the spend on a parry
        # actually becoming possible; a partial lowering that leaves
        # the action still unusable (phase > context.phase()) is
        # treated as a waste and refused entirely.
        if original_phase <= combat_phase:
            # Already usable; no spend needed.
            # (Defensive: condition (2) above should already short-circuit
            # this case, but the guard is kept for direct-call safety.)
            return
        steps_needed = original_phase - combat_phase
        # Max legal steps: cannot drop below phase 1 (FR-008 floor),
        # cannot spend more than the pool holds.
        max_steps = min(pool, original_phase - 1)
        if steps_needed > max_steps:
            # Cannot reach usability with the available pool or without
            # violating the phase-1 floor -- refuse entirely.
            return
        # Transactional spend: decrement pool N times, lower action by N.
        # Use the atomic spend helper for each point so the pool can
        # never go negative even if a concurrent caller drained it.
        spent = 0
        for _ in range(steps_needed):
            if not _try_spend_pool_point(character):
                # Defensive: race-safety; if the pool drained between
                # the upfront check and now, bail. (Should not happen
                # in single-threaded combat simulation.)
                break
            spent += 1
        if spent == 0:
            return
        new_phase = original_phase - spent
        actions[target_index] = new_phase
        actions.sort()
        # SC-006 trace clarity: distinctive [Mirumoto 3rd Dan mode A]
        # marker plus the pre/post action phase so a reviewer can map
        # this spend to rules/04-schools.md Mirumoto Bushi School Third
        # Dan ("Each point may be spent to decrease the phase of one of
        # your actions by 1 in order to parry"; FR-008).
        logger.debug(
            f"[Mirumoto 3rd Dan mode A] {character.name()} lowered action "
            f"phase {original_phase}->{new_phase} (spent {spent} point(s); "
            f"usable on combat phase {combat_phase}; FR-008); "
            f"pool now {_pool_remaining(character)}",
        )
        yield from ()


class MirumotoPostRollBonusStrategy(Strategy):
    """Decides Third Dan mode-B (+2 after-roll) spends.

    Per FR-009 / rules/04-schools.md Mirumoto Bushi School Third Dan:
    "[Each point may be spent...] to provide a bonus of +2 on any type
    of attack or parry after you have seen your roll."

    Invoked by the combat loop's strategy-dispatch on post-roll events
    (``AttackRolledEvent``, ``ParryRolledEvent``, and
    ``CounterattackRolledEvent``) — the moment when the dice have been
    rolled and the total is known but downstream consumers (hit/miss,
    TN comparison) have not yet acted on it. The rules clause says
    "any type of attack or parry," so a counterattack roll (a Mirumoto
    school knack per FR-003) is covered.

    Concrete subclasses implement the per-call spending policy. They
    must:

      - Inspect the just-resolved roll's outcome (via
        ``event.action.skill_roll()`` or ``event.roll``).
      - May spend zero or more points on the roll (stacks per FR-009a-ii,
        each point adding +2).
      - Must never spend more points than ``_pool_remaining(character)``.
      - Must mutate the action's roll via ``action.set_skill_roll(...)``
        and the event's ``roll`` field so downstream listeners see the
        bonused total (matches the existing ``SkillRolledStrategy``
        pattern in ``simulation/strategies/base.py``).
    """

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        raise NotImplementedError()


class MarginalBonusStrategy(MirumotoPostRollBonusStrategy):
    """Default mode-B strategy: spend just enough points to push a
    failing roll over the TN, OR abstain entirely.

    Per research.md R8: this is a deliberately simple greedy baseline so
    playtesters have a known reference policy to benchmark more
    sophisticated strategies against.

    Per the 2026-05-26 spec.md / research.md update (Fix-D): when the
    pool is too small to close the TN gap, the strategy MUST abstain
    rather than burn points on a partial spend that still fails. The
    intuition is that points saved on a roll the strategy CAN'T close
    are preserved for a future roll it CAN close; a best-effort partial
    spend is strictly worse on expectation because it produces neither
    a success now nor a usable pool later.

    Each ``recommend(...)`` call:

      1. Returns immediately on events that aren't post-roll triggers
         (``AttackRolledEvent``, ``ParryRolledEvent``, or
         ``CounterattackRolledEvent``).
      2. Returns immediately on events whose ``action.subject()`` is
         not this character (i.e., bystander dispatch).
      3. Returns immediately if the pool is empty.
      4. Returns immediately if the resolved roll already meets or
         exceeds the action's TN (no point in spending).
      5. Computes ``points_needed = ceil(margin / 2)``. If the pool
         has fewer points than ``points_needed``, abstains entirely
         (the 2026-05-26 update: no partial spend that fails to clear
         the TN).
      6. Otherwise, spends exactly ``points_needed`` points. Each spent
         point adds +2 to the roll's total and decrements the pool by 1,
         exactly once per point (FR-009a-ii: multiple mode-B spends MAY
         target the same roll, each adding a further +2).

    Implementation choice (post-roll mutation): the strategy mutates the
    action's stored roll via ``action.set_skill_roll(new_total)`` AND
    overwrites ``event.roll`` so that downstream consumers see the
    bonused total. This mirrors the existing post-roll pattern used by
    ``simulation.strategies.base.SkillRolledStrategy``.

    No events are yielded (matches the ``EagerPhaseLowerStrategy``
    sibling). The spend is realized as a direct mutation of the action,
    event, and ``character._mirumoto_pool``. Trace logging surfaces the
    bonus.
    """

    def _is_post_roll_event(self, event: events.Event) -> bool:
        """Whether ``event`` is a post-roll trigger for mode B.

        Per FR-009: the spend MUST be declarable after dice have
        resolved. ``AttackRolledEvent``, ``ParryRolledEvent``, and
        ``CounterattackRolledEvent`` are fired in
        ``TakeAttackActionEvent.play``, ``TakeParryActionEvent.play``,
        and ``TakeCounterattackActionEvent.play`` immediately after
        ``action.roll_skill()`` is called, satisfying the "after you
        have seen your roll" clause. The rules clause "any type of
        attack or parry" includes the counterattack knack (FR-003).
        """
        return isinstance(
            event,
            (
                events.AttackRolledEvent,
                events.ParryRolledEvent,
                events.CounterattackRolledEvent,
            ),
        )

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        # Wrong-event guard (FR-009 timing): only post-roll triggers.
        if not self._is_post_roll_event(event):
            return
        # Subject guard: the rules clause is "after you have seen YOUR
        # roll" — bystanders may not spend their pool on someone else's
        # roll.
        action = event.action  # type: ignore[attr-defined]
        if action.subject() is not character:
            return
        # Pool guard: no pool, no spend.
        pool = _pool_remaining(character)
        if pool <= 0:
            return
        # Inspect the resolved roll (FR-009: after dice are resolved).
        current_roll = action.skill_roll()
        if current_roll is None:
            # Defensive: a post-roll event should always have a resolved
            # roll on the action, but if it doesn't, abstain.
            return
        tn = action.tn()
        margin = tn - current_roll
        if margin <= 0:
            # Roll already meets or exceeds TN; don't waste points.
            return
        # Each point gives +2. Compute the minimum number of points
        # required to clear the margin (FR-009a-ii allows stacking).
        points_needed = (margin + 1) // 2  # ceil(margin / 2)
        # 2026-05-26 update (Fix-D): abstain entirely when the pool
        # can't close the gap. A partial spend that still fails the TN
        # wastes pool points on a roll that fails anyway; saving them
        # for a future roll the strategy CAN close is strictly better
        # on expectation. See spec.md / research.md (2026-05-26).
        if pool < points_needed:
            return
        spent = 0
        for _ in range(points_needed):
            if not _try_spend_pool_point(character):
                # Race-safety: if the pool somehow drained between the
                # initial check and now, stop.
                break
            spent += 1
        if spent == 0:
            return
        bonus = 2 * spent
        new_roll = current_roll + bonus
        action.set_skill_roll(new_roll)
        # Update the event's roll field so downstream listeners see the
        # bonused total (mirrors SkillRolledStrategy in
        # simulation/strategies/base.py).
        event.roll = new_roll  # type: ignore[attr-defined]
        # SC-006 trace clarity: distinctive [Mirumoto 3rd Dan mode B]
        # marker plus the bonused skill, the points spent, the +bonus,
        # and the before/after roll totals so a reviewer can map this
        # spend to rules/04-schools.md Mirumoto Bushi School Third Dan
        # ("to provide a bonus of +2 on any type of attack or parry
        # after you have seen your roll"; FR-009).
        logger.debug(
            f"[Mirumoto 3rd Dan mode B] {character.name()} spent {spent} "
            f"point(s) for +{bonus} on {action.skill()} roll "
            f"({current_roll}->{new_roll}, TN {tn}); pool now "
            f"{_pool_remaining(character)}",
        )
        yield from ()
