#!/usr/bin/env python3

#
# test_coverage_simple.py
#
# Unit tests to improve code coverage for the L7R combat simulation project.
#

import io
import unittest

from simulation.actions import (
    AttackAction,
    CounterattackAction,
    DoubleAttackAction,
    FeintAction,
    LungeAction,
    ParryAction,
)
from simulation.character import Character
from simulation.context import EngineContext
from simulation.events import TakeAttackActionEvent, TakeParryActionEvent
from simulation.groups import Group
from simulation.groups_file import GroupsReader
from simulation.mechanics.floating_bonuses import FloatingBonus
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.modifiers import FreeRaise, Modifier
from simulation.mechanics.void_point_manager import VoidPointManager
from simulation.optimizers.attack_optimizer_factory import DefaultAttackOptimizerFactory
from simulation.optimizers.attack_optimizers import AttackOptimizer, DamageOptimizer
from simulation.schools.akodo_school import AkodoBushiSchool
from simulation.schools.bayushi_school import BayushiBushiSchool
from simulation.schools.factory import get_school
from simulation.schools.kakita_school import KakitaBushiSchool
from simulation.schools.shiba_school import ShibaBushiSchool
from simulation.strategies.action_factory import DefaultActionFactory
from simulation.strategies.base import (
    AlwaysAttackActionStrategy,
    AlwaysKeepLightWoundsStrategy,
    AlwaysParryStrategy,
    HoldOneActionStrategy,
    KeepLightWoundsStrategy,
    NeverKeepLightWoundsStrategy,
    NeverParryStrategy,
    PlainAttackStrategy,
    ReluctantParryStrategy,
    StingyPlainAttackStrategy,
    StingyWoundCheckStrategy,
    UniversalAttackStrategy,
    WoundCheckStrategy,
)
from simulation.strategies.factory import get_strategy
from simulation.strategies.take_action_event_factory import DefaultTakeActionEventFactory
from simulation.strategies.target_finders import TargetFinder


# ---------------------------------------------------------------------------
# 1. simulation/groups.py
# ---------------------------------------------------------------------------

class TestGroupNameValidation(unittest.TestCase):
    def test_name_must_be_str(self):
        with self.assertRaises(ValueError):
            Group(123)

    def test_name_valid_str(self):
        group = Group("Samurai")
        self.assertEqual("Samurai", group.name())

    def test_characters_not_list_not_character(self):
        with self.assertRaises(ValueError):
            Group("Bad", 42)

    def test_characters_list_with_non_character(self):
        with self.assertRaises(ValueError):
            Group("Bad", ["not a character"])

    def test_single_character_argument(self):
        c = Character("Solo")
        group = Group("Lone", c)
        self.assertEqual(1, len(group))
        self.assertIn(c, group)


class TestGroupFriendsNearDefeat(unittest.TestCase):
    def setUp(self):
        self.healthy = Character("Healthy")
        self.healthy.set_ring("earth", 3)
        # max_sw = 6, sw_remaining starts at 6

        self.wounded = Character("Wounded")
        self.wounded.set_ring("earth", 2)
        # max_sw = 4
        self.wounded.take_sw(3)
        # sw_remaining = 1 (< 2), still conscious (sw < max_sw)

        self.dead = Character("Dead")
        self.dead.set_ring("earth", 2)
        # max_sw = 4
        self.dead.take_sw(4)
        # sw_remaining = 0, unconscious, not fighting

        self.dummy = Character("Dummy")
        groups = [
            Group("Team", [self.healthy, self.wounded, self.dead]),
            Group("Other", self.dummy),
        ]
        self.context = EngineContext(groups)

    def test_friends_near_defeat(self):
        group = self.healthy.group()
        near_defeat = group.friends_near_defeat(self.context)
        # wounded has sw_remaining < 2 and is fighting
        self.assertIn(self.wounded, near_defeat)
        # healthy has sw_remaining >= 2
        self.assertNotIn(self.healthy, near_defeat)
        # dead is not fighting
        self.assertNotIn(self.dead, near_defeat)


