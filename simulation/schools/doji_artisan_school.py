#!/usr/bin/env python3

#
# doji_artisan_school.py
#
# Implement Doji Artisan School.
#
# School Ring: Water (default; rules say "Air or Water")
# School Knacks: counterattack, oppose social, worldliness
#
# Special Ability: Spend VP to counterattack as interrupt (cost 1 action die);
#                  VP gives +1k1. While counterattacking, bonus = attacker's roll / 5.
# 1st Dan: Extra rolled on counterattack, manipulation, wound check
# 2nd Dan: Free raise on manipulation
# 3rd Dan: AP system — ap_base_skill = "culture", ap_skills = ["counterattack", "wound check"]
# 4th Dan: Ring+1/discount; attacking target who hasn't attacked you this round,
#          bonus = current phase.
# 5th Dan: On TN/contested rolls, bonus = (X-10)/5 where X = TN or opponent's roll.
#

from simulation import events
from simulation.exceptions import NotEnoughActions
from simulation.listeners import Listener, NewRoundListener
from simulation.log import logger
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.schools.base import BaseSchool
from simulation.strategies.base import CounterattackInterruptStrategy
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory


class DojiArtisanSchool(BaseSchool):
    def ap_base_skill(self):
        return "culture"

    def ap_skills(self):
        return ["bragging", "culture", "heraldry", "manipulation", "counterattack", "wound check"]

    def apply_special_ability(self, character):
        # Counterattack as interrupt at cost of 1 action die
        character.set_interrupt_cost("counterattack", 1)
        character.set_strategy("interrupt", DojiArtisanCounterattackInterruptStrategy())
        character.set_take_action_event_factory(DOJI_ARTISAN_TAKE_ACTION_EVENT_FACTORY)

    def apply_rank_three_ability(self, character):
        self.apply_ap(character)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # Phase bonus when attacking target who hasn't attacked this round
        tracker = DojiArtisanAttackTracker()
        character._doji_artisan_attack_tracker = tracker
        character.set_listener("attack_declared", DojiArtisanAttackDeclaredListener(character, tracker))
        character.set_listener("new_round", DojiArtisanNewRoundListener(tracker))
        character.set_listener("attack_rolled", DojiArtisanAttackRolledListener(character, tracker))

    def apply_rank_five_ability(self, character):
        # On TN/contested rolls, bonus = (X-10)/5 where X = TN or opponent's roll.
        # This requires knowing the TN or opponent's contested roll at roll time.
        character.set_roll_parameter_provider(DojiFifthDanRollParameterProvider())

    def extra_rolled(self):
        return ["counterattack", "manipulation", "wound check"]

    def free_raise_skills(self):
        return ["manipulation"]

    def name(self):
        return "Doji Artisan School"

    def school_knacks(self):
        return ["counterattack", "oppose social", "worldliness"]

    def school_ring(self):
        return "water"


# ── Special Ability: VP counterattack interrupt with attacker's roll bonus ──


