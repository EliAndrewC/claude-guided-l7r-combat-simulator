#!/usr/bin/env python3

#
# akodo_school.py
#
# Implement Akodo Bushi School.
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.floating_bonuses import AnyAttackFloatingBonus
from simulation.schools.base import BaseSchool
from simulation.strategies.base import BaseAttackStrategy, Strategy, WoundCheckRolledStrategy


class AkodoBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_listener(character, "lw_damage", AkodoLightWoundsDamageListener())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # Install Akodo's strategy at the wound_check_rolled slot so
        # the listener's dispatch through character.wound_check_rolled_strategy()
        # picks up the 4th-Dan VP-for-raise behavior (layered on top of
        # the engine default's FB/AP/conviction selection via super
        # delegation).
        self._set_school_strategy(character, "wound_check_rolled", AkodoWoundCheckRolledStrategy())
        self._set_school_listener(character, "wound_check_declared", AkodoWoundCheckDeclaredListener())

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_listener(character, "wound_check_succeeded", AkodoWoundCheckSucceededListener())

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Akodo Bushi School: Special Ability":
        # "You get four temporary void points after a successful feint
        # and one void point after an unsuccessful feint."  The two
        # listeners below are the TVP faucet.  Per Constitution Principle
        # VIII (school identity drives defaults), the school's default
        # attack strategy MUST exercise feint -- because the engine
        # default ``UniversalAttackStrategy`` gates feint behind
        # ``vp() == 0`` (simulation/strategies/base.py line ~208), the
        # signature TVP economy NEVER fires under defaults.  This is the
        # P0 Principle IX defect documented in
        # specs/004-akodo-bushi-school/OPEN_QUESTIONS.md Q7.
        #
        # Wiring choices (cf. Mirumoto precedent in
        # simulation/schools/mirumoto_school.py::apply_special_ability):
        #
        #  (a) ``AkodoAttackStrategy`` (defined below) is installed on
        #      the ``"attack"`` slot.  Its three-branch policy --
        #      kill-shot > feint-first > plain-attack fallback --
        #      ensures the TVP economy (FR-026) actually fires AND that
        #      finishing damage is preferred over fuel when an opponent
        #      is at sw_remaining()<=1.  This fuels every higher-Dan
        #      ability that depends on VP (4th Dan WC raises, 5th Dan
        #      counter-damage).
        #
        #  (b) NO ``CounterattackInterruptStrategy`` is installed on the
        #      ``"interrupt"`` slot.  Akodo has no counterattack knack
        #      (school knacks: ``double attack``, ``feint``,
        #      ``iaijutsu``); the engine default
        #      ``DefaultInterruptStrategy`` (routes incoming attacks to
        #      the parry strategy) is correct.  This is the
        #      Mirumoto-precedent regression guard: the same bug was
        #      caught and fixed for Mirumoto in commit 89dc0bb.
        #
        #  (c) NO ``AlwaysParryStrategy`` is installed on the ``"parry"``
        #      slot.  The engine default ``ReluctantParryStrategy``
        #      (parries only when an attack predicts >=2 SW) is correct
        #      for Akodo: the school's defense is the wound-check stack
        #      (1st Dan extra die + 2nd Dan free raise + 3rd Dan
        #      floating bonus + 4th Dan VP raises + 5th Dan
        #      counter-damage), NOT always-parry.  Installing always-
        #      parry here would create an action-disadvantage / mirror
        #      degeneracy that fails Principle IX 3.
        self._set_school_listener(character, "attack_failed", AkodoAttackFailedListener())
        self._set_school_listener(character, "attack_succeeded", AkodoAttackSucceededListener())
        self._set_school_strategy(character, "attack", AkodoAttackStrategy())

    def extra_rolled(self) -> list[str]:
        return ["attack", "double attack", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["wound check"]

    def name(self) -> str:
        return "Akodo Bushi School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "feint", "iaijutsu"]

    def school_ring(self) -> str:
        return "water"


class AkodoAttackFailedListener(Listener):
    """
    Listener to implement the Akodo special ability
    to gain 1 TVP on a failed feint.

    rules/04-schools.md "Akodo Bushi School: Special Ability".
    Tags the emitted event with ``source="Akodo Special Ability"``
    so the trace formatter renders the attribution per
    Constitution Principle VII / FR-006.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackFailedEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    yield events.GainTemporaryVoidPointsEvent(
                        character, 1, source="Akodo Special Ability",
                    )


class AkodoAttackSucceededListener(Listener):
    """
    Listener to implement the Akodo special ability
    to gain 4 TVP on a successful feint.

    rules/04-schools.md "Akodo Bushi School: Special Ability".
    Tags the emitted event with ``source="Akodo Special Ability"``
    so the trace formatter renders the attribution per
    Constitution Principle VII / FR-006.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackSucceededEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    yield events.GainTemporaryVoidPointsEvent(
                        character, 4, source="Akodo Special Ability",
                    )


class AkodoLightWoundsDamageListener(Listener):
    """
    Listener to implement the Akodo 5th Dan technique.

    Replaces the engine default ``LightWoundsDamageListener`` (so the
    5th Dan counter-damage strategy can interleave between the LW take
    and the WC dispatch).  Mirrors the engine default's structure
    including the ``event.damage > 0`` gate on the WC + counter
    dispatch (matching simulation/listeners.py::LightWoundsDamageListener).
    """

    def __init__(self) -> None:
        self._strategy = AkodoFifthDanStrategy()

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.LightWoundsDamageEvent):
            if event.subject != character:
                # observe another character's damage roll
                character.knowledge().observe_damage_roll(event.subject, event.damage)
            if event.target == character:
                character.take_lw(event.damage)
                # continue with wound check + 5th Dan counter only on
                # nonzero damage (matches engine default's gate at
                # simulation/listeners.py::LightWoundsDamageListener).
                if event.damage > 0:
                    yield from character.wound_check_strategy().recommend(character, event, context)
                    yield from self._strategy.recommend(character, event, context)


