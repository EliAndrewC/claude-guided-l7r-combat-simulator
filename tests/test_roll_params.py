#!/usr/bin/env python3

#
# test_roll_params.py
#
# Test roll parameter providers.
#

import unittest

from simulation.character import Character
from simulation.mechanics.roll_params import (
    DefaultRollParameterProvider,
    _normalize_breakdown,
    _school_formula_label,
    normalize_roll_params,
)


class TestSchoolFormulaLabel(unittest.TestCase):
    """Trace-reader cat#10 fix (2026-05-30): the non-overflow
    reconciliation catch-all in breakdowns is now qualified with the
    character's school short name when available."""

    def test_no_character_returns_generic(self):
        self.assertEqual("school formula", _school_formula_label(None))

    def test_no_school_returns_generic(self):
        c = Character("Plain")
        self.assertEqual("school formula", _school_formula_label(c))

    def test_with_school_qualifies_label(self):
        from simulation.schools.akodo_school import AkodoBushiSchool
        c = Character("Akodo")
        c.set_school(AkodoBushiSchool())
        self.assertEqual("Akodo school formula", _school_formula_label(c))

    def test_normalize_breakdown_threads_school_name(self):
        from simulation.schools.akodo_school import AkodoBushiSchool
        c = Character("Akodo")
        c.set_school(AkodoBushiSchool())
        # 5/3 components vs 5/4 aggregate → 1k1 missing in non-overflow
        result = _normalize_breakdown(
            [("ring", 5, 3)], 5, 4, character=c,
        )
        labels = [r[0] for r in result]
        self.assertIn("Akodo school formula", labels)

    def test_damage_breakdown_uses_dan_rank_label(self):
        """Trace-reader cat#10 fix (2026-05-30): the damage breakdown
        labels school extra-rolled/kept dice as "<School> 1st Dan"
        instead of the full school name (matching the attack
        breakdown convention)."""
        from simulation.schools.monk_school import (
            BrotherhoodOfShinseMonkSchool,
        )
        provider = DefaultRollParameterProvider()
        monk = Character("Monk")
        school = BrotherhoodOfShinseMonkSchool()
        monk.set_school(school)
        # Monk SA equips UNARMED and adds +1k1 extra on damage rolls.
        school.apply_special_ability(monk)
        target = Character("Target")
        components = provider.get_breakdown(
            monk, target, "attack", kind="damage",
        )
        labels = [c[0] for c in components]
        self.assertIn("Brotherhood 1st Dan", labels)


class TestNormalize(unittest.TestCase):
    def test_normal(self):
        self.assertEqual((1, 1, 0), normalize_roll_params(1, 1))
        self.assertEqual((6, 3, 0), normalize_roll_params(6, 3))
        self.assertEqual((10, 10, 0), normalize_roll_params(10, 10))
        self.assertEqual((7, 3, 0), normalize_roll_params(7, 3))

    def test_excess_rolled(self):
        self.assertEqual((10, 5, 0), normalize_roll_params(12, 3))
        self.assertEqual((10, 5, 0), normalize_roll_params(11, 4))
        self.assertEqual((10, 10, 0), normalize_roll_params(14, 6))

    def test_excess_kept(self):
        self.assertEqual((10, 10, 2), normalize_roll_params(11, 10))
        self.assertEqual((10, 10, 10), normalize_roll_params(17, 8))
        self.assertEqual((10, 10, 20), normalize_roll_params(25, 5))

    def test_bonus(self):
        self.assertEqual((6, 3, 5), normalize_roll_params(6, 3, 5))
        self.assertEqual((7, 3, 5), normalize_roll_params(7, 3, 5))
        self.assertEqual((10, 10, 7), normalize_roll_params(15, 6, 5))


class TestDefaultRollParameterProvider(unittest.TestCase):
    def setUp(self):
        self.provider = DefaultRollParameterProvider()

    def test_get_damage_roll_params(self):
        character = Character("attacker")
        target = Character("target")
        self.assertEqual((6, 2, 0), self.provider.get_damage_roll_params(character, target, "attack", 0, 0))
        # vp should not change damage roll params for the default provider
        self.assertEqual((6, 2, 0), self.provider.get_damage_roll_params(character, target, "attack", 0, 1))
        # extra rolled die from the attack
        self.assertEqual((7, 2, 0), self.provider.get_damage_roll_params(character, target, "attack", 1, 0))
        # higher Fire and extra rolled dice should result in extra kept dice
        character.set_ring("fire", 5)
        self.assertEqual((10, 3, 0), self.provider.get_damage_roll_params(character, target, "attack", 2, 0))

    def test_get_initiative_roll_params(self):
        character = Character()
        self.assertEqual((3, 2, 0), self.provider.get_initiative_roll_params(character))
        character.set_ring("void", 4)
        self.assertEqual((5, 4, 0), self.provider.get_initiative_roll_params(character))
        character.set_extra_rolled("initiative", 1)
        self.assertEqual((6, 4, 0), self.provider.get_initiative_roll_params(character))

    def test_get_wound_check_roll_params(self):
        character = Character()
        self.assertEqual((3, 2, 0), self.provider.get_wound_check_roll_params(character))
        self.assertEqual((4, 3, 0), self.provider.get_wound_check_roll_params(character, 1))
        character.set_extra_rolled("wound check", 1)
        self.assertEqual((4, 2, 0), self.provider.get_wound_check_roll_params(character, 0))
