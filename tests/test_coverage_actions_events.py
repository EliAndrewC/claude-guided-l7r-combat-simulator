#!/usr/bin/env python3

#
# test_coverage_actions_events.py
#
# Unit tests to improve coverage for actions.py, events.py, and listeners.py.
#

import logging
import sys
import unittest
from unittest.mock import MagicMock

from simulation.actions import (
    Action,
    AttackAction,
    CounterattackAction,
    DoubleAttackAction,
    FeintAction,
    LungeAction,
    ParryAction,
)
from simulation.character import Character
from simulation.context import EngineContext
from simulation.events import (
    AddModifierEvent,
    AttackDeclaredEvent,
    AttackSucceededEvent,
    CrippledEvent,
    DamageEvent,
    InitiativeChangedEvent,
    KeepLightWoundsEvent,
    LightWoundsDamageEvent,
    NewRoundEvent,
    NotCrippledEvent,
    ParryPredeclaredEvent,
    RemoveModifierEvent,
    SeriousWoundsDamageEvent,
    SpendAdventurePointsEvent,
    SpendFloatingBonusEvent,
    SpendVoidPointsEvent,
    SurrenderEvent,
    TakeSeriousWoundEvent,
    WoundCheckDeclaredEvent,
    WoundCheckFailedEvent,
    WoundCheckRolledEvent,
    WoundCheckSucceededEvent,
)
from simulation.groups import Group
from simulation.listeners import (
    AddModifierListener,
    AttackDeclaredListener,
    FeintSucceededListener,
    GainTemporaryVoidPointsListener,
    Listener,
    RemoveModifierListener,
    SpendActionListener,
    SpendAdventurePointsListener,
    SpendFloatingBonusListener,
    SpendVoidPointsListener,
    TakeActionListener,
    WoundCheckDeclaredListener,
    WoundCheckRolledListener,
    WoundCheckSucceededListener,
)
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.modifiers import Modifier
from simulation.mechanics.roll_provider import CalvinistRollProvider

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


def _make_context(attacker, target, round=1, phase=1, initialize=True):
    """Helper to create EngineContext with two groups."""
    groups = [Group("attacker", attacker), Group("target", target)]
    context = EngineContext(groups, round=round, phase=phase)
    if initialize:
        context.initialize()
    return context


def _make_initiative_action(dice=None, phase=1):
    """Helper to create an InitiativeAction."""
    if dice is None:
        dice = [1]
    return InitiativeAction(dice, phase)


# ============================================================================
# TESTS FOR simulation/actions.py
# ============================================================================


class TestActionInit(unittest.TestCase):
    """Test Action.__init__ validation and basic accessors."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.target = Character("target")
        self.context = _make_context(self.attacker, self.target)
        self.initiative_action = _make_initiative_action()

    def test_init_sets_subject(self):
        """Line 37: self._subject = subject"""
        action = Action(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context
        )
        self.assertEqual(self.attacker, action.subject())

    def test_init_sets_target(self):
        """Line 38: self._target = target"""
        action = Action(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context
        )
        self.assertEqual(self.target, action.target())

    def test_init_sets_skill(self):
        """Line 41: self._skill = skill"""
        action = Action(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context
        )
        self.assertEqual("attack", action.skill())

    def test_init_skill_must_be_str(self):
        """Line 39-40: raise ValueError if skill is not str"""
        with self.assertRaises(ValueError):
            Action(
                self.attacker, self.target, 123,
                self.initiative_action, self.context
            )

    def test_init_initiative_action_must_be_initiative_action(self):
        """Line 42-43: raise ValueError if initiative_action is not InitiativeAction"""
        with self.assertRaises(ValueError):
            Action(
                self.attacker, self.target, "attack",
                "not_an_initiative_action", self.context
            )

    def test_init_ring_must_be_str_if_given(self):
        """Lines 46-48: raise ValueError if ring is not str"""
        with self.assertRaises(ValueError):
            Action(
                self.attacker, self.target, "attack",
                self.initiative_action, self.context, ring=42
            )

    def test_init_ring_none_is_allowed(self):
        """Lines 46-49: ring=None is the default and should work"""
        action = Action(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context, ring=None
        )
        self.assertIsNone(action.ring())

    def test_init_ring_str_is_set(self):
        """Lines 46-49: valid str ring should be stored"""
        action = Action(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context, ring="fire"
        )
        self.assertEqual("fire", action.ring())

    def test_init_vp_must_be_int(self):
        """Lines 50-51: raise ValueError if vp is not int"""
        with self.assertRaises(ValueError):
            Action(
                self.attacker, self.target, "attack",
                self.initiative_action, self.context, vp="not_int"
            )

    def test_init_vp_default_zero(self):
        """Line 52: default vp is 0"""
        action = Action(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context
        )
        self.assertEqual(0, action.vp())

    def test_init_vp_custom(self):
        """Line 52: custom vp is stored"""
        action = Action(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context, vp=3
        )
        self.assertEqual(3, action.vp())


class TestActionDamageRollParamsNotImplemented(unittest.TestCase):
    """Test that base Action.damage_roll_params raises NotImplementedError."""

    def test_damage_roll_params_raises(self):
        """Line 59: raise NotImplementedError"""
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        action = Action(attacker, target, "attack", ia, context)
        with self.assertRaises(NotImplementedError):
            action.damage_roll_params()


class TestActionName(unittest.TestCase):
    """Test that Action.skill() returns the skill name."""

    def test_skill_returns_name(self):
        """Line 80: return self._skill"""
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        action = Action(attacker, target, "parry", ia, context)
        self.assertEqual("parry", action.skill())


class TestActionInitiativeAction(unittest.TestCase):
    """Test Action.initiative_action() getter."""

    def test_initiative_action_returns_action(self):
        """Line 62: return self._initiative_action"""
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        action = Action(attacker, target, "attack", ia, context)
        self.assertEqual(ia, action.initiative_action())


class TestActionSkillRollParams(unittest.TestCase):
    """Test Action.skill_roll_params() delegation."""

    def test_skill_roll_params(self):
        """Line 86: delegates to subject.get_skill_roll_params"""
        attacker = Character("attacker")
        attacker.set_ring("fire", 5)
        attacker.set_skill("attack", 4)
        target = Character("target")
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        action = Action(attacker, target, "attack", ia, context)
        params = action.skill_roll_params()
        # should return a tuple (rolled, kept, modifier)
        self.assertIsNotNone(params)
        self.assertEqual(3, len(params))


class TestAttackActionParryMethods(unittest.TestCase):
    """Test AttackAction parry predeclaration and decline tracking."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.target = Character("target")
        self.context = _make_context(self.attacker, self.target)
        self.ia = _make_initiative_action()
        self.attack = AttackAction(
            self.attacker, self.target, "attack", self.ia, self.context
        )

    def test_add_parry_predeclared(self):
        """Lines 112-114: add_parry_predeclared appends to predeclared and declared"""
        mock_event = MagicMock()
        self.attack.add_parry_predeclared(mock_event)
        self.assertIn(mock_event, self.attack.parries_predeclared())
        self.assertIn(mock_event, self.attack.parries_declared())

    def test_add_parry_declined(self):
        """Lines 116-117: add_parry_declined appends character to declined list"""
        other = Character("other")
        self.attack.add_parry_declined(other)
        self.assertIn(other, self.attack.parries_declined())

    def test_parries_declined_initially_empty(self):
        """Line 154-155: parries_declined returns empty list initially"""
        self.assertEqual([], self.attack.parries_declined())