class AkodoFifthDanStrategy(Strategy):
    """
    Strategy to decide how to use the Akodo 5th Dan technique
    to spend VP after taking damage to directly inflict 10 LW
    per VP spent to the attacker.

    Per FR-022 the formula is
    ``max_vp = min(available_vp_for_damage, max_vp_per_roll,
    event.damage // 10)``.  Per FR-023 the counter-damage event is
    a NEW ``LightWoundsDamageEvent`` (not a wrapped/modified version
    of the incoming event), so the attacker's own school listeners
    (e.g., a mirror 5th-Dan Akodo) can react to it.  Per FR-024 the
    emitted ``SpendVoidPointsEvent`` and counter-damage event are
    tagged with ``source="Akodo 5th Dan"`` so the trace formatter
    renders the attribution with the numeric breakdown.

    rules/04-schools.md "Akodo Bushi School: Fifth Dan".
    """

    def recommend(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.LightWoundsDamageEvent):
            if event.target == character:
                # calculate max vp spendable on damage
                available_vp = character.void_point_manager().vp("damage")
                max_vp_for_damage = event.damage // 10
                max_vp = min(available_vp, character.max_vp_per_roll(), max_vp_for_damage)
                if max_vp > 0:
                    yield events.SpendVoidPointsEvent(
                        character, "damage", max_vp,
                        source="Akodo 5th Dan",
                    )
                    yield events.LightWoundsDamageEvent(
                        character, event.subject, 10 * max_vp,
                        source="Akodo 5th Dan",
                    )


