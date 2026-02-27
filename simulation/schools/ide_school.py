#!/usr/bin/env python3

#
# ide_school.py
#
# Implement Ide Diplomat School.
#
# School Ring: Water
# School Knacks: double attack, feint, worldliness
#
# Special Ability: After a feint hits TN, lower target's TN by 10
#                  for the Ide's next attack (even if parried).
# 1st Dan: Extra rolled on wound check, initiative, precepts
# 2nd Dan: Free raise on attack
# 3rd Dan: Spend 1 VP to subtract Xk1 from enemy's attack roll (X = tact skill)
# 4th Dan: Ring+1/discount (+ extra VP per night, no-op in combat)
# 5th Dan: Gain 1 TVP when spending VP (not from 3rd dan tact usage)
#

from simulation import events
from simulation.listeners import Listener
from simulation.mechanics.modifiers import AnyAttackModifier
from simulation.modifier_listeners import ExpireAfterNextAttackByCharacterListener, ExpireAtEndOfRoundListener
from simulation.schools.base import BaseSchool


class IdeDiplomatSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        character.set_listener("attack_succeeded", IdeFeintSucceededListener())
        character.set_listener("attack_failed", IdeFeintFailedListener())

    def apply_rank_three_ability(self, character):
        character.set_listener("attack_rolled", IdeTactSubtractListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)

    def apply_rank_five_ability(self, character):
        character.set_listener("spend_vp", IdeSpendVPListener())

    def extra_rolled(self):
        return ["wound check", "initiative", "precepts"]

    def free_raise_skills(self):
        return ["attack"]

    def name(self):
        return "Ide Diplomat School"

    def school_knacks(self):
        return ["double attack", "feint", "worldliness"]

    def school_ring(self):
        return "water"


class IdeFeintSucceededListener(Listener):
    """
    After a successful feint, lower target's TN by 10 for the Ide's next attack.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.AttackSucceededEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    target = event.action.target()
                    modifier = AnyAttackModifier(character, target, -10)
                    attack_listener = ExpireAfterNextAttackByCharacterListener(character)
                    end_of_round_listener = ExpireAtEndOfRoundListener()
                    modifier.register_listener("attack_failed", attack_listener)
                    modifier.register_listener("attack_succeeded", attack_listener)
                    modifier.register_listener("end_of_round", end_of_round_listener)
                    yield events.AddModifierEvent(target, modifier)


class IdeFeintFailedListener(Listener):
    """
    Even on a failed feint (hit TN but parried), lower target's TN by 10.
    AttackFailedEvent fires both when missing TN and when parried.
    We apply the bonus regardless since the rules say "after a feint hits TN".
    """

    def handle(self, character, event, context):
        if isinstance(event, events.AttackFailedEvent):
            if event.action.subject() == character:
                if event.action.skill() == "feint":
                    # Only apply if the feint was parried (hit TN but was blocked)
                    if event.action.parried():
                        target = event.action.target()
                        modifier = AnyAttackModifier(character, target, -10)
                        attack_listener = ExpireAfterNextAttackByCharacterListener(character)
                        end_of_round_listener = ExpireAtEndOfRoundListener()
                        modifier.register_listener("attack_failed", attack_listener)
                        modifier.register_listener("attack_succeeded", attack_listener)
                        modifier.register_listener("end_of_round", end_of_round_listener)
                        yield events.AddModifierEvent(target, modifier)


class IdeTactSubtractListener(Listener):
    """
    3rd Dan: When this character is the target of an attack, spend 1 VP
    to roll Xk1 (X = tact skill) and subtract from attacker's roll.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.AttackRolledEvent):
            if event.action.target() == character:
                tact = character.skill("tact")
                if tact > 0 and character.vp() >= 1:
                    yield events.SpendVoidPointsEvent(character, "tact", 1)
                    penalty = character.roll_provider().get_skill_roll("tact", tact, 1, True)
                    new_roll = max(0, event.roll - penalty)
                    event.action.set_skill_roll(new_roll)
                    yield events.AttackRolledEvent(event.action, new_roll)
            elif character != event.action.subject():
                # Default behavior: observe and consider interrupt
                character.knowledge().observe_attack_roll(event.action.subject(), event.roll)
                yield from character.interrupt_strategy().recommend(character, event, context)


class IdeSpendVPListener(Listener):
    """
    5th Dan: Gain 1 TVP when spending VP (not from 3rd dan tact usage).
    """

    def handle(self, character, event, context):
        if isinstance(event, events.SpendVoidPointsEvent):
            if event.subject == character:
                character.spend_vp(event.amount)
                if event.skill != "tact":
                    yield events.GainTemporaryVoidPointsEvent(character, 1)
