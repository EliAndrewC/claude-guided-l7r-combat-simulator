#!/usr/bin/env python3

#
# ishi_school.py
#
# Implement Isawa Ishi School.
#
# School Ring: Void
# School Knacks: absorb void, kharmic spin, otherworldliness
#
# Special Ability: Custom VP calculation.
#   Max VP = highest ring + school rank (instead of min ring + worldliness)
#   Max VP per roll = lowest ring - 1 (instead of min ring)
# 1st Dan: Extra rolled on precepts, wound check, initiative.
# 2nd Dan: Free raise on precepts.
# 3rd Dan: Spend 1 VP to add Xk1 to in-group ally's combat roll (X = precepts).
#          Once per roll. Covers attack/parry/counterattack/wound-check events.
#          Decision lives in EagerAllyBoostStrategy (pluggable per Principle V).
# 4th Dan: Void+1 (current and max) and Void XP cost -5.
#          Contested-roll-opponent-cannot-spend-VP clause is out of scope
#          (social contests are not modeled by the combat sim).
# 5th Dan: Spend (2 * opponent.school_rank) VP -- or floor(opponent_xp / 50)
#          for schoolless opponents -- to negate the target's school for the
#          remainder of the current combat. Instantaneous, no action consumed.
#          Decision lives in EagerNegationStrategy. Negation actually blocks
#          school-installed listeners/strategies at dispatch time via
#          Character._school_negated_by + BaseSchool helpers (see SC-2 fix).
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.character import RING_NAMES
from simulation.listeners import (
    AttackRolledListener,
    Listener,
    WoundCheckRolledListener,
    YourMoveListener,
)
from simulation.schools.base import BaseSchool
from simulation.strategies.base import PlainAttackStrategy
from simulation.strategies.ishi_dan_abilities import (
    EagerAllyBoostStrategy,
    EagerNegationStrategy,
    IshiAllyBoostStrategy,
    IshiNegateSchoolStrategy,
)


class IshiMaxVPProvider:
    """Custom VP provider for the Isawa Ishi School special ability."""

    def __init__(self, school_rank: int = 1) -> None:
        self._school_rank = school_rank

    def set_school_rank(self, rank: int) -> None:
        self._school_rank = rank

    def max_vp(self, character: Any) -> int:
        highest_ring: int = max(character.ring(ring) for ring in RING_NAMES)
        return highest_ring + self._school_rank

    def max_vp_per_roll(self, character: Any) -> int:
        lowest_ring: int = min(character.ring(ring) for ring in RING_NAMES)
        return max(0, lowest_ring - 1)