class AkodoWoundCheckSucceededListener(Listener):
    """
    Listener to implement the Akodo 3rd Dan technique
    to gain a floating bonus after a successful Wound Check.

    rules/04-schools.md "Akodo Bushi School: Third Dan".

    Per Constitution Principle VII the listener emits a
    ``GainFloatingBonusEvent`` AFTER appending the bonus.  The event is
    pure observability -- there is no engine-side handler for it; the
    trace formatter renders it with the source attribution and the
    numeric breakdown (margin ÷ 5 × attack skill).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.WoundCheckSucceededEvent):
            if event.subject == character:
                margin = event.roll - event.damage
                attack_skill = character.skill("attack")
                bonus_value = (margin // 5) * attack_skill
                bonus = AnyAttackFloatingBonus(bonus_value, source="Akodo 3rd Dan")
                character.gain_floating_bonus(bonus)
                yield events.GainFloatingBonusEvent(
                    character,
                    bonus,
                    source="Akodo 3rd Dan",
                    breakdown=(
                        f"margin {margin} ÷ 5 × attack {attack_skill}"
                    ),
                )
                # if the character may keep LW, consult the character's light wounds strategy
                yield from character.light_wounds_strategy().recommend(character, event, context)


class AkodoWoundCheckDeclaredListener(Listener):
    """
    Listener for the Akodo 4th Dan technique to spend Void Points
    after a Wound Check roll to apply Free Raises to the roll.

    Mirrors the engine default ``WoundCheckDeclaredListener``
    (simulation/listeners.py) so that:
      * pre-declared ``event.vp`` is actually deducted via a
        ``SpendVoidPointsEvent`` (instead of being consumed "for free"
        by the roll-bonus path),
      * ``tn`` and the ``duel``/``explode`` flag are propagated to the
        synthesized ``WoundCheckRolledEvent`` + ``roll_wound_check``
        call (so custom-TN and iaijutsu-duel paths work),
      * the post-roll dispatch goes through
        ``character.wound_check_rolled_strategy()`` (the school
        installs ``AkodoWoundCheckRolledStrategy`` at the
        ``wound_check_rolled`` slot in ``apply_rank_four_ability``,
        so the engine default's resource selection -- floating
        bonuses, AP, conviction -- is still available alongside the
        Akodo VP-for-raise on top).

    rules/04-schools.md "Akodo Bushi School: Fourth Dan".
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.WoundCheckDeclaredEvent):
            if event.subject == character:
                explode = not getattr(event, "duel", False)
                roll = character.roll_wound_check(event.damage, event.vp, explode=explode)
                if event.vp > 0:
                    yield events.SpendVoidPointsEvent(character, "wound check", event.vp)
                # rules/04-schools.md "Hida Bushi School: Fifth Dan":
                # "Add X to YOUR wound check on the damage from the
                # attack you counterattacked."  Apply the bonus only
                # when the Akodo is the counterattacker themselves
                # (cross-trained Akodo+Hida); a non-counterattacking
                # Akodo defended by an adjacent Hida MUST NOT receive
                # the bonus on its own WC.  Gate on the counterattacker
                # reference stored alongside the margin by
                # ``HidaCounterattackSucceededListener``.
                attack_action = getattr(event, "attack_action", None)
                bonus = 0
                if attack_action is not None:
                    counterattacker = getattr(
                        attack_action, "_counterattack_excess_counterattacker",
                        None,
                    )
                    if counterattacker is character:
                        bonus = getattr(
                            attack_action, "_counterattack_excess_margin", 0,
                        ) or 0
                if bonus:
                    roll += bonus
                initial_roll = events.WoundCheckRolledEvent(
                    character, event.attacker, event.damage, roll, tn=event.tn,
                )
                if bonus:
                    initial_roll._hida_5th_dan_excess_bonus = bonus  # type: ignore[attr-defined]
                yield from character.wound_check_rolled_strategy().recommend(
                    character, initial_roll, context,
                )


