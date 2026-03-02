#!/usr/bin/env python3

#
# otaku_school.py
#
# Implement Otaku Bushi School.
#
# School Ring: Fire
# School Knacks: double attack, iaijutsu, lunge
#
# Special Ability: Interrupt lunge for 1 die after being attacked.
# 1st Dan: Extra rolled on iaijutsu, lunge, wound check
# 2nd Dan: Free raise on wound check
# 3rd Dan: After damage roll, increase target's next X action dice
#          by (6 - target.fire, min 1), max phase 10.
# 4th Dan: Ring+1/discount; custom OtakuLungeAction where
#          calculate_extra_damage_dice always adds 1 even when parried.
# 5th Dan: Strategy: compare expected SW with/without trading 10 rolled dice
#          for 1 automatic SW. Custom damage action that reduces rolled dice
#          by 10 (min 2) and yields SeriousWoundsDamageEvent.
#

from simulation import events
from simulation.actions import AttackAction, LungeAction
from simulation.events import LightWoundsDamageEvent, SeriousWoundsDamageEvent, TakeAttackActionEvent
from simulation.listeners import Listener
from simulation.schools.base import BaseSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory


class OtakuBushiSchool(BaseSchool):
    def ap_base_skill(self):
        return None

    def apply_special_ability(self, character):
        character.set_interrupt_cost("lunge", 1)
        character.add_interrupt_skill("lunge")

    def apply_rank_three_ability(self, character):
        character.set_listener("lw_damage", OtakuLightWoundsDamageListener())

    def apply_rank_four_ability(self, character):
        self.apply_school_ring_raise_and_discount(character)
        character.set_action_factory(OTAKU_ACTION_FACTORY)

    def apply_rank_five_ability(self, character):
        character.set_take_action_event_factory(OTAKU_FIFTH_DAN_TAKE_ACTION_EVENT_FACTORY)

    def extra_rolled(self):
        return ["iaijutsu", "lunge", "wound check"]

    def free_raise_skills(self):
        return ["wound check"]

    def name(self):
        return "Otaku Bushi School"

    def school_knacks(self):
        return ["double attack", "iaijutsu", "lunge"]

    def school_ring(self):
        return "fire"


class OtakuLightWoundsDamageListener(Listener):
    """
    Listener to implement the Otaku 3rd Dan technique:
    After dealing damage, increase target's next X action dice
    by (6 - target.fire, min 1), max phase 10.
    X is the number of action dice affected.
    """

    def handle(self, character, event, context):
        if isinstance(event, events.LightWoundsDamageEvent):
            if event.subject == character and event.target != character:
                target = event.target
                increase = max(1, 6 - target.ring("fire"))
                # Modify target's action dice
                actions = target.actions()
                for i in range(len(actions)):
                    actions[i] = min(10, actions[i] + increase)
                actions.sort()
            if event.subject != character:
                # observe another character's damage roll
                character.knowledge().observe_damage_roll(event.subject, event.damage)
            if event.target == character:
                character.take_lw(event.damage)
                if event.damage > 0:
                    yield from character.wound_check_strategy().recommend(character, event, context)


class OtakuLungeAction(LungeAction):
    """
    Custom LungeAction for Otaku 4th Dan:
    calculate_extra_damage_dice always adds 1 even when parried.
    """

    def calculate_extra_damage_dice(self, skill_roll=None, tn=None):
        if skill_roll is None:
            skill_roll = self.skill_roll()
        if tn is None:
            tn = self.tn()
        if self.parry_attempted():
            # Still get +1 even when parried
            return 1
        return ((skill_roll - tn) // 5) + 1


class OtakuActionFactory(DefaultActionFactory):
    """
    ActionFactory to return Otaku-specific attack actions.
    """

    def get_attack_action(self, subject, target, skill, initiative_action, context, vp=0):
        if skill == "lunge":
            return OtakuLungeAction(subject, target, skill, initiative_action, context, vp=vp)
        return super().get_attack_action(subject, target, skill, initiative_action, context, vp=vp)


OTAKU_ACTION_FACTORY = OtakuActionFactory()


class OtakuFifthDanTakeAttackActionEvent(TakeAttackActionEvent):
    """
    Custom TakeAttackActionEvent for the Otaku 5th Dan ability:
    After a successful attack or lunge roll, decrease the number of
    rolled damage dice by 10 (to a minimum of 2) to automatically
    deal 1 serious wound to the opponent.
    """

    def play(self, context):
        yield self._declare_attack()
        if not self.action.subject().is_fighting():
            return
        yield from self._roll_attack(context)
        if self.action.parried():
            yield self._failed()
            return
        if self.action.is_hit():
            yield self._succeeded()
            direct_damage = self._direct_damage()
            if direct_damage is not None:
                yield direct_damage
            if self.action.target().is_fighting():
                yield from self._roll_damage()
        else:
            yield self._failed()

    def _roll_damage(self):
        subject = self.action.subject()
        target = self.action.target()
        extra_rolled = self.action.calculate_extra_damage_dice()

        # Calculate raw rolled dice before normalization
        ring = subject.ring(subject.get_skill_ring("damage"))
        my_extra_rolled = subject.extra_rolled("damage")
        raw_rolled = ring + my_extra_rolled + extra_rolled + subject.weapon().rolled()

        if raw_rolled >= 12:
            # Trade 10 rolled dice for 1 automatic serious wound
            yield SeriousWoundsDamageEvent(subject, target, 1)
            # Roll damage with reduced dice (subtract 10 from extra)
            reduced_extra = extra_rolled - 10
            damage_roll = subject.roll_damage(target, self.action.skill(), reduced_extra, self.action.vp())
            damage_roll = max(0, damage_roll)
            self.action.set_damage_roll(damage_roll)
            yield LightWoundsDamageEvent(subject, target, damage_roll)
        else:
            # Standard damage roll
            damage_roll = self.action.roll_damage()
            yield LightWoundsDamageEvent(subject, target, damage_roll)


class OtakuFifthDanTakeActionEventFactory(DefaultTakeActionEventFactory):
    """
    TakeActionEventFactory for the Otaku 5th Dan ability.
    Returns OtakuFifthDanTakeAttackActionEvent for attacks.
    """

    def get_take_attack_action_event(self, action):
        if isinstance(action, AttackAction):
            return OtakuFifthDanTakeAttackActionEvent(action)
        else:
            raise ValueError("get_take_attack_action_event only supports AttackAction")


OTAKU_FIFTH_DAN_TAKE_ACTION_EVENT_FACTORY = OtakuFifthDanTakeActionEventFactory()
