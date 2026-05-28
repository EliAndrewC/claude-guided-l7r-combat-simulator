#!/usr/bin/env python3

#
# hida_school.py
#
# Implement Hida Bushi School.
#
# School Ring: Water
# School Knacks: counterattack, double attack, iaijutsu
#
# Special Ability: You may counterattack as an interrupt action by spending
# only 1 action die, but if you do so then the attacker gets a free raise (+5)
# on their attack roll.
#

import math
from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.events import HidaSWForLWTradeEvent, TakeCounterattackActionEvent
from simulation.exceptions import NotEnoughActions
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.roll import DEFAULT_DIE_PROVIDER
from simulation.mechanics.roll_provider import DefaultRollProvider
from simulation.schools.base import BaseSchool
from simulation.strategies.base import (
    BaseAttackStrategy,
    CounterattackInterruptStrategy,
    WoundCheckStrategy,
    WoundCheckStrategy04,
)
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory

# Skills on which the Hida 3rd Dan reroll fires.  Per rules text
# (rules/04-schools.md "Hida Bushi School: Third Dan"), the ability
# applies to "each counterattack roll or any other attack roll" —
# pre-resolved (specs/010 OPEN_QUESTIONS Q1, prompt resolution 1) to
# the attack-class skill set (NOT parry, feint, or wound check).
HIDA_3RD_DAN_REROLL_SKILLS = frozenset({
    "attack",
    "counterattack",
    "double attack",
    "iaijutsu",
})


class HidaBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Hida Bushi School: Special Ability":
        # "You may counterattack as an interrupt action by spending only
        # 1 action die, but if you do so then the attacker gets a free
        # raise (+5) on their attack roll."
        #
        # Wiring choices (cf. OPEN_QUESTIONS Q12 strategy-designer's
        # accepted resolution):
        #
        #  (a) ``set_interrupt_cost("counterattack", 1)`` — the rules
        #      text's 1-die interrupt cost.
        #
        #  (b) ``HIDA_TAKE_ACTION_EVENT_FACTORY`` — installs the Hida-
        #      specific ``HidaTakeCounterattackActionEvent`` that writes
        #      the +5 free raise onto the attacker's pending attack.
        #
        #  (c) ``HidaCounterattackInterruptStrategy`` — replaces the
        #      vanilla ``CounterattackInterruptStrategy`` with the Hida-
        #      aware variant: the same pre-damage path for Dans 1-4 PLUS
        #      mirror-recursion gate (do not counterattack a
        #      counterattack) + SW-saturation gate (do not counterattack
        #      at low SW with a raised attacker), and the 5th Dan post-
        #      damage timing (gated on ``character.school_rank() >= 5``).
        #      Per Constitution Principle IX 2(a) the gates are critical
        #      for mirror-match non-degeneracy.
        #
        #  (d) ``HidaAttackStrategy`` — replaces the engine default
        #      ``UniversalAttackStrategy`` with the Hida three-branch
        #      attack policy (kill-shot → pressure → reserve).  This is
        #      the Constitution Principle VIII (identity-drives-defaults)
        #      wiring: the school's defensive identity (counterattack-
        #      interrupt) is exercised by the reserve branch holding an
        #      action die for the interrupt, but the pressure branch
        #      ensures the Hida actually attacks at full health with
        #      spare actions — the mirror-non-degeneracy fix per
        #      Principle IX.
        #
        #  (e) ``WoundCheckStrategy04`` — 0.4 confidence threshold.  The
        #      1st Dan +1 WC die (rules text: "First Dan: +1 die on
        #      attack, counterattack, wound checks") lets the character
        #      tolerate a more aggressive (lower) confidence threshold.
        #      Overridden at 4th Dan by ``HidaWoundCheckStrategy`` (SW-
        #      for-LW trade).
        character.set_interrupt_cost("counterattack", 1)
        self._set_school_take_action_event_factory(character, HIDA_TAKE_ACTION_EVENT_FACTORY)
        self._set_school_strategy(character, "interrupt", HidaCounterattackInterruptStrategy())
        self._set_school_strategy(character, "attack", HidaAttackStrategy())
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())

    def apply_rank_three_ability(self, character: Any) -> None:
        # rules/04-schools.md "Hida Bushi School: Third Dan":
        # "You may re-roll 2X dice on each counterattack roll or X dice
        # on any other attack roll..."  Install a HidaRollProvider that
        # wraps the existing provider and applies the reroll on attack-
        # class skill rolls only.
        inner = character.roll_provider()
        provider = HidaRollProvider(character=character, inner=inner)
        self._set_school_roll_provider(character, provider)

    def apply_rank_four_ability(self, character: Any) -> None:
        # rules/04-schools.md "Hida Bushi School: Fourth Dan":
        # "Raise your current and maximum Water by 1.  Raising your
        #  Water now costs 5 fewer XP.  Instead of making a wound
        #  check, you may choose to take 2 serious wounds to reduce
        #  your light wounds to 0.  You may not do this during the
        #  iaijutsu phase of a duel."
        # The first sentence (ring raise + discount) is handled by the
        # shared helper; the alternative-wound-check is implemented by
        # installing HidaWoundCheckStrategy in the wound_check slot.
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_strategy(
            character, "wound_check", HidaWoundCheckStrategy(),
        )

    def apply_rank_five_ability(self, character: Any) -> None:
        # rules/04-schools.md "Hida Bushi School: Fifth Dan":
        # "When you counterattack successfully, note the quantity X by
        #  which the counterattack roll exceeded its TN.  Add X to your
        #  wound check on the damage from the attack you counterattacked.
        #  You may choose to counterattack after seeing an opponent's
        #  damage roll, but that roll goes through even if your
        #  counterattack impairs or kills the opponent."
        #
        # Two effects:
        #   1. Counterattack excess → +X on Hida's own WC roll on the
        #      damage from THAT attack.  Storage on the attack action
        #      via ``_counterattack_excess_margin``; read by
        #      ``WoundCheckDeclaredListener`` when forming the WC roll.
        #   2. Post-damage decision point.  The vanilla
        #      ``CounterattackInterruptStrategy`` is replaced by
        #      ``HidaCounterattackInterruptStrategy`` (a Dan-aware
        #      subclass that defers the pre-damage decision and acts on
        #      the new ``PostDamageInterruptCheckEvent``).  The 5th-Dan
        #      counterattack-success handling that captures the excess
        #      margin is also handled by the strategy.
        self._set_school_strategy(
            character, "interrupt", HidaCounterattackInterruptStrategy(),
        )
        self._set_school_listener(
            character, "counterattack_succeeded",
            HidaCounterattackSucceededListener(),
        )

    def extra_rolled(self) -> list[str]:
        return ["attack", "counterattack", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["counterattack"]

    def name(self) -> str:
        return "Hida Bushi School"

    def school_knacks(self) -> list[str]:
        # rules/04-schools.md "Hida Bushi School:
        # School Knacks: counterattack, double attack, iaijutsu"
        return ["counterattack", "double attack", "iaijutsu"]

    def school_ring(self) -> str:
        return "water"


class HidaCounterattackInterruptStrategy(CounterattackInterruptStrategy):
    """Hida counterattack-interrupt strategy with Dan-aware behavior.

    Subclasses ``CounterattackInterruptStrategy`` so 4th-Dan-and-below
    Hida characters continue to use the standard pre-damage decision
    path (``AttackDeclaredEvent`` → fire counterattack).

    rules/04-schools.md "Hida Bushi School: Fifth Dan" enables two
    behavior changes when ``character.school_rank() >= 5``:

      1. **Defer pre-damage decision.**  On ``AttackDeclaredEvent`` (and
         ``AttackRolledEvent``), the strategy yields no events — the
         counterattack decision is postponed.  This implements the
         rules-text language "You may choose to counterattack AFTER
         seeing an opponent's damage roll" (rules/04-schools.md).  The
         action die is effectively "reserved" because nothing has spent
         it yet (Q6 pre-resolution; cf. specs/010-hida-bushi-school
         OPEN_QUESTIONS.md).

      2. **Post-damage decision point.**  On
         ``PostDamageInterruptCheckEvent``, the strategy runs the same
         counterattack decision the base class would run pre-damage:
         can-I-counterattack? if so, fire.  The counterattack consumes
         1 action die (Hida Special Ability), the attacker still gets
         the +5 free raise via ``HidaTakeCounterattackActionEvent``, and
         on success the excess margin is stored on the originating
         attack action by ``HidaCounterattackSucceededListener``.

    The 4th-Dan-and-below path is unchanged: ``recommend(...)`` for
    those Dans falls through to the base class's pre-damage path.

    Two mitigation gates (introduced in Batch E per the strategy-
    designer's resolution in specs/010 OPEN_QUESTIONS Q12) are applied
    via ``_should_counterattack`` for ALL Dan tiers:

      * **Mirror-recursion gate.**  If the incoming attack action's
        ``skill()`` is ``"counterattack"``, decline.  Prevents the
        two-Hida counterattack-of-counterattack spiral that the
        strategy-designer identified as a Principle IX 2(a) risk.

      * **SW-saturation gate.**  If ``character.sw_remaining() <= 1``
        AND the incoming attack action has a non-zero
        ``_counterattack_roll_bonus`` (i.e., the Hida already raised
        the attacker via the special-ability free-raise tag), decline.
        Better to parry/eat the hit and rely on the 4th Dan SW-for-LW
        trade.
    """

    def _should_counterattack(self, character: Any, event: Any, context: Any) -> bool:
        """Apply the Hida-specific gates, then delegate to base.

        Returns False (decline counterattack) when either gate fires;
        otherwise defers to ``CounterattackInterruptStrategy
        ._should_counterattack`` (which validates skill / target /
        adjacency / action availability).
        """
        # Mirror-recursion gate: refuse to counterattack a counterattack.
        # The incoming action's skill is "counterattack" iff it's a
        # CounterattackAction (per CounterattackAction inheriting
        # AttackAction with skill="counterattack").
        if event.action.skill() == "counterattack":
            logger.debug(
                f"{character.name()}: recursion gate — declining "
                f"counterattack on incoming counterattack from "
                f"{event.action.subject().name()}.",
            )
            return False
        # SW-saturation gate: at low SW with a raised attacker, decline.
        if character.sw_remaining() <= 1:
            counterattack_bonus = getattr(
                event.action, "_counterattack_roll_bonus", 0,
            )
            if counterattack_bonus > 0:
                logger.debug(
                    f"{character.name()}: SW-saturation gate — declining "
                    f"counterattack at sw_remaining={character.sw_remaining()} "
                    f"with raised attacker (bonus={counterattack_bonus}).",
                )
                return False
        return super()._should_counterattack(character, event, context)

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        is_5th_dan = character.school_rank() >= 5
        if is_5th_dan:
            # Defer pre-damage decisions (AttackDeclaredEvent /
            # AttackRolledEvent): yield nothing.  The decision happens
            # later on PostDamageInterruptCheckEvent.
            if isinstance(event, events.AttackDeclaredEvent):
                if character != event.action.subject():
                    target = event.action.target()
                    if target == character:
                        # The Hida is the defender — defer.  Return early
                        # so the base class doesn't fire pre-damage.
                        logger.debug(
                            f"{character.name()} (Hida 5th Dan) defers "
                            f"counterattack decision until after damage.",
                        )
                        return
                # Not the defender — fall through to base behavior (e.g.
                # defending a friend per CounterattackInterruptStrategy
                # mechanics).
                yield from super().recommend(character, event, context)
                return
            if isinstance(event, events.AttackRolledEvent):
                # Same as base CounterattackInterruptStrategy on
                # AttackRolledEvent (parry only), but we still want the
                # 5th-Dan defer to extend through this slot — the
                # post-damage path will fire the counterattack.  Delegate
                # to parry strategy directly (no counterattack here).
                yield from character.parry_strategy().recommend(character, event, context)
                return
            if isinstance(event, events.PostDamageInterruptCheckEvent):
                # 5th-Dan-only: act on the deferred decision.
                if character != event.action.subject():
                    target = event.action.target()
                    if target == character:
                        if self._should_counterattack(character, event, context):
                            try:
                                yield from self._do_counterattack(character, event, context)
                                return
                            except NotEnoughActions:  # pragma: no cover  # defensive: _should_counterattack verifies availability
                                pass
                return
            # Other events: defer to the base for completeness.
            yield from super().recommend(character, event, context)
            return
        # Pre-5th-Dan: standard base-class behavior.
        yield from super().recommend(character, event, context)


class HidaCounterattackSucceededListener(Listener):
    """Listener that captures the Hida 5th-Dan counterattack-excess margin.

    rules/04-schools.md "Hida Bushi School: Fifth Dan":
      "When you counterattack successfully, note the quantity X by
       which the counterattack roll exceeded its TN.  Add X to your
       wound check on the damage from the attack you counterattacked."

    Fires when a Hida 5th-Dan counterattacks AND succeeds (the
    CounterattackSucceededEvent dispatches before the
    LightWoundsDamageEvent that triggers the Hida's own WC).  Stores
    the excess on the originating attack action's
    ``_counterattack_excess_margin`` attribute, which
    ``WoundCheckDeclaredListener`` later reads when forming the Hida's
    WC roll.

    Per Q11 pre-resolution (specs/010-hida-bushi-school
    OPEN_QUESTIONS.md): only the FIRST (outermost) counterattack
    writes — if the originating attack already has a nonzero
    ``_counterattack_excess_margin``, do not overwrite.
    """

    def handle(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        if isinstance(event, events.CounterattackSucceededEvent):
            counterattack = event.action
            # Only the Hida who is the counterattack's subject writes.
            if counterattack.subject() != character:
                return
            # Only act for 5th-Dan-or-higher Hidas.  The listener is
            # installed in ``apply_rank_five_ability`` so this gate is
            # belt-and-suspenders (still useful to defend against
            # post-install Dan changes).
            if character.school_rank() < 5:
                return
            # Recover the originating attack action via
            # ``CounterattackAction.attack()`` (set at construction).
            getter = getattr(counterattack, "attack", None)
            if not callable(getter):
                return  # pragma: no cover  # defensive: only CounterattackAction has .attack()
            original_attack = getter()
            if original_attack is None:
                return  # pragma: no cover  # defensive: counterattack always has an originating attack
            # Outermost-only stacking rule (Q11): skip overwrite.
            existing = getattr(original_attack, "_counterattack_excess_margin", 0)
            if existing:
                return
            # Compute excess = roll - TN.
            roll = counterattack.skill_roll()
            if roll is None:
                return  # pragma: no cover  # defensive: CounterattackSucceededEvent fires after roll
            tn = counterattack.tn()
            excess = roll - tn
            if excess <= 0:
                return  # pragma: no cover  # defensive: a successful counterattack has roll >= tn, so excess >= 0; equality means no bonus
            original_attack._counterattack_excess_margin = excess
            # rules/04-schools.md "Hida Bushi School: Fifth Dan":
            # "Add X to YOUR wound check on the damage from the attack
            #  you counterattacked."  The bonus applies to the
            # counterattacker's OWN WC only — not to a defended
            # friend's WC when the Hida counterattacks an attack
            # targeting a friend.  We store the counterattacker
            # reference here so the downstream WC listeners can gate
            # the bonus on ``event.subject == counterattacker``.
            original_attack._counterattack_excess_counterattacker = character
            logger.debug(
                f"Hida 5th Dan: counterattack excess +{excess} stored on "
                f"originating attack ({original_attack.subject().name()} → "
                f"{original_attack.target().name()}) for {character.name()}",
            )
            yield from ()


class HidaTakeCounterattackActionEvent(TakeCounterattackActionEvent):
    """Custom TakeCounterattackActionEvent for the Hida special ability.

    When the counterattack is used as an interrupt (1-die cost), the
    original attacker gets a free raise (+5) on their attack roll.
    Since the counterattack now happens before the attack roll, we
    store the bonus as a pending attribute on the attack action.
    """

    def play(self, context: Any) -> Iterator[Any]:
        if self.action.initiative_action().is_interrupt():
            original_attack = self.action.attack()
            bonus = getattr(original_attack, '_counterattack_roll_bonus', 0)
            original_attack._counterattack_roll_bonus = bonus + 5
        yield from super().play(context)


class HidaTakeActionEventFactory(DefaultTakeActionEventFactory):
    """Custom TakeActionEventFactory that returns Hida-specific counterattack events."""

    def get_take_counterattack_action_event(self, action: Any) -> Any:
        return HidaTakeCounterattackActionEvent(action)


HIDA_TAKE_ACTION_EVENT_FACTORY = HidaTakeActionEventFactory()


# ---------------------------------------------------------------
# Hida 3rd Dan: reroll provider
# ---------------------------------------------------------------


def _find_hida_dice_to_reroll(dice: list[int], n_cap: int) -> list[int]:
    """Return indices into ``dice`` (sorted descending) to reroll.

    Hida 3rd Dan algorithm (per specs/010 OPEN_QUESTIONS Q1):
      * Identify dice that came up below 5.5 (expected value of a d10).
      * Of those, pick the LOWEST ``min(n_cap, len(eligible))`` for
        reroll.  Greedy lowest-first — rerolling a higher die when a
        lower one is available is strictly worse.

    Why ``< 6`` rather than ``< 5.5``: dice are integers; "below 5.5"
    is equivalent to ``<= 5`` which is the same as ``< 6``.  Mirrors
    the Merchant ``_find_dice_to_reroll`` heuristic.

    Args:
        dice: list of die values sorted in descending order.
        n_cap: maximum number of dice to reroll.

    Returns:
        List of indices (into the sorted-descending ``dice`` list) to
        reroll.  May be shorter than ``n_cap`` when fewer eligible dice
        exist.  Empty when ``n_cap == 0`` or no dice are below 5.5.
    """
    if n_cap <= 0:
        return []
    # candidates: dice strictly below 5.5 (i.e., 1-5).
    # dice is sorted descending; low dice are at the tail.
    eligible_indices = [i for i in range(len(dice)) if dice[i] < 6]
    if not eligible_indices:
        return []
    # Take the LOWEST n_cap eligible dice.  Since `dice` is sorted
    # descending, the lowest dice are at the end of `eligible_indices`.
    k = min(n_cap, len(eligible_indices))
    return sorted(eligible_indices[-k:])


class HidaRollProvider(DefaultRollProvider):
    """Roll provider implementing the Hida 3rd Dan reroll ability.

    rules/04-schools.md "Hida Bushi School: Third Dan":
      "You may re-roll 2X dice on each counterattack roll or X dice on
       any other attack roll, where X is your attack skill. When
       impaired, your number of extra dice on these rolls is divided in
       half (round up), but you reroll 10s on these rolls despite being
       impaired."

    The provider wraps an ``inner`` roll provider (defaulting to the
    standard ``DefaultRollProvider`` behavior) and intercepts skill
    rolls on the attack-class skill set
    (``HIDA_3RD_DAN_REROLL_SKILLS``).  After the inner provider rolls
    the dice, we identify the lowest N below-5.5 dice (where N is
    ``2 * attack_skill`` for counterattack and ``attack_skill``
    otherwise), reroll each via ``_reroll_die_provider``, then
    recompute the total.  When the Hida is ``crippled()``, N is
    halved (round up); however, the rerolled dice still explode on
    10s per the rules-text carve-out.

    The reroll metadata (which dice changed from what to what) is
    stored on ``_last_hida_3rd_dan_reroll`` for the trace formatter
    to surface (Principle VII).  If a roll occurs in the context of a
    specific attack action, the metadata is ALSO attached to the
    action (``action._hida_3rd_dan_reroll``) so the per-action trace
    entry can include it.
    """

    def __init__(
        self,
        character: Any = None,
        inner: Any = None,
        die_provider: Any = None,
        reroll_die_provider: Any = None,
    ) -> None:
        super().__init__(die_provider)
        self._character: Any = character
        self._inner: Any = inner
        if reroll_die_provider is not None:
            self._reroll_die_provider: Any = reroll_die_provider
        else:
            self._reroll_die_provider = DEFAULT_DIE_PROVIDER
        # Last reroll metadata for trace attribution (Principle VII).
        # Cleared/overwritten on each skill roll.  Keys:
        #   "skill": skill name
        #   "n": effective reroll cap (after crippled halving)
        #   "crippled": bool
        #   "rerolls": list of (before, after) tuples
        #   "before_dice": pre-reroll dice (sorted desc)
        #   "after_dice": post-reroll dice (sorted desc)
        #   "before_total": pre-reroll total returned by inner
        #   "after_total": post-reroll total
        self._last_hida_3rd_dan_reroll: dict[str, Any] | None = None

    def set_character(self, character: Any) -> None:
        """Bind the provider to a character (used during install)."""
        self._character = character

    # The inner provider, when present, fully replaces the
    # DefaultRollProvider behavior for non-rerolled paths (matches the
    # Merchant precedent of wrapping).  When ``inner`` is None, fall
    # back to DefaultRollProvider's own methods.

    def get_damage_reduction_roll(self, rolled: int, kept: int, reduction: int) -> int:
        if self._inner is not None:
            result = self._inner.get_damage_reduction_roll(rolled, kept, reduction)
            assert isinstance(result, int)
            return result
        return super().get_damage_reduction_roll(rolled, kept, reduction)

    def get_damage_roll(self, rolled: int, kept: int) -> int:
        if self._inner is not None:
            result = self._inner.get_damage_roll(rolled, kept)
            assert isinstance(result, int)
            return result
        return super().get_damage_roll(rolled, kept)

    def get_initiative_roll(self, rolled: int, kept: int) -> list[int]:
        if self._inner is not None:
            result: list[int] = self._inner.get_initiative_roll(rolled, kept)
            return result
        return super().get_initiative_roll(rolled, kept)

    def get_skill_roll(self, skill: str, rolled: int, kept: int, explode: bool = True) -> int:
        # Initial roll — when the Hida 3rd Dan rule applies, override
        # ``explode=True`` so that 10s on the initial dice still
        # explode despite being crippled (rules-text carve-out).
        eligible = skill in HIDA_3RD_DAN_REROLL_SKILLS
        effective_explode = True if eligible else explode
        if self._inner is not None:
            initial_total = self._inner.get_skill_roll(
                skill, rolled, kept, explode=effective_explode,
            )
            info = self._inner.last_skill_info()
        else:
            initial_total = super().get_skill_roll(
                skill, rolled, kept, explode=effective_explode,
            )
            info = self._last_skill_info
        assert isinstance(initial_total, int)
        # Clear last reroll info so the formatter doesn't see stale data
        # on a roll that doesn't trigger.
        self._last_hida_3rd_dan_reroll = None
        if not eligible:
            return initial_total
        return self._maybe_reroll(
            skill, initial_total, info, rolled, kept,
        )

    def get_wound_check_roll(self, rolled: int, kept: int, explode: bool = True) -> int:
        # rules/04-schools.md "Hida Bushi School: Third Dan" applies to
        # attack-class rolls only; wound check is excluded.
        if self._inner is not None:
            result = self._inner.get_wound_check_roll(rolled, kept, explode=explode)
            assert isinstance(result, int)
            return result
        return super().get_wound_check_roll(rolled, kept, explode=explode)

    def last_damage_info(self) -> Any:
        return self._inner_attr("last_damage_info", super().last_damage_info)

    def last_damage_roll(self) -> Any:
        return self._inner_attr("last_damage_roll", super().last_damage_roll)

    def last_initiative_info(self) -> Any:
        return self._inner_attr("last_initiative_info", super().last_initiative_info)

    def last_initiative_roll(self) -> Any:
        return self._inner_attr("last_initiative_roll", super().last_initiative_roll)

    def last_skill_info(self) -> Any:
        if self._inner is not None:
            inner_method = getattr(self._inner, "last_skill_info", None)
            if callable(inner_method):
                return inner_method()
        return self._last_skill_info

    def last_skill_roll(self) -> Any:
        return self._inner_attr("last_skill_roll", super().last_skill_roll)

    def last_wound_check_info(self) -> Any:
        return self._inner_attr("last_wound_check_info", super().last_wound_check_info)

    def last_wound_check_roll(self) -> Any:
        return self._inner_attr("last_wound_check_roll", super().last_wound_check_roll)

    def _inner_attr(self, name: str, fallback: Any) -> Any:
        """Helper: return inner provider's ``name()`` if present, else
        call ``fallback`` (the DefaultRollProvider implementation).

        CalvinistRollProvider only implements a subset of the
        ``last_*_info`` / ``last_*_roll`` accessor methods (see
        simulation/mechanics/roll_provider.py).  When wrapping it,
        we degrade gracefully rather than raising AttributeError —
        observer code that probes provider state needs to be able to
        handle missing data anyway.
        """
        if self._inner is not None:
            inner_method = getattr(self._inner, name, None)
            if callable(inner_method):
                return inner_method()
            return None
        return fallback()

    def set_die_provider(self, die_provider: Any) -> None:
        if self._inner is not None:
            self._inner.set_die_provider(die_provider)
        else:
            super().set_die_provider(die_provider)

    def last_hida_3rd_dan_reroll(self) -> dict[str, Any] | None:
        """Return metadata for the most recent reroll (or None).

        Cleared at the start of each skill roll; populated only when
        the 3rd Dan reroll actually fired and changed at least one
        die.  Used by the trace formatter for Principle VII
        attribution.
        """
        return self._last_hida_3rd_dan_reroll

    def _maybe_reroll(
        self,
        skill: str,
        initial_total: int,
        info: Any,
        rolled: int,
        kept: int,
    ) -> int:
        """Apply the Hida 3rd Dan reroll if eligible dice exist.

        Returns the new total after rerolls.  If no character is bound
        or no dice info is available, returns ``initial_total``
        unchanged.
        """
        if self._character is None:
            return initial_total
        if info is None or info.get("dice") is None:
            return initial_total
        attack_skill = self._character.skill("attack")
        # N = 2X for counterattack, X otherwise (rules text).
        if skill == "counterattack":
            n = 2 * attack_skill
        else:
            n = attack_skill
        crippled = bool(self._character.crippled())
        if crippled:
            # "When impaired, your number of extra dice on these rolls
            # is divided in half (round up)."
            n = math.ceil(n / 2)
        if n <= 0:
            return initial_total
        dice: list[int] = [int(d) for d in info["dice"]]
        dice.sort(reverse=True)
        before_dice: list[int] = list(dice)
        indices = _find_hida_dice_to_reroll(dice, n)
        if not indices:
            return initial_total
        # Reroll each selected die.  Per the rules-text carve-out
        # ("you reroll 10s on these rolls despite being impaired"),
        # the rerolled dice always explode regardless of crippled state.
        rerolls: list[tuple[int, int]] = []
        for i in indices:
            old_value: int = dice[i]
            new_value: int = int(self._reroll_die_provider.roll_die(faces=10, explode=True))
            logger.debug(
                f"Hida 3rd Dan: rerolling die {old_value} -> {new_value} "
                f"(skill={skill}, crippled={crippled})"
            )
            rerolls.append((old_value, new_value))
            dice[i] = new_value
        dice.sort(reverse=True)
        # Compute bonus: the initial total minus the original kept sum
        # gives the modifier portion that does NOT come from the dice
        # themselves (e.g., bonus added by inner provider).
        original_kept_sum: int = sum(before_dice[:kept])
        bonus: int = initial_total - original_kept_sum
        new_total: int = sum(dice[:kept]) + bonus
        # Stash metadata for trace.
        self._last_hida_3rd_dan_reroll = {
            "skill": skill,
            "n": n,
            "crippled": crippled,
            "rerolls": rerolls,
            "before_dice": before_dice,
            "after_dice": dice,
            "before_total": initial_total,
            "after_total": new_total,
        }
        return new_total


# ---------------------------------------------------------------
# Hida 4th Dan: SW-for-LW trade alternative wound check
# ---------------------------------------------------------------


class HidaWoundCheckStrategy(WoundCheckStrategy):
    """Wound check strategy for 4th-Dan-or-higher Hida.

    rules/04-schools.md "Hida Bushi School: Fourth Dan":
      "Instead of making a wound check, you may choose to take 2
       serious wounds to reduce your light wounds to 0.  You may not
       do this during the iaijutsu phase of a duel."

    Extends the base ``WoundCheckStrategy`` with the SW-for-LW trade
    option.  When invoked on a ``LightWoundsDamageEvent`` whose target
    is this character, the strategy:

      1. Checks the trade pre-conditions:
         - ``character.lw() > 0`` (something to reduce; pre-resolved Q3
           — trading 2 SW for "reduce 0 LW to 0" is strictly worse than
           the normal-zero-damage path).
         - ``character.sw() + 2 <= character.max_sw()`` (the 2 SW
           wouldn't push the character to defeat; pre-resolved Q4).
         - NOT ``context.in_iaijutsu_phase(character)`` (rules-text
           guard; bystanders watching a duel are unaffected per
           pre-resolved Q4).
      2. If all pre-conditions hold, computes an expected-SW heuristic
         by evaluating ``character.wound_check`` against the context-
         mean wound check roll (with floating bonuses).  If the
         expected SW from rolling is ≥ 2, the trade is at LEAST as
         good as rolling (and avoids the variance of a failed roll),
         so yield ``HidaSWForLWTradeEvent`` and return.
      3. Otherwise (no pre-conditions or expected SW < 2), fall through
         to the base ``WoundCheckStrategy.recommend`` (rolls normally).

    Pre-resolved Q14: the heuristic threshold is "expected SW from
    rolling ≥ 2".  Below that, rolling normally is preferable because
    the average outcome is 0 or 1 SW.
    """

    # The trade threshold: take the trade only when the expected SW
    # from rolling is at least this many.  Pre-resolved Q14.
    TRADE_THRESHOLD_SW: int = 2

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        if isinstance(event, events.LightWoundsDamageEvent):
            if event.target == character:
                if self._should_trade(character, event, context):
                    lw_before = character.lw()
                    logger.info(
                        f"{character.name()} elects the Hida 4th Dan SW-for-LW "
                        f"trade: take 2 SW to reset LW from {lw_before} to 0",
                    )
                    yield HidaSWForLWTradeEvent(
                        character, event.subject, lw_before,
                    )
                    return
        # Pre-conditions not met (or not an LW event for this character):
        # fall through to the base WoundCheckStrategy.
        yield from super().recommend(character, event, context)

    def _should_trade(self, character: Any, event: Any, context: Any) -> bool:
        """Return True iff all trade pre-conditions are met AND the
        expected SW from a normal roll is ≥ ``TRADE_THRESHOLD_SW``.
        """
        # (i) Something to reduce.
        if character.lw() <= 0:
            return False
        # (ii) Trade wouldn't push to defeat.
        if character.sw() + 2 > character.max_sw():
            return False
        # (iii) Not in this character's iaijutsu duel phase.
        if context is not None and context.in_iaijutsu_phase(character):
            return False
        # (iv) Expected SW from rolling — must be ≥ threshold for the
        # trade to be worthwhile.  Use the context's mean roll +
        # floating-bonus total against the character's wound check.
        try:
            (rolled, kept, modifier) = character.get_wound_check_roll_params(vp=0)
        except Exception:  # pragma: no cover  # defensive: get_wound_check_roll_params is well-defined for any character
            return False
        if context is None:  # pragma: no cover  # defensive: combat strategies are always invoked with a non-None context
            return False
        floating_bonus_total = sum(
            b.bonus() for b in character.floating_bonuses("wound check")
        )
        mean_roll = context.mean_roll(rolled, kept) + modifier + floating_bonus_total
        expected_sw: int = int(character.wound_check(int(mean_roll)))
        return expected_sw >= self.TRADE_THRESHOLD_SW


# ---------------------------------------------------------------
# Hida attack strategy: three-branch identity-driven default
# ---------------------------------------------------------------


class HidaAttackStrategy(BaseAttackStrategy):
    """Identity-driven default attack strategy for Hida Bushi School.

    Per Constitution Principle VIII (school identity drives defaults)
    and Principle IX (defaults must be playable + mirror non-degenerate),
    the engine default ``UniversalAttackStrategy`` is the wrong default
    for Hida: it never holds an action die for the counterattack
    interrupt (the school's signature ability per
    rules/04-schools.md "Hida Bushi School: Special Ability"), so the
    1-die-interrupt counterattack — the school's identity engine —
    rarely fires under defaults.

    This strategy implements the three-branch policy per the strategy-
    designer's resolution (specs/010 OPEN_QUESTIONS Q12):

      1. **Kill-shot branch** — when ``target.sw_remaining() <= 1``,
         prefer finishing damage over reserve.  Try ``double attack``
         (Hida knack per rules text) at threshold 0.6 first, then plain
         ``attack`` at 0.7.  *Lunge is deliberately excluded* because
         lunge is NOT a Hida knack (the rules-text knacks are
         counterattack, double attack, iaijutsu).

      2. **Pressure branch** — when ``character.sw_remaining() ==
         character.max_sw()`` (full health) AND ``len(character.actions())
         >= 2`` (at least one action to spare), attack at threshold 0.7.
         This is the mirror-non-degeneracy mitigation per Principle IX
         2(a): without it, two Hidas at full health with the reserve
         branch both hold their actions forever and the combat never
         terminates.

      3. **Reserve branch** — otherwise, hold the action die for the
         counterattack-interrupt.  This is the school's signature
         defensive posture.

    The lunge skill (when set on the character) is intentionally never
    selected here; only the three knacks (counterattack-as-interrupt is
    in the interrupt slot, not here) plus plain attack participate.

    rules/04-schools.md "Hida Bushi School" + Constitution Principles
    VIII / IX.
    """

    # Confidence thresholds (per strategy-designer's resolution).
    KILL_SHOT_DOUBLE_ATTACK_THRESHOLD = 0.6
    KILL_SHOT_ATTACK_THRESHOLD = 0.7
    PRESSURE_ATTACK_THRESHOLD = 0.7
    # Kill-shot desperation tier (2026-05-28, mirror-match termination
    # fix per combat-simulator Proposal C): when the primary kill-shot
    # thresholds (0.6 double-attack, 0.7 attack) both fail AND the
    # target is at ``sw_remaining == 1`` (one SW from defeat), retry
    # at this very-low threshold to actually close the fight.
    #
    # Why this exists: in mirror-match (two 5-skill Hidas), the
    # optimizer cannot find any VP spend that reaches the 0.7 / 0.6
    # primary thresholds against a 5-skill parry defender — combat
    # reaches ``sw_remaining=1`` on both sides and stalls because
    # neither side can deliver the finisher.  The combat never
    # terminates, ``engine.history()`` grows unboundedly, and pytest
    # OOMs.  The desperation tier ONLY fires when the target is
    # ``sw_remaining == 1`` (one SW from defeat), so it is strictly a
    # finisher — losing the action die to a parried attack is a net
    # win even at 5% confidence because (i) the opponent burns a
    # parry, and (ii) the alternative is the combat never closing.
    #
    # Identity preservation: primary 0.6 / 0.7 thresholds are
    # unchanged, so non-mirror behavior is identical except for the
    # rare ``target.sw_remaining == 1`` finisher case.  Vs Akodo at
    # 450 XP, win-rate is identical to the pre-tuning baseline (1/10).
    KILL_SHOT_DESPERATION_THRESHOLD = 0.05

    def _try_kill_shot(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Kill-shot branch — only fires when any target is at sw_remaining ≤ 1.

        Tries double attack first (Hida knack, higher damage ceiling),
        falls back to plain attack.  Returns an iterator yielding the
        spend_action + take_attack pair, or empty if the branch doesn't
        engage.
        """
        # Probe the easiest target via the character's target_finder.
        # We use a double-attack initiative_action because double_attack
        # is the first kill-shot attempt; the target_finder returns the
        # same easiest target regardless of skill choice.
        initiative_action = self.choose_action(character, "double attack", context)
        target = character.target_finder().find_target(
            character, "double attack", initiative_action, context,
        )
        if target is None or target.sw_remaining() > 1:
            return
        # Branch engaged — try double_attack then attack.
        logger.debug(
            f"[Hida Attack Strategy] kill-shot branch engaged: "
            f"{character.name()} targeting {target.name()} "
            f"(sw_remaining={target.sw_remaining()}).",
        )
        action_event = self.try_skill(
            character, "double attack", initiative_action,
            self.KILL_SHOT_DOUBLE_ATTACK_THRESHOLD, context,
        )
        if action_event is not None:
            yield from self.spend_action(character, "double attack", initiative_action)
            yield action_event
            return
        # double_attack didn't meet threshold (or skill 0); fall back to
        # plain attack at 0.7.
        attack_initiative_action = self.choose_action(character, "attack", context)
        action_event = self.try_skill(
            character, "attack", attack_initiative_action,
            self.KILL_SHOT_ATTACK_THRESHOLD, context,
        )
        if action_event is not None:
            yield from self.spend_action(character, "attack", attack_initiative_action)
            yield action_event
            return
        # Desperation finisher: when target is one SW from defeat AND
        # both primary thresholds failed, retry at 0.05 confidence with
        # either skill.  See KILL_SHOT_DESPERATION_THRESHOLD docstring
        # for rationale (mirror-match termination per Principle IX 2(a)).
        if target.sw_remaining() == 1:
            for desperation_skill, desperation_init in (
                ("double attack", initiative_action),
                ("attack", attack_initiative_action),
            ):
                if character.skill(desperation_skill) == 0:
                    continue
                desperation_event = self.try_skill(
                    character, desperation_skill, desperation_init,
                    self.KILL_SHOT_DESPERATION_THRESHOLD, context,
                )
                if desperation_event is not None:
                    logger.debug(
                        f"[Hida Attack Strategy] kill-shot desperation: "
                        f"{character.name()} closing on {target.name()} "
                        f"with {desperation_skill} at 0.05 confidence "
                        f"(target sw_remaining=1).",
                    )
                    yield from self.spend_action(
                        character, desperation_skill, desperation_init,
                    )
                    yield desperation_event
                    return

    def _try_pressure(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Pressure branch — attack whenever a spare action is available.

        Engagement gate: ``len(character.actions()) >= 2``.  At minimum
        one die remains after the attack — that die is the
        counterattack-interrupt reserve, so identity is preserved.

        Tuning history (2026-05-28, combat-simulator follow-up
        Proposal P5): the original gate was
        ``(sw_remaining == max_sw AND actions >= 2) OR actions >= 3``.
        That gate produced a mirror deadlock: after the opening attack,
        ``sw_remaining < max_sw`` (full-health clause fails) AND
        ``actions < 3`` (action-rich clause fails) → reserve → no
        more attacks for the rest of the round.  Net rate ~5 attacks
        per 30 rounds in mirror, so the Hidas never accumulated enough
        damage to terminate.

        The simpler ``>= 2`` gate fires the pressure branch on every
        phase where the Hida has at least 1 spare action above the
        counterattack reserve.  Identity is still preserved because:
          * The branch reserves the LAST die (never spends it here).
          * The reserve branch is still reached once ``actions``
            drops to 1, at which point the Hida holds for
            counterattack-interrupt.

        Combat-simulator verified: 5/5 mirror seeds terminate in 2-5
        rounds (well under the 18-round Principle IX bound) and
        win-rate vs 450-XP Akodo is unchanged from the pre-tuning
        baseline.

        No desperation tier: the 0.7 threshold is actually reachable
        in mirror (the optimizer finds it via VP spend), so the
        threshold itself was not the bottleneck.  A 0.01 desperation
        tier was tried during initial tuning and crashed win-
        feasibility vs Akodo (2/20 wins).
        """
        if len(character.actions()) < 2:
            return
        # Branch engaged — attack at 0.7.
        initiative_action = self.choose_action(character, "attack", context)
        action_event = self.try_skill(
            character, "attack", initiative_action,
            self.PRESSURE_ATTACK_THRESHOLD, context,
        )
        if action_event is not None:
            logger.debug(
                f"[Hida Attack Strategy] pressure branch engaged: "
                f"{character.name()} attacking "
                f"(actions={character.actions()}, "
                f"sw_remaining={character.sw_remaining()}/{character.max_sw()}).",
            )
            yield from self.spend_action(character, "attack", initiative_action)
            yield action_event

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        if not isinstance(event, events.YourMoveEvent):
            return
        if not character.has_action(context):
            yield events.NoActionEvent(character)
            return

        # Three-branch policy:
        # 1. Kill-shot (any target with sw_remaining <= 1)
        kill_shot_events = list(self._try_kill_shot(character, context))
        if kill_shot_events:
            yield from kill_shot_events
            return
        # 2. Pressure (full health + ≥ 2 actions)
        pressure_events = list(self._try_pressure(character, context))
        if pressure_events:
            yield from pressure_events
            return
        # 3. Reserve — hold the action for counterattack-interrupt.
        logger.debug(
            f"[Hida Attack Strategy] reserve branch: {character.name()} "
            f"holding action for counterattack-interrupt.",
        )
        yield events.HoldActionEvent(character)