class TestGroupFriendsWithActions(unittest.TestCase):
    def setUp(self):
        self.with_action = Character("WithAction")
        self.with_action.set_actions([3])

        self.without_action = Character("WithoutAction")
        # no actions

        self.dead_char = Character("DeadChar")
        self.dead_char.set_ring("earth", 2)
        self.dead_char.take_sw(4)
        self.dead_char.set_actions([3])

        self.dummy = Character("Dummy")
        groups = [
            Group("Team", [self.with_action, self.without_action, self.dead_char]),
            Group("Other", self.dummy),
        ]
        self.context = EngineContext(groups)
        self.context._phase = 3

    def test_friends_with_actions(self):
        group = self.with_action.group()
        friends = group.friends_with_actions(self.context)
        self.assertIn(self.with_action, friends)
        self.assertNotIn(self.without_action, friends)
        self.assertNotIn(self.dead_char, friends)


class TestGroupContains(unittest.TestCase):
    def test_contains_character(self):
        c = Character("A")
        group = Group("G", c)
        self.assertIn(c, group)

    def test_contains_string(self):
        c = Character("A")
        group = Group("G", c)
        self.assertIn("A", group)
        self.assertNotIn("B", group)

    def test_contains_invalid_type(self):
        c = Character("A")
        group = Group("G", c)
        with self.assertRaises(NotImplementedError):
            123 in group


class TestGroupEq(unittest.TestCase):
    def test_eq_self(self):
        group = Group("G", Character("A"))
        self.assertEqual(group, group)

    def test_eq_not_group(self):
        group = Group("G", Character("A"))
        self.assertNotEqual(group, "not a group")

    def test_eq_different_characters(self):
        g1 = Group("G1", Character("A"))
        g2 = Group("G2", Character("B"))
        self.assertNotEqual(g1, g2)


class TestGroupIter(unittest.TestCase):
    def test_iter(self):
        c1 = Character("A")
        c2 = Character("B")
        group = Group("G", [c1, c2])
        members = list(group)
        self.assertIn(c1, members)
        self.assertIn(c2, members)
        self.assertEqual(2, len(members))


# ---------------------------------------------------------------------------
# 2. simulation/groups_file.py
# ---------------------------------------------------------------------------

class TestGroupsReader(unittest.TestCase):
    def test_read_valid_yaml(self):
        yaml_content = """east:
  control: true
  characters:
  - akodo
  - doji
west:
  test: true
  characters:
  - bayushi
  - hida
"""
        akodo = Character("akodo")
        doji = Character("doji")
        bayushi = Character("bayushi")
        hida = Character("hida")
        characterd = {
            "akodo": akodo,
            "doji": doji,
            "bayushi": bayushi,
            "hida": hida,
        }
        reader = GroupsReader()
        groups = reader.read(io.StringIO(yaml_content), characterd)
        self.assertEqual(2, len(groups))
        # control group should be first
        self.assertEqual("east", groups[0].name())
        self.assertEqual("west", groups[1].name())
        self.assertIn(akodo, groups[0])
        self.assertIn(doji, groups[0])
        self.assertIn(bayushi, groups[1])
        self.assertIn(hida, groups[1])

    def test_missing_characters_key(self):
        yaml_content = """east:
  control: true
west:
  test: true
  characters:
  - bayushi
"""
        reader = GroupsReader()
        with self.assertRaises(OSError):
            reader.read(io.StringIO(yaml_content), {})

    def test_duplicate_control_and_test(self):
        yaml_content = """east:
  control: true
  test: true
  characters:
  - akodo
west:
  characters:
  - bayushi
"""
        akodo = Character("akodo")
        bayushi = Character("bayushi")
        characterd = {"akodo": akodo, "bayushi": bayushi}
        reader = GroupsReader()
        with self.assertRaises(OSError):
            reader.read(io.StringIO(yaml_content), characterd)

    def test_missing_character_definition(self):
        yaml_content = """east:
  control: true
  characters:
  - akodo
west:
  test: true
  characters:
  - bayushi
"""
        akodo = Character("akodo")
        characterd = {"akodo": akodo}
        reader = GroupsReader()
        with self.assertRaises(OSError):
            reader.read(io.StringIO(yaml_content), characterd)

    def test_missing_control_group(self):
        """When no control group is designated, the sort should still work
        (control_group remains None)."""
        yaml_content = """east:
  test: true
  characters:
  - akodo
west:
  test: true
  characters:
  - bayushi
"""
        akodo = Character("akodo")
        bayushi = Character("bayushi")
        characterd = {"akodo": akodo, "bayushi": bayushi}
        reader = GroupsReader()
        groups = reader.read(io.StringIO(yaml_content), characterd)
        self.assertEqual(2, len(groups))