class AkodoWoundCheckRolledStrategy(WoundCheckRolledStrategy):
    """
    Strategy for the Akodo 4th Dan technique to decide whether to
    spend Void Points after a Wound Check roll.  Each VP spent adds
    +5 to the roll (one Free Raise equivalent), reducing the resulting
    Serious Wound count.

    Inherits from the engine default ``WoundCheckRolledStrategy`` so
    Akodo characters at Dan 4+ retain access to the default's
    floating-bonus / AP / conviction resource menu.  Akodo's
    VP-for-raise is layered on TOP of the default's resource selection:

      1. Run super().recommend() -- collect FB/AP/conviction spends and
         the resulting (possibly adjusted) WoundCheckRolledEvent.
      2. If the post-default expected SW is still > Akodo's tolerable
         threshold, find the smallest additional VP spend that brings
         expected SW into ``min(1, sw_remaining())``.  Per OPEN_QUESTIONS
         Q2 / FR-018, ties prefer the smallest spend.
      3. Yield the super's spends, then Akodo's SpendVoidPointsEvent
         (if any), then the final WoundCheckRolledEvent.

    Per FR-017 the VP iteration considers every spend from 1 through
    ``max_spend = min(available_vp_for_wc, max_vp_per_roll)``
    INCLUSIVE.  The skeleton's ``range(1, max_spend)`` excluded
    ``max_spend`` itself; the fix is ``range(1, max_spend + 1)``.

    Per FR-019 the emitted ``SpendVoidPointsEvent`` is tagged with
    ``source="Akodo 4th Dan"`` so the trace formatter renders the
    attribution and numeric breakdown.

    rules/04-schools.md "Akodo Bushi School: Fourth Dan".
    """

    def recommend(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if not isinstance(event, events.WoundCheckRolledEvent):
            return
        if event.subject != character:
            return

        # Step 1: run the engine default to spend FB / AP / conviction.
        # Collect events so we can separate the spends from the final WC
        # event we may need to adjust further.
        default_events = list(super().recommend(character, event, context))
        prior_spends: list[events.Event] = []
        wc_event: events.WoundCheckRolledEvent = event
        for e in default_events:
            if isinstance(e, events.WoundCheckRolledEvent):
                wc_event = e
            else:
                prior_spends.append(e)

        # Step 2: compute Akodo VP-for-raise on top of the post-default
        # roll, per FR-018 (smallest spend reaching tolerable;
        # smallest-tie-break otherwise).
        tolerable_sw = min(1, character.sw_remaining())
        current_expected = character.wound_check(wc_event.roll)
        if current_expected <= tolerable_sw:
            # Default already brought us into tolerable range; no VP needed.
            yield from prior_spends
            yield wc_event
            return

        available_vp = character.void_point_manager().vp("wound check")
        max_spend = min(available_vp, character.max_vp_per_roll())
        chosen_spend = 0
        best_sw = current_expected
        # Iterate 1..max_spend INCLUSIVE (FR-017 off-by-one fix).
        for vp in range(1, max_spend + 1):
            new_roll = wc_event.roll + (5 * vp)
            expected_sw = character.wound_check(new_roll)
            if expected_sw <= tolerable_sw:
                chosen_spend = vp
                best_sw = expected_sw
                break
            if expected_sw < best_sw:
                chosen_spend = vp
                best_sw = expected_sw
            # On ties, do NOT update chosen_spend -- preserve the
            # smallest-spend tie-break (OPEN_QUESTIONS Q2 / FR-018).

        # Step 3: emit prior spends, the Akodo VP spend (if any), and
        # the final WC event with the further-adjusted roll.
        yield from prior_spends
        new_roll = wc_event.roll + (5 * chosen_spend)
        if chosen_spend > 0:
            yield events.SpendVoidPointsEvent(
                character, "wound check", chosen_spend,
                source="Akodo 4th Dan",
            )
        yield events.WoundCheckRolledEvent(
            character, wc_event.attacker, wc_event.damage, new_roll, tn=wc_event.tn,
        )


class AkodoAttackStrategy(BaseAttackStrategy):
    """Attack strategy for Akodo Bushi School (Constitution Principle VIII
    / IX, FR-026).

    The engine default ``UniversalAttackStrategy`` gates feint behind
    ``character.vp() == 0`` (simulation/strategies/base.py line ~208).
    Since Akodo's ``character.vp()`` is rarely zero (water-ring max VP +
    accumulated TVP), the engine default never reaches the feint branch,
    so the school's signature TVP economy NEVER fires under defaults --
    a P0 Principle IX defect (see
    specs/004-akodo-bushi-school/OPEN_QUESTIONS.md Q7).

    This strategy implements the three-branch policy per the strategy-
    designer's resolution:

      1. **Kill-shot branch** -- when ``target.sw_remaining() <= 1`` AND
         ``character.vp() >= 1``, prefer damage over fuel: try
         ``double attack`` at threshold 0.6 first, then ``attack`` at
         0.7.  Finishing the opponent eliminates incoming damage faster
         than accumulating another 4 TVP from a feint would.

      2. **Feint-first branch** -- when feint skill > 0 (Akodo's TVP
         faucet is available), try ``feint`` at threshold 0.6.  This is
         the engine that fuels every higher-Dan ability:
           * 4th Dan WC raises (FR-018) consume VP.
           * 5th Dan counter-damage (FR-022) consumes VP.
         Both require accumulated VP/TVP -- so feinting first is the
         identity-driven default per Principle VIII.

      3. **Plain-attack fallback** -- when feint is unavailable (skill=0)
         or the feint check fails at threshold 0.6, fall back to
         ``attack`` at 0.7, then desperation 0.01, then
         ``HoldActionEvent``.  Same ladder as ``PlainAttackStrategy``.

    Thresholds were chosen by the strategy-designer:
      * double_attack 0.6 (lower -- low success is OK because the auto-SW
        on success is decisive for a kill-shot).
      * attack 0.7 (canonical attack threshold, matches engine default).
      * feint 0.6 (lower -- failure also generates TVP, so a marginal
        feint is still net-positive vs holding the action).
      * desperate attack 0.01 (last-resort, matches PlainAttackStrategy).

    rules/04-schools.md "Akodo Bushi School: Special Ability" (TVP on
    feint).  Constitution Principles VIII (identity drives defaults) +
    IX (defaults must be playable + identity engine must fire in mirror).
    """

    def _try_kill_shot(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Kill-shot branch -- only fires when an enemy can be finished.

        Iterates targets via the character's target_finder and checks
        whether the easiest target has ``sw_remaining() <= 1``.  If so,
        and the character has VP available, tries ``double attack``
        (0.6) then ``attack`` (0.7).  Returns an iterator yielding the
        spend_action + take_attack pair, or empty if the branch doesn't
        engage.
        """
        # Branch-engagement check: need at least 1 VP AND a target that's
        # one hit from defeat.
        if character.vp() < 1:
            return
        # Probe the easiest target via the character's target_finder.
        # We use a double-attack initiative_action because double_attack
        # is the first kill-shot attempt -- the target_finder returns the
        # same easiest target regardless of skill choice (it's a
        # probability calculation).
        initiative_action = self.choose_action(character, "double attack", context)
        target = character.target_finder().find_target(
            character, "double attack", initiative_action, context,
        )
        if target is None or target.sw_remaining() > 1:
            return
        # Branch engaged -- try double_attack then attack.
        logger.debug(
            f"[Akodo Attack Strategy] kill-shot branch engaged: "
            f"{character.name()} targeting {target.name()} "
            f"(sw_remaining={target.sw_remaining()}, vp={character.vp()})",
        )
        action_event = self.try_skill(character, "double attack", initiative_action, 0.6, context)
        if action_event is not None:
            yield from self.spend_action(character, "double attack", initiative_action)
            yield action_event
            return
        # double_attack didn't meet threshold; try plain attack at 0.7.
        attack_initiative_action = self.choose_action(character, "attack", context)
        action_event = self.try_skill(character, "attack", attack_initiative_action, 0.7, context)
        if action_event is not None:
            yield from self.spend_action(character, "attack", attack_initiative_action)
            yield action_event

    # TVP saturation cap (see Principle IX 2(a) mirror-termination
    # tuning -- 2026-05-27 implementation).  When the character has
    # accumulated this much TVP, the feint-first branch is skipped in
    # favor of plain-attack so the mirror match actually terminates.
    # Without this cap, two Akodos with high feint skill in a mirror
    # match feint each other forever (feint deals no damage; both sides
    # only accumulate TVP).  Empirical: seed=7 with random.seed-driven
    # DefaultDieProvider produced 238 feints / 2 attacks in 30 rounds
    # with NO TVP cap.  A cap of 4 (one successful feint's worth)
    # ensures the school still gets to engage the TVP economy while
    # forcing transition to damage-dealing once enough fuel is banked.
    TVP_SATURATION_CAP = 4

    def _try_feint_first(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Feint-first branch -- the TVP economy faucet.

        Tries ``feint`` at threshold 0.6.  Note: failure also generates
        TVP (+1), so a marginal feint is still net-positive vs holding.

        TVP-saturation gate (Principle IX 2(a) mirror-termination
        tuning): skip this branch when ``character.tvp() >=
        TVP_SATURATION_CAP``.  Once the Akodo has banked enough TVP to
        fuel a 4th/5th Dan ability, additional feinting wastes turns
        on fuel that won't be spent before the opponent's pool also
        saturates -- a degenerate equilibrium in mirror matches.
        Falling through to plain-attack after saturation forces the
        Akodo to convert banked TVP into damage.
        """
        if character.skill("feint") <= 0:
            return
        if character.tvp() >= self.TVP_SATURATION_CAP:
            logger.debug(
                f"[Akodo Attack Strategy] feint-first branch SKIPPED "
                f"(tvp={character.tvp()} >= cap {self.TVP_SATURATION_CAP}): "
                f"{character.name()} converting fuel into damage",
            )
            return
        initiative_action = self.choose_action(character, "feint", context)
        action_event = self.try_skill(character, "feint", initiative_action, 0.6, context)
        if action_event is not None:
            logger.debug(
                f"[Akodo Attack Strategy] feint-first branch engaged: "
                f"{character.name()} feinting (tvp={character.tvp()})",
            )
            yield from self.spend_action(character, "feint", initiative_action)
            yield action_event

    def _try_plain_attack(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Plain-attack fallback -- attack at 0.7, then desperation 0.01.

        Final fallback before ``HoldActionEvent``.  Mirrors the standard
        ``PlainAttackStrategy`` ladder.
        """
        initiative_action = self.choose_action(character, "attack", context)
        action_event = self.try_skill(character, "attack", initiative_action, 0.7, context)
        if action_event is not None:
            yield from self.spend_action(character, "attack", initiative_action)
            yield action_event
            return
        # Desperation attack -- last resort.
        action_event = self.try_skill(character, "attack", initiative_action, 0.01, context)
        if action_event is not None:
            yield from self.spend_action(character, "attack", initiative_action)
            yield action_event

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        if not isinstance(event, events.YourMoveEvent):
            return
        if not character.has_action(context):
            yield events.NoActionEvent(character)
            return

        # Three-branch policy:
        # 1. Kill-shot (target.sw_remaining() <= 1 AND vp() >= 1)
        kill_shot_events = list(self._try_kill_shot(character, context))
        if kill_shot_events:
            yield from kill_shot_events
            return
        # 2. Feint-first (feint skill > 0)
        feint_events = list(self._try_feint_first(character, context))
        if feint_events:
            yield from feint_events
            return
        # 3. Plain-attack fallback (attack 0.7 -> 0.01 -> HoldAction)
        plain_events = list(self._try_plain_attack(character, context))
        if plain_events:
            yield from plain_events
            return
        # All branches fell through -- hold the action.
        yield events.HoldActionEvent(character)
