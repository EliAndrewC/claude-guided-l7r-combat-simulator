#!/usr/bin/env python3

#
# ikoma_bard_school.py
#
# Implement Ikoma Bard School.
#
# School Ring: Water (default; rules say "any non-Void")
# School Knacks: discern honor, oppose knowledge, oppose social
#
# Special Ability: Once per round, force opponent to parry your attack
#                  (opponent does not get a free raise for pre-declaring).
# 1st Dan: Extra rolled on attack, bragging, wound check
# 2nd Dan: Free raise on attack
# 3rd Dan: AP system -- ap_base_skill = "bragging", ap_skills = ["attack", "wound check"]
# 4th Dan: Ring+1/discount; unparried attack without extra kept damage dice -> roll 10 damage dice
# 5th Dan: Use special ability or oppose knack an extra time per round.
#          After seeing the result of any attack roll made against you
#          (before damage is rolled), may use the Special Ability to
#          cancel that attack and make a counter-attack against the
#          attacker.  The Ikoma spends an action die for the counter
#          (lowest available, interrupt-timing).  The cancelled attack
#          roll value is used as the parry roll defending against the
#          counter — no fresh parry roll is made and the opponent does
#          not spend an action die on it.
#

from collections.abc import Iterator
from typing import Any

from simulation.actions import AttackAction, ParryAction
from simulation.events import (
    AttackRolledEvent,
    NewRoundEvent,
    SpendActionEvent,
    TakeAttackActionEvent,
    TakeParryActionEvent,
)
from simulation.listeners import AttackRolledListener, Listener, NewRoundListener
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.schools.base import BaseSchool
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory


class IkomaBardSchool(BaseSchool):
    def ap_base_skill(self) -> str | None:
        return "bragging"

    def ap_skills(self) -> list[str]:
        return ["bragging", "culture", "heraldry", "intimidation", "attack", "wound check"]

    def apply_special_ability(self, character: Any) -> None:
        # Create the shared tracker (1 use per round by default)
        tracker = IkomaSpecialTracker()
        # Install the custom TakeActionEventFactory that forces parries
        self._set_school_take_action_event_factory(character, IkomaTakeActionEventFactory(tracker))
        # Install the new round listener that resets the tracker
        self._set_school_listener(character, "new_round", IkomaNewRoundListener(tracker))
        # Store the tracker on the character for 5th Dan to access
        character._ikoma_tracker = tracker

    def apply_rank_three_ability(self, character: Any) -> None:
        self.apply_ap(character)

    def apply_rank_four_ability(self, character: Any) -> None:
        self.apply_school_ring_raise_and_discount(character)
        self._set_school_roll_parameter_provider(character, IkomaFourthDanRollParameterProvider())

    def apply_rank_five_ability(self, character: Any) -> None:
        # Extra use of special ability per round
        tracker = getattr(character, '_ikoma_tracker', None)
        if tracker is not None:
            tracker.set_max_uses(2)
        # Install 5th Dan listener: cancel opponent's attack after seeing roll
        self._set_school_listener(
            character,
            "attack_rolled",
            IkomaFifthDanAttackRolledListener(character, tracker),
        )

    def extra_rolled(self) -> list[str]:
        return ["attack", "bragging", "wound check"]

    def free_raise_skills(self) -> list[str]:
        return ["attack"]

    def name(self) -> str:
        return "Ikoma Bard School"

    def school_knacks(self) -> list[str]:
        return ["discern honor", "oppose knowledge", "oppose social"]

    def school_ring(self) -> str:
        # rules/04-schools.md "Ikoma Bard School: School Ring: Any
        # non-Void".  Player picks via ``school_choices["school_ring"]``,
        # default "water" (Monk/Ide/Priest precedent).  Spec 028 Q1
        # fix.  The 4th Dan +1 Ring bump in
        # ``apply_school_ring_raise_and_discount`` reads this method,
        # so the choice redirects the 4th Dan bump.
        default = "water"
        valid_rings = {"air", "earth", "fire", "water"}
        chosen = self.choice("school_ring", default)
        if not isinstance(chosen, str) or chosen not in valid_rings:
            logger.warning(
                f"Ikoma Bard: invalid 'school_ring' choice (expected "
                f"one of {sorted(valid_rings)}; got {chosen!r}). "
                f"Using default."
            )
            chosen = default
        return chosen


# ──────────────────────────────────────────────────────────────────
# IkomaSpecialTracker: tracks uses of the special ability per round
# ──────────────────────────────────────────────────────────────────

class IkomaSpecialTracker:
    """Tracks the number of remaining uses of the Ikoma Bard special ability
    per combat round. Defaults to 1 use per round; 5th Dan raises it to 2."""

    def __init__(self) -> None:
        self._max_uses = 1
        self._uses_remaining = 1

    def has_uses(self) -> bool:
        return self._uses_remaining > 0

    def reset(self) -> None:
        """Reset uses to the max for a new round."""
        self._uses_remaining = self._max_uses

    def set_max_uses(self, n: int) -> None:
        """Set the maximum uses per round (e.g. 2 at 5th Dan)."""
        self._max_uses = n
        self._uses_remaining = n

    def use(self) -> None:
        """Consume one use of the special ability."""
        if self._uses_remaining > 0:
            self._uses_remaining -= 1

    def uses_remaining(self) -> int:
        return self._uses_remaining