class DojiArtisanCounterattackInterruptStrategy(CounterattackInterruptStrategy):
    """Doji Artisan counterattack interrupt triggers on AttackRolledEvent
    (after seeing the attacker's roll) rather than AttackDeclaredEvent.

    Requires spending 1 VP (which gives +1k1 to the counterattack roll).
    Also calculates bonus = attacker's roll // 5 and stores it on the action.
    """

    def _should_counterattack(self, character, event, context):
        """Only counterattack on AttackRolledEvent (need to see the roll)."""
        if not isinstance(event, events.AttackRolledEvent):
            return False
        # Must have VP to spend
        if character.vp() <= 0:
            return False
        return super()._should_counterattack(character, event, context)

    def _do_counterattack(self, character, event, context):
        """Execute the counterattack with VP=1 and attacker roll bonus."""
        initiative_action = self._choose_action(character, context)
        # Calculate attacker's roll bonus
        attacker_roll_bonus = event.roll // 5
        counterattack = character.action_factory().get_counterattack_action(
            character, event.action.subject(), event.action,
            "counterattack", initiative_action, context, vp=1,
        )
        # Store the attacker roll bonus on the action
        counterattack._attacker_roll_bonus = attacker_roll_bonus
        logger.info(
            f"{character.name()} is counterattacking {event.action.subject().name()} "
            f"(spending 1 VP, attacker roll bonus +{attacker_roll_bonus})"
        )
        yield events.SpendActionEvent(character, "counterattack", initiative_action)
        yield character.take_action_event_factory().get_take_counterattack_action_event(counterattack)

    def recommend(self, character, event, context):
        if isinstance(event, events.AttackDeclaredEvent):
            # Do NOT counterattack on declaration -- we need to see the roll
            return
        elif isinstance(event, events.AttackRolledEvent):
            if self._should_counterattack(character, event, context):
                try:
                    yield from self._do_counterattack(character, event, context)
                    return
                except NotEnoughActions:
                    pass
            # Fall through to parry
            yield from character.parry_strategy().recommend(character, event, context)


class DojiArtisanTakeCounterattackActionEvent(events.TakeCounterattackActionEvent):
    """Custom TakeCounterattackActionEvent for the Doji Artisan special ability.

    After rolling the counterattack skill, adds the attacker's roll bonus
    (attacker's roll // 5) to the counterattack skill roll.
    Also spends 1 VP (which was declared on the action with vp=1).
    """

    def play(self, context):
        yield events.CounterattackDeclaredEvent(self.action)
        self.action.roll_skill()
        # Apply the attacker's roll bonus
        attacker_roll_bonus = getattr(self.action, '_attacker_roll_bonus', 0)
        if attacker_roll_bonus > 0:
            new_roll = self.action.skill_roll() + attacker_roll_bonus
            self.action.set_skill_roll(new_roll)
        # Spend VP (declared as vp=1 on the action)
        vp_to_spend = min(self.action.vp(), self.action.subject().vp())
        if vp_to_spend > 0:
            yield events.SpendVoidPointsEvent(
                self.action.subject(), self.action.skill(), vp_to_spend,
            )
        yield events.CounterattackRolledEvent(self.action, self.action.skill_roll())
        if self.action.is_hit():
            yield events.CounterattackSucceededEvent(self.action)
            if self.action.target().is_fighting():
                damage = self.action.roll_damage()
                yield events.LightWoundsDamageEvent(
                    self.action.subject(), self.action.target(), damage,
                )
        else:
            yield events.CounterattackFailedEvent(self.action)


class DojiArtisanTakeActionEventFactory(DefaultTakeActionEventFactory):
    """Custom TakeActionEventFactory that returns Doji Artisan-specific
    counterattack events."""

    def get_take_counterattack_action_event(self, action):
        return DojiArtisanTakeCounterattackActionEvent(action)


DOJI_ARTISAN_TAKE_ACTION_EVENT_FACTORY = DojiArtisanTakeActionEventFactory()


# ── 4th Dan: Phase bonus vs targets who haven't attacked you ──


class DojiArtisanAttackTracker:
    """Tracks which characters have attacked the Doji Artisan this round.
    Used by the 4th Dan ability to determine phase bonus eligibility."""

    def __init__(self):
        self._attackers = set()

    def has_attacked(self, character):
        """Return whether the given character has attacked the artisan this round."""
        return character in self._attackers

    def record_attacker(self, character):
        """Record that the given character has attacked the artisan."""
        self._attackers.add(character)

    def reset(self):
        """Reset the tracker at the start of a new round."""
        self._attackers.clear()


