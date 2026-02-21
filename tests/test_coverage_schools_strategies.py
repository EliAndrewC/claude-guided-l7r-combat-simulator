#!/usr/bin/env python3

#
# test_coverage_schools_strategies.py
#
# Unit tests to improve coverage for school and strategy modules.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.character_builder import CharacterBuilder
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.floating_bonuses import AnyAttackFloatingBonus, FloatingBonus
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.knowledge import Knowledge, TheoreticalCharacter
from simulation.mechanics.modifiers import Modifier
from simulation.mechanics.roll_provider import TestRollProvider
from simulation.schools import akodo_school, bayushi_school
from simulation.schools.akodo_school import (
    AkodoBushiSchool,
    AkodoFifthDanStrategy,
    AkodoLightWoundsDamageListener,
    AkodoWoundCheckDeclaredListener,
    AkodoWoundCheckRolledStrategy,
    AkodoWoundCheckSucceededListener,
)
from simulation.schools.base import BaseSchool
from simulation.schools.bayushi_school import (
    BayushiAttackFailedListener,
    BayushiAttackSucceededListener,
    BayushiBushiSchool,
    BayushiRollParameterProvider,
)
from simulation.schools.kakita_school import (
    KakitaActionFactory,
    KakitaAttackStrategy,
    KakitaBushiSchool,
    KakitaDoubleAttackAction,
    KakitaInitiativeDieProvider,
    KakitaLungeAction,
    KakitaRollProvider,
)
from simulation.strategies.base import (
    AlwaysAttackActionStrategy,
    AlwaysKeepLightWoundsStrategy,
    AlwaysParryStrategy,
    HoldOneActionStrategy,
    NeverKeepLightWoundsStrategy,
    NeverParryStrategy,
    StingyWoundCheckStrategy,
    WoundCheckRolledStrategy,
    WoundCheckStrategy,
)

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


# ============================================================
# 1. simulation/schools/base.py - BaseSchool class coverage
# ============================================================


class TestBaseSchoolMethods(unittest.TestCase):
    """Test base School class methods through a concrete AkodoBushiSchool."""

    def setUp(self):
        self.school = AkodoBushiSchool()

    def test_name(self):
        self.assertEqual("Akodo Bushi School", self.school.name())

    def test_school_ring(self):
        self.assertEqual("water", self.school.school_ring())

    def test_school_knacks(self):
        knacks = self.school.school_knacks()
        self.assertIn("double attack", knacks)
        self.assertIn("feint", knacks)
        self.assertIn("iaijutsu", knacks)

    def test_extra_rolled(self):
        extra = self.school.extra_rolled()
        self.assertIn("double attack", extra)
        self.assertIn("feint", extra)
        self.assertIn("wound check", extra)

    def test_free_raise_skills(self):
        skills = self.school.free_raise_skills()
        self.assertEqual(["wound check"], skills)

    def test_ap_base_skill_returns_none(self):
        self.assertIsNone(self.school.ap_base_skill())

    def test_ap_skills_returns_empty(self):
        self.assertEqual([], self.school.ap_skills())


