#!/usr/bin/env python3

#
# mirumoto_school.py
#
# Implement Mirumoto Bushi School.
#
# School Ring: Void
# School Knacks: counterattack, double attack, iaijutsu
#
# Special Ability: TVP on parry (success or fail).
# 1st Dan: Extra rolled on parry, double attack, wound check
# 2nd Dan: Free raise on parry
# 3rd Dan: NewRoundListener grants 2*attack_skill resource points.
#          Spend to decrease action die by 1 for parry, or +2 on attack/parry after seeing roll.
# 4th Dan: Void+1/cost-discount; failed parries against this Mirumoto's
#          double attacks still suffer the auto-serious-wound (FR-012);
#          failed parries against this Mirumoto's regular attacks have
#          their damage-die-count reduction halved/floor (FR-013).
#          T012 wires the MirumotoAttackAction / MirumotoDoubleAttackAction
#          stubs; T013 / T014 fill them in.
# 5th Dan: Fifth Dan adds +10 modifier per VP on top of the standard
#          +1 rolled / +1 kept from the void point (combat rolls only).
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.actions import AttackAction, DoubleAttackAction
from simulation.listeners import AttackDeclaredListener, Listener
from simulation.log import logger
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import (
    AlwaysParryStrategy,
    AttackRolledStrategy,
    NeverParryStrategy,
    ParryRolledStrategy,
)
from simulation.strategies.mirumoto_third_dan import (
    EagerPhaseLowerStrategy,
    MarginalBonusStrategy,
)


class MirumotoBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md Mirumoto Bushi School Special Ability:
        # "Your successful or unsuccessful parries give you a temporary
        # void point." TVP-on-parry is the school's whole engine.
        #
        # Constitution Principle VIII (school identity drives defaults)
        # AND Principle IX (defaults must be playable) together require
        # this school to install ``AlwaysParryStrategy``: every parry --
        # success OR failure -- generates 1 TVP, so passing up parries
        # via the engine's default ``ReluctantParryStrategy`` (which only
        # parries when the hit is predicted dangerous) starves the
        # school's identity engine entirely. In a mirror match this
        # produces a combat that terminates by wound-check shootout while
        # the school's signature mechanics never fire -- a Principle IX
        # mirror-non-degeneracy failure.
        #
        # We also do NOT install ``CounterattackInterruptStrategy`` on
        # the ``"interrupt"`` slot, and do NOT set the counterattack
        # interrupt cost to 1 -- those are Daidoji/Hida defaults that
        # have no basis in the Mirumoto rules text.
        self._set_school_listener(character, "parry_succeeded", MirumotoParryTVPListener())
        self._set_school_listener(character, "parry_failed", MirumotoParryTVPListener())
        self._set_school_strategy(character, "parry", AlwaysParryStrategy())

    def apply_rank_three_ability(self, character: Any) -> None:
        # FR-007: NewRoundListener grants the per-round 2*attack_skill pool.
        self._set_school_listener(character, "new_round", MirumotoNewRoundListener())
        # FR-008 (mode A: phase-lower) + FR-009 (mode B: +2 after roll).
        # The two spend strategies live in `simulation/strategies/mirumoto_third_dan.py`
        # so playtesters can swap them without touching the combat loop
        # (FR-015 / Constitution Principle V).
        #
        # Wiring approach for mode A (option-b: reactive on AttackDeclaredEvent):
        #   - Strategy is installed on a new slot ``"mirumoto_phase_lower"`` so
        #     the engine's stock dispatch does not invoke it.
        #   - ``MirumotoAttackDeclaredListener`` (below) catches incoming
        #     enemy attack declarations and consults the strategy. This
        #     matches the rules text "decrease the phase of one of your
        #     actions ... in order to parry" -- the parry is the trigger,
        #     so the spend reacts to incoming attacks rather than pre-allocating.
        #
        # Wiring approach for mode B (chaining wrapper):
        #   - Strategy is installed on a new slot ``"mirumoto_post_roll_bonus"``.
        #   - The default ``attack_rolled``/``parry_rolled`` strategies are
        #     replaced by chaining wrappers (``MirumotoAttackRolledStrategy``,
        #     ``MirumotoParryRolledStrategy``) that first apply the +2 bonus
        #     then delegate to the default strategy's AP/conviction logic and
        #     ALWAYS yield the original event so downstream listeners
        #     (enemy parries, etc.) still fire (T009 simulator critique on
        #     event suppression -- regression guarded in tests).
        #   - For ``CounterattackRolledEvent`` (which the engine yields
        #     directly without a strategy hook), a dedicated listener
        #     ``MirumotoCounterattackRolledListener`` dispatches to the
        #     same strategy slot.
        self._set_school_strategy(character, "mirumoto_phase_lower", EagerPhaseLowerStrategy())
        self._set_school_strategy(character, "mirumoto_post_roll_bonus", MarginalBonusStrategy())
        self._set_school_listener(character, "attack_declared", MirumotoAttackDeclaredListener())
        self._set_school_listener(character, "counterattack_rolled", MirumotoCounterattackRolledListener())
        self._set_school_strategy(character, "attack_rolled", MirumotoAttackRolledStrategy())
        self._set_school_strategy(character, "parry_rolled", MirumotoParryRolledStrategy())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_action_factory(character, MIRUMOTO_ACTION_FACTORY)

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_roll_parameter_provider(character, MIRUMOTO_ROLL_PARAMETER_PROVIDER)

    def extra_rolled(self) -> list[str]:
        # rules/04-schools.md Mirumoto Bushi School First Dan:
        # "Roll one extra die on parry, double attack, and wound checks." (FR-005)
        return ["parry", "double attack", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["parry"]

    def name(self) -> str:
        return "Mirumoto Bushi School"

    def school_knacks(self) -> list[str]:
        return ["counterattack", "double attack", "iaijutsu"]

    def school_ring(self) -> str:
        return "void"


class MirumotoParryTVPListener(Listener):
    """
    Listener to implement the Mirumoto special ability:
    gain 1 TVP on parry (success or fail).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, (events.ParrySucceededEvent, events.ParryFailedEvent)):
            if event.action.subject() == character:
                yield events.GainTemporaryVoidPointsEvent(character, 1)


class MirumotoNewRoundListener(Listener):
    """
    Listener to implement the Mirumoto 3rd Dan technique:
    At the start of each round, grant 2*attack_skill resource points.
    These are stored as a pool on the character that can be spent
    to decrease action die phase by 1 for parry or +2 on attack/parry after seeing roll.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            # Grant resource pool
            attack_skill = character.skill("attack")
            pool = 2 * attack_skill
            character._mirumoto_pool = pool
            # SC-006 trace clarity: tag pool creation with a distinctive
            # marker so reviewers grepping the trace can map this event to
            # rules/04-schools.md Mirumoto Bushi School Third Dan ("At the
            # beginning of each round, you get 2X points, where X is equal
            # to your attack skill").
            logger.debug(
                f"[Mirumoto 3rd Dan] {character.name()} pool reset to {pool} "
                f"(2 x attack-skill {attack_skill})",
            )
        yield from ()


class MirumotoAttackDeclaredListener(Listener):
    """Mode-A (phase-lower) hook (FR-008): reactively lower a Mirumoto's
    scheduled action by 1 when an enemy declares an attack against them.

    Per rules/04-schools.md Mirumoto Bushi School Third Dan -- "Each point
    may be spent to decrease the phase of one of your actions by 1 in
    order to parry". The parry is the trigger, so the phase-lower spend
    fires when an enemy attack threatens the Mirumoto (not pre-allocated
    on phase boundaries).

    The listener:
      1. Preserves the engine's stock ``AttackDeclaredListener`` behavior
         (counterattack interrupt + lunge modifier handling) for
         non-subject events, so a 3rd-dan Mirumoto installing this
         listener does not regress those mechanics.
      2. When the attack TARGETS this Mirumoto (a parry-threatening
         situation), runs the 2026-05-26 Fix-C three-condition gate
         BEFORE consulting the phase-lower strategy. The gate enforces
         the user's 2026-05-26 clarification that points must only be
         spent when ALL of:

           (1) The character's parry strategy would parry this attack.
           (2) The character has no action currently available at phase
               <= context.phase() to parry with.
           (3) Lowering an action via the pool could actually make one
               available (delegated to the strategy itself; the strategy
               already implements floor/pool-size checks).

         If any precondition fails, the listener abstains (saves the
         points). Otherwise it synthesizes a ``NewPhaseEvent`` and
         consults the ``"mirumoto_phase_lower"`` strategy, which then
         decides exactly how many points to spend.

         Implementation choice (Option B / predictive intent check):
         precondition (1) is implemented as a heuristic at
         ``AttackDeclaredEvent`` time -- the parry strategy makes its
         actual decision later, on ``AttackRolledEvent``. The
         conservative-but-cheap heuristic here checks whether the
         strategy is ``NeverParryStrategy`` (guaranteed to decline)
         plus the basic group/adjacency/already-parried gates that all
         parry strategies enforce. For ``AlwaysParryStrategy`` /
         ``ReluctantParryStrategy``, condition (1) is treated as
         provisionally TRUE (a ``ReluctantParryStrategy`` may later
         decline a low-danger attack, in which case the spent point
         is wasted; this matches the user's framing "by whatever
         strategy has determined that" while keeping the mode-A
         policy lookahead-free).
    """

    def __init__(self) -> None:
        # Preserve stock attack-declared behavior; the base class
        # delegates to the character's interrupt strategy (the engine
        # default ``DefaultInterruptStrategy`` -- Mirumoto does not
        # override the interrupt slot per Constitution Principle VIII)
        # and handles lunge modifiers.
        self._stock = AttackDeclaredListener()

    def _would_parry_attack(self, character: Any, event: Any, context: Any) -> bool:
        """Predictive heuristic for Fix-C condition (1): would the
        character's parry strategy parry this incoming attack?

        Conservative -- returns True for any strategy other than
        ``NeverParryStrategy`` that passes the basic group/adjacency/
        already-parried gates. The actual per-attack decision (e.g.,
        ``ReluctantParryStrategy`` declining a small attack) happens
        later on ``AttackRolledEvent``; treating those as provisional
        "yes" matches the user's framing and avoids re-implementing
        damage-estimation logic at declaration time.

        Returns False when:
          - The parry strategy is ``NeverParryStrategy`` (guaranteed
            to decline).
          - The target is not in the character's group (parry strategies
            uniformly refuse to parry for enemies).
          - The character is not adjacent to the target (and is not the
            target themselves).
          - The attack is already parried (no re-parry needed).
        """
        # Guard (1a): NeverParryStrategy never parries; no point reserving
        # an action for a parry that won't happen.
        if isinstance(character.parry_strategy(), NeverParryStrategy):
            return False
        # Guard (1b): target must be in the character's group. All
        # BaseParryStrategy subclasses enforce this (`event.action.target()
        # not in character.group()` -> bail), so reserving an action for
        # an out-of-group attack is wasted.
        target = event.action.target()
        if target not in character.group():
            return False
        # Guard (1c): if the target is someone else, the character must
        # be adjacent (parry strategies refuse non-adjacent ally-parries).
        if target is not character:
            if not context.formation().is_adjacent(character, target):
                return False
        # Guard (1d): if the attack has already been parried (e.g.,
        # by a friendly who acted earlier), no further parry is needed.
        if event.action.parried():
            return False
        return True

    def _has_usable_action(self, character: Any, context: Any) -> bool:
        """Predictive heuristic for Fix-C condition (2): does the
        character already have an action at phase <= context.phase()
        that could be used to parry?

        Per the user's 2026-05-26 clarification, the literal check is
        ``any(p <= context.phase() for p in character.actions())``.
        Interrupt-action capability is intentionally NOT considered
        here: an interrupt parry costs more action dice than a
        regular action, so spending mode-A to convert a scheduled
        action into a usable parry is strictly cheaper than burning
        an interrupt -- mode-A remains preferable in the
        interrupt-fallback case.
        """
        return any(p <= context.phase() for p in character.actions())

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if not isinstance(event, events.AttackDeclaredEvent):
            return
        # Always run the stock behavior so counterattack interrupts and
        # lunge modifier handling still fire (T009 simulator regression
        # guard: must not break enemy parry / counterattack cascades).
        yield from self._stock.handle(character, event, context)
        # Mode-A spend: only when the attack targets THIS Mirumoto.
        if event.action.target() is not character:
            return
        # Don't spend if no strategy is installed (e.g., character did not
        # have apply_rank_three_ability run).
        strategy = character._strategies.get("mirumoto_phase_lower")
        if strategy is None:
            return
        # 2026-05-26 Fix-C precondition (1): abstain if the parry
        # strategy would not parry this attack (saves the points).
        if not self._would_parry_attack(character, event, context):
            logger.debug(
                f"[Mirumoto 3rd Dan mode A] {character.name()} abstains: "
                f"parry strategy would not parry this attack (Fix-C "
                f"condition (1))",
            )
            return
        # 2026-05-26 Fix-C precondition (2): abstain if an action is
        # already available to parry with (the parry can happen for
        # free; no mode-A needed). Precondition (3) -- pool sufficient
        # to actually enable usability -- is delegated to the strategy
        # itself, which already implements the floor / pool / minimum-
        # spend logic per the T010 fix-cycle-1 parry-reservation gap.
        if self._has_usable_action(character, context):
            logger.debug(
                f"[Mirumoto 3rd Dan mode A] {character.name()} abstains: "
                f"action already available at phase <= "
                f"{context.phase()} (Fix-C condition (2))",
            )
            return
        # All three preconditions hold (modulo (3), which the strategy
        # checks). Synthesize the NewPhaseEvent the strategy's filter
        # expects so EagerPhaseLowerStrategy (T008) does not need to be
        # modified to accept reactive AttackDeclaredEvents (FR-015
        # separation of concerns: the wiring is here, the policy is
        # there).
        synthetic = events.NewPhaseEvent(context.phase())
        yield from strategy.recommend(character, synthetic, context)


class MirumotoCounterattackRolledListener(Listener):
    """Mode-B hook for counterattack rolls (FR-009).

    The engine's ``TakeCounterattackActionEvent.play`` yields a
    ``CounterattackRolledEvent`` directly (no strategy hook -- compare
    ``TakeAttackActionEvent`` and ``TakeParryActionEvent`` which call
    ``attack_rolled_strategy()`` / ``parry_rolled_strategy()`` for
    post-roll resource spending). To give the 3rd-dan Mirumoto a chance
    to spend a pool point for the +2 bonus on a counterattack roll,
    this listener dispatches to the ``"mirumoto_post_roll_bonus"``
    strategy slot when the counterattacker is this character.

    The rules clause "any type of attack or parry after you have seen
    your roll" covers counterattack (a Mirumoto school knack per FR-003).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if not isinstance(event, events.CounterattackRolledEvent):
            return
        if event.action.subject() is not character:
            return
        strategy = character._strategies.get("mirumoto_post_roll_bonus")
        if strategy is None:
            return
        yield from strategy.recommend(character, event, context)


class _MirumotoPostRollBonusChainMixin:
    """Mixin shared by ``MirumotoAttackRolledStrategy`` and
    ``MirumotoParryRolledStrategy``: invokes the post-roll bonus strategy
    BEFORE the default strategy runs, so the default strategy's AP /
    conviction / floating-bonus spending decisions see the bonused roll.

    Critical (T009 simulator critique): the chain MUST still yield the
    original event so downstream listeners (enemy parries via
    ``AttackRolledListener`` -> ``DefaultInterruptStrategy``, etc.) fire.
    The default strategy already yields the (post-resource-spending)
    event; this mixin therefore relies on super().recommend(...) to
    re-emit it. The post-roll bonus strategy itself ends with
    ``yield from ()`` (it mutates ``event.roll`` and
    ``action.skill_roll()`` directly), so it neither suppresses nor
    duplicates the event.
    """

    def _apply_post_roll_bonus(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        strategy = character._strategies.get("mirumoto_post_roll_bonus")
        if strategy is None:
            return
        yield from strategy.recommend(character, event, context)


class MirumotoAttackRolledStrategy(AttackRolledStrategy, _MirumotoPostRollBonusChainMixin):
    """Chained ``attack_rolled`` strategy for 3rd-dan Mirumoto Bushi.

    Per rules/04-schools.md Mirumoto Bushi School Third Dan: applies the
    +2 post-roll bonus (mode B) BEFORE the default AP/conviction logic so
    the default strategy sees the bonused roll and does not redundantly
    spend resources to clear a margin that the Mirumoto pool already
    closed (FR-009 / FR-015).
    """

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        yield from self._apply_post_roll_bonus(character, event, context)
        yield from super().recommend(character, event, context)


class MirumotoParryRolledStrategy(ParryRolledStrategy, _MirumotoPostRollBonusChainMixin):
    """Chained ``parry_rolled`` strategy for 3rd-dan Mirumoto Bushi.

    Mirror of ``MirumotoAttackRolledStrategy`` for parry rolls. The
    rules clause covers "any type of attack or parry," so the same
    +2 mode-B spend opportunity exists on the parry side.
    """

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        yield from self._apply_post_roll_bonus(character, event, context)
        yield from super().recommend(character, event, context)


class MirumotoAttackAction(AttackAction):
    """
    Custom AttackAction for the Mirumoto 4th Dan attack-side ability.

    rules/04-schools.md Mirumoto Bushi School Fourth Dan: "against your
    regular attacks the number of extra rolled damage dice the failed
    parry reduced is cut in half (rounded down)" (FR-013). That behavior
    fires on the ATTACKER's action (because the reduction is applied to
    the Mirumoto's attack damage dice), so the override hangs off this
    subclass rather than off ParryAction.

    The base ``AttackAction.calculate_extra_damage_dice`` returns 0 when
    ``parry_attempted()`` is True (the full would-be-extra dice count is
    "reduced" away by any parry attempt, successful or failed). FR-013
    halves the reduction on FAILED parries only -- successful parries
    and no-parry-attempted cases defer to the base class.
    """

    def calculate_extra_damage_dice(self, skill_roll: int | None = None, tn: int | None = None) -> int:
        """FR-013: on a FAILED parry against this Mirumoto's regular
        attack, halve the damage-die-count reduction (integer floor).

        The base class collapses the reduction to "all" on any parry
        attempt -- returns 0. To halve the reduction we compute the
        would-be-extra-dice count (the no-parry path) and the
        would-be-reduction (== would-be-extra, since the base class
        zeroes the entire amount). The halved reduction is
        ``would_be_reduction // 2``; the resulting extra dice is
        ``max(0, would_be_extra - would_be_reduction // 2)``. The
        ``max(0, ...)`` guard handles the spec.md Edge Cases bullet
        ("1 -> 0") and the skill-roll-below-TN case where the base
        formula yields a negative.
        """
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn()
        # Only the FAILED-parry branch fires FR-013. Successful parries
        # (parry_attempted AND parried) and no-parry-attempted cases
        # defer to the base class for baseline behavior.
        if self.parry_attempted() and not self.parried():
            assert skill_roll is not None
            # would-be-extra: what the base class returns when no parry
            # was attempted (the unmitigated extra-dice count).
            would_be_extra = (skill_roll - tn) // 5
            # would-be-reduction: what the failed parry would normally
            # remove. In the base AttackAction model the entire
            # would-be-extra is reduced (return 0), so reduction equals
            # would-be-extra.
            would_be_reduction = would_be_extra
            # FR-013 halves the reduction (integer floor) and floors
            # the resulting extra-dice count at 0.
            result = max(0, would_be_extra - would_be_reduction // 2)
            # SC-006 trace clarity: log the original would-be-extra count
            # and the halved result so a reviewer can verify the
            # arithmetic against rules/04-schools.md Mirumoto Bushi
            # School Fourth Dan ("the number of extra rolled damage dice
            # the failed parry reduced is cut in half (rounded down)").
            logger.debug(
                f"[Mirumoto 4th Dan] failed-parry damage-die reduction "
                f"halved: would-be-extra {would_be_extra} -> {result} "
                f"(reduction {would_be_reduction} -> {would_be_reduction // 2}; "
                f"FR-013)",
            )
            return result
        return super().calculate_extra_damage_dice(skill_roll, tn)


class MirumotoDoubleAttackAction(DoubleAttackAction):
    """
    Custom DoubleAttackAction for the Mirumoto 4th Dan double-attack ability.

    rules/04-schools.md Mirumoto Bushi School Fourth Dan: "Failed parries
    against your double attacks do not prevent the automatic serious
    wound." (FR-012 / US3.3).

    The base ``DoubleAttackAction.direct_damage`` (simulation/actions.py
    lines 226-231) returns ``None`` whenever ``self.parry_attempted()`` is
    True, suppressing the double-attack auto-SW on BOTH a successful and a
    failed parry. Per the FR-012 Q3 clarification ("Narrow scope. Only the
    auto-SW prevention is removed"), the Mirumoto override must:

      1. Defer to the base class when no parry was attempted (baseline
         auto-SW path -- regression guard).
      2. Preserve the successful-parry suppression (parry that lands still
         prevents the auto-SW).
      3. Restore the auto-SW event when the parry was attempted but failed
         (``parry_attempted() and not parried()``).

    The override touches ONLY ``direct_damage``; the standard failed-parry
    damage-die-count handling in ``calculate_extra_damage_dice`` is
    inherited unchanged, per Q3.
    """

    def direct_damage(self) -> Any:
        # rules/04-schools.md Mirumoto Bushi School Fourth Dan: failed
        # parries against this Mirumoto's double attacks do NOT prevent
        # the automatic serious wound (FR-012).
        if self.parry_attempted() and not self.parried():
            # Failed-parry branch: emit a SeriousWoundsDamageEvent with
            # BOTH the standard ``_from_double_attack`` marker AND a
            # Mirumoto-specific ``_mirumoto_4th_dan`` marker so the
            # trace renderer can attribute the auto-SW to the
            # Mirumoto-school override rather than the generic
            # "(double attack penalty)" label. Per the 2026-05-30 user
            # report, the bare "(double attack penalty)" label after
            # a failed parry looks like a rules violation to a reader
            # unfamiliar with the Mirumoto 4th Dan exception.
            event = events.SeriousWoundsDamageEvent(self.subject(), self.target(), 1)
            event._from_double_attack = True  # type: ignore[attr-defined]
            event._mirumoto_4th_dan = True  # type: ignore[attr-defined]
            logger.debug(
                f"[Mirumoto 4th Dan] auto-serious-wound lands on "
                f"{self.target().name()} (failed parry against double "
                f"attack -- FR-012)",
            )
            return event
        # No parry attempted -> defer to the base class (auto-SW lands).
        # Successful parry -> defer to the base class (returns None).
        return super().direct_damage()


class MirumotoActionFactory(DefaultActionFactory):
    """
    ActionFactory for Mirumoto 4th Dan: routes ``attack`` to
    ``MirumotoAttackAction`` (FR-013: halved failed-parry damage-die
    reduction on regular attacks) and ``double attack`` to
    ``MirumotoDoubleAttackAction`` (FR-012: failed-parry against a
    double attack still suffers the auto-serious-wound) so the Fourth
    Dan attacker-side hooks can attach to those subclasses without
    disturbing the rest of the engine. All other skills (feint, lunge,
    iaijutsu, counterattack, parry) fall through to the default factory.
    """

    def get_attack_action(self, subject: Any, target: Any, skill: str, initiative_action: Any, context: Any, vp: int = 0) -> Any:
        if skill == "attack":
            return MirumotoAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        elif skill == "double attack":
            return MirumotoDoubleAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


MIRUMOTO_ACTION_FACTORY = MirumotoActionFactory()


# FR-014 combat-roll scope: per the spec.md Clarifications Session
# 2026-05-26 the Fifth Dan +10 bonus applies to all attack-class
# skills plus parry (and wound check, which flows through a separate
# provider method). The user's framing: "apply it to everything in
# case a Mirumoto ends up with it despite it not being in their
# school" -- so we include the full ``ATTACK_SKILLS`` set
# (attack, counterattack, double attack, feint, iaijutsu, lunge) plus
# ``parry``. The seven-skill whitelist below pairs with the dedicated
# wound-check provider method to cover the rules/04-schools.md
# Mirumoto Bushi School Fifth Dan combat-roll scope. Non-combat rolls
# (e.g., a 5th-dan Mirumoto spending a VP on ``investigation`` or
# another BASIC_SKILL) get only the standard void-spend bonus, never
# the +10 modifier delta.
_MIRUMOTO_FIFTH_DAN_COMBAT_SKILLS = frozenset(ATTACK_SKILLS) | {"parry"}


class MirumotoRollParameterProvider(DefaultRollParameterProvider):
    """
    RollParameterProvider to implement the Mirumoto 5th Dan ability:
    Fifth Dan adds +10 modifier per VP on top of the standard +1
    rolled / +1 kept from the void point (FR-014). Per spec.md
    Clarifications Session 2026-05-26 the combat-roll scope covers all
    attack-class skills (``attack``, ``counterattack``, ``double
    attack``, ``feint``, ``iaijutsu``, ``lunge``) plus ``parry`` -- the
    user's framing was "apply it to everything in case a Mirumoto ends
    up with it despite it not being in their school" -- and wound
    checks, which are handled by the dedicated
    ``get_wound_check_roll_params`` method below. Non-combat skill
    rolls (e.g., ``investigation``, ``etiquette``) receive only the
    standard void-spend bonus per US4.4.

    Example (per spec.md Clarifications 2026-05-26): a 6k4 wound check
    with 1 VP spent becomes 7k5 + 10 -- the default provider supplies
    the +1 rolled / +1 kept dice, and this provider stacks a flat +10
    modifier per VP on top.
    """

    def get_skill_roll_params(self, character: Any, target: Any, skill: str, contested_skill: str | None = None, ring: str | None = None, vp: int = 0) -> tuple[int, int, int]:
        (rolled, kept, modifier) = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        # FR-014 / US4.4: the +10 modifier delta only applies on the
        # combat-roll scope -- per spec.md Clarifications Session
        # 2026-05-26 that scope is all attack-class skills (attack,
        # counterattack, double attack, feint, iaijutsu, lunge) plus
        # parry. Non-combat skills like ``investigation``, ``etiquette``,
        # etc. receive ONLY the standard void-spend bonus already
        # credited by the default provider's +1 rolled / +1 kept dice
        # per VP.
        if vp > 0 and skill in _MIRUMOTO_FIFTH_DAN_COMBAT_SKILLS:
            delta = 10 * vp
            modifier += delta
            # SC-006 trace clarity: surface the +10/VP modifier delta
            # separately from the standard void-spend bonus (the +1
            # rolled / +1 kept dice the default provider already
            # credits). The +10 stacks on top of the standard
            # void-spend dice bonus -- rules/04-schools.md Mirumoto
            # Bushi School Fifth Dan (FR-014).
            logger.debug(
                f"[Mirumoto 5th Dan] +{delta} VP-modifier bonus on "
                f"{skill} roll for {character.name()} ({vp} VP; FR-014, "
                f"on top of standard +1 rolled / +1 kept per VP)",
            )
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character: Any, vp: int = 0) -> tuple[int, int, int]:
        (rolled, kept, modifier) = super().get_wound_check_roll_params(character, vp)
        # Wound check is the third entry in the FR-014 combat-roll
        # scope; the dedicated provider method always applies the +10
        # modifier delta per VP when VP is spent.
        if vp > 0:
            delta = 10 * vp
            modifier += delta
            # SC-006 trace clarity (wound-check branch).
            logger.debug(
                f"[Mirumoto 5th Dan] +{delta} VP-modifier bonus on "
                f"wound check for {character.name()} ({vp} VP; FR-014, "
                f"on top of standard +1 rolled / +1 kept per VP)",
            )
        return normalize_roll_params(rolled, kept, modifier)


MIRUMOTO_ROLL_PARAMETER_PROVIDER = MirumotoRollParameterProvider()