# ---------------------------------------------------------------------------
# 3. simulation/schools/factory.py
# ---------------------------------------------------------------------------

class TestSchoolFactory(unittest.TestCase):
    def test_akodo_school(self):
        school = get_school("Akodo Bushi School")
        self.assertIsInstance(school, AkodoBushiSchool)

    def test_bayushi_school(self):
        school = get_school("Bayushi Bushi School")
        self.assertIsInstance(school, BayushiBushiSchool)

    def test_kakita_school(self):
        school = get_school("Kakita Bushi School")
        self.assertIsInstance(school, KakitaBushiSchool)

    def test_shiba_school(self):
        school = get_school("Shiba Bushi School")
        self.assertIsInstance(school, ShibaBushiSchool)

    def test_invalid_school_name(self):
        with self.assertRaises(ValueError):
            get_school("Nonexistent School")

    def test_non_str_name(self):
        with self.assertRaises(ValueError):
            get_school(42)


# ---------------------------------------------------------------------------
# 4. simulation/strategies/factory.py
# ---------------------------------------------------------------------------

class TestStrategyFactory(unittest.TestCase):
    def test_always_attack(self):
        self.assertIsInstance(get_strategy("AlwaysAttackActionStrategy"), AlwaysAttackActionStrategy)

    def test_always_keep_light_wounds(self):
        self.assertIsInstance(get_strategy("AlwaysKeepLightWoundsStrategy"), AlwaysKeepLightWoundsStrategy)

    def test_always_parry(self):
        self.assertIsInstance(get_strategy("AlwaysParryStrategy"), AlwaysParryStrategy)

    def test_hold_one_action(self):
        self.assertIsInstance(get_strategy("HoldOneActionStrategy"), HoldOneActionStrategy)

    def test_keep_light_wounds(self):
        self.assertIsInstance(get_strategy("KeepLightWoundsStrategy"), KeepLightWoundsStrategy)

    def test_never_keep_light_wounds(self):
        self.assertIsInstance(get_strategy("NeverKeepLightWoundsStrategy"), NeverKeepLightWoundsStrategy)

    def test_never_parry(self):
        self.assertIsInstance(get_strategy("NeverParryStrategy"), NeverParryStrategy)

    def test_plain_attack(self):
        self.assertIsInstance(get_strategy("PlainAttackStrategy"), PlainAttackStrategy)

    def test_reluctant_parry(self):
        self.assertIsInstance(get_strategy("ReluctantParryStrategy"), ReluctantParryStrategy)

    def test_stingy_plain_attack(self):
        self.assertIsInstance(get_strategy("StingyPlainAttackStrategy"), StingyPlainAttackStrategy)

    def test_stingy_wound_check(self):
        self.assertIsInstance(get_strategy("StingyWoundCheckStrategy"), StingyWoundCheckStrategy)

    def test_universal_attack(self):
        self.assertIsInstance(get_strategy("UniversalAttackStrategy"), UniversalAttackStrategy)

    def test_wound_check(self):
        self.assertIsInstance(get_strategy("WoundCheckStrategy"), WoundCheckStrategy)

    def test_invalid_strategy(self):
        with self.assertRaises(ValueError):
            get_strategy("DoesNotExist")


# ---------------------------------------------------------------------------
# 5. simulation/mechanics/floating_bonuses.py
# ---------------------------------------------------------------------------

class TestFloatingBonusValidation(unittest.TestCase):
    def test_skills_not_str_or_list(self):
        with self.assertRaises(ValueError):
            FloatingBonus(42, 5)

    def test_skills_list_with_non_str(self):
        with self.assertRaises(ValueError):
            FloatingBonus([42], 5)

    def test_skills_single_str(self):
        fb = FloatingBonus("attack", 3)
        self.assertTrue(fb.is_applicable("attack"))
        self.assertFalse(fb.is_applicable("parry"))

    def test_skills_list_of_str(self):
        fb = FloatingBonus(["attack", "parry"], 3)
        self.assertTrue(fb.is_applicable("attack"))
        self.assertTrue(fb.is_applicable("parry"))
        self.assertFalse(fb.is_applicable("wound check"))