class TestBaseSchoolApplySchoolRing(unittest.TestCase):
    """Test apply_school_ring raises character's school ring from 2 to 3."""

    def test_apply_school_ring(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        # default rings are 2, which is the expected starting point
        self.assertEqual(2, character.ring("water"))
        school.apply_school_ring(character)
        self.assertEqual(3, character.ring("water"))

    def test_apply_school_ring_wrong_starting_rank(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        character.set_ring("water", 4)
        with self.assertRaises(ValueError):
            school.apply_school_ring(character)


class TestBaseSchoolApplyRankOneAbility(unittest.TestCase):
    """Test apply_rank_one_ability sets extra rolled dice."""

    def test_apply_rank_one_ability(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        school.apply_rank_one_ability(character)
        # Akodo gets extra rolled in "double attack", "feint", "wound check"
        self.assertEqual(1, character.extra_rolled("double attack"))
        self.assertEqual(1, character.extra_rolled("feint"))
        self.assertEqual(1, character.extra_rolled("wound check"))
        # No extra rolled for things not in the list
        self.assertEqual(0, character.extra_rolled("attack"))


class TestBaseSchoolApplyRankTwoAbility(unittest.TestCase):
    """Test apply_rank_two_ability adds free raises."""

    def test_apply_rank_two_ability(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        initial_modifier = character.modifier(None, "wound check")
        school.apply_rank_two_ability(character)
        # should have an additional modifier for wound check
        new_modifier = character.modifier(None, "wound check")
        self.assertEqual(initial_modifier + 5, new_modifier)


class TestBaseSchoolApplySchoolAbility(unittest.TestCase):
    """Test apply_school_ability dispatches to the correct rank method."""

    def test_rank_one(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        school.apply_school_ability(character, 1)
        # rank 1 sets extra rolled dice
        self.assertEqual(1, character.extra_rolled("double attack"))

    def test_rank_two(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        school.apply_school_ability(character, 2)
        # rank 2 adds free raise to wound check
        self.assertNotEqual(0, character.modifier(None, "wound check"))

    def test_rank_three(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        school.apply_school_ability(character, 3)
        # rank 3 sets wound_check_succeeded listener (tested by checking no error)

    def test_rank_four(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        character.set_ring("water", 3)  # needs to be >= 3 for raise
        school.apply_school_ability(character, 4)
        # rank 4 raises school ring and sets wound_check_declared listener
        self.assertEqual(4, character.ring("water"))

    def test_rank_five(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        school.apply_school_ability(character, 5)
        # rank 5 sets lw_damage listener

    def test_rank_invalid(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        # rank 0 or 6 should not call anything (no error, no effect)
        school.apply_school_ability(character, 0)
        school.apply_school_ability(character, 6)


class TestBaseSchoolApplySchoolRingRaiseAndDiscount(unittest.TestCase):
    """Test apply_school_ring_raise_and_discount."""

    def test_raises_ring_and_adds_discount(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        character.set_ring("water", 3)
        school.apply_school_ring_raise_and_discount(character)
        self.assertEqual(4, character.ring("water"))
        # discount should be set (we can verify via the character's _discounts)
        self.assertEqual(5, character._discounts.get("water", 0))


class TestBaseSchoolApplySpecialAbility(unittest.TestCase):
    """Test apply_special_ability for Akodo."""

    def test_akodo_special_ability(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        school.apply_special_ability(character)
        # should set attack_failed and attack_succeeded listeners
        # verify by checking that the listeners handle events correctly
        other = Character("Other")
        groups = [Group("A", character), Group("B", other)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        # create a feint action
        action = actions.FeintAction(character, other, "feint", initiative_action, context)
        # test attack failed listener
        event = events.AttackFailedEvent(action)
        responses = list(character._listeners["attack_failed"].handle(character, event, context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.GainTemporaryVoidPointsEvent)


class TestBaseSchoolApplyAp(unittest.TestCase):
    """Test apply_ap when ap_base_skill is None."""

    def test_apply_ap_none(self):
        school = AkodoBushiSchool()
        character = Character("TestChar")
        # ap_base_skill is None, so apply_ap should be a no-op
        school.apply_ap(character)
        self.assertIsNone(character.ap_base_skill())


# ============================================================
# 2. simulation/schools/akodo_school.py - missing coverage
# ============================================================


class TestAkodoLightWoundsDamageListener(unittest.TestCase):
    """Test AkodoLightWoundsDamageListener (5th Dan technique)."""

    def setUp(self):
        self.akodo = Character("Akodo")
        self.akodo.set_ring("water", 3)
        self.akodo.set_ring("earth", 3)
        self.akodo.set_skill("attack", 3)
        self.bayushi = Character("Bayushi")
        groups = [Group("Lion", self.akodo), Group("Scorpion", self.bayushi)]
        self.context = EngineContext(groups)
        self.context.initialize()

    def test_lw_damage_on_target(self):
        """When akodo is the target, should take LW, consult wound check strategy, and use 5th dan."""
        listener = AkodoLightWoundsDamageListener()
        # rig the wound check roll so the wound check strategy can work
        roll_provider = TestRollProvider()
        roll_provider.put_wound_check_roll(100)
        self.akodo.set_roll_provider(roll_provider)
        event = events.LightWoundsDamageEvent(self.bayushi, self.akodo, 7)
        responses = list(listener.handle(self.akodo, event, self.context))
        # akodo should have taken 7 LW
        self.assertEqual(7, self.akodo.lw())
        # responses should include wound check declared + 5th dan events
        self.assertTrue(len(responses) >= 1)

    def test_lw_damage_on_other(self):
        """When another character takes damage, akodo observes the damage roll."""
        listener = AkodoLightWoundsDamageListener()
        # bayushi attacks akodo's ally (bayushi is subject, akodo is not subject or target)
        # For akodo: event.subject (bayushi) != character (akodo) -> observes damage
        # event.target is also not akodo -> no wound check
        event = events.LightWoundsDamageEvent(self.bayushi, self.bayushi, 15)
        responses = list(listener.handle(self.akodo, event, self.context))
        # akodo should not take LW (not the target)
        self.assertEqual(0, self.akodo.lw())
        # akodo should have observed the damage roll on bayushi
        avg = self.akodo.knowledge().average_damage_roll(self.bayushi)
        # Should have observed the 15 damage
        self.assertEqual(15, avg)

    def test_lw_damage_irrelevant(self):
        """When akodo is the subject and target is someone else, only observe damage."""
        listener = AkodoLightWoundsDamageListener()
        other = Character("Other")
        groups = [Group("Lion", self.akodo), Group("Scorpion", [self.bayushi, other])]
        context = EngineContext(groups)
        event = events.LightWoundsDamageEvent(self.akodo, self.bayushi, 10)
        responses = list(listener.handle(self.akodo, event, context))
        # no LW taken, no 5th dan response since akodo is not target
        self.assertEqual(0, self.akodo.lw())


class TestAkodoWoundCheckDeclaredListener(unittest.TestCase):
    """Test AkodoWoundCheckDeclaredListener (4th Dan technique)."""

    def setUp(self):
        self.akodo = Character("Akodo")
        self.akodo.set_ring("water", 4)
        self.akodo.set_ring("earth", 4)
        self.akodo.set_skill("attack", 3)
        self.attacker = Character("Attacker")
        groups = [Group("Lion", self.akodo), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.context.initialize()

    def test_wound_check_declared_rolls_and_yields(self):
        """Listener should roll wound check and use Akodo 4th dan strategy."""
        listener = AkodoWoundCheckDeclaredListener()
        # rig the wound check roll
        roll_provider = TestRollProvider()
        roll_provider.put_wound_check_roll(50)
        self.akodo.set_roll_provider(roll_provider)
        event = events.WoundCheckDeclaredEvent(self.akodo, self.attacker, 20, vp=0)
        responses = list(listener.handle(self.akodo, event, self.context))
        # should yield at least a WoundCheckRolledEvent
        self.assertTrue(len(responses) >= 1)
        # the last event should be a WoundCheckRolledEvent
        final_event = responses[-1]
        self.assertIsInstance(final_event, events.WoundCheckRolledEvent)

    def test_wound_check_declared_other_character_ignored(self):
        """Listener should ignore events for other characters."""
        listener = AkodoWoundCheckDeclaredListener()
        event = events.WoundCheckDeclaredEvent(self.attacker, self.akodo, 20, vp=0)
        responses = list(listener.handle(self.akodo, event, self.context))
        self.assertEqual(0, len(responses))


class TestAkodoWoundCheckRolledStrategy(unittest.TestCase):
    """Test AkodoWoundCheckRolledStrategy (4th Dan VP spending)."""

    def setUp(self):
        self.akodo = Character("Akodo")
        self.akodo.set_ring("water", 4)
        self.akodo.set_ring("earth", 4)
        self.attacker = Character("Attacker")
        groups = [Group("Lion", self.akodo), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)

    def test_tolerable_sw(self):
        """When wound check is already tolerable, yields the event directly."""
        strategy = AkodoWoundCheckRolledStrategy()
        # high roll, low damage -> 0 expected SW
        event = events.WoundCheckRolledEvent(self.akodo, self.attacker, 10, 50)
        responses = list(strategy.recommend(self.akodo, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.WoundCheckRolledEvent)
        self.assertEqual(50, responses[0].roll)

    def test_intolerable_sw_spends_vp(self):
        """When wound check would cause too many SW, should spend VP."""
        strategy = AkodoWoundCheckRolledStrategy()
        # give akodo lots of LW to make wound check fail
        self.akodo.take_lw(60)
        # low roll against high damage -> multiple SW expected
        event = events.WoundCheckRolledEvent(self.akodo, self.attacker, 60, 10)
        responses = list(strategy.recommend(self.akodo, event, self.context))
        # should yield events (possibly SpendVoidPointsEvent + WoundCheckRolledEvent)
        self.assertTrue(len(responses) >= 1)
        last_event = responses[-1]
        self.assertIsInstance(last_event, events.WoundCheckRolledEvent)

    def test_event_for_other_character_ignored(self):
        """Events for other characters should be ignored."""
        strategy = AkodoWoundCheckRolledStrategy()
        event = events.WoundCheckRolledEvent(self.attacker, self.akodo, 10, 50)
        responses = list(strategy.recommend(self.akodo, event, self.context))
        self.assertEqual(0, len(responses))

    def test_intolerable_no_vp_available(self):
        """When SW are intolerable but no VP available, yield adjusted event anyway."""
        strategy = AkodoWoundCheckRolledStrategy()
        # spend all VP
        self.akodo.spend_vp(2)
        self.akodo.take_lw(60)
        event = events.WoundCheckRolledEvent(self.akodo, self.attacker, 60, 10)
        responses = list(strategy.recommend(self.akodo, event, self.context))
        self.assertTrue(len(responses) >= 1)
        last = responses[-1]
        self.assertIsInstance(last, events.WoundCheckRolledEvent)
        # roll should not have changed since no VP could be spent
        self.assertEqual(10, last.roll)


class TestAkodoWoundCheckSucceededListener(unittest.TestCase):
    """Test AkodoWoundCheckSucceededListener (3rd Dan floating bonus)."""

    def setUp(self):
        self.akodo = Character("Akodo")
        self.akodo.set_ring("water", 3)
        self.akodo.set_skill("attack", 3)
        self.attacker = Character("Attacker")
        groups = [Group("Lion", self.akodo), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.context.initialize()

    def test_wound_check_succeeded_grants_floating_bonus(self):
        """A successful wound check should grant a floating bonus."""
        listener = AkodoWoundCheckSucceededListener()
        # roll 40 against 20 damage => (40-20)//5 = 4, bonus = 4 * skill("attack") = 4*3 = 12
        event = events.WoundCheckSucceededEvent(self.akodo, self.attacker, 20, 40)
        responses = list(listener.handle(self.akodo, event, self.context))
        # should have responses from light wounds strategy
        self.assertTrue(len(responses) >= 1)
        # verify the floating bonus was added
        bonuses = self.akodo.floating_bonuses("attack")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(12, bonuses[0].bonus())

    def test_wound_check_for_other_character_ignored(self):
        """Events for other characters should be ignored."""
        listener = AkodoWoundCheckSucceededListener()
        event = events.WoundCheckSucceededEvent(self.attacker, self.akodo, 20, 40)
        responses = list(listener.handle(self.akodo, event, self.context))
        self.assertEqual(0, len(responses))


# ============================================================
# 3. simulation/schools/bayushi_school.py - missing coverage
# ============================================================


class TestBayushiRollParameterProvider(unittest.TestCase):
    """Test BayushiRollParameterProvider.get_damage_roll_params."""

    def setUp(self):
        self.bayushi = Character("Bayushi")
        self.bayushi.set_ring("fire", 3)
        self.bayushi.set_skill("attack", 3)
        self.bayushi.set_roll_parameter_provider(BayushiRollParameterProvider())
        self.target = Character("Target")

    def test_damage_roll_params_no_vp(self):
        """Damage roll params without VP spending."""
        provider = BayushiRollParameterProvider()
        (rolled, kept, mod) = provider.get_damage_roll_params(
            self.bayushi, self.target, "attack", 0, vp=0
        )
        # rolled = fire(3) + extra_rolled(0) + attack_extra_rolled(0) + weapon_rolled(4) + vp(0) = 7
        # kept = weapon_kept(2) + extra_kept(0) + vp(0) = 2
        self.assertEqual(7, rolled)
        self.assertEqual(2, kept)

    def test_damage_roll_params_with_vp(self):
        """Damage roll params with VP spending (Bayushi special: VP adds to both rolled and kept)."""
        provider = BayushiRollParameterProvider()
        (rolled, kept, mod) = provider.get_damage_roll_params(
            self.bayushi, self.target, "attack", 0, vp=2
        )
        # rolled = fire(3) + extra_rolled(0) + attack_extra_rolled(0) + weapon_rolled(4) + vp(2) = 9
        # kept = weapon_kept(2) + extra_kept(0) + vp(2) = 4
        self.assertEqual(9, rolled)
        self.assertEqual(4, kept)

    def test_damage_roll_params_with_extra_rolled(self):
        """Damage roll params with extra rolled dice from attack."""
        provider = BayushiRollParameterProvider()
        (rolled, kept, mod) = provider.get_damage_roll_params(
            self.bayushi, self.target, "attack", 3, vp=0
        )
        # rolled = fire(3) + extra_rolled(0) + attack_extra_rolled(3) + weapon_rolled(4) + vp(0) = 10
        # kept = weapon_kept(2) + extra_kept(0) + vp(0) = 2
        self.assertEqual(10, rolled)
        self.assertEqual(2, kept)


class TestBayushiAttackFailedListener(unittest.TestCase):
    """Test BayushiAttackFailedListener (4th Dan floating bonus on failed feint)."""

    def setUp(self):
        self.bayushi = Character("Bayushi")
        self.target = Character("Target")
        groups = [Group("Scorpion", self.bayushi), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_failed_feint_grants_floating_bonus(self):
        listener = BayushiAttackFailedListener()
        action = actions.FeintAction(
            self.bayushi, self.target, "feint", self.initiative_action, self.context
        )
        event = events.AttackFailedEvent(action)
        responses = list(listener.handle(self.bayushi, event, self.context))
        self.assertEqual(0, len(responses))  # yield from () - empty generator
        # but check that a floating bonus was added to the character
        bonuses = self.bayushi.floating_bonuses("attack")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(5, bonuses[0].bonus())

    def test_failed_non_feint_no_bonus(self):
        listener = BayushiAttackFailedListener()
        action = actions.AttackAction(
            self.bayushi, self.target, "attack", self.initiative_action, self.context
        )
        event = events.AttackFailedEvent(action)
        responses = list(listener.handle(self.bayushi, event, self.context))
        self.assertEqual(0, len(responses))
        bonuses = self.bayushi.floating_bonuses("attack")
        self.assertEqual(0, len(bonuses))

    def test_failed_feint_other_character_no_bonus(self):
        listener = BayushiAttackFailedListener()
        action = actions.FeintAction(
            self.target, self.bayushi, "feint", self.initiative_action, self.context
        )
        event = events.AttackFailedEvent(action)
        responses = list(listener.handle(self.bayushi, event, self.context))
        self.assertEqual(0, len(responses))
        bonuses = self.bayushi.floating_bonuses("attack")
        self.assertEqual(0, len(bonuses))


class TestBayushiAttackSucceededListener(unittest.TestCase):
    """Test BayushiAttackSucceededListener (4th Dan floating bonus on successful feint)."""

    def setUp(self):
        self.bayushi = Character("Bayushi")
        self.target = Character("Target")
        groups = [Group("Scorpion", self.bayushi), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_succeeded_feint_grants_floating_bonus(self):
        listener = BayushiAttackSucceededListener()
        action = actions.FeintAction(
            self.bayushi, self.target, "feint", self.initiative_action, self.context
        )
        event = events.AttackSucceededEvent(action)
        responses = list(listener.handle(self.bayushi, event, self.context))
        self.assertEqual(0, len(responses))  # yield from ()
        bonuses = self.bayushi.floating_bonuses("attack")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(5, bonuses[0].bonus())

    def test_succeeded_non_feint_no_bonus(self):
        listener = BayushiAttackSucceededListener()
        action = actions.AttackAction(
            self.bayushi, self.target, "attack", self.initiative_action, self.context
        )
        event = events.AttackSucceededEvent(action)
        responses = list(listener.handle(self.bayushi, event, self.context))
        self.assertEqual(0, len(responses))
        bonuses = self.bayushi.floating_bonuses("attack")
        self.assertEqual(0, len(bonuses))

    def test_succeeded_feint_other_character_no_bonus(self):
        listener = BayushiAttackSucceededListener()
        action = actions.FeintAction(
            self.target, self.bayushi, "feint", self.initiative_action, self.context
        )
        event = events.AttackSucceededEvent(action)
        responses = list(listener.handle(self.bayushi, event, self.context))
        self.assertEqual(0, len(responses))
        bonuses = self.bayushi.floating_bonuses("attack")
        self.assertEqual(0, len(bonuses))


# ============================================================
# 4. simulation/schools/kakita_school.py - missing coverage
# ============================================================


class TestKakitaActionFactory(unittest.TestCase):
    """Test KakitaActionFactory returns correct action types."""

    def setUp(self):
        self.kakita = CharacterBuilder(xp=9001).with_name("Kakita").with_school(
            KakitaBushiSchool()
        ).buy_skill("double attack", 3).buy_skill("iaijutsu", 3).buy_skill("lunge", 3).buy_ring("fire", 4).build()
        self.target = Character("Target")
        groups = [Group("Crane", self.kakita), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_get_attack_action(self):
        factory = KakitaActionFactory()
        action = factory.get_attack_action(
            self.kakita, self.target, "attack", self.initiative_action, self.context
        )
        self.assertIsInstance(action, actions.AttackAction)

    def test_get_iaijutsu_action(self):
        factory = KakitaActionFactory()
        action = factory.get_attack_action(
            self.kakita, self.target, "iaijutsu", self.initiative_action, self.context
        )
        self.assertIsInstance(action, actions.AttackAction)

    def test_get_double_attack_action(self):
        factory = KakitaActionFactory()
        action = factory.get_attack_action(
            self.kakita, self.target, "double attack", self.initiative_action, self.context
        )
        self.assertIsInstance(action, KakitaDoubleAttackAction)

    def test_get_lunge_action(self):
        factory = KakitaActionFactory()
        action = factory.get_attack_action(
            self.kakita, self.target, "lunge", self.initiative_action, self.context
        )
        self.assertIsInstance(action, KakitaLungeAction)

    def test_invalid_skill_raises(self):
        factory = KakitaActionFactory()
        with self.assertRaises(ValueError):
            factory.get_attack_action(
                self.kakita, self.target, "invalid", self.initiative_action, self.context
            )


class TestKakitaDoubleAttackAction(unittest.TestCase):
    """Test tempo bonus for KakitaDoubleAttackAction."""

    def setUp(self):
        self.kakita = CharacterBuilder(xp=9001).with_name("Kakita").with_school(
            KakitaBushiSchool()
        ).buy_ring("fire", 4).buy_skill("attack", 3).buy_skill("double attack", 3).buy_skill("iaijutsu", 3).buy_skill("lunge", 3).build()
        self.target = Character("Target")
        self.target.set_actions([5, 6, 7])
        self.groups = [Group("Crane", self.kakita), Group("Enemy", self.target)]

    def test_tempo_bonus_earlier_target(self):
        """When target has earlier actions, tempo diff is 0 (no penalty)."""
        self.kakita.set_actions([5, 6, 7])
        self.target.set_actions([1, 2, 3])
        context = EngineContext(self.groups, round=1, phase=5)
        initiative_action = InitiativeAction([5], 5)
        attack = KakitaDoubleAttackAction(
            self.kakita, self.target, "double attack", initiative_action, context
        )
        (rolled, kept, modifier) = attack.skill_roll_params()
        # tempo_diff = max(0, 1 - 5) = 0, bonus = 0
        # base params for double attack: (8, 4, 0)
        self.assertEqual((8, 4, 0), (rolled, kept, modifier))

    def test_no_target_actions(self):
        """When target has no actions, target_tempo defaults to 11."""
        self.kakita.set_actions([3])
        self.target.set_actions([])
        context = EngineContext(self.groups, round=1, phase=3)
        initiative_action = InitiativeAction([3], 3)
        attack = KakitaDoubleAttackAction(
            self.kakita, self.target, "double attack", initiative_action, context
        )
        (rolled, kept, modifier) = attack.skill_roll_params()
        # max(0, 11 - 3) = 8, bonus = 3 * 8 = 24
        self.assertEqual((8, 4, 24), (rolled, kept, modifier))

    def test_tempo_bonus_positive(self):
        """Kakita acting before target gets positive tempo bonus."""
        self.kakita.set_actions([1])
        self.target.set_actions([5])
        context = EngineContext(self.groups, round=1, phase=1)
        initiative_action = InitiativeAction([1], 1)
        attack = KakitaDoubleAttackAction(
            self.kakita, self.target, "double attack", initiative_action, context
        )
        (rolled, kept, modifier) = attack.skill_roll_params()
        # max(0, 5 - 1) = 4, bonus = 3 * 4 = 12
        self.assertEqual((8, 4, 12), (rolled, kept, modifier))


class TestKakitaLungeAction(unittest.TestCase):
    """Test tempo bonus for KakitaLungeAction."""

    def setUp(self):
        self.kakita = CharacterBuilder(xp=9001).with_name("Kakita").with_school(
            KakitaBushiSchool()
        ).buy_ring("fire", 4).buy_skill("attack", 3).buy_skill("double attack", 3).buy_skill("iaijutsu", 3).buy_skill("lunge", 3).build()
        self.target = Character("Target")
        self.groups = [Group("Crane", self.kakita), Group("Enemy", self.target)]

    def test_tempo_bonus(self):
        self.kakita.set_actions([1])
        self.target.set_actions([5])
        context = EngineContext(self.groups, round=1, phase=1)
        initiative_action = InitiativeAction([1], 1)
        attack = KakitaLungeAction(
            self.kakita, self.target, "lunge", initiative_action, context
        )
        (rolled, kept, modifier) = attack.skill_roll_params()
        # max(0, 5 - 1) = 4, bonus = 3 * 4 = 12
        # base lunge params: (7, 4, 0) — lunge not in extra_rolled
        self.assertEqual((7, 4, 12), (rolled, kept, modifier))

    def test_no_target_actions(self):
        self.kakita.set_actions([3])
        self.target.set_actions([])
        context = EngineContext(self.groups, round=1, phase=3)
        initiative_action = InitiativeAction([3], 3)
        attack = KakitaLungeAction(
            self.kakita, self.target, "lunge", initiative_action, context
        )
        (rolled, kept, modifier) = attack.skill_roll_params()
        # max(0, 11 - 3) = 8, bonus = 3 * 8 = 24
        self.assertEqual((7, 4, 24), (rolled, kept, modifier))


class TestKakitaAttackStrategy(unittest.TestCase):
    """Test that Kakita attack strategy restricts Phase 0 to iaijutsu."""

    def setUp(self):
        self.kakita = CharacterBuilder(xp=9001).with_name("Kakita").with_school(
            KakitaBushiSchool()
        ).buy_ring("fire", 4).buy_skill("attack", 3).buy_skill("double attack", 3).buy_skill("iaijutsu", 3).buy_skill("lunge", 3).build()
        self.target = Character("Target")
        self.groups = [Group("Crane", self.kakita), Group("Enemy", self.target)]

    def test_phase_0_uses_iaijutsu(self):
        """In Phase 0, attack strategy must use iaijutsu skill."""
        self.kakita.set_actions([0, 3, 5])
        context = EngineContext(self.groups, round=1, phase=0)
        context.initialize()
        strategy = KakitaAttackStrategy()
        event = events.YourMoveEvent(self.kakita)
        responses = list(strategy.recommend(self.kakita, event, context))
        # Find the TakeAttackActionEvent
        attack_events = [r for r in responses if isinstance(r, events.TakeAttackActionEvent)]
        self.assertEqual(1, len(attack_events))
        self.assertEqual("iaijutsu", attack_events[0].action.skill())

    def test_non_phase_0_allows_other_skills(self):
        """In non-Phase 0, attack strategy may use double attack or other skills."""
        self.kakita.set_actions([3, 5])
        context = EngineContext(self.groups, round=1, phase=3)
        context.initialize()
        strategy = KakitaAttackStrategy()
        event = events.YourMoveEvent(self.kakita)
        responses = list(strategy.recommend(self.kakita, event, context))
        attack_events = [r for r in responses if isinstance(r, events.TakeAttackActionEvent)]
        self.assertEqual(1, len(attack_events))
        # Should use double attack or attack, not restricted to iaijutsu
        self.assertIn(attack_events[0].action.skill(), ["double attack", "attack", "feint", "lunge"])

    def test_school_sets_attack_strategy(self):
        """KakitaBushiSchool should set KakitaAttackStrategy on the character."""
        kakita = CharacterBuilder(xp=9001).with_name("Kakita").with_school(
            KakitaBushiSchool()
        ).buy_ring("fire", 4).buy_skill("attack", 3).buy_skill("iaijutsu", 3).build()
        self.assertIsInstance(kakita.attack_strategy(), KakitaAttackStrategy)


class TestKakitaInitiativeDieProvider(unittest.TestCase):
    """Test KakitaInitiativeDieProvider rolls 0-9."""

    def test_roll_die_range(self):
        provider = KakitaInitiativeDieProvider()
        results = set()
        for _ in range(1000):
            result = provider.roll_die()
            self.assertGreaterEqual(result, 0)
            self.assertLessEqual(result, 9)
            results.add(result)
        # with 1000 rolls, we should see all values 0-9
        self.assertEqual(10, len(results))

    def test_roll_die_ignores_params(self):
        provider = KakitaInitiativeDieProvider()
        # params should be ignored
        result = provider.roll_die(faces=20, explode=False)
        self.assertGreaterEqual(result, 0)
        self.assertLessEqual(result, 9)


class TestKakitaRollProvider(unittest.TestCase):
    """Test KakitaRollProvider returns initiative rolls."""

    def test_get_initiative_roll(self):
        provider = KakitaRollProvider()
        # should return a list of ints (action phases)
        roll = provider.get_initiative_roll(3, 3)
        self.assertIsInstance(roll, list)
        for phase in roll:
            self.assertIsInstance(phase, int)
            self.assertGreaterEqual(phase, 0)
            self.assertLessEqual(phase, 10)


# ============================================================
# 5. simulation/strategies/base.py - missing coverage
# ============================================================


class TestAlwaysAttackActionStrategy(unittest.TestCase):
    """Test AlwaysAttackActionStrategy."""

    def setUp(self):
        self.character = Character("Subject")
        self.character.set_actions([1])
        self.target = Character("Target")
        groups = [Group("A", self.character), Group("B", self.target)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.context.initialize()

    def test_has_action_attacks(self):
        strategy = AlwaysAttackActionStrategy()
        event = events.YourMoveEvent(self.character)
        responses = list(strategy.recommend(self.character, event, self.context))
        # should delegate to attack_strategy and produce attack events
        self.assertTrue(len(responses) >= 1)

    def test_no_action_yields_no_action(self):
        self.character.set_actions([])
        strategy = AlwaysAttackActionStrategy()
        event = events.YourMoveEvent(self.character)
        responses = list(strategy.recommend(self.character, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.NoActionEvent)


class TestHoldOneActionStrategy(unittest.TestCase):
    """Test HoldOneActionStrategy."""

    def setUp(self):
        self.character = Character("Subject")
        self.target = Character("Target")
        groups = [Group("A", self.character), Group("B", self.target)]
        self.groups = groups

    def test_hold_action_with_one_action(self):
        """With only one action early in the round, should hold."""
        self.character.set_actions([3])
        context = EngineContext(self.groups, round=1, phase=3)
        context.initialize()
        strategy = HoldOneActionStrategy()
        event = events.YourMoveEvent(self.character)
        responses = list(strategy.recommend(self.character, event, context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.HoldActionEvent)

    def test_attack_with_multiple_actions(self):
        """With multiple available actions, should attack."""
        self.character.set_actions([1, 3])
        context = EngineContext(self.groups, round=1, phase=3)
        context.initialize()
        strategy = HoldOneActionStrategy()
        event = events.YourMoveEvent(self.character)
        responses = list(strategy.recommend(self.character, event, context))
        # should delegate to attack strategy
        self.assertTrue(len(responses) >= 1)

    def test_attack_on_phase_10(self):
        """On phase 10 with one action, should attack (don't waste actions)."""
        self.character.set_actions([10])
        context = EngineContext(self.groups, round=1, phase=10)
        context.initialize()
        strategy = HoldOneActionStrategy()
        event = events.YourMoveEvent(self.character)
        responses = list(strategy.recommend(self.character, event, context))
        # should delegate to attack strategy
        self.assertTrue(len(responses) >= 1)
        # should not be a HoldActionEvent
        self.assertNotIsInstance(responses[0], events.HoldActionEvent)

    def test_no_action(self):
        """With no actions, should yield NoActionEvent."""
        self.character.set_actions([])
        context = EngineContext(self.groups, round=1, phase=5)
        context.initialize()
        strategy = HoldOneActionStrategy()
        event = events.YourMoveEvent(self.character)
        responses = list(strategy.recommend(self.character, event, context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.NoActionEvent)

    def test_attack_in_phase_0_with_single_action(self):
        """In Phase 0 with a Phase 0 action, should attack (not hold).

        Phase 0 actions are special (e.g. Kakita school) and should always
        be used immediately — the whole point is to strike first.
        """
        self.character.set_actions([0, 3, 5])
        context = EngineContext(self.groups, round=1, phase=0)
        context.initialize()
        strategy = HoldOneActionStrategy()
        event = events.YourMoveEvent(self.character)
        responses = list(strategy.recommend(self.character, event, context))
        self.assertTrue(len(responses) >= 1)
        self.assertNotIsInstance(responses[0], events.HoldActionEvent)

    def test_phase_0_action_not_held_in_later_phases(self):
        """Phase 0 action dice should never be held, even in later phases.

        A Phase 0 die (value 0) is available in all phases (0 <= any phase).
        If it's the only available action, the hold strategy should still
        attack with it rather than holding it indefinitely.
        """
        self.character.set_actions([0, 5])
        context = EngineContext(self.groups, round=1, phase=2)
        context.initialize()
        strategy = HoldOneActionStrategy()
        event = events.YourMoveEvent(self.character)
        responses = list(strategy.recommend(self.character, event, context))
        self.assertTrue(len(responses) >= 1)
        self.assertNotIsInstance(responses[0], events.HoldActionEvent)

    def test_hold_normal_action_when_no_phase_0(self):
        """Normal actions should still be held when only 1 is available."""
        self.character.set_actions([3, 5])
        context = EngineContext(self.groups, round=1, phase=3)
        context.initialize()
        strategy = HoldOneActionStrategy()
        event = events.YourMoveEvent(self.character)
        responses = list(strategy.recommend(self.character, event, context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.HoldActionEvent)


class TestAlwaysParryStrategy(unittest.TestCase):
    """Test AlwaysParryStrategy directly."""

    def setUp(self):
        self.attacker = Character("Attacker")
        self.target = Character("Target")
        roll_provider = TestRollProvider()
        roll_provider.put_initiative_roll([1, 2, 3])
        self.target.set_roll_provider(roll_provider)
        self.target.roll_initiative()
        self.target.set_strategy("parry", AlwaysParryStrategy())
        self.initiative_action = InitiativeAction([1], 1)
        attacker_group = Group("Attacker", self.attacker)
        target_group = Group("Target", self.target)
        groups = [attacker_group, target_group]
        self.context = EngineContext(groups, round=1, phase=1)

    def test_always_parries_hit(self):
        """AlwaysParryStrategy should always parry a successful hit."""
        attack = actions.AttackAction(
            self.attacker, self.target, "attack", self.initiative_action, self.context
        )
        attack.set_skill_roll(9001)
        event = events.AttackRolledEvent(attack, 9001)
        strategy = AlwaysParryStrategy()
        responses = list(strategy.recommend(self.target, event, self.context))
        self.assertEqual(2, len(responses))
        self.assertIsInstance(responses[0], events.SpendActionEvent)
        self.assertIsInstance(responses[1], events.TakeParryActionEvent)


class TestNeverParryStrategy(unittest.TestCase):
    """Test NeverParryStrategy yields nothing."""

    def test_never_parries(self):
        character = Character("Subject")
        target = Character("Target")
        groups = [Group("A", character), Group("B", target)]
        context = EngineContext(groups)
        strategy = NeverParryStrategy()
        # test with any event
        event = events.YourMoveEvent(character)
        responses = list(strategy.recommend(character, event, context))
        self.assertEqual(0, len(responses))


class TestAlwaysKeepLightWoundsStrategy(unittest.TestCase):
    """Test AlwaysKeepLightWoundsStrategy."""

    def test_always_keeps(self):
        character = Character("Subject")
        attacker = Character("Attacker")
        groups = [Group("A", character), Group("B", attacker)]
        context = EngineContext(groups)
        strategy = AlwaysKeepLightWoundsStrategy()
        event = events.WoundCheckSucceededEvent(character, attacker, 10, 30)
        responses = list(strategy.recommend(character, event, context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.KeepLightWoundsEvent)

    def test_ignores_other_characters(self):
        character = Character("Subject")
        attacker = Character("Attacker")
        groups = [Group("A", character), Group("B", attacker)]
        context = EngineContext(groups)
        strategy = AlwaysKeepLightWoundsStrategy()
        event = events.WoundCheckSucceededEvent(attacker, character, 10, 30)
        responses = list(strategy.recommend(character, event, context))
        self.assertEqual(0, len(responses))


class TestNeverKeepLightWoundsStrategy(unittest.TestCase):
    """Test NeverKeepLightWoundsStrategy always takes SW."""

    def test_never_keeps(self):
        character = Character("Subject")
        attacker = Character("Attacker")
        groups = [Group("A", character), Group("B", attacker)]
        context = EngineContext(groups)
        strategy = NeverKeepLightWoundsStrategy()
        event = events.WoundCheckSucceededEvent(character, attacker, 10, 30)
        responses = list(strategy.recommend(character, event, context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.SeriousWoundsDamageEvent)

    def test_ignores_other_characters(self):
        character = Character("Subject")
        attacker = Character("Attacker")
        groups = [Group("A", character), Group("B", attacker)]
        context = EngineContext(groups)
        strategy = NeverKeepLightWoundsStrategy()
        event = events.WoundCheckSucceededEvent(attacker, character, 10, 30)
        responses = list(strategy.recommend(character, event, context))
        self.assertEqual(0, len(responses))


class TestStingyWoundCheckStrategy(unittest.TestCase):
    """Test StingyWoundCheckStrategy never spends VP on wound checks."""

    def test_ignores_other_characters(self):
        character = Character("Subject")
        attacker = Character("Attacker")
        groups = [Group("A", character), Group("B", attacker)]
        context = EngineContext(groups)
        strategy = StingyWoundCheckStrategy()
        event = events.LightWoundsDamageEvent(character, attacker, 15)
        responses = list(strategy.recommend(character, event, context))
        self.assertEqual(0, len(responses))

    def test_matches_correct_event_type(self):
        """StingyWoundCheckStrategy only responds to LightWoundsDamageEvent for the target."""
        character = Character("Subject")
        attacker = Character("Attacker")
        groups = [Group("A", character), Group("B", attacker)]
        context = EngineContext(groups)
        strategy = StingyWoundCheckStrategy()
        # wrong event type should yield nothing
        event = events.YourMoveEvent(character)
        responses = list(strategy.recommend(character, event, context))
        self.assertEqual(0, len(responses))


class TestWoundCheckStrategy(unittest.TestCase):
    """Test WoundCheckStrategy.recommend for wound check events."""

    def test_recommend_declares_wound_check(self):
        character = Character("Subject")
        attacker = Character("Attacker")
        character.take_lw(20)
        groups = [Group("A", character), Group("B", attacker)]
        context = EngineContext(groups)
        context.initialize()
        strategy = WoundCheckStrategy()
        event = events.LightWoundsDamageEvent(attacker, character, 20)
        responses = list(strategy.recommend(character, event, context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.WoundCheckDeclaredEvent)

    def test_recommend_ignores_other_character(self):
        character = Character("Subject")
        attacker = Character("Attacker")
        groups = [Group("A", character), Group("B", attacker)]
        context = EngineContext(groups)
        context.initialize()
        strategy = WoundCheckStrategy()
        event = events.LightWoundsDamageEvent(character, attacker, 20)
        responses = list(strategy.recommend(character, event, context))
        self.assertEqual(0, len(responses))


class TestWoundCheckRolledStrategy(unittest.TestCase):
    """Test WoundCheckRolledStrategy for deciding VP/floating bonus spend on wound checks."""

    def setUp(self):
        self.character = Character("Subject")
        self.character.set_ring("water", 3)
        self.character.set_ring("earth", 3)
        self.attacker = Character("Attacker")
        groups = [Group("A", self.character), Group("B", self.attacker)]
        self.context = EngineContext(groups)

    def test_no_sw_expected(self):
        """If roll is high enough that no SW are expected, pass through."""
        strategy = WoundCheckRolledStrategy()
        # roll 50 vs 20 damage -> 0 SW
        event = events.WoundCheckRolledEvent(self.character, self.attacker, 20, 50)
        responses = list(strategy.recommend(self.character, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.WoundCheckRolledEvent)
        self.assertEqual(50, responses[0].roll)

    def test_sw_expected_no_resources(self):
        """If SW are expected but character has no resources to spend, pass through."""
        self.character.spend_vp(2)  # spend all VP
        strategy = WoundCheckRolledStrategy()
        # roll 5 vs 30 damage -> SW expected
        self.character.take_lw(30)
        event = events.WoundCheckRolledEvent(self.character, self.attacker, 30, 5)
        responses = list(strategy.recommend(self.character, event, self.context))
        # should just pass through since no resources to spend
        self.assertTrue(len(responses) >= 1)
        last = responses[-1]
        self.assertIsInstance(last, events.WoundCheckRolledEvent)

    def test_ignores_other_character(self):
        strategy = WoundCheckRolledStrategy()
        event = events.WoundCheckRolledEvent(self.attacker, self.character, 20, 50)
        responses = list(strategy.recommend(self.character, event, self.context))
        self.assertEqual(0, len(responses))

    def test_sw_expected_no_progress(self):
        """When SW expected but floating bonuses don't help enough, fall through."""
        strategy = WoundCheckRolledStrategy()
        # give character a small floating bonus that won't reduce SW count
        self.character.gain_floating_bonus(FloatingBonus("wound check", 1))
        # spend all VP so AP path also can't help
        self.character.spend_vp(2)
        # roll 5 vs 100 damage -> SW expected: 1 + (100-5)//10 = 10 SW
        # with +1 bonus: 1 + (100-6)//10 = 10 SW (no change)
        self.character.take_lw(100)
        event = events.WoundCheckRolledEvent(self.character, self.attacker, 100, 5)
        responses = list(strategy.recommend(self.character, event, self.context))
        # no progress was made, so it should just yield the original event
        self.assertTrue(len(responses) >= 1)
        last = responses[-1]
        self.assertIsInstance(last, events.WoundCheckRolledEvent)
        # roll should be unchanged (5) because no progress was made
        self.assertEqual(5, last.roll)


# ============================================================
# 6. simulation/mechanics/knowledge.py - missing coverage
# ============================================================


class TestKnowledgeClear(unittest.TestCase):
    """Test Knowledge.clear() method."""

    def test_clear_resets_all_state(self):
        knowledge = Knowledge()
        akodo = Character("Akodo")
        bayushi = Character("Bayushi")
        # populate knowledge
        knowledge.observe_action(akodo)
        knowledge.observe_action(akodo)
        knowledge.observe_attack_roll(akodo, 50)
        knowledge.observe_damage_roll(akodo, 30)
        knowledge.observe_ring(akodo, "fire", 4)
        knowledge.observe_skill(akodo, "attack", 3)
        knowledge.observe_tn_to_hit(akodo, 25)
        knowledge.observe_wounds(akodo, 2)
        knowledge.end_of_round()
        # verify state is populated
        self.assertEqual(2, knowledge.actions_per_round(akodo))
        self.assertEqual(50, knowledge.average_attack_roll(akodo))
        self.assertEqual(30, knowledge.average_damage_roll(akodo))
        self.assertEqual(25, knowledge.tn_to_hit(akodo))
        self.assertEqual(2, knowledge.wounds(akodo))
        # clear
        knowledge.clear()
        # verify state is cleared to defaults
        self.assertEqual(2, knowledge.actions_per_round(akodo))  # default is 2
        self.assertEqual(27, knowledge.average_attack_roll(akodo))  # default is 27
        self.assertEqual(18, knowledge.average_damage_roll(akodo))  # default is 18
        self.assertEqual(20, knowledge.tn_to_hit(akodo))  # default is 20
        self.assertEqual(0, knowledge.wounds(akodo))  # default is 0


class TestKnowledgeObserveDamageRoll(unittest.TestCase):
    """Test Knowledge.observe_damage_roll method."""

    def test_observe_damage_roll_new_character(self):
        knowledge = Knowledge()
        akodo = Character("Akodo")
        knowledge.observe_damage_roll(akodo, 25)
        self.assertEqual(25, knowledge.average_damage_roll(akodo))

    def test_observe_damage_roll_existing_character(self):
        knowledge = Knowledge()
        akodo = Character("Akodo")
        knowledge.observe_damage_roll(akodo, 20)
        knowledge.observe_damage_roll(akodo, 40)
        self.assertEqual(30, knowledge.average_damage_roll(akodo))


class TestKnowledgeObserveWounds(unittest.TestCase):
    """Test Knowledge.observe_wounds for accumulation."""

    def test_observe_wounds_accumulates(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        knowledge.observe_wounds(char, 1)
        self.assertEqual(1, knowledge.wounds(char))
        knowledge.observe_wounds(char, 2)
        self.assertEqual(3, knowledge.wounds(char))


class TestKnowledgeLwAndSw(unittest.TestCase):
    """Test Knowledge.lw() and Knowledge.sw() which delegate to character."""

    def test_lw_returns_character_lw(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        char.take_lw(15)
        self.assertEqual(15, knowledge.lw(char))

    def test_sw_returns_character_sw(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        char.take_sw(2)
        self.assertEqual(2, knowledge.sw(char))


class TestKnowledgeObserveRing(unittest.TestCase):
    """Test Knowledge.observe_ring."""

    def test_observe_ring(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        knowledge.observe_ring(char, "fire", 4)
        # verify it's stored (TheoreticalCharacter doesn't use it directly but internal state is set)
        self.assertIn("fire", knowledge._rings.get(char.name(), {}))
        self.assertEqual(4, knowledge._rings[char.name()]["fire"])

    def test_observe_ring_invalid_ring_type(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        with self.assertRaises(ValueError):
            knowledge.observe_ring(char, 123, 4)

    def test_observe_ring_invalid_rank_type(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        with self.assertRaises(ValueError):
            knowledge.observe_ring(char, "fire", "four")


class TestKnowledgeObserveSkill(unittest.TestCase):
    """Test Knowledge.observe_skill."""

    def test_observe_skill(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        knowledge.observe_skill(char, "attack", 3)
        self.assertIn("attack", knowledge._skills.get(char.name(), {}))
        self.assertEqual(3, knowledge._skills[char.name()]["attack"])

    def test_observe_skill_invalid_skill_type(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        with self.assertRaises(ValueError):
            knowledge.observe_skill(char, 123, 3)

    def test_observe_skill_invalid_rank_type(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        with self.assertRaises(ValueError):
            knowledge.observe_skill(char, "attack", "three")


class TestKnowledgeObserveModifier(unittest.TestCase):
    """Test Knowledge.observe_modifier_added and observe_modifier_removed."""

    def test_observe_modifier_added_and_removed(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        modifier = Modifier(char, None, "tn to hit", -5)
        knowledge.observe_modifier_added(char, modifier)
        # modifier should affect knowledge
        self.assertEqual(-5, knowledge.modifier(char, None, "tn to hit"))
        # remove modifier
        knowledge.observe_modifier_removed(char, modifier)
        self.assertEqual(0, knowledge.modifier(char, None, "tn to hit"))

    def test_observe_modifier_multiple(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        mod1 = Modifier(char, None, "tn to hit", -5)
        mod2 = Modifier(char, None, "tn to hit", -10)
        knowledge.observe_modifier_added(char, mod1)
        knowledge.observe_modifier_added(char, mod2)
        self.assertEqual(-15, knowledge.modifier(char, None, "tn to hit"))


class TestKnowledgeWeapon(unittest.TestCase):
    """Test Knowledge.weapon returns character's weapon."""

    def test_weapon(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        weapon = knowledge.weapon(char)
        self.assertEqual(char.weapon(), weapon)


class TestTheoreticalCharacterAccessors(unittest.TestCase):
    """Test TheoreticalCharacter accessors."""

    def test_actions(self):
        char = Character("Fighter")
        char.set_actions([1, 3, 5])
        knowledge = Knowledge()
        tc = TheoreticalCharacter(knowledge, char)
        self.assertEqual([1, 3, 5], tc.actions())

    def test_lw(self):
        char = Character("Fighter")
        char.take_lw(25)
        knowledge = Knowledge()
        tc = TheoreticalCharacter(knowledge, char)
        self.assertEqual(25, tc.lw())

    def test_ring(self):
        char = Character("Fighter")
        knowledge = Knowledge()
        tc = TheoreticalCharacter(knowledge, char)
        # TheoreticalCharacter.ring() always returns 3 (TODO in source)
        self.assertEqual(3, tc.ring("fire"))
        self.assertEqual(3, tc.ring("water"))

    def test_sw(self):
        char = Character("Fighter")
        char.take_sw(2)
        knowledge = Knowledge()
        tc = TheoreticalCharacter(knowledge, char)
        self.assertEqual(2, tc.sw())

    def test_tn_to_hit(self):
        char = Character("Fighter")
        char.set_skill("parry", 3)
        knowledge = Knowledge()
        knowledge.observe_tn_to_hit(char, 20)
        tc = TheoreticalCharacter(knowledge, char)
        self.assertEqual(20, tc.tn_to_hit())

    def test_tn_to_hit_with_modifier(self):
        char = Character("Fighter")
        char.set_skill("parry", 3)
        knowledge = Knowledge()
        knowledge.observe_tn_to_hit(char, 20)
        modifier = Modifier(char, None, "tn to hit", -5)
        knowledge.observe_modifier_added(char, modifier)
        tc = TheoreticalCharacter(knowledge, char)
        # tn_to_hit = knowledge.tn_to_hit(char) + knowledge.modifier(char, None, "tn to hit")
        # = 20 + (-5) = 15
        self.assertEqual(15, tc.tn_to_hit())


class TestKnowledgeObserveTnToHit(unittest.TestCase):
    """Test observe_tn_to_hit with modifier adjustment."""

    def test_observe_tn_to_hit_with_existing_modifier(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        modifier = Modifier(char, None, "tn to hit", -5)
        knowledge.observe_modifier_added(char, modifier)
        # observe TN to hit (should subtract existing modifier)
        knowledge.observe_tn_to_hit(char, 15)
        # stored value should be 15 - (-5) = 20 (base TN)
        self.assertEqual(20, knowledge.tn_to_hit(char))

    def test_observe_tn_to_hit_not_overwritten(self):
        knowledge = Knowledge()
        char = Character("Fighter")
        knowledge.observe_tn_to_hit(char, 25)
        # second observation should not overwrite
        knowledge.observe_tn_to_hit(char, 30)
        self.assertEqual(25, knowledge.tn_to_hit(char))


# ============================================================
# Additional coverage for Bayushi school methods
# ============================================================


class TestBayushiSchoolMethods(unittest.TestCase):
    """Test Bayushi school base methods via BayushiBushiSchool."""

    def test_name(self):
        school = BayushiBushiSchool()
        self.assertEqual("Bayushi Bushi School", school.name())

    def test_school_ring(self):
        school = BayushiBushiSchool()
        self.assertEqual("fire", school.school_ring())

    def test_school_knacks(self):
        school = BayushiBushiSchool()
        knacks = school.school_knacks()
        self.assertIn("double attack", knacks)
        self.assertIn("feint", knacks)
        self.assertIn("iaijutsu", knacks)

    def test_extra_rolled(self):
        school = BayushiBushiSchool()
        extra = school.extra_rolled()
        self.assertIn("double attack", extra)
        self.assertIn("iaijutsu", extra)
        self.assertIn("wound check", extra)

    def test_free_raise_skills(self):
        school = BayushiBushiSchool()
        skills = school.free_raise_skills()
        self.assertEqual(["double attack"], skills)

    def test_apply_special_ability(self):
        school = BayushiBushiSchool()
        char = Character("Bayushi")
        school.apply_special_ability(char)
        # should set roll parameter provider
        self.assertIsInstance(char.roll_parameter_provider(), BayushiRollParameterProvider)

    def test_apply_rank_three(self):
        school = BayushiBushiSchool()
        char = Character("Bayushi")
        school.apply_rank_three_ability(char)
        # should set action factory to Bayushi's

    def test_apply_rank_four(self):
        school = BayushiBushiSchool()
        char = Character("Bayushi")
        char.set_ring("fire", 3)
        school.apply_rank_four_ability(char)
        # should raise fire ring and set listeners
        self.assertEqual(4, char.ring("fire"))

    def test_apply_rank_five(self):
        school = BayushiBushiSchool()
        char = Character("Bayushi")
        school.apply_rank_five_ability(char)
        # should set wound check provider


# ============================================================
# Additional coverage for Kakita school methods
# ============================================================


class TestKakitaSchoolMethods(unittest.TestCase):
    """Test Kakita school base methods via KakitaBushiSchool."""

    def test_name(self):
        school = KakitaBushiSchool()
        self.assertEqual("Kakita Bushi School", school.name())

    def test_school_ring(self):
        school = KakitaBushiSchool()
        self.assertEqual("fire", school.school_ring())

    def test_school_knacks(self):
        school = KakitaBushiSchool()
        knacks = school.school_knacks()
        self.assertIn("double attack", knacks)
        self.assertIn("iaijutsu", knacks)
        self.assertIn("lunge", knacks)

    def test_extra_rolled(self):
        school = KakitaBushiSchool()
        extra = school.extra_rolled()
        self.assertIn("double attack", extra)
        self.assertIn("iaijutsu", extra)
        self.assertIn("initiative", extra)

    def test_free_raise_skills(self):
        school = KakitaBushiSchool()
        skills = school.free_raise_skills()
        self.assertEqual(["iaijutsu"], skills)

    def test_apply_special_ability(self):
        school = KakitaBushiSchool()
        char = Character("Kakita")
        school.apply_special_ability(char)
        # should set roll provider and add iaijutsu as interrupt skill
        self.assertIn("iaijutsu", char._interrupt_skills)


# ============================================================
# Additional strategy coverage
# ============================================================


class TestAttackRolledStrategy(unittest.TestCase):
    """Test AttackRolledStrategy (SkillRolledStrategy subclass) for coverage."""

    def setUp(self):
        from simulation.strategies.base import AttackRolledStrategy
        self.strategy = AttackRolledStrategy()
        self.character = Character("Attacker")
        self.character.set_ring("fire", 4)
        self.character.set_skill("attack", 3)
        self.target = Character("Target")
        groups = [Group("A", self.character), Group("B", self.target)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.initiative_action = InitiativeAction([1], 1)

    def test_event_matches(self):
        """AttackRolledStrategy should match AttackRolledEvent for the subject."""
        action = actions.AttackAction(
            self.character, self.target, "attack", self.initiative_action, self.context
        )
        action.set_skill_roll(25)
        event = events.AttackRolledEvent(action, 25)
        self.assertTrue(self.strategy.event_matches(self.character, event))
        # should not match for wrong character
        self.assertFalse(self.strategy.event_matches(self.target, event))

    def test_get_skill(self):
        action = actions.AttackAction(
            self.character, self.target, "attack", self.initiative_action, self.context
        )
        action.set_skill_roll(25)
        event = events.AttackRolledEvent(action, 25)
        self.assertEqual("attack", self.strategy.get_skill(event))

    def test_get_tn(self):
        action = actions.AttackAction(
            self.character, self.target, "attack", self.initiative_action, self.context
        )
        action.set_skill_roll(25)
        event = events.AttackRolledEvent(action, 25)
        self.assertEqual(self.target.tn_to_hit(), self.strategy.get_tn(event))

    def test_recommend_roll_already_succeeds(self):
        """When roll >= TN, should pass through the event."""
        action = actions.AttackAction(
            self.character, self.target, "attack", self.initiative_action, self.context
        )
        tn = self.target.tn_to_hit()
        action.set_skill_roll(tn + 5)  # roll exceeds TN
        event = events.AttackRolledEvent(action, tn + 5)
        responses = list(self.strategy.recommend(self.character, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.AttackRolledEvent)

    def test_recommend_with_floating_bonus_reaches_tn(self):
        """When roll is below TN but floating bonus makes it, should spend bonus."""
        action = actions.AttackAction(
            self.character, self.target, "attack", self.initiative_action, self.context
        )
        tn = self.target.tn_to_hit()  # 10 by default (5 * (1+1))
        action.set_skill_roll(tn - 3)  # 3 below TN
        event = events.AttackRolledEvent(action, tn - 3)
        # give character a floating bonus for attack
        self.character.gain_floating_bonus(AnyAttackFloatingBonus(5))
        responses = list(self.strategy.recommend(self.character, event, self.context))
        # should have SpendFloatingBonusEvent + the AttackRolledEvent
        self.assertTrue(len(responses) >= 2)
        self.assertIsInstance(responses[0], events.SpendFloatingBonusEvent)
        self.assertIsInstance(responses[-1], events.AttackRolledEvent)

    def test_recommend_floating_bonus_not_enough(self):
        """When floating bonus doesn't fully reach TN and no AP available."""
        action = actions.AttackAction(
            self.character, self.target, "attack", self.initiative_action, self.context
        )
        tn = self.target.tn_to_hit()
        action.set_skill_roll(tn - 20)  # far below TN
        event = events.AttackRolledEvent(action, tn - 20)
        # give a small floating bonus
        self.character.gain_floating_bonus(AnyAttackFloatingBonus(3))
        responses = list(self.strategy.recommend(self.character, event, self.context))
        # should still yield the event (margin > 0, no AP available, so falls through)
        self.assertTrue(len(responses) >= 1)
        self.assertIsInstance(responses[-1], events.AttackRolledEvent)

    def test_recommend_non_matching_event(self):
        """Non-matching events should yield nothing."""
        event = events.YourMoveEvent(self.character)
        responses = list(self.strategy.recommend(self.character, event, self.context))
        self.assertEqual(0, len(responses))

    def test_reset(self):
        """Test that reset clears state."""
        self.strategy._chosen_ap = 5
        self.strategy._chosen_bonuses = [AnyAttackFloatingBonus(10)]
        self.strategy.reset()
        self.assertEqual(0, self.strategy._chosen_ap)
        self.assertEqual([], self.strategy._chosen_bonuses)

    def test_use_floating_bonuses(self):
        """Test use_floating_bonuses directly."""
        self.character.gain_floating_bonus(AnyAttackFloatingBonus(5))
        self.character.gain_floating_bonus(AnyAttackFloatingBonus(3))
        self.strategy.use_floating_bonuses(self.character, "attack", 7)
        # should have chosen both bonuses (5 + 3 = 8, which covers margin of 7)
        self.assertEqual(2, len(self.strategy._chosen_bonuses))


class TestParryRolledStrategy(unittest.TestCase):
    """Test ParryRolledStrategy (SkillRolledStrategy subclass)."""

    def test_event_matches(self):
        from simulation.strategies.base import ParryRolledStrategy
        strategy = ParryRolledStrategy()
        attacker = Character("Attacker")
        parrier = Character("Parrier")
        target = Character("Target")
        groups = [Group("A", [parrier, target]), Group("B", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, target, "attack", initiative_action, context)
        attack.set_skill_roll(30)
        parry = actions.ParryAction(parrier, attacker, "parry", initiative_action, context, attack)
        parry.set_skill_roll(25)
        event = events.ParryRolledEvent(parry, 25)
        self.assertTrue(strategy.event_matches(parrier, event))
        self.assertFalse(strategy.event_matches(attacker, event))


class TestWoundCheckRolledStrategyUseAp(unittest.TestCase):
    """Test WoundCheckRolledStrategy.use_ap path."""

    def test_use_ap_when_available(self):
        strategy = WoundCheckRolledStrategy()
        character = Character("Subject")
        character.set_ring("water", 3)
        character.set_ring("earth", 3)
        # set up AP capability
        character._ap_base_skill = "attack"
        character._ap_skills = ["wound check"]
        character.set_skill("attack", 3)
        attacker = Character("Attacker")
        # create event
        event = events.WoundCheckRolledEvent(character, attacker, 50, 10)
        # call use_ap
        result = strategy.use_ap(character, event, 0, "wound check")
        self.assertIsInstance(result, events.WoundCheckRolledEvent)
        # check that AP was spent (roll should have been increased)
        self.assertGreater(result.roll, 10)

    def test_use_ap_no_ap_skills(self):
        """When character can't spend AP on wound check, no AP should be used."""
        strategy = WoundCheckRolledStrategy()
        character = Character("Subject")
        character.set_ring("water", 3)
        attacker = Character("Attacker")
        event = events.WoundCheckRolledEvent(character, attacker, 50, 10)
        result = strategy.use_ap(character, event, 0, "wound check")
        self.assertIsInstance(result, events.WoundCheckRolledEvent)
        # roll should not have changed
        self.assertEqual(10, result.roll)


class TestWoundCheckRolledStrategyUseFloatingBonuses(unittest.TestCase):
    """Test WoundCheckRolledStrategy.use_floating_bonuses path."""

    def test_use_floating_bonuses(self):
        strategy = WoundCheckRolledStrategy()
        character = Character("Subject")
        character.set_ring("water", 3)
        character.set_ring("earth", 3)
        character.take_lw(50)
        attacker = Character("Attacker")
        # give character wound check floating bonus
        character.gain_floating_bonus(FloatingBonus("wound check", 15))
        event = events.WoundCheckRolledEvent(character, attacker, 50, 10)
        result = strategy.use_floating_bonuses(character, event, 1, "wound check")
        self.assertIsInstance(result, events.WoundCheckRolledEvent)
        # roll should have been boosted by the floating bonus
        self.assertEqual(25, result.roll)
        self.assertEqual(1, len(strategy._chosen_bonuses))


class TestBaseParryStrategyEstimateDamage(unittest.TestCase):
    """Test BaseParryStrategy._estimate_damage."""

    def test_estimate_damage(self):
        from simulation.strategies.base import ReluctantParryStrategy
        attacker = Character("Attacker")
        attacker.set_ring("fire", 4)
        target = Character("Target")
        roll_provider = TestRollProvider()
        roll_provider.put_initiative_roll([1, 2, 3])
        target.set_roll_provider(roll_provider)
        target.roll_initiative()
        groups = [Group("Attacker", attacker), Group("Target", target)]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, target, "attack", initiative_action, context)
        attack.set_skill_roll(30)
        event = events.AttackRolledEvent(attack, 30)
        strategy = ReluctantParryStrategy()
        # test _estimate_damage
        estimated_sw = strategy._estimate_damage(target, event, context)
        self.assertIsInstance(estimated_sw, int)


class TestBaseParryStrategyCanShirk(unittest.TestCase):
    """Test BaseParryStrategy._can_shirk."""

    def test_can_shirk_with_friends(self):
        from simulation.strategies.base import ReluctantParryStrategy
        attacker = Character("Attacker")
        friend1 = Character("Friend1")
        friend2 = Character("Friend2")
        # give both friends actions and initiative
        roll_provider1 = TestRollProvider()
        roll_provider1.put_initiative_roll([1, 2])
        friend1.set_roll_provider(roll_provider1)
        friend1.roll_initiative()
        roll_provider2 = TestRollProvider()
        roll_provider2.put_initiative_roll([1, 2])
        friend2.set_roll_provider(roll_provider2)
        friend2.roll_initiative()
        groups = [Group("Friends", [friend1, friend2]), Group("Attacker", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, friend1, "attack", initiative_action, context)
        attack.set_skill_roll(9001)
        event = events.AttackRolledEvent(attack, 9001)
        strategy = ReluctantParryStrategy()
        # friend2 has an action and is willing to parry, so friend1 can shirk
        can_shirk = strategy._can_shirk(friend1, event, context)
        self.assertTrue(can_shirk)

    def test_cannot_shirk_alone(self):
        from simulation.strategies.base import ReluctantParryStrategy
        attacker = Character("Attacker")
        target = Character("Target")
        roll_provider = TestRollProvider()
        roll_provider.put_initiative_roll([1, 2])
        target.set_roll_provider(roll_provider)
        target.roll_initiative()
        groups = [Group("Target", target), Group("Attacker", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, target, "attack", initiative_action, context)
        attack.set_skill_roll(9001)
        event = events.AttackRolledEvent(attack, 9001)
        strategy = ReluctantParryStrategy()
        # no friends to shirk to
        can_shirk = strategy._can_shirk(target, event, context)
        self.assertFalse(can_shirk)

    def test_cannot_shirk_friends_with_never_parry(self):
        from simulation.strategies.base import ReluctantParryStrategy
        attacker = Character("Attacker")
        friend1 = Character("Friend1")
        friend2 = Character("Friend2")
        # friend2 uses NeverParryStrategy
        friend2.set_parry_strategy(NeverParryStrategy())
        roll_provider1 = TestRollProvider()
        roll_provider1.put_initiative_roll([1, 2])
        friend1.set_roll_provider(roll_provider1)
        friend1.roll_initiative()
        roll_provider2 = TestRollProvider()
        roll_provider2.put_initiative_roll([1, 2])
        friend2.set_roll_provider(roll_provider2)
        friend2.roll_initiative()
        groups = [Group("Friends", [friend1, friend2]), Group("Attacker", attacker)]
        context = EngineContext(groups, round=1, phase=1)
        initiative_action = InitiativeAction([1], 1)
        attack = actions.AttackAction(attacker, friend1, "attack", initiative_action, context)
        attack.set_skill_roll(9001)
        event = events.AttackRolledEvent(attack, 9001)
        strategy = ReluctantParryStrategy()
        # friend2 has NeverParryStrategy, so friend1 can't shirk
        can_shirk = strategy._can_shirk(friend1, event, context)
        self.assertFalse(can_shirk)


class TestReluctantParryShirkAndAlreadyAttempted(unittest.TestCase):
    """Test ReluctantParry edge cases: shirking and parry_attempted."""

    def setUp(self):
        from simulation.strategies.base import ReluctantParryStrategy
        self.attacker = Character("Attacker")
        self.friend1 = Character("Friend1")
        self.friend2 = Character("Friend2")
        # give friends actions and initiative
        roll_provider1 = TestRollProvider()
        roll_provider1.put_initiative_roll([1, 2])
        self.friend1.set_roll_provider(roll_provider1)
        self.friend1.roll_initiative()
        roll_provider2 = TestRollProvider()
        roll_provider2.put_initiative_roll([1, 2])
        self.friend2.set_roll_provider(roll_provider2)
        self.friend2.roll_initiative()
        groups = [Group("Friends", [self.friend1, self.friend2]), Group("Attacker", self.attacker)]
        self.context = EngineContext(groups, round=1, phase=1)
        self.initiative_action = InitiativeAction([1], 1)
        self.strategy = ReluctantParryStrategy()

    def test_shirk_to_friend(self):
        """When a friend can parry, the reluctant character should shirk."""
        self.friend1.take_sw(3)  # make friend1 near defeat
        attack = actions.AttackAction(
            self.attacker, self.friend1, "attack", self.initiative_action, self.context
        )
        attack.set_skill_roll(9001)
        event = events.AttackRolledEvent(attack, 9001)
        responses = list(self.strategy.recommend(self.friend1, event, self.context))
        # friend1 should shirk because friend2 can parry
        self.assertEqual(0, len(responses))

    def test_do_not_parry_when_already_attempted(self):
        """When parry was already attempted, should not parry again."""
        attack = actions.AttackAction(
            self.attacker, self.friend1, "attack", self.initiative_action, self.context
        )
        attack.set_skill_roll(9001)
        attack.set_parry_attempted()  # mark as already attempted
        # make it so friend1 can't shirk (no other friends)
        self.friend2.set_parry_strategy(NeverParryStrategy())
        event = events.AttackRolledEvent(attack, 9001)
        responses = list(self.strategy.recommend(self.friend1, event, self.context))
        # should not parry since it was already attempted
        self.assertEqual(0, len(responses))


if __name__ == "__main__":
    unittest.main()
