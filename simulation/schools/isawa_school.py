#!/usr/bin/env python3

#
# isawa_school.py
#
# Implement Isawa Duelist School.
#
# School Ring: Water
# School Knacks: double attack, iaijutsu, lunge
#
# Special Ability: Uses Water ring for damage instead of Fire.
# 1st Dan: Extra rolled on double attack, lunge, wound check
# 2nd Dan: Free raise on wound check
# 3rd Dan: Custom attack actions add +3*attack_skill to modifier
#          AND lower own TN by 5 (add Modifier on self, "tn to hit", -5,
#          expires after next attack)
# 4th Dan: Ring+1/discount; interrupt lunge for 1 die, once per round
#          (reset via NewRoundListener)
# 5th Dan: After successful wound check, gain WoundCheckFloatingBonus(roll - damage)
#

from simulation import events
from simulation.actions import AttackAction, DoubleAttackAction, LungeAction
from simulation.listeners import Listener
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.mechanics.modifiers import Modifier
from simulation.mechanics.roll_params import DefaultRollParameterProvider, normalize_roll_params
from simulation.modifier_listeners import ExpireAfterNextAttackListener
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory


class IsawaDuelistSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        # Water ring for damage instead of Fire
        character._skill_rings["damage"] = "water"
        character.set_roll_parameter_provider(ISAWA_ROLL_PARAMETER_PROVIDER)

    def apply_rank_three_ability(self, character):
        character.set_action_factory(ISAWA_ACTION_FACTORY)

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_interrupt_cost("lunge", 1)
        character.add_interrupt_skill("lunge")
        character.set_listener("new_round", IsawaNewRoundListener())

    def apply_rank_five_ability(self, character):
        character.set_listener("wound_check_succeeded", IsawaWoundCheckSucceededListener())

    def extra_rolled(self):
        return ["double attack", "lunge", "wound check"]

    def free_raise_skills(self):
        return ["wound check"]

    def name(self):
        return "Isawa Duelist School"

    def school_knacks(self):
        return ["double attack", "iaijutsu", "lunge"]

    def school_ring(self):
        return "water"


class IsawaRollParameterProvider(DefaultRollParameterProvider):
    """
    RollParameterProvider to implement the Isawa special ability:
    Uses Water ring for damage instead of Fire.
    """

    def get_damage_roll_params(self, character, target, skill, attack_extra_rolled, vp=0):
        # Use water ring for damage
        ring = character.ring("water")
        my_extra_rolled = character.extra_rolled("damage")
        rolled = ring + my_extra_rolled + attack_extra_rolled + character.weapon().rolled()
        kept = character.weapon().kept() + character.extra_kept("damage")
        mod = character.modifier(None, "damage")
        return normalize_roll_params(rolled, kept, mod)


ISAWA_ROLL_PARAMETER_PROVIDER = IsawaRollParameterProvider()


class IsawaAttackAction(AttackAction):
    """
    Custom AttackAction for Isawa 3rd Dan:
    Add +3*attack_skill to skill roll modifier.
    After the attack, lower own TN by 5 (expires after next attack).
    """

    def skill_roll_params(self):
        (rolled, kept, modifier) = self.subject().get_skill_roll_params(self.target(), self.skill(), vp=self.vp())
        bonus = 3 * self.subject().skill("attack")
        return (rolled, kept, modifier + bonus)


class IsawaDoubleAttackAction(DoubleAttackAction):
    """
    Custom DoubleAttackAction for Isawa 3rd Dan.
    """

    def skill_roll_params(self):
        (rolled, kept, modifier) = self.subject().get_skill_roll_params(self.target(), self.skill(), vp=self.vp())
        bonus = 3 * self.subject().skill("attack")
        return (rolled, kept, modifier + bonus)


class IsawaLungeAction(LungeAction):
    """
    Custom LungeAction for Isawa 3rd Dan.
    """

    def skill_roll_params(self):
        (rolled, kept, modifier) = self.subject().get_skill_roll_params(self.target(), self.skill(), vp=self.vp())
        bonus = 3 * self.subject().skill("attack")
        return (rolled, kept, modifier + bonus)


class IsawaActionFactory(DefaultActionFactory):
    """
    ActionFactory to return Isawa-specific attack actions.
    """

    def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
        if skill in ("attack", "iaijutsu"):
            return IsawaAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        elif skill == "double attack":
            return IsawaDoubleAttackAction(subject, target, skill, initiative_action, context, vp=vp)
        elif skill == "lunge":
            return IsawaLungeAction(subject, target, skill, initiative_action, context, vp=vp)
        elif skill == "feint":
            return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)
        else:
            raise ValueError(f"Invalid attack skill: {skill}")


ISAWA_ACTION_FACTORY = IsawaActionFactory()


class IsawaAttackDeclaredListener(Listener):
    """
    Listener for Isawa 3rd Dan: after declaring an attack,
    lower own TN by 5 (expires after next attack against self).
    """

    def handle(self, character, event, context):
        if isinstance(event, events.AttackDeclaredEvent):
            if event.action.subject() == character:
                # Lower own TN by 5
                modifier = Modifier(character, None, "tn to hit", -5)
                listener = ExpireAfterNextAttackListener()
                modifier.register_listener("attack_failed", listener)
                modifier.register_listener("attack_succeeded", listener)
                yield events.AddModifierEvent(character, modifier)
            else:
                # Default attack declared behavior (counterattack/interrupt opportunities)
                yield from ()


class IsawaNewRoundListener(Listener):
    """
    Listener to reset the Isawa 4th Dan interrupt lunge ability each round.
    The standard interrupt cost mechanism handles this; we just need to
    re-enable it each round by resetting the character's interrupt state.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.NewRoundEvent):
            character.roll_initiative()
            # Reset interrupt lunge availability by restoring interrupt cost
            character.set_interrupt_cost("lunge", 1)
        yield from ()


class IsawaWoundCheckSucceededListener(Listener):
    """
    Listener to implement the Isawa 5th Dan technique:
    After successful wound check, gain WoundCheckFloatingBonus(roll - damage).
    """

    def handle(self, character, event, context):
        if isinstance(event, events.WoundCheckSucceededEvent):
            if event.subject == character:
                bonus = event.roll - event.damage
                if bonus > 0:
                    character.gain_floating_bonus(WoundCheckFloatingBonus(bonus))
                # Continue with normal wound check succeeded behavior
                yield from character.light_wounds_strategy().recommend(character, event, context)
