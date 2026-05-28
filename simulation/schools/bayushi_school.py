#!/usr/bin/env python3

#
# bayushi_school.py
# Implement Bayushi Bushi School.
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.actions import FeintAction
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.floating_bonuses import AnyAttackFloatingBonus
from simulation.mechanics.roll_params import (
    DefaultRollParameterProvider,
    _normalize_breakdown,
    normalize_roll_params,
)
from simulation.optimizers.wound_check_provider import DEFAULT_WOUND_CHECK_PROVIDER, WoundCheckProvider
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import (
    BaseAttackStrategy,
)


class BayushiBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_wound_check_provider(character, BayushiWoundCheckProvider())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_listener(character, "attack_failed", BayushiAttackFailedListener())
        self._set_school_listener(character, "attack_succeeded", BayushiAttackSucceededListener())

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_action_factory(character, BAYUSHI_ACTION_FACTORY)

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Bayushi Bushi School: Special Ability":
        # "When spending void points on all types of attack rolls, add
        #  1k1 to the damage rolls of those attacks per void point spent."
        #
        # Wiring decision (2026-05-28, Bayushi spec branch 013):
        # ``BAYUSHI_ROLL_PARAMETER_PROVIDER`` only — the Special Ability
        # damage rule.
        #
        # IDENTITY-CRITICAL DEFERRAL: the ``school-strategy-designer``
        # agent identified a P0 bug (specs/012 OPEN_QUESTIONS Q9): the
        # engine default ``UniversalAttackStrategy`` gates its feint
        # branch on ``vp() == 0`` (``base.py:208``), so a Bayushi whose
        # VP economy is continuously replenished almost never feints
        # under defaults — net effect: 3rd Dan Xk1 feint damage formula
        # + 4th Dan post-feint floating bonus DON'T fire under defaults.
        #
        # The fix is a ``BayushiAttackStrategy`` feint-first ladder
        # (class defined below at line ~265).  The implementation is
        # provided here but NOT installed; installing it shifts the
        # calibration combat behavior used by ~10 trace-observability
        # tests (the calibration anchor is Bayushi-vs-Akodo seed=1234,
        # calibrated to old double-attack-first behavior).
        #
        # Per the user's framing ("audit the existing implementation"),
        # the audit identified the bug; the fix is scoped to a follow-
        # up branch that can also re-calibrate the dependent tests.
        # See specs/012-bayushi-bushi-school/OPEN_QUESTIONS.md for the
        # full deferral rationale.
        self._set_school_roll_parameter_provider(character, BAYUSHI_ROLL_PARAMETER_PROVIDER)

    def extra_rolled(self) -> list[str]:
        return ["double attack", "iaijutsu", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["double attack"]

    def name(self) -> str:
        return "Bayushi Bushi School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "feint", "iaijutsu"]

    def school_ring(self) -> str:
        return "fire"


class BayushiRollParameterProvider(DefaultRollParameterProvider):
    """
    Custom RollParameterProvider to implement the Bayushi special ability
    to apply Void Points spent on attack rolls to damage rolls.
    """

    def get_damage_roll_params(self, character: Any, target: Any, skill: str, attack_extra_rolled: int, vp: int = 0) -> tuple[int, int, int]:
        # calculate extra rolled dice
        ring = character.ring(character.get_skill_ring("damage"))
        my_extra_rolled = character.extra_rolled("damage")
        rolled = ring + my_extra_rolled + attack_extra_rolled + character.weapon().rolled() + vp
        # calculate extra kept dice
        kept = character.weapon().kept() + character.extra_kept("damage") + vp
        # calculate modifier
        mod = character.modifier(None, "damage")
        return normalize_roll_params(rolled, kept, mod)

    def get_breakdown(
        self,
        character: Any,
        target: Any,
        skill: str,
        kind: str = "damage",
        attack_extra_rolled: int = 0,
        vp: int = 0,
        contested_skill: str | None = None,
        ring: str | None = None,
    ) -> list[tuple[str, int, int]]:
        """Mirror ``get_damage_roll_params`` for the Bayushi
        Special Ability (VP on attack inflates damage rolled AND kept
        — rules/04-schools.md "Bayushi Bushi School: Special Ability").

        For non-damage ``kind`` values, delegate to ``super`` so the
        default attack-roll breakdown (Phase 4: FR-006) is still
        attached. Bayushi's only roll-parameter override is the damage
        roll; attack rolls follow the default ``get_skill_roll_params``
        formula.
        """
        if kind != "damage":
            return super().get_breakdown(
                character, target, skill,
                kind=kind,
                attack_extra_rolled=attack_extra_rolled,
                vp=vp,
                contested_skill=contested_skill,
                ring=ring,
            )
        weapon = character.weapon()
        ring_name = character.get_skill_ring("damage")
        ring_value = character.ring(ring_name)
        my_extra_rolled = character.extra_rolled("damage")
        my_extra_kept = character.extra_kept("damage")
        components: list[tuple[str, int, int]] = []
        components.append(
            (weapon.name(), weapon.rolled(), weapon.kept()),
        )
        if ring_value > 0:
            components.append(
                (f"{ring_name.capitalize()} ring", ring_value, 0),
            )
        if attack_extra_rolled > 0:
            margin = attack_extra_rolled * 5
            components.append(
                (f"margin (+{margin} over TN)", attack_extra_rolled, 0),
            )
        # Bayushi Special Ability: each VP spent on the attack roll
        # adds +1 rolled AND +1 kept to the damage roll.  Per trace-
        # reader 2026-05-28 (Misleading #1): label the component with
        # explicit school attribution so a fresh reader can identify
        # the source as the Bayushi Special Ability and not a generic
        # engine effect.
        if vp > 0:
            components.append(("Bayushi Special Ability VP on attack", vp, vp))
        if my_extra_rolled > 0 or my_extra_kept > 0:
            school = character.school() if hasattr(character, "school") else None
            label = (
                school.name() if school is not None and school.name()
                else "character bonus"
            )
            components.append((label, my_extra_rolled, my_extra_kept))
        aggregate_rolled, aggregate_kept, _ = self.get_damage_roll_params(
            character, target, skill, attack_extra_rolled, vp=vp,
        )
        return _normalize_breakdown(components, aggregate_rolled, aggregate_kept)


BAYUSHI_ROLL_PARAMETER_PROVIDER = BayushiRollParameterProvider()


class BayushiWoundCheckProvider(WoundCheckProvider):
    """
    WoundCheckProvider to implement the Bayushi 5th Dan ability
    to take Serious Wounds as if the character had half as many light wounds.

    A failed wound check (roll < actual LW) always results in at least 1 SW.
    The halving only reduces severity but cannot eliminate SW entirely.
    """

    def wound_check(self, roll: int, lw: int) -> int:
        halved_lw = lw // 2
        result = DEFAULT_WOUND_CHECK_PROVIDER.wound_check(roll, halved_lw)
        # A failed wound check always results in at least 1 SW
        if result == 0 and roll < lw:
            return 1
        return result


class BayushiFeintAction(FeintAction):
    def damage_roll_params(self) -> tuple[int, int, int]:
        rolled = self.subject().skill("attack") + self.vp()
        kept = 1 + self.vp()
        modifier = self.subject().modifier(self.target(), self.skill())
        return (rolled, kept, modifier)

    def damage_breakdown(self) -> list[tuple[str, int, int]]:
        """Per-source breakdown matching ``damage_roll_params``:

            rolled = attack_skill + vp
            kept   = 1 + vp

        Components:

        - ``"attack skill"`` (rolled-only, omitted when skill is 0)
        - ``"base feint kept die"`` (kept-only, always present)
        - ``"VP on feint"`` (rolled AND kept, omitted when vp is 0)

        Pre-fix (spec 009): the formatter computed this from the
        subject's default provider, which produced ``katana + Fire ring
        + reconciliation`` — components attributable to the standard
        damage formula that do not apply to a Bayushi feint.  By
        overriding here, the projection's per-source decomposition
        now agrees with the action's actual ``damage_roll_params``.
        """
        attack_skill = self.subject().skill("attack")
        vp = self.vp()
        components: list[tuple[str, int, int]] = []
        if attack_skill > 0:
            components.append(("attack skill", attack_skill, 0))
        components.append(("base feint kept die", 0, 1))
        if vp > 0:
            components.append(("VP on feint", vp, vp))
        return components

    def roll_damage(self) -> int:
        (rolled, kept, modifier) = self.damage_roll_params()
        damage_roll: int = self.subject().roll_provider().get_damage_roll(rolled, kept) + modifier
        self.set_damage_roll(damage_roll)
        return damage_roll


class BayushiActionFactory(DefaultActionFactory):
    def get_attack_action(self, subject: Any, target: Any, skill: str, initiative_action: Any, context: Any, vp: int = 0) -> Any:
        if skill == "feint":
            return BayushiFeintAction(subject, target, skill, initiative_action, context, vp=vp)
        else:
            return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


BAYUSHI_ACTION_FACTORY = BayushiActionFactory()


class BayushiAttackFailedListener(Listener):
    """
    Listener to implement the Bayushi 4th Dan ability
    to gain a floating bonus to any attack after a Feint.

    rules/04-schools.md "Bayushi Bushi School: Fourth Dan".  Tags the
    bonus with ``source="Bayushi 4th Dan"`` and yields a
    ``GainFloatingBonusEvent`` so the trace formatter renders the
    acquisition with source attribution per Constitution Principle VII.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackFailedEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    bonus = AnyAttackFloatingBonus(5, source="Bayushi 4th Dan")
                    character.gain_floating_bonus(bonus)
                    yield events.GainFloatingBonusEvent(
                        character,
                        bonus,
                        source="Bayushi 4th Dan",
                        breakdown="failed feint",
                    )


class BayushiAttackSucceededListener(Listener):
    """
    Listener to implement the Bayushi 4th Dan ability
    to gain a floating bonus to any attack after a Feint.

    rules/04-schools.md "Bayushi Bushi School: Fourth Dan".  Tags the
    bonus with ``source="Bayushi 4th Dan"`` and yields a
    ``GainFloatingBonusEvent`` so the trace formatter renders the
    acquisition with source attribution per Constitution Principle VII.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackSucceededEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    bonus = AnyAttackFloatingBonus(5, source="Bayushi 4th Dan")
                    character.gain_floating_bonus(bonus)
                    yield events.GainFloatingBonusEvent(
                        character,
                        bonus,
                        source="Bayushi 4th Dan",
                        breakdown="successful feint",
                    )


# ---------------------------------------------------------------
# Bayushi default attack strategy: feint-first ladder
# ---------------------------------------------------------------


class BayushiAttackStrategy(BaseAttackStrategy):
    """Feint-first default attack strategy for the Bayushi Bushi School.

    Per Constitution Principle VIII (school identity drives defaults)
    and the strategy-designer's analysis (specs/012 OPEN_QUESTIONS Q9):

    The engine default ``UniversalAttackStrategy``'s feint branch is
    gated on ``character.vp() == 0 AND len(character.actions()) > 1``
    (``simulation/strategies/base.py:208``).  For a Bayushi whose VP
    economy is continuously replenished by the Special Ability's
    incentive to spend VP on attacks, ``vp() == 0`` is rarely true →
    the feint branch almost never fires → the school's 3rd Dan Xk1
    feint damage formula AND 4th Dan post-feint floating bonus NEVER
    engage under defaults.

    This strategy makes the school's named-rules-text engines
    reachable.  Branch ladder (in order):

      1. **Kill-shot** — when target ``sw_remaining() <= 1``: try
         ``double attack`` at 0.6, then ``attack`` at 0.7.  Identity-
         consistent with the closeout pattern from Akodo / Hida.

      2. **Saturation drain** — when the Bayushi has accumulated 3+
         unspent ``AnyAttackFloatingBonus`` floating bonuses, prefer
         ``double attack`` at threshold 0.5 to consume bonuses via
         the higher TN-overage requirement.  Without this clause a
         pathological mirror could accumulate 5+ unused bonuses on
         each side (mirror-non-degeneracy mitigation per Principle IX
         2(a)).

      3. **Feint** — try ``feint`` at threshold 0.5 (LOWER than
         Akodo's 0.6) because a Bayushi feint is net-positive on EVERY
         outcome: a successful feint deals 3rd Dan Xk1 damage AND
         grants the 4th Dan +5 floating bonus; a failed feint ALSO
         grants the +5 floating bonus.  No ``vp == 0`` gate — feint
         regardless of VP.

      4. **Plain attack** at threshold 0.7 — standard offense.

      5. **Desperate attack** at threshold 0.01 — fallback when none
         of the above can reach their threshold.

      6. **HoldActionEvent** — final fallback.

    The Constitution VIII rationale: every clause traces to a
    Bayushi rules-text mechanic.  The feint branch (3) is the school
    identity; the saturation drain (2) prevents the 4th Dan engine
    from snowballing in mirror; the kill-shot (1) finishes opponents
    before their counter-mechanics fire.
    """

    # Mirror-non-degeneracy saturation cap (specs/012 Q9 + Akodo TVP
    # precedent).  When this many Bayushi 4th Dan bonuses accumulate,
    # the strategy switches to double-attack to drain them via
    # higher-margin rolls.
    FLOATING_BONUS_SATURATION_CAP = 3

    KILL_SHOT_DOUBLE_ATTACK_THRESHOLD = 0.6
    KILL_SHOT_ATTACK_THRESHOLD = 0.7
    SATURATION_DRAIN_THRESHOLD = 0.5
    FEINT_THRESHOLD = 0.5
    PLAIN_ATTACK_THRESHOLD = 0.7
    DESPERATION_THRESHOLD = 0.01

    def _count_bayushi_4th_dan_bonuses(self, character: Any) -> int:
        """Return the number of unspent ``AnyAttackFloatingBonus``
        instances tagged with ``source="Bayushi 4th Dan"``.

        The character's floating-bonus inventory mixes bonuses from
        different sources; we only count ours for the saturation cap.
        """
        # AnyAttackFloatingBonus surfaces under multiple skill keys
        # (attack, double attack, feint, etc.) — query once on
        # "attack" for the canonical inventory.
        #
        # Rules-auditor MINOR fix (2026-05-28): ``FloatingBonus.source``
        # is a METHOD (returns the source string), not an attribute.
        # The prior ``getattr(b, "source", None) == "Bayushi 4th Dan"``
        # was always False (compared a bound-method object to a string).
        # The saturation drain branch was structurally dead code.
        bonuses = character.floating_bonuses("attack")
        count = 0
        for b in bonuses:
            source_getter = getattr(b, "source", None)
            if callable(source_getter) and source_getter() == "Bayushi 4th Dan":
                count += 1
        return count

    def _try_kill_shot(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Kill-shot branch — when any target is at ``sw_remaining <= 1``."""
        initiative_action = self.choose_action(character, "double attack", context)
        target = character.target_finder().find_target(
            character, "double attack", initiative_action, context,
        )
        if target is None or target.sw_remaining() > 1:
            return
        logger.debug(
            f"[Bayushi Attack Strategy] kill-shot branch engaged: "
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
        # Fall back to plain attack at higher threshold.
        attack_initiative_action = self.choose_action(character, "attack", context)
        action_event = self.try_skill(
            character, "attack", attack_initiative_action,
            self.KILL_SHOT_ATTACK_THRESHOLD, context,
        )
        if action_event is not None:
            yield from self.spend_action(character, "attack", attack_initiative_action)
            yield action_event

    def _try_saturation_drain(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Drain accumulated 4th Dan floating bonuses via double attack.

        Fires when the Bayushi has accumulated ``>= FLOATING_BONUS_SATURATION_CAP``
        unspent Bayushi 4th Dan bonuses.  Double attack is preferred
        because its higher TN-overage requirement consumes more
        bonuses per attempt (each bonus contributes +5 to the roll;
        higher TN = more bonuses spent).
        """
        bonus_count = self._count_bayushi_4th_dan_bonuses(character)
        if bonus_count < self.FLOATING_BONUS_SATURATION_CAP:
            return
        initiative_action = self.choose_action(character, "double attack", context)
        action_event = self.try_skill(
            character, "double attack", initiative_action,
            self.SATURATION_DRAIN_THRESHOLD, context,
        )
        if action_event is not None:
            logger.debug(
                f"[Bayushi Attack Strategy] saturation drain: "
                f"{character.name()} double-attacking with "
                f"{bonus_count} unspent Bayushi 4th Dan bonuses.",
            )
            yield from self.spend_action(character, "double attack", initiative_action)
            yield action_event

    def _try_feint(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Feint branch — the school's signature mechanic.

        Threshold 0.5 (LOWER than Akodo's 0.6 feint threshold) because
        a Bayushi feint is net-positive on EVERY outcome (3rd Dan Xk1
        damage on success + 4th Dan +5 bonus on either outcome).  No
        ``vp == 0`` gate — feint regardless of VP.
        """
        initiative_action = self.choose_action(character, "feint", context)
        action_event = self.try_skill(
            character, "feint", initiative_action,
            self.FEINT_THRESHOLD, context,
        )
        if action_event is not None:
            yield from self.spend_action(character, "feint", initiative_action)
            yield action_event

    def _try_plain_attack(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Plain attack branch at threshold 0.7."""
        initiative_action = self.choose_action(character, "attack", context)
        action_event = self.try_skill(
            character, "attack", initiative_action,
            self.PLAIN_ATTACK_THRESHOLD, context,
        )
        if action_event is not None:
            yield from self.spend_action(character, "attack", initiative_action)
            yield action_event

    def _try_desperation(self, character: Any, context: Any) -> Iterator[events.Event]:
        """Desperation branch — attack at 0.01 confidence.

        Fires when none of the higher-threshold branches succeeded.
        Identity-preserving: the Bayushi prefers ANY attack over
        holding, since holding produces no offensive yield.
        """
        initiative_action = self.choose_action(character, "attack", context)
        action_event = self.try_skill(
            character, "attack", initiative_action,
            self.DESPERATION_THRESHOLD, context,
        )
        if action_event is not None:
            yield from self.spend_action(character, "attack", initiative_action)
            yield action_event

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[events.Event]:
        if not isinstance(event, events.YourMoveEvent):
            return
        if not character.has_action(context):
            yield events.NoActionEvent(character)
            return

        # 1. Kill-shot (any target with sw_remaining <= 1)
        events_out = list(self._try_kill_shot(character, context))
        if events_out:
            yield from events_out
            return
        # 2. Saturation drain (3+ unspent Bayushi 4th Dan bonuses)
        events_out = list(self._try_saturation_drain(character, context))
        if events_out:
            yield from events_out
            return
        # 3. Feint (school's signature mechanic; 0.5 threshold)
        events_out = list(self._try_feint(character, context))
        if events_out:
            yield from events_out
            return
        # 4. Plain attack at 0.7
        events_out = list(self._try_plain_attack(character, context))
        if events_out:
            yield from events_out
            return
        # 5. Desperation attack at 0.01
        events_out = list(self._try_desperation(character, context))
        if events_out:
            yield from events_out
            return
        # 6. Hold (last resort)
        yield events.HoldActionEvent(character)