class TestFloatingBonusComparison(unittest.TestCase):
    def test_lt(self):
        small = FloatingBonus("attack", 3)
        large = FloatingBonus("attack", 7)
        self.assertTrue(small < large)
        self.assertFalse(large < small)

    def test_lt_self(self):
        fb = FloatingBonus("attack", 3)
        self.assertFalse(fb < fb)

    def test_lt_not_floating_bonus(self):
        fb = FloatingBonus("attack", 3)
        with self.assertRaises(NotImplementedError):
            fb < 5

    def test_eq(self):
        fb1 = FloatingBonus("attack", 5)
        fb2 = FloatingBonus("attack", 5)
        self.assertEqual(fb1, fb2)

    def test_eq_different_bonus(self):
        fb1 = FloatingBonus("attack", 5)
        fb2 = FloatingBonus("attack", 3)
        self.assertNotEqual(fb1, fb2)

    def test_eq_not_floating_bonus(self):
        fb = FloatingBonus("attack", 5)
        self.assertNotEqual(fb, "not a bonus")

    def test_eq_self(self):
        fb = FloatingBonus("attack", 5)
        self.assertEqual(fb, fb)


# ---------------------------------------------------------------------------
# 6. simulation/mechanics/initiative_actions.py
# ---------------------------------------------------------------------------

class TestInitiativeAction(unittest.TestCase):
    def test_dice_getter(self):
        action = InitiativeAction([3, 7], 3)
        self.assertEqual([3, 7], action.dice())

    def test_phase_getter(self):
        action = InitiativeAction([5], 5)
        self.assertEqual(5, action.phase())

    def test_is_interrupt_default(self):
        action = InitiativeAction([4], 4)
        self.assertFalse(action.is_interrupt())

    def test_is_interrupt_true(self):
        action = InitiativeAction([4], 4, is_interrupt=True)
        self.assertTrue(action.is_interrupt())

    def test_dice_must_be_list(self):
        with self.assertRaises(ValueError):
            InitiativeAction(5, 5)

    def test_dice_must_be_list_of_ints(self):
        with self.assertRaises(ValueError):
            InitiativeAction(["a"], 5)

    def test_phase_must_be_int(self):
        with self.assertRaises(ValueError):
            InitiativeAction([5], "5")

    def test_is_interrupt_must_be_bool(self):
        with self.assertRaises(ValueError):
            InitiativeAction([5], 5, is_interrupt="yes")


# ---------------------------------------------------------------------------
# 7. simulation/mechanics/void_point_manager.py
# ---------------------------------------------------------------------------