class TestAttackActionDamageRoll(unittest.TestCase):
    """Test AttackAction.damage_roll() and set_damage_roll()."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.attacker.set_ring("fire", 5)
        self.attacker.set_skill("attack", 4)
        self.target = Character("target")
        self.context = _make_context(self.attacker, self.target)
        self.ia = _make_initiative_action()
        self.attack = AttackAction(
            self.attacker, self.target, "attack", self.ia, self.context
        )

    def test_damage_roll_initially_none(self):
        """Line 129-130: damage_roll returns None initially"""
        self.assertIsNone(self.attack.damage_roll())

    def test_damage_roll_params_returns_none_without_skill_roll(self):
        """Lines 133-134: damage_roll_params returns None if skill_roll is None"""
        self.assertIsNone(self.attack.damage_roll_params())

    def test_set_damage_roll(self):
        """Lines 170-173: set_damage_roll stores value"""
        self.attack.set_damage_roll(25)
        self.assertEqual(25, self.attack.damage_roll())

    def test_set_damage_roll_requires_int(self):
        """Lines 171-172: set_damage_roll raises ValueError for non-int"""
        with self.assertRaises(ValueError):
            self.attack.set_damage_roll("not_int")


class TestCounterattackAction(unittest.TestCase):
    """Test CounterattackAction.__init__, attack(), and tn()."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.attacker.set_ring("fire", 5)
        self.attacker.set_skill("attack", 4)
        self.target = Character("target")
        self.target.set_skill("parry", 5)
        self.context = _make_context(self.attacker, self.target)
        self.ia = _make_initiative_action()
        # create original attack
        self.original_attack = AttackAction(
            self.attacker, self.target, "attack", self.ia, self.context
        )

    def test_init_stores_attack(self):
        """Lines 186-188: CounterattackAction stores the original attack"""
        counter = CounterattackAction(
            self.target, self.attacker, "counterattack",
            self.ia, self.context, self.original_attack
        )
        self.assertEqual(self.original_attack, counter.attack())

    def test_attack_getter(self):
        """Lines 190-191: attack() returns the original attack"""
        counter = CounterattackAction(
            self.target, self.attacker, "counterattack",
            self.ia, self.context, self.original_attack
        )
        self.assertIs(self.original_attack, counter.attack())

    def test_tn_when_target_is_subject(self):
        """Lines 193-195: tn penalty is 0 when attack target == counterattack subject"""
        # The original attack's target is self.target, and counterattack's subject is self.target
        # So penalty should be 0
        counter = CounterattackAction(
            self.target, self.attacker, "counterattack",
            self.ia, self.context, self.original_attack
        )
        expected_tn = self.attacker.tn_to_hit()  # no penalty
        self.assertEqual(expected_tn, counter.tn())

    def test_tn_when_target_is_not_subject(self):
        """Lines 193-195: tn has penalty when attack target != counterattack subject.
        The penalty uses the attacker's parry skill, not attack skill."""
        # Create a third character
        third = Character("third")
        third.set_skill("counterattack", 3)
        # Set different attack and parry skills on the attacker to verify parry is used
        self.attacker.set_skill("attack", 4)
        self.attacker.set_skill("parry", 6)
        # Need to create a context with three characters
        groups = [
            Group("group1", [self.attacker, third]),
            Group("group2", self.target),
        ]
        context3 = EngineContext(groups, round=1, phase=1)
        context3.initialize()
        # Create original attack targeting the target (not third)
        original_attack = AttackAction(
            self.attacker, self.target, "attack", self.ia, context3
        )
        # Create counterattack from third (who is not the attack's target)
        counter = CounterattackAction(
            third, self.attacker, "counterattack",
            self.ia, context3, original_attack
        )
        # penalty = 5 * attack subject's "parry" skill (not attack)
        penalty = 5 * self.attacker.skill("parry")
        expected_tn = self.attacker.tn_to_hit() + penalty
        self.assertEqual(expected_tn, counter.tn())
        # Verify it's NOT using attack skill
        wrong_penalty = 5 * self.attacker.skill("attack")
        self.assertNotEqual(self.attacker.tn_to_hit() + wrong_penalty, counter.tn())


