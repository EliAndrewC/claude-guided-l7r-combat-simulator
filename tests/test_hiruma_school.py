#!/usr/bin/env python3

#
# test_hiruma_school.py
#
# Unit tests for the Hiruma Scout School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.modifiers import Modifier
from simulation.modifier_listeners import ExpireAfterNDamageRollsListener
from simulation.schools import hiruma_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestHirumaScoutSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        school = hiruma_school.HirumaScoutSchool()
        self.assertEqual(["initiative", "parry", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = hiruma_school.HirumaScoutSchool()
        self.assertEqual("air", school.school_ring())

    def test_school_knacks(self):
        school = hiruma_school.HirumaScoutSchool()
        self.assertEqual(["double attack", "feint", "iaijutsu"], school.school_knacks())

    def test_free_raise_skills(self):
        school = hiruma_school.HirumaScoutSchool()
        self.assertEqual(["parry"], school.free_raise_skills())


class TestHirumaParryListener(unittest.TestCase):
    def setUp(self):
        self.hiruma = Character("Hiruma")
        self.hiruma.set_skill("attack", 4)
        self.hiruma.set_actions([1])
        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [Group("Crab", self.hiruma), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_emit_3rd_dan_modifier_on_parry_succeeded(self):
        """Spec 019 T-A2 + T-A3 (Q2 + Q3 BLOCKING fixes): the 3rd
        Dan effect emits a target-scoped Modifier with skills
        ATTACK_SKILLS + ["damage"] and target=attacker, NOT the
        previous AnyAttackFloatingBonus."""
        attack = actions.AttackAction(self.attacker, self.hiruma, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.hiruma, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(parry)
        listener = hiruma_school.HirumaParryListener()
        emitted = list(listener.handle(self.hiruma, event, self.context))
        # One AddModifierEvent emitted.
        add_mod_events = [e for e in emitted if isinstance(e, events.AddModifierEvent)]
        self.assertEqual(1, len(add_mod_events))
        modifier = add_mod_events[0].modifier
        self.assertEqual(8, modifier.adjustment())  # 2 * attack=4 = 8
        # Target-scoped to the attacker.
        self.assertEqual(self.attacker, modifier.target())
        # Skills include ATTACK_SKILLS + "damage".
        self.assertIn("attack", modifier.skills())
        self.assertIn("damage", modifier.skills())
        # Trace attribution tag.
        self.assertTrue(getattr(modifier, "_hiruma_3rd_dan", False))

    def test_no_modifier_when_attack_skill_is_zero(self):
        """If the Hiruma has 0 attack skill, bonus = 0 → no modifier.

        Coverage for the ``if bonus <= 0: return`` guard."""
        self.hiruma.set_skill("attack", 0)
        attack = actions.AttackAction(self.attacker, self.hiruma, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.hiruma, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(parry)
        listener = hiruma_school.HirumaParryListener()
        emitted = list(listener.handle(self.hiruma, event, self.context))
        add_mod_events = [e for e in emitted if isinstance(e, events.AddModifierEvent)]
        self.assertEqual(0, len(add_mod_events))

    def test_emit_3rd_dan_modifier_on_parry_failed(self):
        """3rd Dan modifier MUST fire on FAILED parries too (rules
        text — "successful or unsuccessful")."""
        attack = actions.AttackAction(self.attacker, self.hiruma, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.hiruma, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(20)
        event = events.ParryFailedEvent(parry)
        listener = hiruma_school.HirumaParryListener()
        emitted = list(listener.handle(self.hiruma, event, self.context))
        add_mod_events = [e for e in emitted if isinstance(e, events.AddModifierEvent)]
        self.assertEqual(1, len(add_mod_events))
        self.assertEqual(8, add_mod_events[0].modifier.adjustment())

    def test_3rd_dan_modifier_expires_on_damage_roll(self):
        """Trace-reader cat#10 finding (2026-05-30): the 3rd Dan
        bonus must actually EXPIRE on the next damage roll.

        Pre-fix, the engine had a broken ``RemoveModifierListener``
        (wrong isinstance check in ``listeners.py``) that silently
        ignored every ``RemoveModifierEvent`` — so the registered
        ``ExpireAfterNDamageRollsListener`` fired but the modifier
        never actually left ``character._modifiers``.  Hiruma stacks
        grew unboundedly, producing the +400 attack rolls the sweep
        flagged.  With the engine fix in place, this test guards the
        per-damage-roll expiry that the rules-as-written intended.
        """
        listener = hiruma_school.HirumaParryListener()
        # Parry → AddModifierEvent for one +2X bonus.
        attack1 = actions.AttackAction(self.attacker, self.hiruma, "attack", self.initiative_action, self.context)
        parry1 = actions.ParryAction(self.hiruma, self.attacker, "parry", self.initiative_action, self.context, attack1)
        parry1.set_skill_roll(50)
        for ev in listener.handle(self.hiruma, events.ParrySucceededEvent(parry1), self.context):
            if isinstance(ev, events.AddModifierEvent):
                self.hiruma.add_modifier(ev.modifier)
        active = [m for m in self.hiruma._modifiers if getattr(m, "_hiruma_3rd_dan", False)]
        self.assertEqual(1, len(active))
        # Simulate a damage roll firing the registered "lw_damage"
        # trigger on the modifier; the listener emits RemoveModifierEvent
        # which the (now-fixed) RemoveModifierListener processes.
        modifier = active[0]
        dmg_event = events.LightWoundsDamageEvent(self.hiruma, self.attacker, 5)
        from simulation import listeners as core_listeners
        remove_listener = core_listeners.RemoveModifierListener()
        # Modifier.handle dispatches the event to its registered
        # per-event listeners; the lw_damage expiry yields the
        # RemoveModifierEvent which the (now-fixed) core
        # RemoveModifierListener processes to remove the modifier.
        for ev in modifier.handle(self.hiruma, dmg_event, self.context):
            for _ in remove_listener.handle(self.hiruma, ev, self.context):
                pass
        active_after = [m for m in self.hiruma._modifiers if getattr(m, "_hiruma_3rd_dan", False)]
        self.assertEqual(0, len(active_after))


class TestHirumaNewRoundListener(unittest.TestCase):
    def test_subtract_2_from_action_dice(self):
        from simulation.mechanics.roll_provider import CalvinistRollProvider
        hiruma = Character("Hiruma")
        enemy = Character("enemy")
        groups = [Group("Crab", hiruma), Group("Enemy", enemy)]
        context = EngineContext(groups)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_initiative_roll([3, 5, 8])
        hiruma.set_roll_provider(roll_provider)
        listener = hiruma_school.HirumaNewRoundListener(hiruma)
        event = events.NewRoundEvent(1)
        list(listener.handle(hiruma, event, context))
        # After init roll [3,5,8] -> minus 2 with min 1 -> [1, 3, 6].
        self.assertEqual([1, 3, 6], hiruma.actions())

    def test_min_floor_on_action_dice(self):
        """When dice would go below 1 after -2, they're floored at 1."""
        from simulation.mechanics.roll_provider import CalvinistRollProvider
        hiruma = Character("Hiruma")
        enemy = Character("enemy")
        groups = [Group("Crab", hiruma), Group("Enemy", enemy)]
        context = EngineContext(groups)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_initiative_roll([1, 2, 8])
        hiruma.set_roll_provider(roll_provider)
        listener = hiruma_school.HirumaNewRoundListener(hiruma)
        event = events.NewRoundEvent(1)
        list(listener.handle(hiruma, event, context))
        # After [1, 2, 8] -> [max(1, -1), max(1, 0), 6] = [1, 1, 6].
        self.assertEqual([1, 1, 6], hiruma.actions())


class TestHirumaFifthDanParryListener(unittest.TestCase):
    def setUp(self):
        self.hiruma = Character("Hiruma")
        self.hiruma.set_skill("attack", 4)
        self.hiruma.set_actions([1])
        self.attacker = Character("attacker")
        self.attacker.set_actions([1])
        groups = [Group("Crab", self.hiruma), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_add_damage_modifier_on_parry(self):
        """Spec 019 T-A5: the 5th Dan listener subclasses
        HirumaParryListener and delegates the 3rd Dan effect via
        super(), then adds its own 5th Dan -10 damage modifier on
        the attacker.  Result: TWO AddModifierEvents — the 3rd Dan
        attack+damage bonus on the Hiruma + the 5th Dan -10 damage
        debuff on the attacker."""
        attack = actions.AttackAction(self.attacker, self.hiruma, "attack", self.initiative_action, self.context)
        parry = actions.ParryAction(self.hiruma, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(50)
        event = events.ParrySucceededEvent(parry)
        listener = hiruma_school.HirumaFifthDanParryListener()
        emitted = list(listener.handle(self.hiruma, event, self.context))
        add_mod_events = [e for e in emitted if isinstance(e, events.AddModifierEvent)]
        self.assertEqual(2, len(add_mod_events))
        # First emitted is 3rd Dan (super delegation): +8 on Hiruma
        # targeting attacker.
        third_dan = add_mod_events[0]
        self.assertEqual(self.hiruma, third_dan.subject)
        self.assertEqual(8, third_dan.modifier.adjustment())
        self.assertTrue(getattr(third_dan.modifier, "_hiruma_3rd_dan", False))
        # Second emitted is 5th Dan: -10 on attacker.
        fifth_dan = add_mod_events[1]
        self.assertEqual(self.attacker, fifth_dan.subject)
        self.assertEqual(-10, fifth_dan.modifier.adjustment())
        self.assertTrue(getattr(fifth_dan.modifier, "_hiruma_5th_dan", False))


class TestExpireAfterNDamageRollsListener(unittest.TestCase):
    def test_expire_after_2_damage_rolls(self):
        attacker = Character("attacker")
        target = Character("target")
        groups = [Group("A", attacker), Group("B", target)]
        context = EngineContext(groups)
        modifier = Modifier(attacker, None, "damage", -10)
        listener = ExpireAfterNDamageRollsListener(attacker, 2)
        modifier.register_listener("lw_damage", listener)
        attacker.add_modifier(modifier)
        # First damage roll - should not expire
        event1 = events.LightWoundsDamageEvent(attacker, target, 15)
        responses1 = list(modifier.handle(attacker, event1, context))
        self.assertEqual(0, len(responses1))
        # Second damage roll - should expire
        event2 = events.LightWoundsDamageEvent(attacker, target, 20)
        responses2 = list(modifier.handle(attacker, event2, context))
        self.assertEqual(1, len(responses2))
        self.assertTrue(isinstance(responses2[0], events.RemoveModifierEvent))

    def test_do_not_expire_for_different_attacker(self):
        attacker = Character("attacker")
        other = Character("other")
        target = Character("target")
        groups = [Group("A", [attacker, other]), Group("B", target)]
        context = EngineContext(groups)
        modifier = Modifier(attacker, None, "damage", -10)
        listener = ExpireAfterNDamageRollsListener(attacker, 2)
        modifier.register_listener("lw_damage", listener)
        attacker.add_modifier(modifier)
        # Damage from another character - should not count
        event = events.LightWoundsDamageEvent(other, target, 15)
        responses = list(modifier.handle(attacker, event, context))
        self.assertEqual(0, len(responses))
