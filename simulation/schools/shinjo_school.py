#!/usr/bin/env python3

#
# shinjo_school.py
#
# Implement Shinjo Bushi School.
#
# School Ring: Air
# School Knacks: double attack, iaijutsu, lunge
#
# Special Ability: Each action gains bonus of 2X where X = phases action die was held.
# 1st Dan: Extra rolled on initiative, parry, wound check.
# 2nd Dan: Free raise on parry.
# 3rd Dan: After parry (success/fail), decrease all remaining action dice by attack_skill.
#          Can go negative.
# 4th Dan: Ring+1/discount; NewRoundListener sets highest action die to 1.
#          When multiple dice tie at the max, ALL of them are reduced.
# 5th Dan: After successful parry, gain WoundCheckFloatingBonus(parry_roll - attack_roll).
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.mechanics.modifiers import Modifier
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.modifier_listeners import ExpireAfterNextAttackByCharacterListener, ExpireAtEndOfRoundListener
from simulation.schools.base import BaseSchool
from simulation.strategies.base import (
    AlwaysParryStrategy,
    HoldOneActionStrategy,
    WoundCheckStrategy04,
)


class ShinjoBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Shinjo Bushi School: Special Ability":
        # "Each action you take in combat has a bonus of 2X, where X
        # is the number of phases for which the action die was held."
        #
        # Wiring (spec 017 T-A3 + T-B1):
        # 1. ``ShinjoSpendActionListener`` — when an action die is
        #    spent, emits an ``AddModifierEvent`` adding +2X to the
        #    character's next attack-skill roll (X = phases held).
        #    The modifier is auto-expired after one consumption via
        #    ``ExpireAfterNextAttackByCharacterListener`` and at
        #    end-of-round via ``ExpireAtEndOfRoundListener`` (Daidoji
        #    precedent at ``daidoji_school.py:231-237``).
        # 2. ``HoldOneActionStrategy`` — Special Ability rewards
        #    held dice; this strategy reserves one die for late-phase
        #    fire while spending the rest normally.
        # 3. ``AlwaysParryStrategy`` — 2nd / 3rd / 5th Dan all trigger
        #    on parry attempt, so eager parry is identity-aligned.
        # 4. ``WoundCheckStrategy04`` — 1st Dan +1 WC die + 5th Dan
        #    margin-to-WC floating bonus = above-average WC pool;
        #    0.4 confidence threshold spends more aggressively.
        self._set_school_listener(character, "spend_action", ShinjoSpendActionListener())
        self._set_school_strategy(character, "action", HoldOneActionStrategy())
        self._set_school_strategy(character, "parry", AlwaysParryStrategy())
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_listener(character, "parry_succeeded", ShinjoParryListener())
        self._set_school_listener(character, "parry_failed", ShinjoParryListener())

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_listener(character, "new_round", ShinjoNewRoundListener())

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_listener(character, "parry_succeeded", ShinjoFifthDanParryListener())
        self._set_school_listener(character, "parry_failed", ShinjoParryListener())

    def extra_rolled(self) -> list[str]:
        # rules/04-schools.md "Shinjo Bushi School: First Dan":
        # "Roll one extra die on initiative, parry, and wound checks."
        # Spec 017 Q1 BLOCKING fix — skeleton previously returned
        # ``["double attack", "initiative", "parry"]`` which omitted
        # ``wound check`` and included ``double attack`` (not in the
        # rules clause).
        return ["initiative", "parry", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["parry"]

    def name(self) -> str:
        return "Shinjo Bushi School"

    def school_knacks(self) -> list[str]:
        return ["double attack", "iaijutsu", "lunge"]

    def school_ring(self) -> str:
        return "air"


class ShinjoSpendActionListener(Listener):
    """rules/04-schools.md "Shinjo Bushi School: Special Ability":

    "Each action you take in combat has a bonus of 2X, where X is
    the number of phases for which the action die was held."

    When an action die is spent, emit an ``AddModifierEvent`` adding
    +2X to the character's next attack-skill roll (X = phases held =
    ``current_phase - initiative_action.phase()``).  ``phase()``
    returns the ORIGINAL die value for non-interrupt actions (the
    engine constructs them with ``InitiativeAction([die], die)`` —
    confirmed by rules-auditor against ``base.py:97-98``), so the
    delta is the genuine hold delay.

    The modifier auto-expires after one consumption via
    ``ExpireAfterNextAttackByCharacterListener`` and at end-of-round
    via ``ExpireAtEndOfRoundListener`` (Daidoji precedent at
    ``daidoji_school.py:231-237``).

    Spec 017 T-A3 + T-A4 (Q4 BLOCKING IDENTITY fix) — the previous
    skeleton wrote ``character._shinjo_hold_bonus = bonus`` which
    NOTHING read.  Confirmed structurally dead by rules-auditor +
    combat-simulator (0/10 wins vs Akodo 450 pre-fix).  Also: the
    previous skeleton called ``character.spend_action(...)`` directly
    which is redundant with the engine's default ``SpendActionListener``
    — note that ``_set_school_listener`` REPLACES the slot, so the
    Shinjo listener IS responsible for spending the action.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.SpendActionEvent):
            if event.subject == character:
                # Compute hold-phases.  initiative_action.phase() is
                # the ORIGINAL die value for non-interrupt actions
                # (rules-auditor confirmed).  For interrupt actions,
                # phase() is set to context.phase(), so hold_phases
                # collapses to 0 (max(0, ...) clamp) — correct since
                # interrupts aren't "held" in the rules sense.
                die_phase = event.initiative_action.phase()
                current_phase = context.phase()
                hold_phases = max(0, current_phase - die_phase)
                bonus = 2 * hold_phases
                if bonus > 0:
                    # Add transient modifier on the next attack-skill
                    # roll.  Auto-expires after consumption OR at
                    # end-of-round (safety net).
                    modifier = Modifier(character, None, ATTACK_SKILLS, bonus)
                    attack_listener = ExpireAfterNextAttackByCharacterListener(character)
                    end_of_round_listener = ExpireAtEndOfRoundListener()
                    modifier.register_listener("attack_failed", attack_listener)
                    modifier.register_listener("attack_succeeded", attack_listener)
                    modifier.register_listener("end_of_round", end_of_round_listener)
                    # Trace attribution tag (spec 017 T-C2; renderer
                    # surfacing is via the existing modifier-breakdown
                    # path since the modifier appears in the next
                    # attack-skill roll's modifier sum).
                    modifier._shinjo_special_ability_hold_phases = hold_phases  # type: ignore[attr-defined]
                    yield events.AddModifierEvent(character, modifier)
                # Spend the action die (replaces the default
                # SpendActionListener which is overwritten by this
                # listener via ``_set_school_listener``).
                character.spend_action(event.initiative_action)


class ShinjoParryListener(Listener):
    """
    Listener to implement the Shinjo 3rd Dan technique:
    After parry (success/fail), decrease all remaining action dice by attack_skill.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, (events.ParrySucceededEvent, events.ParryFailedEvent)):
            if event.action.subject() == character:
                decrease = character.skill("attack")
                actions = character.actions()
                for i in range(len(actions)):
                    actions[i] = actions[i] - decrease
                actions.sort()
        yield from ()