class IsawaIshiSchool(BaseSchool):
    def __init__(self) -> None:
        self._vp_provider = IshiMaxVPProvider()
        super().__init__()

    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # Install the school's custom VP provider (rules/04-schools.md "Isawa
        # Ishi School: Special Ability" -- max_vp = highest_ring + school_rank,
        # max_vp_per_roll = lowest_ring - 1).
        character.set_max_vp_provider(self._vp_provider)
        # Q4 (OPEN_QUESTIONS.md): the Ishi school's knacks are
        # ``absorb void``, ``kharmic spin``, ``otherworldliness`` -- no
        # double attack, no feint, no counterattack. The engine default
        # ``UniversalAttackStrategy`` opens by trying double-attack and
        # feint, wasting branches for a school that has neither knack.
        # Per the school-strategy-designer audit AND Constitution
        # Principle VIII (school identity drives defaults), install
        # ``PlainAttackStrategy`` so the Ishi cuts straight to plain
        # attack on every action.
        self._set_school_strategy(character, "attack", PlainAttackStrategy())

    def apply_rank_one_ability(self, character: Any) -> None:
        # Delegate to BaseSchool for the standard 1st-Dan extra-rolled wiring
        # (rules/04-schools.md "Isawa Ishi School: 1st Dan"), then sync the
        # VP provider to rank 1 so max_vp = highest_ring + school_rank
        # (rules/04-schools.md "Isawa Ishi School: Special Ability").
        super().apply_rank_one_ability(character)
        self._vp_provider.set_school_rank(1)

    def apply_rank_two_ability(self, character: Any) -> None:
        # Delegate to BaseSchool for the standard 2nd-Dan free-raise wiring
        # (rules/04-schools.md "Isawa Ishi School: 2nd Dan"), then sync the
        # VP provider to rank 2.
        super().apply_rank_two_ability(character)
        self._vp_provider.set_school_rank(2)

    def apply_rank_three_ability(self, character: Any) -> None:
        # Per Constitution Principle V the spend decision lives in a
        # pluggable Strategy (rules/04-schools.md "Isawa Ishi School: 3rd
        # Dan"); install the default ``EagerAllyBoostStrategy`` and the
        # chained Listener that delegates to it on every supported combat
        # roll event (per OAD-4: install on multiple ``*_rolled`` slots).
        self._set_school_strategy(character, "ishi_ally_boost", EagerAllyBoostStrategy())
        # Install on ``attack_rolled`` (which also covers double attack /
        # iaijutsu / feint / lunge since they all use AttackRolledEvent),
        # ``parry_rolled``, ``counterattack_rolled``, and
        # ``wound_check_rolled``. Each listener CHAINS to the engine
        # default so the existing interrupt / observation cascade still
        # fires (Bug #1 from OPEN_QUESTIONS.md Q4 audit).
        self._set_school_listener(character, "attack_rolled", IshiAllyBoostListener("attack_rolled"))
        self._set_school_listener(character, "parry_rolled", IshiAllyBoostListener("parry_rolled"))
        self._set_school_listener(
            character, "counterattack_rolled", IshiAllyBoostListener("counterattack_rolled"),
        )
        self._set_school_listener(
            character, "wound_check_rolled", IshiAllyBoostListener("wound_check_rolled"),
        )
        self._vp_provider.set_school_rank(3)

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # Sync AFTER the school ring raise so any callers reading max_vp
        # after rank 4 see both the bumped ring and the bumped rank.
        # Contested roll VP restriction is a social ability, not applicable in combat simulation
        self._vp_provider.set_school_rank(4)

    def apply_rank_five_ability(self, character: Any) -> None:
        # rules/04-schools.md "Isawa Ishi School: 5th Dan": spend VP equal to
        # 2 * opponent's school rank to negate their school/profession for a
        # fight (or floor(opponent.xp/50) for schoolless opponents).
        #
        # Per Constitution Principle V the spend decision lives in a
        # pluggable Strategy: install ``EagerNegationStrategy`` on the
        # ``"ishi_negate_school"`` slot so playtesters can swap it without
        # touching the listener.  The chained ``IshiYourMoveListener``
        # consults this strategy before delegating to the engine's stock
        # ``YourMoveListener`` so the normal action flow still fires when
        # the strategy abstains.
        self._set_school_strategy(character, "ishi_negate_school", EagerNegationStrategy())
        self._set_school_listener(character, "your_move", IshiYourMoveListener())
        self._vp_provider.set_school_rank(5)

    def extra_rolled(self) -> list[str]:
        return ["precepts", "wound check", "initiative"]

    def free_raise_skills(self) -> list[str]:
        # rules/04-schools.md "Isawa Ishi School: 2nd Dan" — free raise on
        # precepts (the school's signature skill; see specs/002
        # OPEN_QUESTIONS.md Q2 for the rationale).
        return ["precepts"]

    def name(self) -> str:
        return "Isawa Ishi School"

    def school_knacks(self) -> list[str]:
        return ["absorb void", "kharmic spin", "otherworldliness"]

    def school_ring(self) -> str:
        return "void"

    def vp_provider(self) -> "IshiMaxVPProvider":
        return self._vp_provider


