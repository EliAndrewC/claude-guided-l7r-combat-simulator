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
from simulation.mechanics.skills import ATTACK_SKILLS
from simulation.modifier_listeners import ExpireAfterNextAttackByCharacterListener, ExpireAtEndOfRoundListener
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import CounterattackInterruptStrategy
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory


class DaidojiYojimboSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        character.set_interrupt_cost("counterattack", 1)
        character.set_action_factory(DAIDOJI_ACTION_FACTORY)
        character.set_take_action_event_factory(DAIDOJI_TAKE_ACTION_EVENT_FACTORY)
        character.set_strategy("interrupt", CounterattackInterruptStrategy())

    def apply_rank_three_ability(self, character):
        # After a successful counterattack, grant X free raises on wound check
        # to the target of the original attack, where X = Daidoji's attack skill.
        character._daidoji_third_dan = True

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        # Redirect damage from allies to the Daidoji
        character.set_listener("lw_damage", DaidojiFourthDanListener(character))

    def apply_rank_five_ability(self, character):
        # After a wound check succeeds, lower the attacker's TN to hit
        # by the excess amount.
        character.set_listener("wound_check_succeeded", DaidojiFifthDanWoundCheckListener(character))

    def extra_rolled(self):
        return ["attack", "counterattack", "wound check"]

    def free_raise_skills(self):
        return ["counterattack"]

    def name(self):
        return "Daidoji Yojimbo School"

    def school_knacks(self):
        return ["counterattack", "double attack", "iaijutsu"]

    def school_ring(self):
        return "water"


class DaidojiCounterattackAction(CounterattackAction):
    """Daidoji counterattacks have no TN penalty for counterattacking
    on behalf of other characters."""

    def tn(self):
        return self.target().tn_to_hit()


class DaidojiActionFactory(DefaultActionFactory):
    """ActionFactory that returns DaidojiCounterattackAction for counterattacks."""

    def get_counterattack_action(self, subject, target, attack, skill, initiative_action, context, vp=0):
        return DaidojiCounterattackAction(subject, target, skill, initiative_action, context, attack, vp=vp)


DAIDOJI_ACTION_FACTORY = DaidojiActionFactory()


class DaidojiTakeCounterattackActionEvent(TakeCounterattackActionEvent):
    """Custom TakeCounterattackActionEvent for the Daidoji special ability.

    When the counterattack is used as an interrupt (1-die cost) and hits,
    the opponent gets a free raise on their wound check (+5 to roll,
    implemented as -5 on the wound check TN).
    """

    def play(self, context):
        yield CounterattackDeclaredEvent(self.action)
        self.action.roll_skill()
        if self.action.vp() > 0:
            yield SpendVoidPointsEvent(self.action.subject(), self.action.skill(), self.action.vp())
        yield CounterattackRolledEvent(self.action, self.action.skill_roll())
        if self.action.is_hit():
            yield CounterattackSucceededEvent(self.action)
            # 3rd Dan: grant wound check floating bonus to the original attack target
            daidoji = self.action.subject()
            if getattr(daidoji, '_daidoji_third_dan', False):
                original_target = self.action.attack().target()
                bonus = 5 * daidoji.skill("attack")
                if bonus > 0:
                    original_target.gain_floating_bonus(WoundCheckFloatingBonus(bonus))
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

    def get_take_counterattack_action_event(self, action):
        return DaidojiTakeCounterattackActionEvent(action)


DAIDOJI_TAKE_ACTION_EVENT_FACTORY = DaidojiTakeActionEventFactory()


class DaidojiFourthDanListener(Listener):
    """4th Dan: Redirect damage from allies to the Daidoji.

    When an ally (same group, not the Daidoji) is the target of a
    LightWoundsDamageEvent, the Daidoji takes the damage instead.
    When the Daidoji is the target, damage is handled normally.
    Also observes other characters' damage rolls (same as default).
    """

    def __init__(self, daidoji):
        self._daidoji = daidoji
        self._default_listener = LightWoundsDamageListener()

    def handle(self, character, event, context):
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
    """5th Dan: After a wound check succeeds for the Daidoji or an ally,
    lower the attacker's TN to hit by the excess amount.

    The modifier is added to the Daidoji (not the ally) and targets
    the attacker with ATTACK_SKILLS. It expires after the next attack
    against the attacker or at end of round.
    """

    def __init__(self, daidoji):
        self._daidoji = daidoji
        self._default_listener = None

    def handle(self, character, event, context):
        if isinstance(event, WoundCheckSucceededEvent):
            if character != self._daidoji:
                # Non-Daidoji characters: use default behavior
                yield from character.light_wounds_strategy().recommend(character, event, context)
                return
            # Check if the wound check subject is the Daidoji or an ally
            subject_is_daidoji = (event.subject == self._daidoji)
            subject_is_ally = (
                event.subject in self._daidoji.group()
                and event.subject != self._daidoji
                and context.formation().is_adjacent(self._daidoji, event.subject)
            )
            if subject_is_daidoji:
                # Daidoji's own wound check: handle default behavior first
                yield from self._daidoji.light_wounds_strategy().recommend(
                    self._daidoji, event, context,
                )
            # Grant the modifier if the subject is the Daidoji or an ally
            if subject_is_daidoji or subject_is_ally:
                excess = event.roll - event.tn
                if excess > 0:
                    attacker = event.attacker
                    modifier = Modifier(self._daidoji, attacker, ATTACK_SKILLS, excess)
                    attack_listener = ExpireAfterNextAttackByCharacterListener(self._daidoji)
                    end_of_round_listener = ExpireAtEndOfRoundListener()
                    modifier.register_listener("attack_failed", attack_listener)
                    modifier.register_listener("attack_succeeded", attack_listener)
                    modifier.register_listener("end_of_round", end_of_round_listener)
                    yield AddModifierEvent(self._daidoji, modifier)