class DojiArtisanAttackDeclaredListener(Listener):
    """Listener that records when opponents attack the Doji Artisan.
    Also delegates to the standard AttackDeclaredListener for interrupt handling."""

    def __init__(self, doji, tracker):
        self._doji = doji
        self._tracker = tracker

    def handle(self, character, event, context):
        if isinstance(event, events.AttackDeclaredEvent):
            if character == self._doji:
                # Record attacker if they are targeting the Doji
                if event.action.target() == self._doji:
                    self._tracker.record_attacker(event.action.subject())
            # Delegate to standard interrupt handling
            if character != event.action.subject():
                yield from character.interrupt_strategy().recommend(character, event, context)
                # Lunge modifier handling (from the default AttackDeclaredListener)
                if event.action.skill() == "lunge":
                    if event.action.subject() not in character.group():
                        from simulation import modifier_listeners
                        from simulation.mechanics import modifiers
                        modifier = modifiers.AnyAttackModifier(character, event.subject(), 5)
                        attack_listener = modifier_listeners.ExpireAfterNextAttackByCharacterListener(modifier, event.action.subject())
                        end_of_round_listener = modifier_listeners.ExpireAtEndOfRoundListener(modifier)
                        modifier.register_listener("attack_failed", attack_listener)
                        modifier.register_listener("attack_succeeded", attack_listener)
                        modifier.register_listener("end_of_round", end_of_round_listener)
                        yield events.AddModifierEvent(modifier)


class DojiArtisanNewRoundListener(Listener):
    """Listener that resets the attack tracker each round and rolls initiative."""

    def __init__(self, tracker):
        self._tracker = tracker
        self._default_listener = NewRoundListener()

    def handle(self, character, event, context):
        if isinstance(event, events.NewRoundEvent):
            self._tracker.reset()
            yield from self._default_listener.handle(character, event, context)


class DojiArtisanAttackRolledListener(Listener):
    """Listener for the 4th Dan ability: when the Doji attacks a target who
    has not attacked the Doji this round, add the current phase as a bonus
    to the attack roll.

    Also delegates to the standard AttackRolledListener for interrupt/parry handling."""

    def __init__(self, doji, tracker):
        self._doji = doji
        self._tracker = tracker

    def handle(self, character, event, context):
        if isinstance(event, events.AttackRolledEvent):
            if character == self._doji:
                # Apply 4th Dan phase bonus if the Doji is the attacker
                if event.action.subject() == self._doji:
                    target = event.action.target()
                    if not self._tracker.has_attacked(target):
                        phase_bonus = context.phase()
                        if phase_bonus > 0:
                            new_roll = event.action.skill_roll() + phase_bonus
                            event.action.set_skill_roll(new_roll)
                            event.roll = new_roll
                            logger.info(
                                f"{self._doji.name()} gets +{phase_bonus} phase bonus "
                                f"against {target.name()} (4th Dan)"
                            )
            # Standard handling: observe roll and check for interrupts
            if character != event.action.subject():
                character.knowledge().observe_attack_roll(event.action.subject(), event.roll)
                yield from character.interrupt_strategy().recommend(character, event, context)
            else:
                yield from ()


# ── 5th Dan ──


class DojiFifthDanRollParameterProvider(DefaultRollParameterProvider):
    """5th Dan: on TN/contested rolls, bonus = max(0, (TN - 10) / 5)."""

    def get_skill_roll_params(self, character, target, skill, contested_skill=None, ring=None, vp=0):
        rolled, kept, modifier = super().get_skill_roll_params(character, target, skill, contested_skill, ring, vp)
        # For attack rolls, the TN is the target's TN to hit
        if target is not None:
            tn = target.tn_to_hit()
            bonus = max(0, (tn - 10) // 5)
            modifier += bonus
        return normalize_roll_params(rolled, kept, modifier)

    def get_wound_check_roll_params(self, character, vp=0):
        rolled, kept, modifier = super().get_wound_check_roll_params(character, vp)
        # For wound checks, X = LW total (the TN).
        # Since we don't have the TN at this point, we use LW.
        lw = character.lw()
        bonus = max(0, (lw - 10) // 5)
        modifier += bonus
        return normalize_roll_params(rolled, kept, modifier)
