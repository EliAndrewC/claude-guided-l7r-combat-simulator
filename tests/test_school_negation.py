#!/usr/bin/env python3

#
# test_school_negation.py
#
# Tests for the engine-surface short-circuit consumed by the Isawa Ishi 5th
# Dan school-negation ability (rules/04-schools.md "Isawa Ishi School:
# 5th Dan").  When `Character._school_negated_by` is set, applying that
# character's school abilities must become a no-op.
#

import unittest

from simulation import events
from simulation.character import Character
from simulation.schools.akodo_school import AkodoBushiSchool


class TestSchoolNegationShortCircuit(unittest.TestCase):
    """
    The BaseSchool helper used by 5th Dan school-negation must short-circuit
    `apply_*_ability` calls when `_school_negated_by` is set on the target,
    and must be a fast no-op for the (overwhelming) default case where the
    flag is None.
    """

    def test_apply_rank_one_active_when_not_negated(self):
        """1st Dan extra-rolled dice land on the character when not negated."""
        c = Character("Akodo")
        school = AkodoBushiSchool()
        school.apply_rank_one_ability(c)
        # Akodo 1st Dan grants extra rolled on attack/double attack/wound check
        self.assertEqual(1, c.extra_rolled("attack"))
        self.assertEqual(1, c.extra_rolled("wound check"))

    def test_apply_rank_one_short_circuits_when_negated(self):
        """When _school_negated_by is set, apply_rank_one_ability is a no-op."""
        c = Character("Akodo")
        negator = Character("Ishi")
        c._school_negated_by = negator
        school = AkodoBushiSchool()
        school.apply_rank_one_ability(c)
        # No extra rolled dice should have been applied
        self.assertEqual(0, c.extra_rolled("attack"))
        self.assertEqual(0, c.extra_rolled("double attack"))
        self.assertEqual(0, c.extra_rolled("wound check"))

    def test_apply_rank_two_active_when_not_negated(self):
        """2nd Dan free raise modifiers land on the character when not negated."""
        c = Character("Akodo")
        school = AkodoBushiSchool()
        school.apply_rank_two_ability(c)
        # Akodo 2nd Dan grants a free raise on wound check; modifier list grows.
        self.assertEqual(1, len(c._modifiers))

    def test_apply_rank_two_short_circuits_when_negated(self):
        """When _school_negated_by is set, apply_rank_two_ability is a no-op."""
        c = Character("Akodo")
        negator = Character("Ishi")
        c._school_negated_by = negator
        school = AkodoBushiSchool()
        school.apply_rank_two_ability(c)
        # No free raise modifier should have been added
        self.assertEqual(0, len(c._modifiers))

    def test_helper_returns_true_when_negated(self):
        """The BaseSchool short-circuit helper exposes the check to subclasses."""
        c = Character("Akodo")
        school = AkodoBushiSchool()
        # Not negated -> helper says no short-circuit
        self.assertFalse(school._is_school_negated(c))
        # Negated -> helper says short-circuit
        c._school_negated_by = Character("Ishi")
        self.assertTrue(school._is_school_negated(c))


class TestSchoolNegatedEvent(unittest.TestCase):
    """
    SchoolNegatedEvent advertises the Isawa Ishi 5th Dan negation moment
    (rules/04-schools.md "Isawa Ishi School: 5th Dan") so the trace/UI
    adapters can render the source, target, and VP cost.
    """

    def test_event_carries_negator_target_cost_and_school_name(self):
        ishi = Character("Ishi")
        akodo = Character("Akodo")
        event = events.SchoolNegatedEvent(
            negator=ishi,
            target=akodo,
            vp_cost=3,
            target_school_name="Akodo Bushi School",
        )
        self.assertEqual("school_negated", event.name)
        self.assertIs(ishi, event.negator)
        self.assertIs(akodo, event.target)
        self.assertEqual(3, event.vp_cost)
        self.assertEqual("Akodo Bushi School", event.target_school_name)


if __name__ == "__main__":
    unittest.main()