# ──────────────────────────────────────────────────────────────────
# IkomaNewRoundListener: reset tracker and roll initiative
# ──────────────────────────────────────────────────────────────────

class IkomaNewRoundListener(NewRoundListener):
    """New round listener that resets the IkomaSpecialTracker and
    rolls initiative (standard new round behavior)."""

    def __init__(self, tracker: Any) -> None:
        self._tracker = tracker

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, NewRoundEvent):
            self._tracker.reset()
            character.roll_initiative()
            yield from ()


# ──────────────────────────────────────────────────────────────────
# IkomaTakeAttackActionEvent: forced parry after attack hits
# ──────────────────────────────────────────────────────────────────

class IkomaTakeAttackActionEvent(TakeAttackActionEvent):
    """Custom TakeAttackActionEvent for the Ikoma Bard special ability.

    After the attack is rolled, if the attack hit and the tracker has uses,
    force the target to spend their next available action die to attempt
    a parry. The forced parry does NOT get a free raise for pre-declaring.
    """

    def __init__(self, action: Any, tracker: Any) -> None:
        super().__init__(action)
        self._tracker = tracker

    def play(self, context: Any) -> Iterator[Any]:
        yield self._declare_attack()
        # Counterattack may have killed/incapacitated the attacker
        if not self.action.subject().is_fighting():  # pragma: no cover  # defensive: rare counterattack-kills-attacker path
            return
        yield from self._roll_attack(context)
        # After attack is rolled, attempt forced parry if applicable
        if (
            not self.action.parried()
            and self.action.is_hit()
            and self._tracker.has_uses()
        ):
            yield from self._force_parry(context)
        if self.action.parried():
            yield self._failed()
            return
        if self.action.is_hit():
            yield self._succeeded()
            # A listener (e.g. Monk 5th Dan) may cancel the attack
            # after it succeeded but before damage is rolled.
            if self.action.parried():  # pragma: no cover  # defensive: Monk 5th Dan post-success cancel — rare cross-school interaction
                return
            direct_damage = self._direct_damage()
            if direct_damage is not None:  # pragma: no cover  # defensive: only double-attack-penalty SW path produces direct damage
                yield direct_damage
            if self.action.target().is_fighting():
                yield self._roll_damage()
        else:
            yield self._failed()

    def _force_parry(self, context: Any) -> Iterator[Any]:
        """Force the target to parry using their next available action die."""
        target = self.action.target()
        # Check if target has action dice
        if len(target.actions()) == 0:
            return
        # Consume a use of the special ability
        self._tracker.use()
        # Spend the target's lowest (next available) action die
        lowest_die = min(target.actions())
        initiative_action = InitiativeAction([lowest_die], lowest_die)
        # Spend the action die
        yield SpendActionEvent(target, "parry", initiative_action)
        # Create a parry action for the target, WITHOUT free raise bonus
        # The parry is not pre-declared so no free raise
        parry = ParryAction(
            target,
            self.action.subject(),
            "parry",
            initiative_action,
            context,
            self.action,
            predeclared=False,
        )
        # Play the parry event
        yield TakeParryActionEvent(parry)


# ──────────────────────────────────────────────────────────────────
# IkomaTakeActionEventFactory: returns Ikoma-specific attack events
# ──────────────────────────────────────────────────────────────────

class IkomaTakeActionEventFactory(DefaultTakeActionEventFactory):
    """Custom TakeActionEventFactory that returns IkomaTakeAttackActionEvent
    for attacks."""

    def __init__(self, tracker: Any) -> None:
        self._tracker = tracker

    def get_take_attack_action_event(self, action: Any) -> Any:
        if isinstance(action, AttackAction):
            return IkomaTakeAttackActionEvent(action, self._tracker)
        else:  # pragma: no cover  # defensive: factory only invoked with AttackAction in normal engine flow
            raise ValueError("get_take_attack_action_event only supports AttackAction")


# ──────────────────────────────────────────────────────────────────
# 5th Dan: IkomaFifthDanAttackRolledListener
# Cancel opponent's attack after seeing their roll
# ──────────────────────────────────────────────────────────────────