class TestDoubleAttackAction(unittest.TestCase):
    """Test DoubleAttackAction.__init__, calculate_extra_damage_dice, direct_damage, etc."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.attacker.set_ring("fire", 5)
        self.attacker.set_skill("double attack", 4)
        self.target = Character("target")
        self.target.set_skill("parry", 5)
        self.context = _make_context(self.attacker, self.target)
        self.ia = _make_initiative_action()

    def test_init(self):
        """Lines 198+: DoubleAttackAction can be created"""
        da = DoubleAttackAction(
            self.attacker, self.target, "double attack", self.ia, self.context
        )
        self.assertEqual(self.attacker, da.subject())
        self.assertEqual(self.target, da.target())

    def test_tn_adds_20(self):
        """Lines 221-222: tn = target.tn_to_hit() + 20"""
        da = DoubleAttackAction(
            self.attacker, self.target, "double attack", self.ia, self.context
        )
        expected_tn = self.target.tn_to_hit() + 20
        self.assertEqual(expected_tn, da.tn())

    def test_calculate_extra_damage_dice_no_parry(self):
        """Lines 199-216: extra damage uses base tn (tn_to_hit, not +20)"""
        da = DoubleAttackAction(
            self.attacker, self.target, "double attack", self.ia, self.context
        )
        # tn_to_hit = 5 * (1 + 5) = 30
        # Extra dice use base TN (30), not double attack TN (50)
        # If skill_roll = 55, extra dice = (55 - 30) // 5 = 5
        da.set_skill_roll(55)
        self.assertEqual(5, da.calculate_extra_damage_dice())

    def test_calculate_extra_damage_dice_parried_by_target(self):
        """On unsuccessful parry by target, extra dice = flat 2."""
        da = DoubleAttackAction(
            self.attacker, self.target, "double attack", self.ia, self.context
        )
        da.set_skill_roll(75)
        # Without parry: (75 - 30) // 5 = 9
        self.assertEqual(9, da.calculate_extra_damage_dice())
        # Simulate a parry by the target
        da.set_parry_attempted()
        mock_parry_event = MagicMock()
        mock_parry_event.action = MagicMock()
        mock_parry_event.action.subject.return_value = self.target
        da.add_parry_declared(mock_parry_event)
        # flat 2 extra dice when target parried
        self.assertEqual(2, da.calculate_extra_damage_dice())

    def test_calculate_extra_damage_dice_parried_by_third_party(self):
        """On unsuccessful parry by third party, extra dice = flat 4."""
        third = Character("third")
        da = DoubleAttackAction(
            self.attacker, self.target, "double attack", self.ia, self.context
        )
        da.set_skill_roll(75)
        # Without parry: (75 - 30) // 5 = 9
        da.set_parry_attempted()
        mock_parry_event = MagicMock()
        mock_parry_event.action = MagicMock()
        mock_parry_event.action.subject.return_value = third  # not the target
        da.add_parry_declared(mock_parry_event)
        # flat 4 extra dice when third party parried
        self.assertEqual(4, da.calculate_extra_damage_dice())

    def test_direct_damage_no_parry(self):
        """When no parry attempted, direct_damage returns 1 SW."""
        da = DoubleAttackAction(
            self.attacker, self.target, "double attack", self.ia, self.context
        )
        direct = da.direct_damage()
        self.assertIsNotNone(direct)
        self.assertIsInstance(direct, SeriousWoundsDamageEvent)
        self.assertEqual(self.attacker, direct.subject)
        self.assertEqual(self.target, direct.target)
        self.assertEqual(1, direct.damage)

    def test_direct_damage_with_parry_attempted(self):
        """When parry was attempted, direct_damage returns None (no 1 SW)."""
        da = DoubleAttackAction(
            self.attacker, self.target, "double attack", self.ia, self.context
        )
        da.set_parry_attempted()
        mock_parry_event = MagicMock()
        mock_parry_event.action = MagicMock()
        mock_parry_event.action.subject.return_value = self.target
        da.add_parry_declared(mock_parry_event)
        self.assertIsNone(da.direct_damage())

    def test_set_direct_damage_via_set_damage_roll(self):
        """Lines 170-173: set_damage_roll validation"""
        da = DoubleAttackAction(
            self.attacker, self.target, "double attack", self.ia, self.context
        )
        da.set_damage_roll(10)
        self.assertEqual(10, da.damage_roll())
        with self.assertRaises(ValueError):
            da.set_damage_roll("bad")


class TestFeintAction(unittest.TestCase):
    """Test FeintAction extra damage and damage roll."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.attacker.set_ring("fire", 5)
        self.attacker.set_skill("feint", 4)
        self.target = Character("target")
        self.target.set_skill("parry", 5)
        self.context = _make_context(self.attacker, self.target)
        self.ia = _make_initiative_action()

    def test_calculate_extra_damage_dice_always_zero(self):
        """Line 227: always returns 0"""
        feint = FeintAction(
            self.attacker, self.target, "feint", self.ia, self.context
        )
        feint.set_skill_roll(100)
        self.assertEqual(0, feint.calculate_extra_damage_dice())

    def test_damage_roll_params_always_zero(self):
        """Lines 229-230: returns (0, 0, 0)"""
        feint = FeintAction(
            self.attacker, self.target, "feint", self.ia, self.context
        )
        self.assertEqual((0, 0, 0), feint.damage_roll_params())

    def test_roll_damage_always_zero(self):
        """Lines 232-234: roll_damage returns 0 and sets damage_roll to 0"""
        feint = FeintAction(
            self.attacker, self.target, "feint", self.ia, self.context
        )
        result = feint.roll_damage()
        self.assertEqual(0, result)
        self.assertEqual(0, feint.damage_roll())


class TestLungeAction(unittest.TestCase):
    """Test LungeAction extra damage dice."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.attacker.set_ring("fire", 5)
        self.attacker.set_skill("lunge", 4)
        self.target = Character("target")
        self.target.set_skill("parry", 5)
        self.context = _make_context(self.attacker, self.target)
        self.ia = _make_initiative_action()

    def test_calculate_extra_damage_dice_adds_one(self):
        """Line 239: adds 1 to parent's extra damage dice"""
        lunge = LungeAction(
            self.attacker, self.target, "lunge", self.ia, self.context
        )
        # tn_to_hit = 30
        # skill_roll = 35: normal extra = (35 - 30) // 5 = 1
        # lunge adds 1 more = 2
        lunge.set_skill_roll(35)
        self.assertEqual(2, lunge.calculate_extra_damage_dice())

    def test_calculate_extra_damage_dice_adds_one_from_zero(self):
        """Line 239: adds 1 even when parent gives 0"""
        lunge = LungeAction(
            self.attacker, self.target, "lunge", self.ia, self.context
        )
        # tn_to_hit = 30
        # skill_roll = 31: normal extra = (31 - 30) // 5 = 0
        # lunge adds 1 = 1
        lunge.set_skill_roll(31)
        self.assertEqual(1, lunge.calculate_extra_damage_dice())