class TestVoidPointManagerCoverage(unittest.TestCase):
    def setUp(self):
        character = Character("TestChar")
        character.set_ring("air", 3)
        character.set_ring("earth", 3)
        character.set_ring("fire", 3)
        character.set_ring("water", 3)
        character.set_ring("void", 3)
        self.character = character
        self.assertEqual(3, self.character.vp())

    def test_cancel_removes_reservation(self):
        manager = VoidPointManager(self.character)
        manager.reserve("attack", 2)
        self.assertEqual(2, manager.reserved("attack"))
        manager.cancel("attack")
        self.assertEqual(0, manager.reserved("attack"))

    def test_cancel_invalid_skill_type(self):
        manager = VoidPointManager(self.character)
        with self.assertRaises(ValueError):
            manager.cancel(42)

    def test_cancel_invalid_skill_name(self):
        manager = VoidPointManager(self.character)
        with self.assertRaises(ValueError):
            manager.cancel("nonexistent_skill")

    def test_reserve_and_reserved(self):
        manager = VoidPointManager(self.character)
        manager.reserve("wound check", 2)
        self.assertEqual(2, manager.reserved("wound check"))
        # overwrite reservation
        manager.reserve("wound check", 1)
        self.assertEqual(1, manager.reserved("wound check"))

    def test_reserve_invalid_skill_type(self):
        manager = VoidPointManager(self.character)
        with self.assertRaises(ValueError):
            manager.reserve(42, 1)

    def test_reserve_invalid_skill_name(self):
        manager = VoidPointManager(self.character)
        with self.assertRaises(ValueError):
            manager.reserve("nonexistent_skill", 1)

    def test_reserve_invalid_vp_type(self):
        manager = VoidPointManager(self.character)
        with self.assertRaises(ValueError):
            manager.reserve("attack", "one")

    def test_reserved_invalid_skill_type(self):
        manager = VoidPointManager(self.character)
        with self.assertRaises(ValueError):
            manager.reserved(42)

    def test_reserved_invalid_skill_name(self):
        manager = VoidPointManager(self.character)
        with self.assertRaises(ValueError):
            manager.reserved("nonexistent_skill")

    def test_reserved_default_zero(self):
        manager = VoidPointManager(self.character)
        self.assertEqual(0, manager.reserved("attack"))

    def test_vp_for_different_skills(self):
        manager = VoidPointManager(self.character)
        # no reservations: full vp available for any skill
        self.assertEqual(3, manager.vp("attack"))
        self.assertEqual(3, manager.vp("wound check"))
        # reserve 2 for wound check
        manager.reserve("wound check", 2)
        # attack should have 3 - 2 = 1
        self.assertEqual(1, manager.vp("attack"))
        # wound check should have full 3 (its own reservation doesn't subtract)
        self.assertEqual(3, manager.vp("wound check"))

    def test_vp_invalid_skill_type(self):
        manager = VoidPointManager(self.character)
        with self.assertRaises(ValueError):
            manager.vp(42)

    def test_vp_invalid_skill_name(self):
        manager = VoidPointManager(self.character)
        with self.assertRaises(ValueError):
            manager.vp("nonexistent_skill")

    def test_vp_clamps_to_zero(self):
        manager = VoidPointManager(self.character)
        # reserve more than available
        manager.reserve("wound check", 10)
        # vp for attack should clamp to 0
        self.assertEqual(0, manager.vp("attack"))

    def test_reset_clears_reservations(self):
        manager = VoidPointManager(self.character)
        manager.reserve("attack", 1)
        manager.reserve("wound check", 2)
        manager.clear()
        self.assertEqual(0, manager.reserved("attack"))
        self.assertEqual(0, manager.reserved("wound check"))
        self.assertEqual(3, manager.vp("attack"))


# ---------------------------------------------------------------------------
# 8. simulation/mechanics/modifiers.py
# ---------------------------------------------------------------------------

class TestModifierSkillsValidation(unittest.TestCase):
    def test_skills_single_str(self):
        subject = Character("Subject")
        modifier = Modifier(subject, None, "attack", 5)
        self.assertEqual(["attack"], modifier.skills())

    def test_skills_list_of_str(self):
        subject = Character("Subject")
        modifier = Modifier(subject, None, ["attack", "parry"], 5)
        self.assertEqual(["attack", "parry"], modifier.skills())

    def test_skills_list_with_non_str(self):
        subject = Character("Subject")
        with self.assertRaises(ValueError):
            Modifier(subject, None, [42], 5)

    def test_skills_invalid_type(self):
        subject = Character("Subject")
        with self.assertRaises(ValueError):
            Modifier(subject, None, 42, 5)


class TestModifierRegisterListener(unittest.TestCase):
    def test_register_listener_invalid_event_name(self):
        subject = Character("Subject")
        modifier = Modifier(subject, None, "attack", 5)
        with self.assertRaises(ValueError):
            modifier.register_listener(42, None)

    def test_register_listener_valid(self):
        subject = Character("Subject")
        modifier = Modifier(subject, None, "attack", 5)
        # Just verify it doesn't raise
        modifier.register_listener("attack_succeeded", object())


class TestFreeRaiseApply(unittest.TestCase):
    def test_apply_correct_skill(self):
        subject = Character("Subject")
        fr = FreeRaise(subject, "attack")
        self.assertEqual(5, fr.apply(None, "attack"))

    def test_apply_wrong_skill(self):
        subject = Character("Subject")
        fr = FreeRaise(subject, "attack")
        self.assertEqual(0, fr.apply(None, "parry"))

    def test_register_listener_does_nothing(self):
        subject = Character("Subject")
        fr = FreeRaise(subject, "attack")
        # FreeRaise.register_listener is a no-op
        fr.register_listener("attack_succeeded", object())
        # No error should occur and no listener should be stored


