#!/usr/bin/env python3

#
# test_shiba_school.py
#
# Unit tests for Shiba Bushi School classes.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import shiba_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestShibaBushiSchoolBasics(unittest.TestCase):
    """Spec 016 T-E1 — coverage padding for the school's trivial
    accessors."""

    def test_name(self) -> None:
        school = shiba_school.ShibaBushiSchool()
        self.assertEqual("Shiba Bushi School", school.name())

    def test_ap_base_skill(self) -> None:
        """``ap_base_skill`` returns None for Shiba (no AP base skill)."""
        school = shiba_school.ShibaBushiSchool()
        self.assertIsNone(school.ap_base_skill())

    def test_school_knacks(self) -> None:
        school = shiba_school.ShibaBushiSchool()
        self.assertEqual(["counterattack", "double attack", "iaijutsu"], school.school_knacks())

    def test_school_ring(self) -> None:
        school = shiba_school.ShibaBushiSchool()
        self.assertEqual("air", school.school_ring())

    def test_extra_rolled(self) -> None:
        school = shiba_school.ShibaBushiSchool()
        self.assertEqual(["double attack", "parry", "wound check"], school.extra_rolled())

    def test_free_raise_skills(self) -> None:
        school = shiba_school.ShibaBushiSchool()
        self.assertEqual(["parry"], school.free_raise_skills())


class TestShibaTakeActionEventFactoryRejects(unittest.TestCase):
    """Spec 016 T-E1 — coverage for the non-ParryAction guard in
    ``ShibaTakeActionEventFactory.get_take_parry_action_event``."""

    def test_rejects_non_parry_action(self) -> None:
        from simulation.actions import AttackAction
        from simulation.mechanics.initiative_actions import InitiativeAction
        attacker = Character("Attacker")
        target = Character("Target")
        ia = InitiativeAction([1], 1)
        ctx = EngineContext([Group("A", attacker), Group("T", target)])
        attack = AttackAction(attacker, target, "attack", ia, ctx)
        factory = shiba_school.ShibaTakeActionEventFactory()
        with self.assertRaises(ValueError):
            factory.get_take_parry_action_event(attack)


class TestShibaActionFactory(unittest.TestCase):
    def test_get_parry(self):
        shiba = Character("Shiba")
        shiba.set_actions([1])
        attacker = Character("attacker")
        attacker.set_actions([1])
        initiative_action = InitiativeAction([1], 1)
        factory = shiba_school.ShibaActionFactory()
        context = EngineContext([Group("Phoenix", shiba), Group("Attacker", attacker)])
        attack = actions.AttackAction(attacker, shiba, "attack", initiative_action, context)
        parry = factory.get_parry_action(shiba, attacker, attack, "parry", initiative_action, context)
        self.assertTrue(isinstance(parry, shiba_school.ShibaParryAction))
        self.assertEqual(shiba, parry.subject())
        self.assertEqual(attacker, parry.target())


class TestShibaParryAction(unittest.TestCase):
    def test_no_parry_other_penalty(self):
        """rules/04-schools.md Shiba Special Ability: parry-other has
        no penalty. Calls the SAME method the engine calls
        (``roll_skill``, not the non-existent ``roll_parry``) so the
        test exercises the production code path.  Spec 016 T-A1 fix.
        """
        shiba = Character("Shiba")
        shiba.set_actions([1])
        attacker = Character("attacker")
        attacker.set_actions([1])
        attacker.set_skill("attack", 4)
        initiative_action = InitiativeAction([1], 1)
        target = Character("target")
        context = EngineContext([Group("Phoenix", shiba), Group("Target", target)])
        attack = actions.AttackAction(attacker, target, "attack", initiative_action, context)
        parry = shiba_school.ShibaParryAction(shiba, attacker, "parry", initiative_action, context, attack)
        # rig shiba's parry roll
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("parry", 50)
        shiba.set_roll_provider(roll_provider)
        # Engine calls roll_skill (NOT roll_parry).  Without the Shiba
        # override on the right method, the base ParryAction.roll_skill
        # would apply a `5 * attacker.skill("attack")` = 20 penalty.
        # The override must skip that penalty.
        skill_roll = parry.roll_skill()
        self.assertEqual(skill_roll, 50)