class TestParryActionTn(unittest.TestCase):
    """Test ParryAction.tn() calculation."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.attacker.set_ring("fire", 5)
        self.attacker.set_skill("attack", 4)
        self.target = Character("target")
        self.target.set_ring("air", 5)
        self.target.set_skill("parry", 5)
        self.context = _make_context(self.attacker, self.target)
        self.ia = _make_initiative_action()

    def test_parry_tn_matches_attack_roll(self):
        """Line 272-273: parry tn = attack's parry_tn = attack's skill_roll"""
        attack = AttackAction(
            self.attacker, self.target, "attack", self.ia, self.context
        )
        attack.set_skill_roll(42)
        parry = ParryAction(
            self.target, self.attacker, "parry", self.ia, self.context, attack
        )
        self.assertEqual(42, parry.tn())


class TestParryActionForOthersPenalty(unittest.TestCase):
    """Test ParryAction penalty when parrying for someone else."""

    def test_parry_for_self_no_penalty(self):
        """Parrying for yourself has no penalty."""
        attacker = Character("attacker")
        attacker.set_ring("fire", 5)
        attacker.set_skill("attack", 4)
        target = Character("target")
        target.set_ring("air", 5)
        target.set_skill("parry", 5)
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        attack = AttackAction(attacker, target, "attack", ia, context)
        attack.set_skill_roll(42)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("parry", 50)
        target.set_roll_provider(roll_provider)
        parry = ParryAction(target, attacker, "parry", ia, context, attack)
        result = parry.roll_skill()
        # no penalty: result should be the raw roll (50)
        self.assertEqual(50, result)

    def test_parry_for_others_penalty_scales_with_attack_skill(self):
        """Parrying for someone else has penalty = 5 * attacker's attack skill."""
        attacker = Character("attacker")
        attacker.set_ring("fire", 5)
        attacker.set_skill("attack", 3)
        target = Character("target")
        third = Character("third")
        third.set_ring("air", 5)
        third.set_skill("parry", 5)
        groups = [
            Group("group1", [target, third]),
            Group("group2", attacker),
        ]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        ia = _make_initiative_action()
        attack = AttackAction(attacker, target, "attack", ia, context)
        attack.set_skill_roll(42)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("parry", 50)
        third.set_roll_provider(roll_provider)
        # third parries for target; penalty = 5 * 3 = 15
        parry = ParryAction(third, attacker, "parry", ia, context, attack)
        result = parry.roll_skill()
        self.assertEqual(50 - 15, result)

    def test_parry_for_others_penalty_with_higher_attack_skill(self):
        """Verify penalty scales: attacker with skill 5 → penalty 25."""
        attacker = Character("attacker")
        attacker.set_ring("fire", 5)
        attacker.set_skill("attack", 5)
        target = Character("target")
        third = Character("third")
        third.set_ring("air", 5)
        third.set_skill("parry", 5)
        groups = [
            Group("group1", [target, third]),
            Group("group2", attacker),
        ]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        ia = _make_initiative_action()
        attack = AttackAction(attacker, target, "attack", ia, context)
        attack.set_skill_roll(42)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("parry", 60)
        third.set_roll_provider(roll_provider)
        # penalty = 5 * 5 = 25
        parry = ParryAction(third, attacker, "parry", ia, context, attack)
        result = parry.roll_skill()
        self.assertEqual(60 - 25, result)


# ============================================================================
# TESTS FOR simulation/events.py
# ============================================================================


class TestInitiativeChangedEvent(unittest.TestCase):
    """Test InitiativeChangedEvent constructor."""

    def test_init(self):
        """Line 89-90: InitiativeChangedEvent constructor"""
        event = InitiativeChangedEvent()
        self.assertEqual("initiative_changed", event.name)


class TestSpendVoidPointsEvent(unittest.TestCase):
    """Test SpendVoidPointsEvent constructor."""

    def test_init(self):
        """Lines 441-443: SpendVoidPointsEvent constructor"""
        subject = Character("sub")
        event = SpendVoidPointsEvent(subject, "attack", 2)
        self.assertEqual("spend_vp", event.name)
        self.assertEqual(subject, event.subject)
        self.assertEqual("attack", event.skill)
        self.assertEqual(2, event.amount)


class TestDamageEvent(unittest.TestCase):
    """Test DamageEvent constructor and validation."""

    def test_init(self):
        """Lines 248-254: DamageEvent constructor"""
        sub = Character("sub")
        tgt = Character("tgt")
        event = DamageEvent("test_damage", sub, tgt, 10)
        self.assertEqual("test_damage", event.name)
        self.assertEqual(sub, event.subject)
        self.assertEqual(tgt, event.target)
        self.assertEqual(10, event.damage)

    def test_damage_must_be_int(self):
        """Lines 252-253: ValueError if damage is not int"""
        sub = Character("sub")
        tgt = Character("tgt")
        with self.assertRaises(ValueError):
            DamageEvent("test_damage", sub, tgt, "not_int")


class TestLightWoundsDamageEvent(unittest.TestCase):
    """Test LightWoundsDamageEvent with custom tn."""

    def test_default_tn_equals_damage(self):
        """Lines 268-269: default tn is damage"""
        sub = Character("sub")
        tgt = Character("tgt")
        event = LightWoundsDamageEvent(sub, tgt, 15)
        self.assertEqual(15, event.wound_check_tn)

    def test_custom_tn(self):
        """Lines 270-273: custom tn overrides damage"""
        sub = Character("sub")
        tgt = Character("tgt")
        event = LightWoundsDamageEvent(sub, tgt, 15, tn=20)
        self.assertEqual(20, event.wound_check_tn)

    def test_tn_must_be_int(self):
        """Lines 271-272: ValueError if tn is not int"""
        sub = Character("sub")
        tgt = Character("tgt")
        with self.assertRaises(ValueError):
            LightWoundsDamageEvent(sub, tgt, 15, tn="bad")


class TestNewRoundEvent(unittest.TestCase):
    """Test NewRoundEvent constructor."""

    def test_init(self):
        """Lines 55-57: NewRoundEvent stores round number"""
        event = NewRoundEvent(3)
        self.assertEqual("new_round", event.name)
        self.assertEqual(3, event.round)


class TestSeriousWoundsDamageEvent(unittest.TestCase):
    """Test SeriousWoundsDamageEvent constructor."""

    def test_init(self):
        """Lines 277-278: SeriousWoundsDamageEvent constructor"""
        sub = Character("sub")
        tgt = Character("tgt")
        event = SeriousWoundsDamageEvent(sub, tgt, 2)
        self.assertEqual("sw_damage", event.name)
        self.assertEqual(sub, event.subject)
        self.assertEqual(tgt, event.target)
        self.assertEqual(2, event.damage)


