#!/usr/bin/env python3

#
# test_coverage_gaps.py
#
# Targeted tests to cover remaining gaps in code coverage.
#

import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.listeners import (
    SeriousWoundsDamageListener,
)
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_params import DefaultRollParameterProvider
from simulation.mechanics.skills import AdvancedSkill, BasicSkill
from simulation.professions import (
    ABILITY_NAMES,
    CRIPPLED_BONUS,
    DAMAGE_PENALTY,
    WEAPON_DAMAGE_BONUS,
    WOUND_CHECK_BONUS,
    WOUND_CHECK_PENALTY,
    Profession,
    WaveManActionFactory,
    WaveManAttackAction,
    WaveManRoll,
    WaveManTakeActionEventFactory,
    get_profession_ability,
)
from simulation.strategies.base import (
    WoundCheckRolledStrategy,
)

# ================================================================
# Groups
# ================================================================


class TestGroupAdd(unittest.TestCase):
    def test_add_character(self):
        group = Group("test")
        char = Character("alice")
        group.add(char)
        self.assertIn(char, group)

    def test_add_non_character_raises(self):
        group = Group("test")
        with self.assertRaises(ValueError):
            group.add("not a character")

    def test_add_int_raises(self):
        group = Group("test")
        with self.assertRaises(ValueError):
            group.add(42)


class TestGroupClear(unittest.TestCase):
    def test_clear_removes_all(self):
        char1 = Character("a")
        char2 = Character("b")
        group = Group("test", [char1, char2])
        self.assertEqual(len(group), 2)
        group.clear()
        self.assertEqual(len(group), 0)


class TestGroupDiscard(unittest.TestCase):
    def test_discard_character(self):
        char1 = Character("a")
        char2 = Character("b")
        group = Group("test", [char1, char2])
        group.discard(char1)
        self.assertEqual(len(group), 1)
        self.assertNotIn(char1, group)
        self.assertIn(char2, group)


# ================================================================
# Listeners
# ================================================================


class TestSeriousWoundsDamageListener(unittest.TestCase):
    def setUp(self):
        self.subject = Character("attacker")
        self.target = Character("target")
        self.target.set_ring("earth", 2)
        groups = [Group("a", self.subject), Group("b", self.target)]
        self.context = EngineContext(groups)
        self.listener = SeriousWoundsDamageListener()

    def test_death_event(self):
        # max_sw = earth*2 = 4, take 5 SW to die
        event = events.SeriousWoundsDamageEvent(self.subject, self.target, 5)
        result = list(self.listener.handle(self.target, event, self.context))
        self.assertFalse(self.target.is_alive())
        death_events = [e for e in result if isinstance(e, events.DeathEvent)]
        self.assertEqual(len(death_events), 1)

    def test_unconscious_event(self):
        # max_sw = 4, take exactly 4 to go unconscious
        event = events.SeriousWoundsDamageEvent(self.subject, self.target, 4)
        result = list(self.listener.handle(self.target, event, self.context))
        self.assertTrue(self.target.is_alive())
        self.assertFalse(self.target.is_conscious())
        unconscious_events = [e for e in result if isinstance(e, events.UnconsciousEvent)]
        self.assertEqual(len(unconscious_events), 1)

    def test_observer_records_wounds(self):
        event = events.SeriousWoundsDamageEvent(self.subject, self.target, 1)
        list(self.listener.handle(self.subject, event, self.context))
        # subject's knowledge should have recorded the wound via observe_wounds
        self.assertEqual(self.subject.knowledge()._wounds.get(self.target.name(), 0), 1)


# ================================================================
# Roll Parameters - Contested Skill Bonus
# ================================================================