class ShinjoNewRoundListener(Listener):
    """rules/04-schools.md "Shinjo Bushi School: Fourth Dan":

    "Your highest action die is set to 1 at the beginning of each
    combat round."

    Note: ``_set_school_listener`` REPLACES the engine's default
    ``NewRoundListener`` at the ``new_round`` slot, so THIS listener
    owns the new-round flow — including the ``roll_initiative()``
    call.  The engine default's roll never fires for Shinjos.

    Spec 017 T-A2 fix — when multiple dice tie at the max value,
    ALL of them are reduced to 1 (not just the first occurrence —
    the previous skeleton's ``actions.index(max(actions))`` left
    other tied dice unchanged, so a `[2,3,5,5]` initial roll
    produced `[1,2,3,5]` instead of `[1,1,2,3]`).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            actions = character.actions()
            if len(actions) > 0:
                max_value = max(actions)
                # Set ALL dice tied at the max value to 1 (spec 017
                # T-A2 tie-handling fix).
                for i in range(len(actions)):
                    if actions[i] == max_value:
                        actions[i] = 1
                actions.sort()
        yield from ()


class ShinjoFifthDanParryListener(ShinjoParryListener):
    """rules/04-schools.md "Shinjo Bushi School: Fifth Dan":

    "After you successfully parry, you may add X to a future wound
    check this combat after seeing your roll, where X is the amount
    by which your parry roll exceeded its TN."

    Note: ``_set_school_listener`` REPLACES the slot, so at 5th Dan
    this listener takes over from ``ShinjoParryListener`` on the
    ``parry_succeeded`` slot.  ``parry_failed`` continues to use the
    3rd Dan listener (kept via ``apply_rank_five_ability``).  To
    preserve the 3rd Dan action-die decrease on success, this class
    subclasses ``ShinjoParryListener`` and delegates via ``super()``
    instead of duplicating the loop inline (spec 017 T-C1
    refactor).
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, events.ParrySucceededEvent):
            if event.action.subject() == character:
                # 3rd Dan action-die decrease (delegated to super).
                yield from super().handle(character, event, context)
                # 5th Dan WC floating bonus = parry margin.
                parry_roll = event.action.skill_roll()
                attack_roll = event.action.attack().skill_roll()
                bonus = parry_roll - attack_roll
                if bonus > 0:
                    character.gain_floating_bonus(WoundCheckFloatingBonus(bonus))