class IkomaFifthDanAttackRolledListener(Listener):
    """5th Dan listener: when an opponent attacks the Ikoma and the
    tracker has uses remaining, cancel the attack AND fire an Ikoma
    counter-attack against the attacker.  The Ikoma spends their
    lowest available action die for the counter (interrupt-timing).
    The cancelled attack roll value is used as the forced parry roll
    defending against the counter — no fresh parry roll, no opponent
    action die spent.

    Replaces the default AttackRolledListener for the Ikoma character;
    preserves default behavior (observe roll, consult interrupt
    strategy) when 5th Dan does not fire.
    """

    def __init__(self, ikoma: Any, tracker: Any) -> None:
        self._ikoma = ikoma
        self._tracker = tracker
        self._default_listener = AttackRolledListener()

    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]:
        if isinstance(event, AttackRolledEvent):
            # 5th Dan defensive trigger: opponent's attack lands on Ikoma.
            if (
                character == self._ikoma
                and event.action.target() == self._ikoma
                and event.action.subject() != self._ikoma
                and event.action.is_hit()
                and not event.action.parried()
                and self._tracker is not None
                and self._tracker.has_uses()
                and self._ikoma.is_fighting()
                and len(self._ikoma.actions()) > 0
            ):
                attacker = event.action.subject()
                saved_roll = event.action.skill_roll()
                assert saved_roll is not None
                # Cancel the opponent's attack.
                event.action.set_parried()
                self._tracker.use()
                logger.info(
                    f"{self._ikoma.name()} (Ikoma 5th Dan) cancels "
                    f"{attacker.name()}'s attack (roll {saved_roll}); "
                    f"counter-attacking with forced parry = {saved_roll}"
                )
                # Counter-attack: spend the Ikoma's lowest available
                # action die (interrupt-timing).  The forced parry uses
                # the cancelled attack roll, so the opponent spends
                # nothing additional on defense.
                lowest_die = min(self._ikoma.actions())
                interrupt_ia = InitiativeAction(
                    [lowest_die], context.phase(), is_interrupt=True,
                )
                counter = AttackAction(
                    self._ikoma, attacker, "attack", interrupt_ia, context,
                )
                yield SpendActionEvent(self._ikoma, "attack", interrupt_ia)
                yield IkomaFifthDanCounterAttackEvent(counter, saved_roll)
                return
            # Default behavior for all other cases
            yield from self._default_listener.handle(character, event, context)


# ──────────────────────────────────────────────────────────────────
# 5th Dan counter-attack: free attack with parry roll fixed to
# the cancelled opponent attack roll value
# ──────────────────────────────────────────────────────────────────

class IkomaFifthDanCounterAttackEvent(TakeAttackActionEvent):
    """Ikoma counter-attack triggered by the 5th Dan cancel.

    Plays like a normal attack (declare → roll → succeed/fail → damage)
    but the forced parry uses a fixed roll value: the cancelled
    opponent attack roll.  If ``fixed_parry_roll >= ikoma_attack_roll``
    the counter is parried; otherwise it proceeds to damage.

    The Ikoma spends an action die for this counter (handled by the
    listener that yields this event).  The opponent does not spend an
    action die on the parry — the "parry" is automatic, using the
    value already rolled on their cancelled attack.
    """

    def __init__(self, action: Any, fixed_parry_roll: int) -> None:
        super().__init__(action)
        self._fixed_parry_roll = fixed_parry_roll

    def play(self, context: Any) -> Iterator[Any]:
        yield self._declare_attack()
        if not self.action.subject().is_fighting():  # pragma: no cover  # defensive: listener already gated on is_fighting
            return
        yield from self._roll_attack(context)
        if self.action.parried():  # pragma: no cover  # defensive: no listener parries the counter-attack itself
            yield self._failed()
            return
        if self.action.is_hit():
            ikoma_roll = self.action.skill_roll()
            assert ikoma_roll is not None
            if self._fixed_parry_roll >= ikoma_roll:
                # Forced parry succeeds — counter-attack parried.
                self.action.set_parry_attempted()
                self.action.set_parried()
                logger.info(
                    f"Ikoma 5th Dan counter-attack parried: forced parry "
                    f"{self._fixed_parry_roll} >= attack roll {ikoma_roll}"
                )
                yield self._failed()
                return
            yield self._succeeded()
            if self.action.parried():  # pragma: no cover  # defensive: no listener cancels after success here
                return
            if self.action.target().is_fighting():
                yield self._roll_damage()
        else:
            yield self._failed()


# ──────────────────────────────────────────────────────────────────
# 4th Dan: IkomaFourthDanRollParameterProvider
# ──────────────────────────────────────────────────────────────────

class IkomaFourthDanRollParameterProvider(DefaultRollParameterProvider):
    """4th Dan: unparried attack without extra kept damage dice -> always roll 10 dice."""

    def get_damage_roll_params(self, character: Any, target: Any, skill: str, attack_extra_rolled: int, vp: int = 0) -> tuple[int, int, int]:
        rolled, kept, modifier = super().get_damage_roll_params(character, target, skill, attack_extra_rolled, vp)
        # If no extra kept damage dice (attack_extra_rolled == 0 means no raises
        # were called on the attack), roll 10 dice
        if attack_extra_rolled == 0:
            rolled = max(rolled, 10)
        return normalize_roll_params(rolled, kept, modifier)
