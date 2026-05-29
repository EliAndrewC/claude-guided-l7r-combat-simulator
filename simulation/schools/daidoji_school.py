#!/usr/bin/env python3

#
# daidoji_school.py
#
# Implement Daidoji Yojimbo School.
#
# School Ring: Water
# School Knacks: counterattack, double attack, iaijutsu
#
# Special Ability: You may counterattack as an interrupt action by spending
# only 1 action die, but if you do so then your opponent gets a free raise
# on their wound check if you hit.  You may counterattack for other
# characters at no penalty.
#

from collections.abc import Iterator
from typing import Any

from simulation.actions import CounterattackAction
from simulation.events import (
    AddModifierEvent,
    CounterattackDeclaredEvent,
    CounterattackFailedEvent,
    CounterattackRolledEvent,
    CounterattackSucceededEvent,
    LightWoundsDamageEvent,
    SpendVoidPointsEvent,
    TakeCounterattackActionEvent,
    WoundCheckSucceededEvent,
)
from simulation.listeners import LightWoundsDamageListener, Listener
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.mechanics.modifiers import Modifier
from simulation.modifier_listeners import ExpireAfterNextAttackListener, ExpireAtEndOfRoundListener
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import CounterattackInterruptStrategy, WoundCheckStrategy04
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory


class DaidojiYojimboSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return None

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Daidoji Yojimbo School: Special Ability":
        # "You may counterattack as an interrupt action by spending
        # only 1 action die, but if you do so then your opponent gets
        # a free raise on their wound check if you hit.  You may
        # counterattack for other characters at no penalty."
        #
        # Wiring (spec 018 T-B1):
        # - 1-die interrupt-cost; ``CounterattackInterruptStrategy``
        #   already fires for attacks against allies (gates on
        #   ``target in character.group()`` + adjacency per
        #   ``strategies/base.py:763-770``).
        # - ``DAIDOJI_ACTION_FACTORY`` -> ``DaidojiCounterattackAction``
        #   drops the "+5 TN when counterattacking for others" base
        #   penalty.
        # - ``DAIDOJI_TAKE_ACTION_EVENT_FACTORY`` -> 3rd Dan WC bonus
        #   + interrupt-counterattack -5 WC TN.
        # - ``WoundCheckStrategy04`` (0.4 confidence threshold) — 1st
        #   Dan +1 WC die + 3rd Dan WC floating bonus give Daidoji
        #   above-average WC pool; aggressive threshold spends VP
        #   more readily (Hida/Shiba/Otaku precedent).
        # - Initialize the per-character counterattack-history set
        #   (spec 018 T-A3, Q5 fix) used by the 5th Dan listener to
        #   gate the ally branch on counterattack history rather than
        #   bare adjacency.
        character.set_interrupt_cost("counterattack", 1)
        self._set_school_action_factory(character, DAIDOJI_ACTION_FACTORY)
        self._set_school_take_action_event_factory(character, DAIDOJI_TAKE_ACTION_EVENT_FACTORY)
        self._set_school_strategy(character, "interrupt", CounterattackInterruptStrategy())
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())
        character._daidoji_counterattacked_for = set()

    def apply_rank_three_ability(self, character: Any) -> None:
        # After a successful counterattack, grant X free raises on wound check
        # to the target of the original attack, where X = Daidoji's attack skill.
        character._daidoji_third_dan = True

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        # Redirect damage from allies to the Daidoji
        self._set_school_listener(character, "lw_damage", DaidojiFourthDanListener(character))

    def apply_rank_five_ability(self, character: Any) -> None:
        # After a wound check succeeds, lower the attacker's TN to hit
        # by the excess amount.
        self._set_school_listener(character, "wound_check_succeeded", DaidojiFifthDanWoundCheckListener(character))

    def extra_rolled(self) -> list[str]:
        return ["attack", "counterattack", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["counterattack"]

    def name(self) -> str:
        return "Daidoji Yojimbo School"

    def school_knacks(self) -> list[str]:
        return ["counterattack", "double attack", "iaijutsu"]

    def school_ring(self) -> str:
        return "water"


class DaidojiCounterattackAction(CounterattackAction):
    """Daidoji counterattacks have no TN penalty for counterattacking
    on behalf of other characters."""

    def tn(self) -> int:
        result: int = self.target().tn_to_hit()
        return result


class DaidojiActionFactory(DefaultActionFactory):
    """ActionFactory that returns DaidojiCounterattackAction for counterattacks."""

    def get_counterattack_action(self, subject: Any, target: Any, attack: Any, skill: str, initiative_action: Any, context: Any, vp: int = 0) -> Any:
        return DaidojiCounterattackAction(subject, target, skill, initiative_action, context, attack, vp=vp)


DAIDOJI_ACTION_FACTORY = DaidojiActionFactory()


class DaidojiTakeCounterattackActionEvent(TakeCounterattackActionEvent):
    """Custom TakeCounterattackActionEvent for the Daidoji special ability.

    When the counterattack is used as an interrupt (1-die cost) and hits,
    the opponent gets a free raise on their wound check (+5 to roll,
    implemented as -5 on the wound check TN).
    """

    def play(self, context: Any) -> Iterator[Any]:
        yield CounterattackDeclaredEvent(self.action)
        self.action.roll_skill()
        if self.action.vp() > 0:
            yield SpendVoidPointsEvent(self.action.subject(), self.action.skill(), self.action.vp())
        yield CounterattackRolledEvent(self.action, self.action.skill_roll())
        # Spec 018 T-A3 (Q5 fix): track which characters the Daidoji
        # has counterattacked for, so the 5th Dan listener can gate
        # the ally branch on counterattack history per the rules-text
        # "for whom you've counterattacked" clause.  Populate
        # regardless of hit/miss — the rules-text trigger is "After
        # ... you've counterattacked", not "after a successful
        # counterattack".
        daidoji = self.action.subject()
        original_target = self.action.attack().target()
        if hasattr(daidoji, "_daidoji_counterattacked_for"):
            daidoji._daidoji_counterattacked_for.add(original_target)
        if self.action.is_hit():
            yield CounterattackSucceededEvent(self.action)
            # 3rd Dan: grant wound check floating bonus to the
            # original attack target (spec 018 T-B2 — the ad-hoc
            # ``_daidoji_third_dan`` attribute remains for now;
            # refactor to a listener-based slot deferred to a
            # follow-up branch per OPEN_QUESTIONS Q1).
            if getattr(daidoji, '_daidoji_third_dan', False):
                bonus = 5 * daidoji.skill("attack")
                if bonus > 0:
                    floating = WoundCheckFloatingBonus(bonus)
                    # Trace attribution tag for downstream renderer
                    # work (spec 018 Q8).
                    floating._daidoji_3rd_dan = True  # type: ignore[attr-defined]
                    original_target.gain_floating_bonus(floating)
            if self.action.target().is_fighting():
                damage = self.action.roll_damage()
                if self.action.initiative_action().is_interrupt():
                    # Daidoji penalty: opponent gets free raise on wound check (-5 TN)
                    wound_check_tn = max(0, damage - 5)
                    yield LightWoundsDamageEvent(
                        self.action.subject(), self.action.target(), damage, tn=wound_check_tn,
                    )
                else:
                    yield LightWoundsDamageEvent(
                        self.action.subject(), self.action.target(), damage,
                    )
        else:
            yield CounterattackFailedEvent(self.action)


class DaidojiTakeActionEventFactory(DefaultTakeActionEventFactory):
    """Custom TakeActionEventFactory that returns Daidoji-specific counterattack events."""

    def get_take_counterattack_action_event(self, action: Any) -> Any:
        return DaidojiTakeCounterattackActionEvent(action)


DAIDOJI_TAKE_ACTION_EVENT_FACTORY = DaidojiTakeActionEventFactory()


class DaidojiFourthDanListener(Listener):
    """rules/04-schools.md "Daidoji Yojimbo School: Fourth Dan":

    "You may choose to take the damage from a hit dealt to an
    adjacent character before damage has been rolled."

    Currently fires on ``LightWoundsDamageEvent`` (AFTER damage was
    rolled).  The rules-text "before damage has been rolled" timing
    requires intercepting earlier (e.g., ``AttackSucceededEvent``) so
    the damage rolls against the Daidoji's stats rather than the
    ally's.  Deferred — see OPEN_QUESTIONS Q2 in spec 018 for the
    architectural rationale.

    Spec 018 T-A5 (Q3 "may choose" strategic gate): **DEFERRED** —
    combat-simulator validated 10/10 wins vs Akodo 450 with
    unconditional redirect; adding a "danger-only" gate without
    rebalancing the rest of the Daidoji's identity engine risks
    breaking playability.  The strategic-choice fix requires
    paired playability re-validation and is left to a follow-up
    branch.
    """

    def __init__(self, daidoji: Any) -> None:
        self._daidoji = daidoji
        self._default_listener = LightWoundsDamageListener()

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, LightWoundsDamageEvent):
            if character != self._daidoji:
                # Not the Daidoji character: use default behavior
                yield from self._default_listener.handle(character, event, context)
                return
            # This is the Daidoji character handling the event
            if event.target == self._daidoji:
                # Daidoji is the target: handle normally
                yield from self._default_listener.handle(character, event, context)
            elif event.target in self._daidoji.group() and event.target != self._daidoji:
                # An ally is the target: redirect damage to the Daidoji if adjacent
                if not context.formation().is_adjacent(self._daidoji, event.target):
                    # Not adjacent: just observe the damage roll
                    if event.subject != character:
                        character.knowledge().observe_damage_roll(event.subject, event.damage)
                    return
                if event.subject != character:
                    character.knowledge().observe_damage_roll(event.subject, event.damage)
                self._daidoji.take_lw(event.damage)
                if event.damage > 0:
                    yield from self._daidoji.wound_check_strategy().recommend(
                        self._daidoji, event, context,
                    )
            else:
                # Non-ally target: just observe
                if event.subject != character:
                    character.knowledge().observe_damage_roll(event.subject, event.damage)