class TestModifierEq(unittest.TestCase):
    def test_eq_self(self):
        subject = Character("Subject")
        m = Modifier(subject, None, "attack", 5)
        self.assertEqual(m, m)

    def test_eq_not_modifier(self):
        subject = Character("Subject")
        m = Modifier(subject, None, "attack", 5)
        self.assertNotEqual(m, "not a modifier")

    def test_eq_different_modifiers(self):
        subject = Character("Subject")
        m1 = Modifier(subject, None, "attack", 5)
        m2 = Modifier(subject, None, "attack", 5)
        # different UUIDs
        self.assertNotEqual(m1, m2)


# ---------------------------------------------------------------------------
# 9. simulation/optimizers/attack_optimizer_factory.py
# ---------------------------------------------------------------------------

class TestAttackOptimizerFactory(unittest.TestCase):
    def setUp(self):
        self.attacker = Character("attacker")
        self.attacker.set_ring("fire", 3)
        self.attacker.set_ring("air", 3)
        self.attacker.set_ring("earth", 3)
        self.attacker.set_ring("water", 3)
        self.attacker.set_ring("void", 3)
        self.attacker.set_skill("attack", 3)
        self.attacker.set_actions([3])

        self.target = Character("target")
        self.target.set_skill("parry", 3)

        groups = [Group("attacker", self.attacker), Group("target", self.target)]
        self.context = EngineContext(groups)
        self.context.initialize()
        self.initiative_action = InitiativeAction([3], 3)
        self.factory = DefaultAttackOptimizerFactory()

    def test_feint_returns_attack_optimizer(self):
        opt = self.factory.get_optimizer(
            self.attacker, self.target, "feint", self.initiative_action, self.context
        )
        self.assertIsInstance(opt, AttackOptimizer)

    def test_double_attack_returns_damage_optimizer(self):
        opt = self.factory.get_optimizer(
            self.attacker, self.target, "double attack", self.initiative_action, self.context
        )
        self.assertIsInstance(opt, DamageOptimizer)

    def test_default_returns_damage_optimizer(self):
        opt = self.factory.get_optimizer(
            self.attacker, self.target, "attack", self.initiative_action, self.context
        )
        self.assertIsInstance(opt, DamageOptimizer)


# ---------------------------------------------------------------------------
# 10. simulation/strategies/action_factory.py
# ---------------------------------------------------------------------------

