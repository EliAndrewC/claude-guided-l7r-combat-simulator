#!/usr/bin/env python3

#
# shiba_school.py
# Author: Patrick Bannister (ptbannister@gmail.com)
#
#

from collections.abc import Iterator
from typing import Any

from simulation import events
from simulation.actions import ParryAction
from simulation.events import (
    AddModifierEvent,
    LightWoundsDamageEvent,
    ParrySucceededEvent,
    ShibaFifthDanTnReductionEvent,
    TakeParryActionEvent,
)
from simulation.listeners import Listener
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.modifiers import Modifier
from simulation.mechanics.roll_params import normalize_roll_params
from simulation.modifier_listeners import ExpireAfterNextAttackListener
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import Strategy, WoundCheckStrategy04
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory


class ShibaBushiSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        pass

    def apply_special_ability(self, character: Any) -> None:
        # rules/04-schools.md "Shiba Bushi School: Special Ability":
        # "You may parry as an interrupt action by spending your
        # lowest 1 action die, and you may parry attacks directed at
        # other characters with no penalty."
        #
        # Wiring (spec 016 T-B2):
        # 1. ``set_interrupt_cost("parry", 1)`` — interrupt costs 1 die.
        # 2. ``SHIBA_ACTION_FACTORY`` — returns ``ShibaParryAction``
        #    which overrides ``roll_skill`` to suppress the parry-other
        #    penalty (T-A1 fix).
        # 3. ``ShibaInterruptParryStrategy`` — fires interrupt-parry on
        #    ``AttackRolledEvent`` with LOWEST-die selection (rules text
        #    Q2 BLOCKING fix; the engine default
        #    ``DefaultInterruptStrategy`` delegates to ``ReluctantParry``
        #    which (a) gates on expected-SW (under-fires for Shiba
        #    whose 3rd Dan deals damage on every parry) and (b) picks
        #    MAX die for interrupt, contradicting the rules).
        # 4. ``WoundCheckStrategy04`` — 0.4 confidence threshold honors
        #    Shiba's WC-tank identity (1st Dan +1 WC die + 4th Dan
        #    +3k1 WC = +4k1 on WC rolls).
        # ``parry`` is already in the engine default ``_interrupt_skills``
        # (``character.py:73``), so ``add_interrupt_skill("parry")`` is
        # an idempotent no-op and is not required for reachability.
        character.set_interrupt_cost("parry", 1)
        self._set_school_action_factory(character, SHIBA_ACTION_FACTORY)
        self._set_school_strategy(character, "interrupt", ShibaInterruptParryStrategy())
        self._set_school_strategy(character, "wound_check", WoundCheckStrategy04())

    def apply_rank_three_ability(self, character: Any) -> None:
        self._set_school_take_action_event_factory(character, SHIBA_TAKE_ACTION_EVENT_FACTORY)

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_extra_rolled(character, "wound check", 3)
        self._set_school_extra_kept(character, "wound check", 1)

    def apply_rank_five_ability(self, character: Any) -> None:
        self._set_school_listener(character, "parry_succeeded", ShibaParrySucceededListener())

    def extra_rolled(self) -> list[str]:
        return ["double attack", "parry", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["parry"]

    def name(self) -> str:
        return "Shiba Bushi School"

    def school_knacks(self) -> list[str]:
        return ["counterattack", "double attack", "iaijutsu"]

    def school_ring(self) -> str:
        return "air"


class ShibaInterruptParryStrategy(Strategy):
    """rules/04-schools.md "Shiba Bushi School: Special Ability":

    "You may parry as an interrupt action by spending your **lowest**
    1 action die, and you may parry attacks directed at other
    characters with no penalty."

    Fires on ``AttackRolledEvent`` against the Shiba OR an adjacent
    ally — the rules-text "parry-other no penalty" clause requires us
    to react to attacks on allies, not just on the Shiba.

    Differences from the engine-default
    ``DefaultInterruptStrategy`` + ``ReluctantParryStrategy`` chain:

    * **Lowest-die selection** (rules text — strict).
      ``BaseAttackStrategy.choose_action`` / ``BaseParryStrategy.
      _choose_action`` both pick ``max`` for the interrupt branch.
      For Shiba this strategy picks ``min(actions())``.
    * **Eager** rather than damage-gated. Shiba's 3rd Dan deals
      ``(2 × attack)k1`` damage on EVERY parry attempt
      (succeeded OR failed). ``ReluctantParryStrategy`` declines
      "small" attacks based on expected SW — that gate suppresses
      the 3rd Dan damage engine for a school whose identity IS
      damage-on-defense.
    * **SW-saturation gate** (Principle IX): decline at
      ``sw_remaining() <= 1``. Don't burn the interrupt die when
      WC is the better path to surviving the killing blow.
    """

    def _should_parry(self, character: Any, event: Any, context: Any) -> bool:
        # Must have parry skill.
        if character.skill("parry") <= 0:
            return False
        # Must have an interrupt action available.
        if not character.has_interrupt_action("parry", context):
            return False
        # Don't parry a miss.
        if not event.action.is_hit():
            return False
        # Don't parry an attack that is already parried.  Note:
        # ``is_hit()`` already returns False for parried attacks
        # (see ``AttackAction.is_hit``: ``not self.parried()``), so
        # this guard is defensive against future engine changes.
        if event.action.parried():  # pragma: no cover  # defensive: is_hit() above already returns False when parried
            return False
        # SW-saturation gate (Principle IX).
        if character.sw_remaining() <= 1:
            return False
        # Target must be the Shiba or an adjacent ally in the Shiba's group.
        target = event.action.target()
        if target not in character.group():
            return False
        if target != character:
            # Parrying for an ally — must be adjacent (NullFormation
            # default returns True; only real Formation subclasses
            # exercise the False branch).
            if not context.formation().is_adjacent(character, target):  # pragma: no cover  # defensive: NullFormation (engine default) returns True
                return False
        return True

    def _choose_action(self, character: Any, context: Any) -> InitiativeAction:
        cost = character.interrupt_cost("parry", context)
        unspent = list(character.actions())
        action_dice: list[int] = []
        # rules text: "spending your **lowest** 1 action die".
        # Standard BaseAttackStrategy / BaseParryStrategy pick max;
        # Shiba picks min.  Q2 BLOCKING fix in spec 016.
        while len(action_dice) < cost:
            die = min(unspent)
            unspent.remove(die)
            action_dice.append(die)
        return InitiativeAction(action_dice, context.phase(), is_interrupt=True)

    def _do_parry(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        initiative_action = self._choose_action(character, context)
        parry = character.action_factory().get_parry_action(
            character, event.action.subject(), event.action,
            "parry", initiative_action, context,
        )
        logger.info(
            f"{character.name()} interrupt-parries (Shiba Special Ability) "
            f"with lowest die {initiative_action.dice()}"
        )
        yield events.SpendActionEvent(character, "parry", initiative_action)
        yield character.take_action_event_factory().get_take_parry_action_event(parry)

    def recommend(self, character: Any, event: events.Event, context: Any) -> Iterator[Any]:
        if isinstance(event, events.AttackRolledEvent):
            if self._should_parry(character, event, context):
                yield from self._do_parry(character, event, context)


class ShibaActionFactory(DefaultActionFactory):
    """
    ActionFactory that returns the ShibaParryAction for parries.
    """

    def get_parry_action(self, subject: Any, target: Any, attack: Any, skill: str, initiative_action: Any, context: Any, vp: int = 0) -> Any:
        return ShibaParryAction(subject, target, skill, initiative_action, context, attack, vp=vp)


SHIBA_ACTION_FACTORY = ShibaActionFactory()


class ShibaParryAction(ParryAction):
    """rules/04-schools.md "Shiba Bushi School: Special Ability":
    "you may parry attacks directed at other characters with no
    penalty."

    Override ``roll_skill`` (the method the engine actually calls
    during ``TakeParryActionEvent._roll_parry``) so the standard
    ``5 * attacker.skill("attack")`` parry-other penalty (base
    ``ParryAction.roll_skill`` at ``simulation/actions.py:327-336``)
    is NOT applied for Shibas. Spec 016 T-A1 — the previous
    ``roll_parry`` override was dead code (engine never calls
    ``roll_parry``).
    """

    def roll_skill(self) -> int:
        self.set_skill_roll(self.subject().roll_skill(self.target(), self.skill(), ring=self.ring(), vp=self.vp()))
        roll = self.skill_roll()
        assert roll is not None
        return roll


class ShibaParrySucceededListener(Listener):
    """rules/04-schools.md "Shiba Bushi School: Fifth Dan":

    "After you successfully parry, the TN to hit the parried opponent
    on the next attack directed at them this combat is lowered by the
    amount by which your parry roll exceeded its TN.  This can lower
    the TN to a negative number."

    Emits BOTH an ``AddModifierEvent`` (which installs the actual
    ``Modifier`` — the engine mechanism that lowers TN-to-hit) AND a
    discrete ``ShibaFifthDanTnReductionEvent`` so the trace surfaces
    the school identity in user-facing rendering.  Trace-reader
    cat#10 fix (2026-05-30): pre-fix the modifier was installed
    silently and the school's marquee defensive ability never
    appeared in the trace.
    """

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, ParrySucceededEvent):
            margin = event.action.skill_roll() - event.action.attack().skill_roll()
            penalty = -1 * margin
            attacker = event.action.target()
            modifier = Modifier(attacker, None, "tn to hit", penalty)
            listener = ExpireAfterNextAttackListener()
            modifier.register_listener("attack_failed", listener)
            modifier.register_listener("attack_succeeded", listener)
            add_event = AddModifierEvent(attacker, modifier)
            add_event._shiba_5th_dan_margin = margin  # type: ignore[attr-defined]
            yield add_event
            yield ShibaFifthDanTnReductionEvent(
                subject=character, target=attacker, margin=margin,
            )


class ShibaTakeActionEventFactory(DefaultTakeActionEventFactory):
    """
    Custom TakeActionEventFactory to help implement Shiba Bushi School 3rd Dan technique
    to do damage with parries.
    """

    def get_take_parry_action_event(self, parry: Any) -> Any:
        if isinstance(parry, ParryAction):
            return ShibaTakeParryEvent(parry)
        else:
            raise ValueError("get_take_parry_action_event requires a ParryAction")


SHIBA_TAKE_ACTION_EVENT_FACTORY = ShibaTakeActionEventFactory()


class ShibaTakeParryEvent(TakeParryActionEvent):
    """
    Custom TakeParryActionEvent to implement the Shiba Bushi School 3rd Dan technique
    to do damage with parries.
    """

    def play(self, context: Any) -> Iterator[Any]:
        yield self._declare_parry()
        yield from self._roll_parry(context)
        if self.action.is_success():
            yield self._succeeded()
        else:
            yield self._failed()
        yield self._roll_damage()

    def _roll_damage(self) -> Any:
        """rules/04-schools.md "Shiba Bushi School: Third Dan":
        "Your successful or unsuccessful parry rolls deal (2X)k1
        damage, where X is equal to your attack skill.  You don't
        roll extra damage dice from your Fire or from exceeding
        the TN."

        The raw rolled count (2 * attack) is routed through
        ``normalize_roll_params`` so the engine-wide invariant
        (rolled > 10 converts excess to kept) is honored — spec 016
        T-A2 / Q3 BLOCKING fix.  For attack=6 (rolled=12), this
        produces 10k3 instead of the buggy raw 12k1.
        """
        attack_skill = self.action.subject().skill("attack")
        raw_rolled = 2 * attack_skill
        rolled, kept, bonus = normalize_roll_params(raw_rolled, 1, 0)
        damage_roll = self.action.subject().roll_provider().get_damage_roll(rolled, kept) + bonus
        return LightWoundsDamageEvent(self.action.subject(), self.action.target(), damage_roll)