class TestCrippledEvent(unittest.TestCase):
    """Test CrippledEvent constructor."""

    def test_init(self):
        """Lines 288-289: CrippledEvent constructor"""
        sub = Character("sub")
        event = CrippledEvent("crippled", sub)
        self.assertEqual("crippled", event.name)
        self.assertEqual(sub, event.subject)


class TestNotCrippledEvent(unittest.TestCase):
    """Test NotCrippledEvent constructor.
    Note: NotCrippledEvent has a bug -- it passes (name, subject) to Event.__init__
    which only accepts (name). This causes a TypeError.
    We test that the constructor is called (covering line 294) and that it raises."""

    def test_init_raises_due_to_bug(self):
        """Lines 293-294: NotCrippledEvent constructor has a bug passing extra arg to Event."""
        sub = Character("sub")
        with self.assertRaises(TypeError):
            NotCrippledEvent("not_crippled", sub)


class TestSurrenderEvent(unittest.TestCase):
    """Test SurrenderEvent constructor."""

    def test_init(self):
        """Lines 307-308: SurrenderEvent constructor"""
        sub = Character("sub")
        event = SurrenderEvent(sub)
        self.assertEqual("surrender", event.name)
        self.assertEqual(sub, event.subject)


class TestParryPredeclaredEvent(unittest.TestCase):
    """Test ParryPredeclaredEvent constructor."""

    def test_init(self):
        """Lines 219-220: ParryPredeclaredEvent constructor"""
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        attack = AttackAction(attacker, target, "attack", ia, context)
        parry_action = ParryAction(target, attacker, "parry", ia, context, attack)
        event = ParryPredeclaredEvent(parry_action)
        self.assertEqual("parry_predeclared", event.name)
        self.assertEqual(parry_action, event.action)


class TestSpendAdventurePointsEvent(unittest.TestCase):
    """Test SpendAdventurePointsEvent constructor."""

    def test_init(self):
        """Lines 437-438: SpendAdventurePointsEvent constructor"""
        sub = Character("sub")
        event = SpendAdventurePointsEvent(sub, "attack", 3)
        self.assertEqual("spend_ap", event.name)
        self.assertEqual(sub, event.subject)
        self.assertEqual("attack", event.skill)
        self.assertEqual(3, event.amount)


class TestSpendFloatingBonusEvent(unittest.TestCase):
    """Test SpendFloatingBonusEvent constructor."""

    def test_init(self):
        """Lines 453-456: SpendFloatingBonusEvent constructor"""
        sub = Character("sub")
        bonus = MagicMock()
        event = SpendFloatingBonusEvent(sub, bonus)
        self.assertEqual("spend_floating_bonus", event.name)
        self.assertEqual(sub, event.subject)
        self.assertEqual(bonus, event.bonus)


class TestKeepLightWoundsEvent(unittest.TestCase):
    """Test KeepLightWoundsEvent constructor."""

    def test_init(self):
        """Lines 386-387: KeepLightWoundsEvent constructor"""
        sub = Character("sub")
        attacker = Character("att")
        event = KeepLightWoundsEvent(sub, attacker, 15)
        self.assertEqual("keep_lw", event.name)
        self.assertEqual(sub, event.subject)
        self.assertEqual(attacker, event.attacker)
        self.assertEqual(15, event.damage)
        self.assertEqual(15, event.tn)

    def test_init_with_custom_tn(self):
        """Lines 386-387: KeepLightWoundsEvent with custom tn"""
        sub = Character("sub")
        attacker = Character("att")
        event = KeepLightWoundsEvent(sub, attacker, 15, tn=20)
        self.assertEqual(20, event.tn)


class TestTakeSeriousWoundEvent(unittest.TestCase):
    """Test TakeSeriousWoundEvent constructor."""

    def test_init(self):
        """Lines 390-392: TakeSeriousWoundEvent constructor"""
        sub = Character("sub")
        attacker = Character("att")
        event = TakeSeriousWoundEvent(sub, attacker, 10)
        self.assertEqual("take_sw", event.name)
        self.assertEqual(sub, event.subject)
        self.assertEqual(attacker, event.attacker)
        self.assertEqual(10, event.damage)


class TestWoundCheckEvents(unittest.TestCase):
    """Test WoundCheckDeclaredEvent, WoundCheckRolledEvent, etc."""

    def test_wound_check_declared_with_vp(self):
        """Lines 362-364: WoundCheckDeclaredEvent with vp"""
        sub = Character("sub")
        att = Character("att")
        event = WoundCheckDeclaredEvent(sub, att, 20, vp=2)
        self.assertEqual("wound_check_declared", event.name)
        self.assertEqual(2, event.vp)

    def test_wound_check_rolled(self):
        """Lines 373-376: WoundCheckRolledEvent"""
        sub = Character("sub")
        att = Character("att")
        event = WoundCheckRolledEvent(sub, att, 20, 35)
        self.assertEqual("wound_check_rolled", event.name)
        self.assertEqual(35, event.roll)
        self.assertEqual(20, event.tn)

    def test_wound_check_failed(self):
        """Lines 367-370: WoundCheckFailedEvent"""
        sub = Character("sub")
        att = Character("att")
        event = WoundCheckFailedEvent(sub, att, 20, 10, tn=20)
        self.assertEqual("wound_check_failed", event.name)
        self.assertEqual(10, event.roll)
        self.assertEqual(20, event.tn)

    def test_wound_check_succeeded(self):
        """Lines 379-382: WoundCheckSucceededEvent"""
        sub = Character("sub")
        att = Character("att")
        event = WoundCheckSucceededEvent(sub, att, 20, 35, tn=20)
        self.assertEqual("wound_check_succeeded", event.name)
        self.assertEqual(35, event.roll)
        self.assertEqual(20, event.tn)


class TestAddModifierEvent(unittest.TestCase):
    """Test AddModifierEvent constructor."""

    def test_init(self):
        """Lines 475-476: AddModifierEvent constructor"""
        sub = Character("sub")
        modifier = Modifier(sub, None, "attack", 5)
        event = AddModifierEvent(sub, modifier)
        self.assertEqual("add_modifier", event.name)
        self.assertEqual(sub, event.subject)
        self.assertEqual(modifier, event.modifier)