class TestContestedSkillBonus(unittest.TestCase):
    def test_contested_skill_bonus_applies(self):
        provider = DefaultRollParameterProvider()
        char = Character("a")
        char.set_ring("fire", 3)
        char.set_skill("iaijutsu", 5)
        target = Character("b")
        target.set_ring("fire", 3)
        target.set_skill("iaijutsu", 2)
        (rolled, kept, modifier) = provider.get_skill_roll_params(char, target, "iaijutsu", contested_skill="iaijutsu")
        # my_skill(5) > your_skill(2), bonus = 5 * (5-2) = 15
        self.assertEqual(modifier, 15)

    def test_no_contested_bonus_when_equal(self):
        provider = DefaultRollParameterProvider()
        char = Character("a")
        char.set_ring("fire", 3)
        char.set_skill("attack", 3)
        target = Character("b")
        target.set_ring("fire", 3)
        target.set_skill("attack", 3)
        (rolled, kept, modifier) = provider.get_skill_roll_params(char, target, "attack", contested_skill="attack")
        self.assertEqual(modifier, 0)

    def test_no_contested_bonus_when_lower(self):
        provider = DefaultRollParameterProvider()
        char = Character("a")
        char.set_ring("fire", 3)
        char.set_skill("attack", 2)
        target = Character("b")
        target.set_ring("fire", 3)
        target.set_skill("attack", 5)
        (rolled, kept, modifier) = provider.get_skill_roll_params(char, target, "attack", contested_skill="attack")
        # my_skill(2) < your_skill(5), no bonus
        self.assertEqual(modifier, 0)


# ================================================================
# Skills - AdvancedSkill and BasicSkill
# ================================================================


class TestAdvancedSkill(unittest.TestCase):
    def test_valid_advanced_skill(self):
        skill = AdvancedSkill("attack")
        self.assertTrue(skill.is_advanced())

    def test_invalid_advanced_skill(self):
        with self.assertRaises(ValueError):
            AdvancedSkill("etiquette")


class TestBasicSkill(unittest.TestCase):
    def test_valid_basic_skill(self):
        skill = BasicSkill("etiquette")
        self.assertFalse(skill.is_advanced())

    def test_invalid_basic_skill(self):
        with self.assertRaises(ValueError):
            BasicSkill("attack")


# ================================================================
# Professions
# ================================================================


class TestProfessionAbility(unittest.TestCase):
    def test_ability_type_validation(self):
        p = Profession()
        with self.assertRaises(ValueError):
            p.ability(123)

    def test_ability_invalid_name(self):
        p = Profession()
        with self.assertRaises(ValueError):
            p.ability("nonexistent ability")

    def test_take_ability_type_validation(self):
        p = Profession()
        with self.assertRaises(ValueError):
            p.take_ability(123)

    def test_take_ability_invalid_name(self):
        p = Profession()
        with self.assertRaises(ValueError):
            p.take_ability("nonexistent ability")

    def test_take_ability_max_rank(self):
        p = Profession()
        p.take_ability(CRIPPLED_BONUS)
        p.take_ability(CRIPPLED_BONUS)
        with self.assertRaises(RuntimeError):
            p.take_ability(CRIPPLED_BONUS)


class TestGetProfessionAbility(unittest.TestCase):
    def test_type_validation(self):
        with self.assertRaises(ValueError):
            get_profession_ability(42)

    def test_damage_penalty(self):
        ability = get_profession_ability(DAMAGE_PENALTY)
        self.assertIsNotNone(ability)

    def test_wound_check_penalty(self):
        ability = get_profession_ability(WOUND_CHECK_PENALTY)
        self.assertIsNotNone(ability)

    def test_wound_check_bonus(self):
        ability = get_profession_ability(WOUND_CHECK_BONUS)
        self.assertIsNotNone(ability)

    def test_invalid_name(self):
        with self.assertRaises(ValueError):
            get_profession_ability("nonexistent")

    def test_all_abilities_have_factory(self):
        for name in ABILITY_NAMES:
            ability = get_profession_ability(name)
            self.assertIsNotNone(ability)