class TestShibaParrySucceededListener(unittest.TestCase):
    def setUp(self):
        # set up characters
        shiba = Character("Shiba")
        shiba.set_actions([1])
        shiba.set_skill("attack", 4)
        shiba.set_skill("parry", 5)
        attacker = Character("attacker")
        attacker.set_actions([1])
        attacker.set_skill("parry", 5)
        # set up context
        groups = [Group("Shiba", shiba), Group("attacker", attacker)]
        context = EngineContext(groups)
        # set instances on test case
        self.attacker = attacker
        self.shiba = shiba
        self.context = context
        self.initiative_action = InitiativeAction([1], 1)

    def test_handle_parry_succeeded(self):
        # set up attack action
        attack = actions.AttackAction(self.attacker, self.shiba, "attack", self.initiative_action, self.context)
        attack.set_skill_roll(45)
        # set up parry action
        parry = shiba_school.ShibaParryAction(self.shiba, self.attacker, "parry", self.initiative_action, self.context, attack)
        parry.set_skill_roll(51)
        # set up parry succeeded event
        event = events.ParrySucceededEvent(parry)
        # play parry succeeded event on listener
        listener = shiba_school.ShibaParrySucceededListener()
        responses = list([response for response in listener.handle(self.shiba, event, self.context)])
        # 2026-05-30 cat#10 fix: now emits 1 AddModifierEvent +
        # 1 ShibaFifthDanTnReductionEvent (the discrete trace event).
        self.assertEqual(2, len(responses))
        add_event = responses[0]
        self.assertTrue(isinstance(add_event, events.AddModifierEvent))
        # should add a penalty to self.attacker's TN to be hit
        modifier = add_event.modifier
        self.assertEqual(self.attacker, modifier.subject())
        self.assertEqual(-6, modifier.adjustment())
        # discrete trace event carries the school identity
        tn_reduction = responses[1]
        self.assertTrue(isinstance(tn_reduction, events.ShibaFifthDanTnReductionEvent))
        self.assertEqual(self.shiba, tn_reduction.subject)
        self.assertEqual(self.attacker, tn_reduction.target)
        self.assertEqual(6, tn_reduction.margin)

    def test_run_parry_engine(self):
        # build Shiba as a 5th Dan character
        school = shiba_school.ShibaBushiSchool()
        builder = CharacterBuilder(9001).with_name("Shiba").with_school(school).buy_skill("attack", 4).buy_skill("parry", 5)
        for skill in school.school_knacks():
            builder.buy_skill(skill, 5)
        self.shiba = builder.build()
        groups = [Group("Shiba", self.shiba), Group("attacker", self.attacker)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()
        # set up attack
        attack = actions.AttackAction(self.attacker, self.shiba, "attack", self.initiative_action, self.context)
        attack.set_skill_roll(45)
        # set up parry
        parry = shiba_school.ShibaParryAction(self.shiba, self.attacker, "parry", self.initiative_action, self.context, attack)
        take_action_event = shiba_school.ShibaTakeParryEvent(parry)
        # rig parry and damage rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("parry", 51)
        roll_provider.put_damage_roll(9)
        self.shiba.set_roll_provider(roll_provider)
        # set up engine
        engine = CombatEngine(self.context)
        # play parry event
        engine.event(take_action_event)
        # assert expected parry state
        self.assertTrue(parry.is_success())
        self.assertEqual(56, parry.skill_roll())
        # assert expected attack state
        self.assertFalse(attack.is_hit())
        self.assertTrue(attack.parry_attempted())
        self.assertTrue(attack.parried())
        # assert expected damage roll parameters
        self.assertEqual((8, 1), roll_provider.pop_observed_params("damage"))
        # assert attacker has expected modifier to tn to be hit
        self.assertEqual(-11, self.attacker.modifier(None, "tn to hit"))
        self.assertEqual(19, self.attacker.tn_to_hit())
        # assert expected event history
        history = engine.history()
        # take_parry
        first_event = history.pop(0)
        self.assertTrue(isinstance(first_event, shiba_school.ShibaTakeParryEvent))
        # parry_declared
        second_event = history.pop(0)
        self.assertTrue(isinstance(second_event, events.ParryDeclaredEvent))
        # parry_rolled
        third_event = history.pop(0)
        self.assertTrue(isinstance(third_event, events.ParryRolledEvent))
        # parry_succeeded
        fourth_event = history.pop(0)
        self.assertTrue(isinstance(fourth_event, events.ParrySucceededEvent))
        # add_modifier
        fifth_event = history.pop(0)
        self.assertTrue(isinstance(fifth_event, events.AddModifierEvent))
        # shiba_5th_dan_tn_reduction (discrete trace event, 2026-05-30)
        sixth_event = history.pop(0)
        self.assertTrue(isinstance(sixth_event, events.ShibaFifthDanTnReductionEvent))
        # lw_damage
        seventh_event = history.pop(0)
        self.assertTrue(isinstance(seventh_event, events.LightWoundsDamageEvent))


class TestShibaTakeParryEvent(unittest.TestCase):
    def setUp(self):
        # characters
        shiba = Character("Shiba")
        shiba.set_skill("attack", 3)
        attacker = Character("attacker")
        # initiative action
        initiative_action = InitiativeAction([1], 1)
        # groups and context
        groups = [Group("Phoenix", shiba), Group("attacker", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        # attack
        attack = actions.AttackAction(attacker, shiba, "attack", initiative_action, context)
        attack.set_skill_roll(50)
        # parry
        parry = shiba_school.ShibaParryAction(shiba, attacker, "parry", initiative_action, context, attack)
        take_action_event = shiba_school.ShibaTakeParryEvent(parry)
        # instances
        self.shiba = shiba
        self.attacker = attacker
        self.attack = attack
        self.context = context
        self.parry = parry
        self.take_action_event = take_action_event

    def test_damage_high_attack_normalized_rolled(self):
        """rules-fidelity: when 2 × attack > 10, the rolled count MUST
        be normalized via normalize_roll_params (rolled > 10 converts
        excess to kept).  Spec 016 T-A2 fix for Q3 BLOCKING."""
        # set Shiba's attack to 6 → raw rolled = 12 → normalizes to 10k3.
        self.shiba.set_skill("attack", 6)
        engine = CombatEngine(self.context)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("parry", 44)
        roll_provider.put_damage_roll(15)
        self.shiba.set_roll_provider(roll_provider)
        engine.event(self.take_action_event)
        observed_damage_params = roll_provider.pop_observed_params("damage")
        # Pre-fix bug: would have been (12, 1).  Post-fix: 10k(1+2)=10k3.
        self.assertEqual((10, 3), observed_damage_params)

    def test_damage_parry_failed(self):
        # set up engine
        engine = CombatEngine(self.context)
        # rig shiba's rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("parry", 44)
        roll_provider.put_damage_roll(10)
        self.shiba.set_roll_provider(roll_provider)
        # play parry action
        engine.event(self.take_action_event)
        # assert expected parry action state
        self.assertEqual(44, self.parry.skill_roll())
        self.assertFalse(self.parry.is_success())
        # assert expected attack action state
        self.assertTrue(self.attack.is_hit())
        self.assertFalse(self.attack.parried())
        self.assertTrue(self.attack.parry_attempted())
        # assert expected damage roll params
        observed_damage_params = roll_provider.pop_observed_params("damage")
        self.assertEqual((6, 1), observed_damage_params)
        # assert expected event history
        history = engine.history()
        # take_parry
        first_event = history.pop(0)
        self.assertTrue(isinstance(first_event, shiba_school.ShibaTakeParryEvent))
        # parry_declared
        second_event = history.pop(0)
        self.assertTrue(isinstance(second_event, events.ParryDeclaredEvent))
        # parry_rolled
        third_event = history.pop(0)
        self.assertTrue(isinstance(third_event, events.ParryRolledEvent))
        self.assertEqual(44, third_event.roll)
        # parry_failed
        fourth_event = history.pop(0)
        self.assertTrue(isinstance(fourth_event, events.ParryFailedEvent))
        # lw_damage
        fifth_event = history.pop(0)
        self.assertTrue(isinstance(fifth_event, events.LightWoundsDamageEvent))
        self.assertEqual(self.shiba, fifth_event.subject)
        self.assertEqual(self.attacker, fifth_event.target)
        self.assertEqual(10, fifth_event.damage)

    def test_damage_parry_succeeded(self):
        # set up engine
        engine = CombatEngine(self.context)
        # rig shiba's rolls
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("parry", 51)
        roll_provider.put_damage_roll(10)
        self.shiba.set_roll_provider(roll_provider)
        # play parry action
        engine.event(self.take_action_event)
        # assert expected parry action state
        self.assertEqual(51, self.parry.skill_roll())
        self.assertTrue(self.parry.is_success())
        # assert expected attack action state
        self.assertFalse(self.attack.is_hit())
        self.assertTrue(self.attack.parried())
        self.assertTrue(self.attack.parry_attempted())
        # assert expected damage roll params
        observed_damage_params = roll_provider.pop_observed_params("damage")
        self.assertEqual((6, 1), observed_damage_params)
        # assert expected event history
        history = engine.history()
        # take_parry
        first_event = history.pop(0)
        self.assertTrue(isinstance(first_event, shiba_school.ShibaTakeParryEvent))
        # parry_declared
        second_event = history.pop(0)
        self.assertTrue(isinstance(second_event, events.ParryDeclaredEvent))
        # parry_rolled
        third_event = history.pop(0)
        self.assertTrue(isinstance(third_event, events.ParryRolledEvent))
        self.assertEqual(51, third_event.roll)
        # parry_succeeded
        fourth_event = history.pop(0)
        self.assertTrue(isinstance(fourth_event, events.ParrySucceededEvent))
        # lw_damage
        fifth_event = history.pop(0)
        self.assertTrue(isinstance(fifth_event, events.LightWoundsDamageEvent))
        self.assertEqual(self.shiba, fifth_event.subject)
        self.assertEqual(self.attacker, fifth_event.target)
        self.assertEqual(10, fifth_event.damage)