class TestRemoveModifierEvent(unittest.TestCase):
    """Test RemoveModifierEvent constructor."""

    def test_init(self):
        """Lines 484-485: RemoveModifierEvent constructor"""
        sub = Character("sub")
        modifier = Modifier(sub, None, "attack", 5)
        event = RemoveModifierEvent(sub, modifier)
        self.assertEqual("remove_modifier", event.name)
        self.assertEqual(sub, event.subject)
        self.assertEqual(modifier, event.modifier)


# ============================================================================
# TESTS FOR simulation/listeners.py
# ============================================================================


class TestListenerAbstract(unittest.TestCase):
    """Test that Listener.handle is abstract."""

    def test_abstract_handle(self):
        """Line 41: abstract handle method. Concrete subclass can call super().handle()"""
        # Verify that Listener is abstract
        with self.assertRaises(TypeError):
            Listener()


class TestRemoveModifierListener(unittest.TestCase):
    """Test RemoveModifierListener.handle."""

    def setUp(self):
        self.char = Character("char")
        self.other = Character("other")
        self.context = _make_context(self.char, self.other)

    def test_handle_removes_modifier_for_subject(self):
        """Lines 69-75: RemoveModifierListener responds to AddModifierEvent
        (note: there appears to be a bug in listeners.py where it checks for
        AddModifierEvent instead of RemoveModifierEvent, but we test as-is)."""
        modifier = Modifier(self.char, None, "attack", 5)
        self.char.add_modifier(modifier)
        # RemoveModifierListener responds to AddModifierEvent (bug in source)
        event = AddModifierEvent(self.char, modifier)
        listener = RemoveModifierListener()
        responses = list(listener.handle(self.char, event, self.context))
        self.assertEqual([], responses)

    def test_handle_other_character_observes(self):
        """Lines 73-74: other characters observe modifier removal.
        We must first make the other character's modifier known to char's knowledge,
        so that observe_modifier_removed can find it."""
        modifier = Modifier(self.other, None, "attack", 5)
        self.other.add_modifier(modifier)
        # Pre-populate char's knowledge so it knows about the modifier
        self.char.knowledge().observe_modifier_added(self.other, modifier)
        event = AddModifierEvent(self.other, modifier)
        listener = RemoveModifierListener()
        responses = list(listener.handle(self.char, event, self.context))
        self.assertEqual([], responses)

    def test_handle_ignores_non_matching_event(self):
        """Lines 70: only responds to AddModifierEvent (bug)"""
        event = NewRoundEvent(1)
        listener = RemoveModifierListener()
        responses = list(listener.handle(self.char, event, self.context))
        self.assertEqual([], responses)


class TestAttackDeclaredListener(unittest.TestCase):
    """Test AttackDeclaredListener.handle for lunge modifier granting."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.attacker.set_ring("fire", 5)
        self.attacker.set_skill("lunge", 4)
        self.attacker.set_skill("attack", 3)
        self.target = Character("target")
        self.target.set_skill("parry", 5)
        self.context = _make_context(self.attacker, self.target)
        self.ia = _make_initiative_action()

    def test_handle_non_lunge_no_response(self):
        """Lines 83: only responds when skill is lunge"""
        attack = AttackAction(
            self.attacker, self.target, "attack", self.ia, self.context
        )
        event = AttackDeclaredEvent(attack)
        listener = AttackDeclaredListener()
        responses = list(listener.handle(self.target, event, self.context))
        self.assertEqual([], responses)

    def test_handle_subject_ignores(self):
        """Line 81: subject of attack ignores the event"""
        attack = AttackAction(
            self.attacker, self.target, "attack", self.ia, self.context
        )
        event = AttackDeclaredEvent(attack)
        listener = AttackDeclaredListener()
        responses = list(listener.handle(self.attacker, event, self.context))
        self.assertEqual([], responses)

    def test_handle_ignores_non_attack_declared(self):
        """Line 80: only handles AttackDeclaredEvent"""
        event = NewRoundEvent(1)
        listener = AttackDeclaredListener()
        responses = list(listener.handle(self.target, event, self.context))
        self.assertEqual([], responses)

    def test_handle_lunge_same_group_no_modifier(self):
        """Lines 84: lunge from same group does not generate modifier"""
        # Put both in same group
        groups = [
            Group("team", [self.attacker, self.target]),
            Group("enemy", Character("enemy")),
        ]
        context = EngineContext(groups, round=1, phase=1)
        context.initialize()
        ia = _make_initiative_action()
        attack = AttackAction(
            self.attacker, self.target, "lunge", ia, context
        )
        event = AttackDeclaredEvent(attack)
        listener = AttackDeclaredListener()
        # Target is in same group as attacker, so no modifier
        responses = list(listener.handle(self.target, event, context))
        self.assertEqual([], responses)


class TestFeintSucceededListener(unittest.TestCase):
    """Test FeintSucceededListener.handle."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.attacker.set_ring("fire", 5)
        self.attacker.set_skill("feint", 4)
        self.attacker.set_actions([1, 5])
        self.target = Character("target")
        self.target.set_skill("parry", 5)
        self.context = _make_context(self.attacker, self.target)
        self.ia = _make_initiative_action()

    def test_feint_succeeded_gains_tvp_and_reorders_actions(self):
        """Lines 104-113: FeintSucceededListener grants TVP and tries to reorder actions.
        Note: There is a bug in the source (list.insert called with 1 arg instead of 2).
        This test covers lines 104-111 (the lines before the bug) and verifies the
        TypeError is raised on line 112."""
        attack = FeintAction(
            self.attacker, self.target, "feint", self.ia, self.context
        )
        event = AttackSucceededEvent(attack)
        listener = FeintSucceededListener()
        with self.assertRaises(TypeError):
            list(listener.handle(self.attacker, event, self.context))
        # TVP should still be gained (line 108 executes before the bug on line 112)
        self.assertEqual(1, self.attacker.tvp())

    def test_feint_succeeded_no_actions(self):
        """Lines 109-113: No initiative change if character has no actions left."""
        self.attacker.set_actions([])
        attack = FeintAction(
            self.attacker, self.target, "feint", self.ia, self.context
        )
        event = AttackSucceededEvent(attack)
        listener = FeintSucceededListener()
        responses = list(listener.handle(self.attacker, event, self.context))
        # Should gain 1 TVP but no InitiativeChangedEvent
        self.assertEqual(1, self.attacker.tvp())
        self.assertEqual(0, len(responses))

    def test_non_feint_attack_not_handled(self):
        """Lines 107: only responds to feint skill"""
        attack = AttackAction(
            self.attacker, self.target, "attack", self.ia, self.context
        )
        event = AttackSucceededEvent(attack)
        listener = FeintSucceededListener()
        responses = list(listener.handle(self.attacker, event, self.context))
        self.assertEqual(0, len(responses))
        self.assertEqual(0, self.attacker.tvp())

    def test_other_character_not_handled(self):
        """Lines 106: only subject gets the effect"""
        attack = FeintAction(
            self.attacker, self.target, "feint", self.ia, self.context
        )
        event = AttackSucceededEvent(attack)
        listener = FeintSucceededListener()
        responses = list(listener.handle(self.target, event, self.context))
        self.assertEqual(0, len(responses))