class TestDefaultActionFactory(unittest.TestCase):
    def setUp(self):
        self.subject = Character("attacker")
        self.subject.set_skill("attack", 3)
        self.subject.set_actions([3])

        self.target = Character("target")
        self.target.set_skill("parry", 3)

        groups = [Group("attacker", self.subject), Group("target", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([3], 3)
        self.factory = DefaultActionFactory()

    def test_attack(self):
        action = self.factory.get_attack_action(
            self.subject, self.target, "attack", self.initiative_action, self.context
        )
        self.assertIsInstance(action, AttackAction)

    def test_double_attack(self):
        action = self.factory.get_attack_action(
            self.subject, self.target, "double attack", self.initiative_action, self.context
        )
        self.assertIsInstance(action, DoubleAttackAction)

    def test_feint(self):
        action = self.factory.get_attack_action(
            self.subject, self.target, "feint", self.initiative_action, self.context
        )
        self.assertIsInstance(action, FeintAction)

    def test_lunge(self):
        action = self.factory.get_attack_action(
            self.subject, self.target, "lunge", self.initiative_action, self.context
        )
        self.assertIsInstance(action, LungeAction)

    def test_invalid_attack_skill(self):
        with self.assertRaises(ValueError):
            self.factory.get_attack_action(
                self.subject, self.target, "nonexistent_skill", self.initiative_action, self.context
            )

    def test_counterattack(self):
        attack = AttackAction(
            self.target, self.subject, "attack", self.initiative_action, self.context
        )
        action = self.factory.get_counterattack_action(
            self.subject, self.target, attack, "counterattack", self.initiative_action, self.context
        )
        self.assertIsInstance(action, CounterattackAction)

    def test_parry(self):
        attack = AttackAction(
            self.target, self.subject, "attack", self.initiative_action, self.context
        )
        action = self.factory.get_parry_action(
            self.subject, self.target, attack, "parry", self.initiative_action, self.context
        )
        self.assertIsInstance(action, ParryAction)


# ---------------------------------------------------------------------------
# 11. simulation/strategies/target_finders.py
# ---------------------------------------------------------------------------

class TestTargetFinderMostDangerous(unittest.TestCase):
    def setUp(self):
        self.akodo = Character("Akodo")
        self.akodo.set_skill("parry", 4)

        self.bayushi = Character("Bayushi")
        self.bayushi.set_skill("parry", 4)

        self.hida = Character("Hida")
        self.hida.set_skill("parry", 4)

        groups = [
            Group("East", [self.akodo]),
            Group("West", [self.bayushi, self.hida]),
        ]
        self.context = EngineContext(groups)
        self.context.initialize()
        self.initiative_action = InitiativeAction([4], 4)

    def test_find_most_dangerous_no_enemies(self):
        """When all enemies are defeated, should return None."""
        # Defeat both enemies
        self.bayushi.take_sw(self.bayushi.max_sw())
        self.hida.take_sw(self.hida.max_sw())
        finder = TargetFinder()
        result = finder.find_most_dangerous_target(
            self.akodo, "attack", self.initiative_action, self.context
        )
        self.assertIsNone(result)


class TestTargetFinderMostWounded(unittest.TestCase):
    def setUp(self):
        self.akodo = Character("Akodo")
        self.akodo.set_skill("parry", 4)

        self.bayushi = Character("Bayushi")
        self.bayushi.set_skill("parry", 4)
        self.bayushi.set_ring("earth", 4)

        self.hida = Character("Hida")
        self.hida.set_skill("parry", 4)
        self.hida.set_ring("earth", 4)

        groups = [
            Group("East", [self.akodo]),
            Group("West", [self.bayushi, self.hida]),
        ]
        self.context = EngineContext(groups)
        self.context.initialize()
        self.initiative_action = InitiativeAction([4], 4)

    def test_find_most_wounded_target(self):
        # Bayushi has more wounds
        self.bayushi.take_sw(3)
        self.hida.take_sw(1)
        finder = TargetFinder()
        result = finder.find_most_wounded_target(
            self.akodo, "attack", self.initiative_action, self.context
        )
        self.assertEqual(self.bayushi, result)

    def test_find_most_wounded_no_enemies(self):
        """When all enemies are defeated, should return None."""
        self.bayushi.take_sw(self.bayushi.max_sw())
        self.hida.take_sw(self.hida.max_sw())
        finder = TargetFinder()
        result = finder.find_most_wounded_target(
            self.akodo, "attack", self.initiative_action, self.context
        )
        self.assertIsNone(result)

    def test_find_most_wounded_same_sw_different_lw(self):
        """When SW are tied, character with more LW is more wounded."""
        self.bayushi.take_sw(1)
        self.hida.take_sw(1)
        self.bayushi.take_lw(20)
        self.hida.take_lw(5)
        finder = TargetFinder()
        result = finder.find_most_wounded_target(
            self.akodo, "attack", self.initiative_action, self.context
        )
        self.assertEqual(self.bayushi, result)


# ---------------------------------------------------------------------------
# 12. simulation/strategies/take_action_event_factory.py
# ---------------------------------------------------------------------------

class TestDefaultTakeActionEventFactory(unittest.TestCase):
    def setUp(self):
        self.subject = Character("attacker")
        self.subject.set_skill("attack", 3)
        self.subject.set_actions([3])

        self.target = Character("target")
        self.target.set_skill("parry", 3)

        groups = [Group("attacker", self.subject), Group("target", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([3], 3)
        self.factory = DefaultTakeActionEventFactory()

    def test_get_take_attack_action_event(self):
        attack = AttackAction(
            self.subject, self.target, "attack", self.initiative_action, self.context
        )
        event = self.factory.get_take_attack_action_event(attack)
        self.assertIsInstance(event, TakeAttackActionEvent)

    def test_get_take_attack_action_event_invalid(self):
        with self.assertRaises(ValueError):
            self.factory.get_take_attack_action_event("not an action")

    def test_get_take_parry_action_event(self):
        attack = AttackAction(
            self.target, self.subject, "attack", self.initiative_action, self.context
        )
        parry = ParryAction(
            self.subject, self.target, "parry", self.initiative_action, self.context, attack
        )
        event = self.factory.get_take_parry_action_event(parry)
        self.assertIsInstance(event, TakeParryActionEvent)

    def test_get_take_parry_action_event_invalid(self):
        with self.assertRaises(ValueError):
            self.factory.get_take_parry_action_event("not an action")


if __name__ == "__main__":
    unittest.main()
