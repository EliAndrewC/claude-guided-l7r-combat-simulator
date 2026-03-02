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
# 5th Dan: Use special ability or oppose knack an extra time per round;
#          may cancel opponent's attack and use their roll as parry.
#

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
    def ap_base_skill(self):
        return "bragging"

    def ap_skills(self):
        return ["bragging", "culture", "heraldry", "intimidation", "attack", "wound check"]

    def apply_special_ability(self, character):
        # Create the shared tracker (1 use per round by default)
        tracker = IkomaSpecialTracker()
        # Install the custom TakeActionEventFactory that forces parries
        character.set_take_action_event_factory(IkomaTakeActionEventFactory(tracker))
        # Install the new round listener that resets the tracker
        character.set_listener("new_round", IkomaNewRoundListener(tracker))
        # Store the tracker on the character for 5th Dan to access
        character._ikoma_tracker = tracker

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_roll_parameter_provider(IkomaFourthDanRollParameterProvider())

    def apply_rank_five_ability(self, character):
        # Extra use of special ability per round
        tracker = getattr(character, '_ikoma_tracker', None)
        if tracker is not None:
            tracker.set_max_uses(2)
        # Install 5th Dan listener: cancel opponent's attack after seeing roll
        character.set_listener(
            "attack_rolled",
            IkomaFifthDanAttackRolledListener(character, tracker),
        )

    def extra_rolled(self):
        return ["attack", "bragging", "wound check"]

    def free_raise_skills(self):
        return ["attack"]

    def name(self):
        return "Ikoma Bard School"

    def school_knacks(self):
        return ["discern honor", "oppose knowledge", "oppose social"]

    def school_ring(self):
        return "water"


# ──────────────────────────────────────────────────────────────────
# IkomaSpecialTracker: tracks uses of the special ability per round
# ──────────────────────────────────────────────────────────────────

class IkomaSpecialTracker:
    """Tracks the number of remaining uses of the Ikoma Bard special ability
    per combat round. Defaults to 1 use per round; 5th Dan raises it to 2."""

    def __init__(self):
        self._max_uses = 1
        self._uses_remaining = 1

    def has_uses(self):
        return self._uses_remaining > 0

    def reset(self):
        """Reset uses to the max for a new round."""
        self._uses_remaining = self._max_uses

    def set_max_uses(self, n):
        """Set the maximum uses per round (e.g. 2 at 5th Dan)."""
        self._max_uses = n
        self._uses_remaining = n

    def use(self):
        """Consume one use of the special ability."""
        if self._uses_remaining > 0:
            self._uses_remaining -= 1

    def uses_remaining(self):
        return self._uses_remaining


# ──────────────────────────────────────────────────────────────────
# IkomaNewRoundListener: reset tracker and roll initiative
# ──────────────────────────────────────────────────────────────────

class IkomaNewRoundListener(NewRoundListener):
    """New round listener that resets the IkomaSpecialTracker and
    rolls initiative (standard new round behavior)."""

    def __init__(self, tracker):
        self._tracker = tracker

    def handle(self, character, event, context):
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

    def __init__(self, action, tracker):
        super().__init__(action)
        self._tracker = tracker

    def play(self, context):
        yield self._declare_attack()
        # Counterattack may have killed/incapacitated the attacker
        if not self.action.subject().is_fighting():
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
            if self.action.parried():
                return
            direct_damage = self._direct_damage()
            if direct_damage is not None:
                yield direct_damage
            if self.action.target().is_fighting():
                yield self._roll_damage()
        else:
            yield self._failed()

    def _force_parry(self, context):
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

    def __init__(self, tracker):
        self._tracker = tracker

    def get_take_attack_action_event(self, action):
        if isinstance(action, AttackAction):
            return IkomaTakeAttackActionEvent(action, self._tracker)
        else:
            raise ValueError("get_take_attack_action_event only supports AttackAction")


# ──────────────────────────────────────────────────────────────────
# 5th Dan: IkomaFifthDanAttackRolledListener
# Cancel opponent's attack after seeing their roll
# ──────────────────────────────────────────────────────────────────

class IkomaFifthDanAttackRolledListener(Listener):
    """5th Dan listener: when an opponent attacks the Ikoma and the tracker
    has uses remaining, cancel the attack (set it as parried).

    This replaces the default AttackRolledListener for the Ikoma character.
    It preserves the default behavior (observe roll, consult interrupt strategy)
    while adding the 5th Dan cancel ability.
    """

    def __init__(self, ikoma, tracker):
        self._ikoma = ikoma
        self._tracker = tracker
        self._default_listener = AttackRolledListener()

    def handle(self, character, event, context):
        if isinstance(event, AttackRolledEvent):
            # 5th Dan cancel: when an opponent attacks the Ikoma
            if (
                character == self._ikoma
                and event.action.target() == self._ikoma
                and event.action.subject() != self._ikoma
                and event.action.is_hit()
                and not event.action.parried()
                and self._tracker is not None
                and self._tracker.has_uses()
            ):
                # Cancel the attack
                event.action.set_parried()
                self._tracker.use()
                logger.info(
                    f"{self._ikoma.name()} (Ikoma 5th Dan) cancels "
                    f"{event.action.subject().name()}'s attack"
                )
                yield from ()
                return
            # Default behavior for all other cases
            yield from self._default_listener.handle(character, event, context)


# ──────────────────────────────────────────────────────────────────
# 4th Dan: IkomaFourthDanRollParameterProvider
# ──────────────────────────────────────────────────────────────────

class IkomaFourthDanRollParameterProvider(DefaultRollParameterProvider):
    """4th Dan: unparried attack without extra kept damage dice -> always roll 10 dice."""

    def get_damage_roll_params(self, character, target, skill, attack_extra_rolled, vp=0):
        rolled, kept, modifier = super().get_damage_roll_params(character, target, skill, attack_extra_rolled, vp)
        # If no extra kept damage dice (attack_extra_rolled == 0 means no raises
        # were called on the attack), roll 10 dice
        if attack_extra_rolled == 0:
            rolled = max(rolled, 10)
        return normalize_roll_params(rolled, kept, modifier)