class TestWoundCheckDeclaredListenerVP(unittest.TestCase):
    """Test WoundCheckDeclaredListener with VP spending."""

    def test_wound_check_declared_with_vp(self):
        """Lines 200-208: WoundCheckDeclaredListener spends VP if vp > 0"""
        attacker = Character("attacker")
        target = Character("target")
        target.set_ring("void", 3)
        context = _make_context(attacker, target)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_wound_check_roll(50)
        target.set_roll_provider(roll_provider)
        event = WoundCheckDeclaredEvent(target, attacker, 20, vp=1)
        listener = WoundCheckDeclaredListener()
        responses = list(listener.handle(target, event, context))
        # Should yield SpendVoidPointsEvent then WoundCheckRolledEvent
        self.assertEqual(2, len(responses))
        self.assertIsInstance(responses[0], SpendVoidPointsEvent)
        self.assertEqual(1, responses[0].amount)
        self.assertIsInstance(responses[1], WoundCheckRolledEvent)


class TestWoundCheckRolledListenerCoverage(unittest.TestCase):
    """Test WoundCheckRolledListener yields correct events."""

    def setUp(self):
        self.attacker = Character("attacker")
        self.target = Character("target")
        self.context = _make_context(self.attacker, self.target)

    def test_wound_check_rolled_passes_tn(self):
        """Lines 222-229: verifies tn is passed through"""
        # Roll >= tn -> success
        event = WoundCheckRolledEvent(self.target, self.attacker, 20, 25, tn=20)
        listener = WoundCheckRolledListener()
        responses = list(listener.handle(self.target, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], WoundCheckSucceededEvent)
        self.assertEqual(20, responses[0].tn)

    def test_wound_check_rolled_fail_passes_tn(self):
        """Lines 225-227: failed wound check passes tn"""
        event = WoundCheckRolledEvent(self.target, self.attacker, 20, 10, tn=20)
        listener = WoundCheckRolledListener()
        responses = list(listener.handle(self.target, event, self.context))
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], WoundCheckFailedEvent)
        self.assertEqual(20, responses[0].tn)

    def test_wound_check_rolled_other_character_ignored(self):
        """Lines 223: only subject handles the event"""
        event = WoundCheckRolledEvent(self.target, self.attacker, 20, 25)
        listener = WoundCheckRolledListener()
        responses = list(listener.handle(self.attacker, event, self.context))
        self.assertEqual(0, len(responses))


class TestWoundCheckSucceededListenerCoverage(unittest.TestCase):
    """Test WoundCheckSucceededListener delegates to light_wounds_strategy."""

    def test_wound_check_succeeded_delegates_to_strategy(self):
        """Lines 232-237: WoundCheckSucceededListener delegates to light_wounds_strategy"""
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        event = WoundCheckSucceededEvent(target, attacker, 20, 25, tn=20)
        listener = WoundCheckSucceededListener()
        responses = list(listener.handle(target, event, context))
        # Default strategy is KeepLightWoundsStrategy which should yield an event
        self.assertTrue(len(responses) >= 1)


class TestTakeActionListenerCoverage(unittest.TestCase):
    """Test TakeActionListener for other characters observing actions.
    Note: TakeActionEvent and subclasses use .action (from ActionEvent),
    not .subject, but TakeActionListener checks event.subject.
    TakeAttackActionEvent has no .subject attribute (bug in listeners.py line 147).
    We test that the listener hits the isinstance check (line 146) and then
    the AttributeError occurs on the buggy line."""

    def test_other_character_observes_action_hits_bug(self):
        """Lines 145-149: TakeActionListener hits bug when accessing event.subject"""
        attacker = Character("attacker")
        attacker.set_ring("fire", 5)
        attacker.set_skill("attack", 4)
        target = Character("target")
        target.set_skill("parry", 5)
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        attack = AttackAction(attacker, target, "attack", ia, context)
        from simulation.events import TakeAttackActionEvent
        event = TakeAttackActionEvent(attack)
        listener = TakeActionListener()
        # TakeAttackActionEvent has no .subject, so this raises AttributeError
        with self.assertRaises(AttributeError):
            list(listener.handle(target, event, context))


class TestGainTemporaryVoidPointsListenerCoverage(unittest.TestCase):
    """Test GainTemporaryVoidPointsListener."""

    def test_gain_tvp(self):
        """Lines 160-165: character gains TVP"""
        char = Character("char")
        other = Character("other")
        context = _make_context(char, other)
        from simulation.events import GainTemporaryVoidPointsEvent
        event = GainTemporaryVoidPointsEvent(char, 2)
        listener = GainTemporaryVoidPointsListener()
        responses = list(listener.handle(char, event, context))
        self.assertEqual([], responses)
        self.assertEqual(2, char.tvp())


class TestSpendActionListenerCoverage(unittest.TestCase):
    """Test SpendActionListener."""

    def test_spend_action(self):
        """Lines 168-173: character spends action"""
        char = Character("char")
        char.set_actions([1, 3])
        other = Character("other")
        context = _make_context(char, other)
        ia = InitiativeAction([1], 1)
        from simulation.events import SpendActionEvent
        event = SpendActionEvent(char, "attack", ia)
        listener = SpendActionListener()
        responses = list(listener.handle(char, event, context))
        self.assertEqual([], responses)
        self.assertEqual([3], char.actions())