class IshiAllyBoostListener(Listener):
    """3rd Dan listener: chains to the engine default, then asks the
    ``ishi_ally_boost`` strategy whether to spend a VP for the Xk1 ally
    boost.

    Per OPEN_QUESTIONS.md Q4 audit, the previous implementation had 4
    bugs which this listener fixes:

      1. (Bug #1 -- HIGH) The old listener REPLACED the engine's
         ``AttackRolledListener``, which broke the interrupt cascade for
         non-attack-subject characters. This implementation owns a stock
         ``_chained`` listener for the engine-default behavior and
         delegates first so observation/interrupt fire normally.
      2. (Bug #2 -- HIGH) The old listener only handled
         ``AttackRolledEvent``. This listener is installed on the four
         supported combat-roll slots (``attack_rolled``, ``parry_rolled``,
         ``counterattack_rolled``, ``wound_check_rolled``); ``slot_name``
         distinguishes them at construction time.
      3. (Bug #3 -- HIGH) The old listener had no once-per-roll guard,
         so multiple Ishi or repeated listener firings could stack
         boosts on a single roll. The strategy now writes
         ``_ishi_boosted_by`` on the action/event and checks it via
         ``_already_boosted`` before deciding to spend.
      4. (Bug #5 -- MEDIUM) The old listener required
         ``context.formation().is_adjacent(...)`` — per Q3 this had no
         rules basis and has been DROPPED. The strategy now uses group
         membership only.

    Plus the design fixes:

      5. (Bug #7 -- MEDIUM) Decision logic moved to
         ``EagerAllyBoostStrategy`` (the strategy is consulted via
         ``character.strategies["ishi_ally_boost"]``). Constitution
         Principle V (pluggable decisions).
      6. (Constitution Principle VIII) The fallthrough branch in the
         old listener manually called ``interrupt_strategy().recommend``
         on non-allies. That is the engine default behavior; the chained
         listener now provides it without duplication.
    """

    # Maps each installable slot to the engine's default listener so the
    # chained call preserves the engine-baseline behavior (interrupts,
    # observations, success/failure routing). ``parry_rolled`` and
    # ``counterattack_rolled`` have NO engine-default listener registered
    # (their post-roll handling lives in the event ``play`` methods, not
    # in the listener layer), so they chain to a no-op.
    _DEFAULT_LISTENERS: dict[str, Listener | None] = {
        "attack_rolled": AttackRolledListener(),
        "parry_rolled": None,
        "counterattack_rolled": None,
        "wound_check_rolled": WoundCheckRolledListener(),
    }

    def __init__(self, slot_name: str = "attack_rolled") -> None:
        if slot_name not in self._DEFAULT_LISTENERS:
            raise ValueError(
                f"IshiAllyBoostListener: unsupported slot {slot_name!r}; "
                f"valid slots are {sorted(self._DEFAULT_LISTENERS.keys())}",
            )
        self._slot_name = slot_name
        self._chained: Listener | None = self._DEFAULT_LISTENERS[slot_name]

    def handle(
        self, character: Any, event: Any, context: Any,
    ) -> Iterator[Any]:
        # Step 1: run the engine default for this slot so the standard
        # interrupt/observation cascade still fires (Bug #1 fix).
        if self._chained is not None:
            yield from self._chained.handle(character, event, context)
        # Step 2: delegate the boost decision to the pluggable strategy.
        # Per Constitution Principle V, the listener does NOT make the
        # decision; the strategy installed in
        # ``character.strategies["ishi_ally_boost"]`` does.
        strategy: IshiAllyBoostStrategy | None = character._strategies.get(
            "ishi_ally_boost",
        )
        if strategy is None:
            return
        yield from strategy.recommend(character, event, context)


class IshiYourMoveListener(Listener):
    """5th Dan listener: consults the ``ishi_negate_school`` strategy on
    ``YourMoveEvent`` BEFORE delegating to the engine's stock
    ``YourMoveListener`` so the normal action handling proceeds when the
    strategy abstains.

    rules/04-schools.md "Isawa Ishi School: 5th Dan": the negation is
    instantaneous and does not require spending an action, so we yield
    the negation events BEFORE the action strategy fires.

    Per Constitution Principle V the decision is delegated to the
    pluggable strategy installed at ``character._strategies["ishi_negate_school"]``.
    The strategy is responsible for the once-per-combat guard and the
    rank/affordability checks.
    """

    def __init__(self) -> None:
        # Preserve the engine-default ``YourMoveListener`` so chained
        # invocation still routes to the character's action strategy
        # (HoldOneActionStrategy / PlainAttackStrategy / ...).
        self._chained: Listener = YourMoveListener()

    def handle(
        self, character: Any, event: Any, context: Any,
    ) -> Iterator[Any]:
        # Step 1: consult the negation strategy (yields nothing when the
        # strategy abstains -- e.g., negation already done, no schooled
        # enemy, insufficient VP, etc.).  Per Constitution Principle V
        # the listener does NOT make the decision.
        strategy: IshiNegateSchoolStrategy | None = character._strategies.get(
            "ishi_negate_school",
        )
        if strategy is not None and isinstance(event, events.YourMoveEvent):
            yield from strategy.recommend(character, event, context)
        # Step 2: delegate to the engine default so the normal action
        # cascade still fires.  The negation is instantaneous (no action
        # consumed per rules-text), so the Ishi may also act on this
        # YourMoveEvent.
        yield from self._chained.handle(character, event, context)
