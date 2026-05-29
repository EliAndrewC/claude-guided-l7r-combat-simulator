#!/usr/bin/env python3

#
# test_courtier_school.py
#
# Unit tests for the Courtier School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.schools import courtier_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestCourtierSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = courtier_school.CourtierSchool()
        self.assertEqual("Courtier School", school.name())

    def test_extra_rolled(self):
        school = courtier_school.CourtierSchool()
        self.assertEqual(["manipulation", "tact", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = courtier_school.CourtierSchool()
        self.assertEqual("air", school.school_ring())

    def test_school_knacks(self):
        school = courtier_school.CourtierSchool()
        self.assertEqual(["discern honor", "oppose social", "worldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        school = courtier_school.CourtierSchool()
        self.assertEqual(["manipulation"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = courtier_school.CourtierSchool()
        self.assertEqual("tact", school.ap_base_skill())

    def test_ap_skills(self):
        school = courtier_school.CourtierSchool()
        self.assertEqual(["attack", "wound check"], school.ap_skills())


class TestCourtierSpecialAbility(unittest.TestCase):
    def test_air_added_to_attack_roll(self):
        courtier = Character("Courtier")
        courtier.set_ring("air", 4)
        target = Character("Target")
        school = courtier_school.CourtierSchool()
        school.apply_special_ability(courtier)
        # Attack roll should get +Air modifier
        provider = courtier.roll_parameter_provider()
        rolled, kept, modifier = provider.get_skill_roll_params(courtier, target, "attack")
        # Base attack: skill(attack) + ring rolled, ring kept, 0 modifier
        # With special: modifier += Air (4)
        self.assertEqual(4, modifier)

    def test_air_added_to_damage_roll(self):
        courtier = Character("Courtier")
        courtier.set_ring("air", 3)
        target = Character("Target")
        school = courtier_school.CourtierSchool()
        school.apply_special_ability(courtier)
        provider = courtier.roll_parameter_provider()
        rolled, kept, modifier = provider.get_damage_roll_params(courtier, target, "attack", 0)
        # Damage modifier should include Air
        self.assertEqual(3, modifier)

    def test_no_bonus_on_non_attack(self):
        courtier = Character("Courtier")
        courtier.set_ring("air", 4)
        target = Character("Target")
        school = courtier_school.CourtierSchool()
        school.apply_special_ability(courtier)
        provider = courtier.roll_parameter_provider()
        rolled, kept, modifier = provider.get_skill_roll_params(courtier, target, "parry")
        # Non-attack skill should not get Air bonus from special ability
        self.assertEqual(0, modifier)


class TestCourtierAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        courtier = Character("Courtier")
        courtier.set_skill("tact", 5)
        school = courtier_school.CourtierSchool()
        school.apply_rank_three_ability(courtier)
        self.assertEqual("tact", courtier.ap_base_skill())
        self.assertTrue(courtier.can_spend_ap("attack"))
        self.assertTrue(courtier.can_spend_ap("wound check"))
        self.assertFalse(courtier.can_spend_ap("parry"))
        # AP = 2 * tact skill = 10
        self.assertEqual(10, courtier.ap())


class TestCourtierFourthDan(unittest.TestCase):
    def setUp(self):
        self.courtier = Character("Courtier")
        self.target = Character("Target")
        groups = [Group("Courtier", self.courtier), Group("Target", self.target)]
        self.context = EngineContext(groups)

    def test_tvp_on_attack_succeeded(self):
        school = courtier_school.CourtierSchool()
        school.apply_rank_four_ability(self.courtier)

        # Create a mock action for AttackSucceededEvent
        class MockAction:
            def __init__(self, subject, target):
                self._subject = subject
                self._target = target

            def subject(self):
                return self._subject

            def target(self):
                return self._target

        action = MockAction(self.courtier, self.target)
        event = events.AttackSucceededEvent(action)
        listener = self.courtier._listeners["attack_succeeded"]
        responses = list(listener.handle(self.courtier, event, self.context))
        # Should yield GainTemporaryVoidPointsEvent
        self.assertEqual(1, len(responses))
        self.assertIsInstance(responses[0], events.GainTemporaryVoidPointsEvent)
        self.assertEqual(1, responses[0].amount)

    def test_tvp_only_once_per_target(self):
        school = courtier_school.CourtierSchool()
        school.apply_rank_four_ability(self.courtier)

        class MockAction:
            def __init__(self, subject, target):
                self._subject = subject
                self._target = target

            def subject(self):
                return self._subject

            def target(self):
                return self._target

        action = MockAction(self.courtier, self.target)
        event = events.AttackSucceededEvent(action)
        listener = self.courtier._listeners["attack_succeeded"]
        # First attack: should trigger TVP
        responses = list(listener.handle(self.courtier, event, self.context))
        self.assertEqual(1, len(responses))
        # Second attack on same target: should NOT trigger TVP
        responses = list(listener.handle(self.courtier, event, self.context))
        self.assertEqual(0, len(responses))


class TestCourtierFifthDan(unittest.TestCase):
    def test_air_added_to_all_skill_rolls(self):
        courtier = Character("Courtier")
        courtier.set_ring("air", 4)
        target = Character("Target")
        school = courtier_school.CourtierSchool()
        school.apply_special_ability(courtier)
        school.apply_rank_five_ability(courtier)
        provider = courtier.roll_parameter_provider()
        # Attack: special Air + 5th Dan Air = 2*Air = 8
        _, _, modifier = provider.get_skill_roll_params(courtier, target, "attack")
        self.assertEqual(8, modifier)
        # Non-attack skill: 5th Dan Air only = 4
        _, _, modifier = provider.get_skill_roll_params(courtier, target, "parry")
        self.assertEqual(4, modifier)

    def test_air_added_to_wound_check(self):
        courtier = Character("Courtier")
        courtier.set_ring("air", 3)
        school = courtier_school.CourtierSchool()
        school.apply_rank_five_ability(courtier)
        provider = courtier.roll_parameter_provider()
        _, _, modifier = provider.get_wound_check_roll_params(courtier)
        self.assertEqual(3, modifier)


class TestCourtierFourthDanResetBetweenFights(unittest.TestCase):
    """Spec 026 Q2 MINOR fix: rules text "once per target per
    conversation or **fight**" requires the once-per-target set to
    reset between fights. Implemented via ``CourtierNewRoundListener``
    which resets the AttackSucceededListener's set on round==1
    (start of a new combat)."""

    def setUp(self):
        self.courtier = Character("Courtier")
        self.target = Character("Target")
        groups = [
            Group("Courtier", self.courtier),
            Group("Target", self.target),
        ]
        self.context = EngineContext(groups)
        school = courtier_school.CourtierSchool()
        school.apply_rank_four_ability(self.courtier)

    def test_tvp_resets_at_new_fight(self):
        """First fight: TVP fires on first attack vs target. Second
        fight (round==1): the once-per-target set MUST reset so TVP
        fires again."""

        class MockAction:
            def __init__(self, subject, target):
                self._subject = subject
                self._target = target

            def subject(self):
                return self._subject

            def target(self):
                return self._target

        action = MockAction(self.courtier, self.target)
        attack_event = events.AttackSucceededEvent(action)
        attack_listener = self.courtier._listeners["attack_succeeded"]
        # First fight, first attack: TVP fires.
        responses = list(attack_listener.handle(self.courtier, attack_event, self.context))
        self.assertEqual(1, len(responses))
        # First fight, second attack (same target): NO TVP.
        responses2 = list(attack_listener.handle(self.courtier, attack_event, self.context))
        self.assertEqual(0, len(responses2))
        # Start of second fight: NewRoundEvent with round==1.
        new_round_listener = self.courtier._listeners["new_round"]
        # Stub roll_initiative to avoid needing a roll provider.
        self.courtier.roll_initiative = lambda: None
        list(new_round_listener.handle(
            self.courtier, events.NewRoundEvent(1), self.context,
        ))
        # Second fight, first attack: TVP fires AGAIN (set was reset).
        responses3 = list(attack_listener.handle(self.courtier, attack_event, self.context))
        self.assertEqual(1, len(responses3))
        # Trace attribution tag.
        self.assertTrue(getattr(responses3[0], "_courtier_4th_dan", False))

    def test_round_2_plus_does_not_reset(self):
        """Mid-combat rounds (round > 1) MUST NOT reset the set —
        otherwise the once-per-target gate would be once-per-target-
        per-round which is wrong."""

        class MockAction:
            def __init__(self, subject, target):
                self._subject = subject
                self._target = target

            def subject(self):
                return self._subject

            def target(self):
                return self._target

        action = MockAction(self.courtier, self.target)
        attack_event = events.AttackSucceededEvent(action)
        attack_listener = self.courtier._listeners["attack_succeeded"]
        new_round_listener = self.courtier._listeners["new_round"]
        self.courtier.roll_initiative = lambda: None
        # First attack of round 1: fires.
        list(attack_listener.handle(self.courtier, attack_event, self.context))
        # NewRoundEvent for round 2.
        list(new_round_listener.handle(
            self.courtier, events.NewRoundEvent(2), self.context,
        ))
        # Round 2 attack on same target: must NOT fire (still gated).
        responses = list(attack_listener.handle(self.courtier, attack_event, self.context))
        self.assertEqual(0, len(responses))