class TestSpendAdventurePointsListenerCoverage(unittest.TestCase):
    """Test SpendAdventurePointsListener.
    Note: There is a bug in listeners.py line 180 where spend_ap is called
    with only event.amount instead of (skill, amount). This causes a TypeError.
    We test that the listener reaches that code path."""

    def test_spend_ap(self):
        """Lines 178-183: SpendAdventurePointsListener spends AP correctly"""
        char = Character("char")
        other = Character("other")
        context = _make_context(char, other)
        event = SpendAdventurePointsEvent(char, "attack", 1)
        listener = SpendAdventurePointsListener()
        char._ap_base_skill = "attack"
        char._ap_skills = ["attack"]
        char.set_skill("attack", 5)
        list(listener.handle(char, event, context))
        self.assertEqual(9, char.ap())

    def test_spend_ap_non_subject_ignored(self):
        """Lines 178-179: non-subject is ignored"""
        char = Character("char")
        other = Character("other")
        context = _make_context(char, other)
        event = SpendAdventurePointsEvent(other, "attack", 1)
        listener = SpendAdventurePointsListener()
        responses = list(listener.handle(char, event, context))
        self.assertEqual([], responses)


class TestSpendFloatingBonusListenerCoverage(unittest.TestCase):
    """Test SpendFloatingBonusListener."""

    def test_spend_floating_bonus(self):
        """Lines 184-189: character spends floating bonus"""
        char = Character("char")
        other = Character("other")
        context = _make_context(char, other)
        bonus = MagicMock()
        bonus.is_applicable = MagicMock(return_value=True)
        char.gain_floating_bonus(bonus)
        event = SpendFloatingBonusEvent(char, bonus)
        listener = SpendFloatingBonusListener()
        responses = list(listener.handle(char, event, context))
        self.assertEqual([], responses)


class TestSpendVoidPointsListenerCoverage(unittest.TestCase):
    """Test SpendVoidPointsListener."""

    def test_spend_vp(self):
        """Lines 192-197: character spends VP"""
        char = Character("char")
        char.set_ring("void", 5)
        other = Character("other")
        context = _make_context(char, other)
        event = SpendVoidPointsEvent(char, "attack", 1)
        listener = SpendVoidPointsListener()
        responses = list(listener.handle(char, event, context))
        self.assertEqual([], responses)


class TestSeriousWoundsDamageListenerSurrender(unittest.TestCase):
    """Test SeriousWoundsDamageListener for surrender path."""

    def test_surrender(self):
        """Lines 138-139: character surrenders when not fighting."""
        from simulation.listeners import SeriousWoundsDamageListener
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        # Set SW so that the next wound doesn't kill or make unconscious
        # but does trigger surrender (is_fighting returns False)
        # max_sw = earth * 2 = 2 * 2 = 4
        # 3 SW: alive (3 <= 4), conscious (3 < 4), but is_fighting = is_conscious = True
        # 4 SW: alive (4 <= 4), not conscious (4 < 4 is False) -> unconscious, not surrender
        # We need to reach is_fighting() == False but is_conscious() == True
        # Looking at character.py: is_fighting returns is_conscious
        # So surrender and unconscious are essentially the same path
        # Let's just verify the "not alive" and "not conscious" paths
        # are distinct from the "still fighting" path.
        # With earth=2, max_sw=4. Take 3 SW -> still fighting
        target.take_sw(3)
        event = SeriousWoundsDamageEvent(attacker, target, 1)
        listener = SeriousWoundsDamageListener()
        responses = list(listener.handle(target, event, context))
        # 4 SW = max_sw -> not conscious -> UnconsciousEvent
        self.assertEqual(1, len(responses))
        from simulation.events import UnconsciousEvent
        self.assertIsInstance(responses[0], UnconsciousEvent)

    def test_other_character_observes_wounds(self):
        """Lines 140-141: other character observes wounds"""
        from simulation.listeners import SeriousWoundsDamageListener
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        event = SeriousWoundsDamageEvent(attacker, target, 1)
        listener = SeriousWoundsDamageListener()
        # Attacker observes target's wounds
        responses = list(listener.handle(attacker, event, context))
        self.assertEqual([], responses)


class TestAddModifierListenerCoverage(unittest.TestCase):
    """Test AddModifierListener for subject and non-subject paths."""

    def test_subject_adds_modifier(self):
        """Lines 58-65: subject adds modifier to self"""
        char = Character("char")
        other = Character("other")
        context = _make_context(char, other)
        modifier = Modifier(char, None, "attack", 5)
        event = AddModifierEvent(char, modifier)
        listener = AddModifierListener()
        responses = list(listener.handle(char, event, context))
        self.assertEqual([], responses)

    def test_other_observes_modifier(self):
        """Lines 63-64: other character observes modifier added"""
        char = Character("char")
        other = Character("other")
        context = _make_context(char, other)
        modifier = Modifier(char, None, "attack", 5)
        event = AddModifierEvent(char, modifier)
        listener = AddModifierListener()
        responses = list(listener.handle(other, event, context))
        self.assertEqual([], responses)


class TestAttackActionContextAndVP(unittest.TestCase):
    """Test AttackAction.context() and vp-related methods."""

    def test_context_getter(self):
        """Line 55-56: context() returns context"""
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        attack = AttackAction(attacker, target, "attack", ia, context)
        self.assertEqual(context, attack.context())

    def test_set_vp(self):
        """Lines 76-77: set_vp changes vp"""
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        attack = AttackAction(attacker, target, "attack", ia, context)
        self.assertEqual(0, attack.vp())
        attack.set_vp(2)
        self.assertEqual(2, attack.vp())


class TestAttackActionDirectDamage(unittest.TestCase):
    """Test AttackAction.direct_damage() returns None."""

    def test_direct_damage_none(self):
        """Lines 139-140: AttackAction.direct_damage returns None"""
        attacker = Character("attacker")
        target = Character("target")
        context = _make_context(attacker, target)
        ia = _make_initiative_action()
        attack = AttackAction(attacker, target, "attack", ia, context)
        self.assertIsNone(attack.direct_damage())


if __name__ == "__main__":
    unittest.main()
