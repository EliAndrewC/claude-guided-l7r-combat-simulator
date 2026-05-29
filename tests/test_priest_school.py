#!/usr/bin/env python3

#
# test_priest_school.py
#
# Unit tests for the Priest School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import priest_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestPriestSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = priest_school.PriestSchool()
        self.assertEqual("Priest School", school.name())

    def test_extra_rolled(self):
        school = priest_school.PriestSchool()
        self.assertEqual(["precepts", "initiative", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = priest_school.PriestSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = priest_school.PriestSchool()
        self.assertEqual(["conviction", "otherworldliness", "pontificate"], school.school_knacks())

    def test_free_raise_skills(self):
        school = priest_school.PriestSchool()
        self.assertEqual(["bragging", "precepts", "sincerity"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = priest_school.PriestSchool()
        self.assertIsNone(school.ap_base_skill())


class TestPriestSpecialAbility(unittest.TestCase):
    def test_no_combat_effect(self):
        priest = Character("Priest")
        school = priest_school.PriestSchool()
        # apply_special_ability should be a no-op
        school.apply_special_ability(priest)
        # Character state unchanged
        self.assertEqual(0, priest.extra_rolled("attack"))
        self.assertEqual(0, priest.extra_kept("attack"))


class TestPriestThirdDan(unittest.TestCase):
    def setUp(self):
        self.priest = Character("Priest")
        self.priest.set_skill("precepts", 3)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_initiative_roll([2, 5])
        # Queue 3 skill rolls for pool dice (one per precepts rank)
        roll_provider.put_skill_roll("precepts", 7)
        roll_provider.put_skill_roll("precepts", 7)
        roll_provider.put_skill_roll("precepts", 7)
        self.priest.set_roll_provider(roll_provider)
        self.target = Character("Target")
        groups = [Group("Phoenix", self.priest), Group("Enemy", self.target)]
        self.context = EngineContext(groups)

    def test_pool_dice_created_on_new_round(self):
        school = priest_school.PriestSchool()
        school.apply_rank_three_ability(self.priest)
        event = events.NewRoundEvent(1)
        list(self.priest.event(event, self.context))
        # Should have 3 floating bonuses (one per precepts skill rank)
        bonuses = self.priest.floating_bonuses("attack")
        self.assertEqual(3, len(bonuses))
        # Each bonus should be 7 (from queued roll provider)
        for bonus in bonuses:
            self.assertEqual(7, bonus.bonus())

    def test_pool_dice_applicable_to_multiple_skills(self):
        school = priest_school.PriestSchool()
        school.apply_rank_three_ability(self.priest)
        event = events.NewRoundEvent(1)
        list(self.priest.event(event, self.context))
        # Bonuses should be applicable to attack, parry, wound check, damage
        for skill in ["attack", "parry", "wound check", "damage"]:
            bonuses = self.priest.floating_bonuses(skill)
            self.assertEqual(3, len(bonuses), f"Expected 3 bonuses for {skill}")

    def test_no_pool_with_zero_precepts(self):
        self.priest.set_skill("precepts", 0)
        roll_provider = CalvinistRollProvider()
        roll_provider.put_initiative_roll([2, 5])
        self.priest.set_roll_provider(roll_provider)
        school = priest_school.PriestSchool()
        school.apply_rank_three_ability(self.priest)
        event = events.NewRoundEvent(1)
        list(self.priest.event(event, self.context))
        bonuses = self.priest.floating_bonuses("attack")
        self.assertEqual(0, len(bonuses))


class TestPriestFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        priest = Character("Priest")
        priest.set_ring("water", 3)
        school = priest_school.PriestSchool()
        school.apply_rank_four_ability(priest)
        self.assertEqual(4, priest.ring("water"))


class TestPriestSchoolRingChoice(unittest.TestCase):
    """Spec 025 Q1 MEDIUM fix: rules text "Any non-Void" — player
    picks ring via school_choices (Monk/Ide/Ise Zumi precedent)."""

    def test_school_ring_default_is_water(self) -> None:
        school = priest_school.PriestSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_ring_choice_overrides_default(self) -> None:
        for chosen in ("air", "earth", "fire", "water"):
            with self.subTest(chosen=chosen):
                school = priest_school.PriestSchool()
                school.set_choice("school_ring", chosen)
                self.assertEqual(chosen, school.school_ring())

    def test_school_ring_void_falls_back_to_default(self) -> None:
        """Void is explicitly disallowed per rules text "Any non-Void"."""
        school = priest_school.PriestSchool()
        school.set_choice("school_ring", "void")
        self.assertEqual("water", school.school_ring())

    def test_school_ring_invalid_type_falls_back(self) -> None:
        school = priest_school.PriestSchool()
        school.set_choice("school_ring", 42)
        self.assertEqual("water", school.school_ring())

    def test_fourth_dan_raises_chosen_ring(self) -> None:
        """Spec 025 Q1 fix: choosing a non-default school_ring
        redirects the 4th Dan +1 ring bump."""
        priest = Character("Priest")
        priest.set_ring("fire", 3)
        school = priest_school.PriestSchool()
        school.set_choice("school_ring", "fire")
        school.apply_rank_four_ability(priest)
        self.assertEqual(4, priest.ring("fire"))


class TestPriestFirstDanChoices(unittest.TestCase):
    """Spec 025 Q2 MEDIUM fix: rules text "Roll one extra die on
    precepts, any one skill, and any one type of combat roll" — the
    two "any one" slots are player choices."""

    def test_default_extra_rolled(self) -> None:
        """Defaults match the previous skeleton's hardcoded list
        for backwards compatibility."""
        school = priest_school.PriestSchool()
        self.assertEqual(
            ["precepts", "initiative", "wound check"],
            school.extra_rolled(),
        )

    def test_first_dan_extra_skill_choice(self) -> None:
        """Player can choose any skill for the "any one skill" slot."""
        school = priest_school.PriestSchool()
        school.set_choice("first_dan_extra_skill", "athletics")
        self.assertEqual(
            ["precepts", "athletics", "wound check"],
            school.extra_rolled(),
        )

    def test_first_dan_extra_combat_choice(self) -> None:
        """Player can choose a different combat roll."""
        school = priest_school.PriestSchool()
        school.set_choice("first_dan_extra_combat", "parry")
        self.assertEqual(
            ["precepts", "initiative", "parry"],
            school.extra_rolled(),
        )

    def test_first_dan_extra_combat_invalid_falls_back(self) -> None:
        """An invalid combat roll (not in VALID_COMBAT_ROLLS) MUST
        fall back to the default."""
        school = priest_school.PriestSchool()
        school.set_choice("first_dan_extra_combat", "skill-that-does-not-exist")
        self.assertEqual(
            ["precepts", "initiative", "wound check"],
            school.extra_rolled(),
        )

    def test_first_dan_extra_skill_invalid_type_falls_back(self) -> None:
        """Non-string falls back."""
        school = priest_school.PriestSchool()
        school.set_choice("first_dan_extra_skill", 42)
        self.assertEqual(
            ["precepts", "initiative", "wound check"],
            school.extra_rolled(),
        )


class TestPriestThirdDanOnceperCombat(unittest.TestCase):
    """Spec 025 Q4 BLOCKING fix: pool MUST roll ONCE per combat,
    not per round.  Pre-fix combat-simulator measured 5 dice
    accumulated per round at precepts=5 (over-powered).
    """

    def test_pool_does_not_re_roll_on_subsequent_rounds(self) -> None:
        priest = Character("Priest")
        priest.set_skill("precepts", 3)
        rp = CalvinistRollProvider()
        rp.put_initiative_roll([2, 5])
        rp.put_initiative_roll([3, 6])
        rp.put_initiative_roll([4, 7])
        # 3 pool-roll dice for round 1 ONLY.  If round 2 or 3 tried
        # to roll the pool, the CalvinistRollProvider would run out
        # of queued precepts rolls and raise.
        rp.put_skill_roll("precepts", 6)
        rp.put_skill_roll("precepts", 7)
        rp.put_skill_roll("precepts", 8)
        priest.set_roll_provider(rp)
        target = Character("Target")
        groups = [Group("Phoenix", priest), Group("Enemy", target)]
        context = EngineContext(groups)
        school = priest_school.PriestSchool()
        school.apply_rank_three_ability(priest)
        # Round 1: rolls pool (3 dice).
        list(priest.event(events.NewRoundEvent(1), context))
        round1_count = len(priest.floating_bonuses("attack"))
        self.assertEqual(3, round1_count)
        # Round 2: MUST NOT re-roll.  If it does, the
        # CalvinistRollProvider runs out of queued rolls and
        # raises ValueError.
        list(priest.event(events.NewRoundEvent(2), context))
        round2_count = len(priest.floating_bonuses("attack"))
        # Pool unchanged (still 3).
        self.assertEqual(3, round2_count)
        # Round 3: same.
        list(priest.event(events.NewRoundEvent(3), context))
        round3_count = len(priest.floating_bonuses("attack"))
        self.assertEqual(3, round3_count)

    def test_pool_dice_tagged_for_trace_attribution(self) -> None:
        """The 3rd Dan pool dice carry a ``_priest_3rd_dan_pool_die``
        attribute for future renderer work."""
        priest = Character("Priest")
        priest.set_skill("precepts", 2)
        rp = CalvinistRollProvider()
        rp.put_initiative_roll([2, 5])
        rp.put_skill_roll("precepts", 7)
        rp.put_skill_roll("precepts", 8)
        priest.set_roll_provider(rp)
        target = Character("Target")
        groups = [Group("Phoenix", priest), Group("Enemy", target)]
        context = EngineContext(groups)
        school = priest_school.PriestSchool()
        school.apply_rank_three_ability(priest)
        list(priest.event(events.NewRoundEvent(1), context))
        bonuses = priest.floating_bonuses("attack")
        for b in bonuses:
            self.assertTrue(
                getattr(b, "_priest_3rd_dan_pool_die", False),
            )


class TestPriestMisc(unittest.TestCase):
    """Coverage padding."""

    def test_apply_rank_five_does_not_raise(self) -> None:
        """Spec 025 Q8 DEFERRED: 5th Dan is intentionally a no-op
        (ally-buff mechanics moot in 1v1 simulator).  Must not
        raise."""
        priest = Character("Priest")
        school = priest_school.PriestSchool()
        school.apply_rank_five_ability(priest)