class TestProfessionAbilityApply(unittest.TestCase):
    def test_damage_penalty_apply(self):
        char = Character("test")
        profession = Profession()
        ability = get_profession_ability(DAMAGE_PENALTY)
        ability.apply(char, profession)
        # should set a listener without error

    def test_weapon_damage_bonus_apply(self):
        char = Character("test")
        profession = Profession()
        ability = get_profession_ability(WEAPON_DAMAGE_BONUS)
        ability.apply(char, profession)
        # should set roll parameter provider

    def test_wound_check_penalty_apply(self):
        char = Character("test")
        profession = Profession()
        ability = get_profession_ability(WOUND_CHECK_PENALTY)
        ability.apply(char, profession)
        # should set take action event factory


class TestWaveManActionFactory(unittest.TestCase):
    def test_attack_skill_returns_wave_man_action(self):
        profession = Profession()
        factory = WaveManActionFactory(profession)
        subject = Character("a")
        subject.set_ring("fire", 3)
        subject.set_skill("attack", 3)
        target = Character("b")
        groups = [Group("a", subject), Group("b", target)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([5], 5)
        action = factory.get_attack_action(subject, target, "attack", initiative_action, context)
        self.assertIsInstance(action, WaveManAttackAction)

    def test_non_attack_skill_returns_default(self):
        profession = Profession()
        factory = WaveManActionFactory(profession)
        subject = Character("a")
        subject.set_ring("fire", 3)
        subject.set_skill("double attack", 3)
        target = Character("b")
        groups = [Group("a", subject), Group("b", target)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([5], 5)
        action = factory.get_attack_action(subject, target, "double attack", initiative_action, context)
        self.assertNotIsInstance(action, WaveManAttackAction)


class TestWaveManRollValidation(unittest.TestCase):
    def test_always_explode_not_int(self):
        with self.assertRaises(ValueError):
            WaveManRoll(5, 3, always_explode="bad")

    def test_always_explode_too_high(self):
        with self.assertRaises(ValueError):
            WaveManRoll(5, 3, always_explode=3)

    def test_valid_always_explode(self):
        roll = WaveManRoll(5, 3, always_explode=2)
        self.assertEqual(roll.always_explode, 2)


class TestWaveManRollParameterProviderValidation(unittest.TestCase):
    def test_invalid_profession(self):
        with self.assertRaises(ValueError):
            from simulation.professions import WaveManRollProvider

            WaveManRollProvider("not a profession")


class TestWaveManTakeActionEventFactory(unittest.TestCase):
    def test_attack_action(self):
        from simulation.actions import AttackAction

        factory = WaveManTakeActionEventFactory()
        subject = Character("a")
        subject.set_ring("fire", 3)
        subject.set_skill("attack", 3)
        target = Character("b")
        groups = [Group("a", subject), Group("b", target)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([5], 5)
        action = AttackAction(subject, target, "attack", initiative_action, context)
        event = factory.get_take_attack_action_event(action)
        self.assertIsNotNone(event)

    def test_non_attack_action_raises(self):
        factory = WaveManTakeActionEventFactory()
        with self.assertRaises(ValueError):
            factory.get_take_attack_action_event("not an action")


# ================================================================
# Strategies
# ================================================================


class TestWoundCheckRolledStrategyBonusBreak(unittest.TestCase):
    def test_use_floating_bonuses_breaks_when_tolerable(self):
        strategy = WoundCheckRolledStrategy()
        char = Character("char")
        char.set_ring("earth", 3)
        # add floating bonuses
        from simulation.mechanics.floating_bonuses import FloatingBonus

        char.gain_floating_bonus(FloatingBonus("wound check", 100))
        event = events.WoundCheckRolledEvent(char, None, 10, 5, tn=10)
        # tolerable_sw = 1, wound_check with roll=5 would give some SW
        # after applying bonus of 100 it should break early
        new_event = strategy.use_floating_bonuses(char, event, 1, "wound check")
        # verify it returns a new event with improved roll
        self.assertGreater(new_event.roll, event.roll)