class DaidojiFifthDanWoundCheckListener(Listener):
    """rules/04-schools.md "Daidoji Yojimbo School: Fifth Dan":

    "After you or a character for whom you've counterattacked makes
    a wound check, lower the TN to hit the attacker the next time
    they are attacked by the amount by which the wound check
    exceeded the damage roll.  This can lower a TN to below 0."

    Spec 018 BLOCKING fixes (rules-auditor):

    * **T-A1** (HIGH-severity NEW BUG): the previous skeleton emitted
      ``Modifier(daidoji, attacker, ATTACK_SKILLS, +excess)`` which
      buffed Daidoji's OWN attack-skill rolls instead of lowering the
      attacker's ``tn_to_hit``.  Correct: ``Modifier(attacker, None,
      "tn to hit", -excess)`` (rules text — "lower the TN to hit the
      attacker").  ``tn_to_hit`` is read via ``character.modifier(None,
      "tn to hit")`` (``character.py:897``), so the modifier must be
      held by the attacker with skill ``"tn to hit"``.  Existing tests
      at ``tests/test_daidoji_school.py:577-678`` codified the buggy
      behavior — rewritten alongside this fix.
    * **T-A2** (Q4): the previous skeleton's
      ``ExpireAfterNextAttackByCharacterListener(daidoji)`` required
      ``daidoji == event.target() AND daidoji == event.subject()``,
      which never fires (only end-of-round expiry triggered).
      Replaced with ``ExpireAfterNextAttackListener`` which expires
      after the next attack TARGETING the modifier holder (= the
      attacker) by anyone — matches "the next time they are
      attacked".
    * **T-A3** (Q5): the previous skeleton gated the ally branch on
      ``adjacency``.  Rules text: "a character for whom you've
      counterattacked".  Now gates on the Daidoji's per-combat
      ``_daidoji_counterattacked_for`` set, populated by
      ``DaidojiTakeCounterattackActionEvent.play``.
    """

    def __init__(self, daidoji: Any) -> None:
        self._daidoji = daidoji

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, WoundCheckSucceededEvent):
            if character != self._daidoji:
                # Non-Daidoji characters: use default behavior.
                yield from character.light_wounds_strategy().recommend(character, event, context)
                return
            # The Daidoji is the handler.  Check whether the WC
            # subject is eligible per rules text.
            subject_is_daidoji = (event.subject == self._daidoji)
            counterattacked_for: set[Any] = getattr(
                self._daidoji, "_daidoji_counterattacked_for", set(),
            )
            subject_is_protected_ally = (
                event.subject in counterattacked_for
                and event.subject != self._daidoji
            )
            if subject_is_daidoji:
                # Daidoji's own wound check — delegate to light-wounds
                # strategy first (engine default flow).
                yield from self._daidoji.light_wounds_strategy().recommend(
                    self._daidoji, event, context,
                )
            if subject_is_daidoji or subject_is_protected_ally:
                excess = event.roll - event.tn
                if excess > 0:
                    attacker = event.attacker
                    # T-A1 fix: modifier holds on the ATTACKER, skill
                    # "tn to hit", adjustment NEGATIVE excess.
                    modifier = Modifier(attacker, None, "tn to hit", -excess)
                    # T-A2 fix: expire after next attack targeting the
                    # attacker (by anyone), not after Daidoji attacks.
                    attack_listener = ExpireAfterNextAttackListener()
                    end_of_round_listener = ExpireAtEndOfRoundListener()
                    modifier.register_listener("attack_failed", attack_listener)
                    modifier.register_listener("attack_succeeded", attack_listener)
                    modifier.register_listener("end_of_round", end_of_round_listener)
                    # Trace attribution tag for future renderer work.
                    modifier._daidoji_5th_dan_excess = excess  # type: ignore[attr-defined]
                    yield AddModifierEvent(attacker, modifier)
