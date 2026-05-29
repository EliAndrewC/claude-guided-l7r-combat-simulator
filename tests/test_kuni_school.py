#!/usr/bin/env python3

#
# test_kuni_school.py
#
# Unit tests for the Kuni Witch Hunter School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.schools import kuni_school
from simulation.strategies.base import AlwaysKeepLightWoundsStrategy

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestKuniWitchHunterSchoolName(unittest.TestCase):
    def test_name(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual("Kuni Witch Hunter School", school.name())


class TestKuniWitchHunterSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        """Spec 020 Q2 BLOCKING fix: rules text says 1st Dan grants
        extra die on "damage, interrogation, and wound checks".  The
        skeleton previously omitted "interrogation"."""
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual(
            ["damage", "interrogation", "wound check"],
            school.extra_rolled(),
        )

    def test_school_ring(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual("earth", school.school_ring())

    def test_school_knacks(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual(["detect taint", "iaijutsu", "presence"], school.school_knacks())

    def test_free_raise_skills(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual(["interrogation"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual("investigation", school.ap_base_skill())

    def test_ap_skills(self):
        school = kuni_school.KuniWitchHunterSchool()
        self.assertEqual(["attack", "wound check"], school.ap_skills())


class TestKuniSpecialAbility(unittest.TestCase):
    """Spec 020 Q1 BLOCKING fix: rules text says (X+1)k(X+1) on
    wound checks where X is the attacker's Shadowlands Taint.  With
    Taint=0 (simulator baseline), this is 1k1 = +1 rolled AND +1
    kept.  The skeleton previously only added +1 kept."""

    def test_extra_rolled_and_kept_on_wound_check(self):
        kuni = Character("Kuni")
        school = kuni_school.KuniWitchHunterSchool()
        school.apply_special_ability(kuni)
        # Q1 fix: BOTH rolled and kept get +1.
        self.assertEqual(1, kuni.extra_rolled("wound check"))
        self.assertEqual(1, kuni.extra_kept("wound check"))


class TestKuniAPSystem(unittest.TestCase):
    def test_apply_ap(self):
        kuni = Character("Kuni")
        kuni.set_skill("investigation", 5)
        school = kuni_school.KuniWitchHunterSchool()
        school.apply_rank_three_ability(kuni)
        self.assertEqual("investigation", kuni.ap_base_skill())
        self.assertTrue(kuni.can_spend_ap("attack"))
        self.assertTrue(kuni.can_spend_ap("wound check"))
        self.assertFalse(kuni.can_spend_ap("parry"))
        # AP = 2 * investigation skill = 10
        self.assertEqual(10, kuni.ap())


class TestKuniWoundCheckSucceededListener(unittest.TestCase):
    def setUp(self):
        self.kuni = Character("Kuni")
        self.kuni.set_strategy("light_wounds", AlwaysKeepLightWoundsStrategy())
        self.attacker = Character("attacker")
        groups = [Group("Crab", self.kuni), Group("Attacker", self.attacker)]
        self.context = EngineContext(groups)

    def test_reflect_damage_and_backlash(self):
        """Spec 020 Q4 BLOCKING fix: rules text says "inflict that
        number of light wounds on the opponent who dealt them AND
        take half that amount yourself".  Previously the Kuni
        reflected the full amount but took NO backlash — over-powered.
        Now the Kuni also takes ``damage // 2`` LW.
        """
        self.kuni._lw = 15
        listener = kuni_school.KuniWoundCheckSucceededListener()
        event = events.WoundCheckSucceededEvent(self.kuni, self.attacker, 15, 25)
        responses = list(listener.handle(self.kuni, event, self.context))
        lw_events = [r for r in responses if isinstance(r, events.LightWoundsDamageEvent)]
        # Two LightWoundsDamageEvents: reflection + backlash.
        self.assertEqual(2, len(lw_events))
        # First: reflection (Kuni → attacker, 15 LW).
        reflect = lw_events[0]
        self.assertEqual(self.kuni, reflect.subject)
        self.assertEqual(self.attacker, reflect.target)
        self.assertEqual(15, reflect.damage)
        # Trace attribution tag (spec 020 FR-008).
        self.assertTrue(getattr(reflect, "_kuni_5th_dan_reflection", False))
        # Second: backlash (attacker → Kuni, 15 // 2 = 7 LW).
        backlash = lw_events[1]
        self.assertEqual(self.attacker, backlash.subject)
        self.assertEqual(self.kuni, backlash.target)
        self.assertEqual(7, backlash.damage)
        self.assertTrue(getattr(backlash, "_kuni_5th_dan_backlash", False))

    def test_no_backlash_when_damage_is_odd_one(self):
        """When the LW amount is 1, backlash = 1 // 2 = 0, so no
        backlash event emitted (only the reflection).  Coverage for
        the ``if backlash_damage > 0`` guard."""
        self.kuni._lw = 1
        listener = kuni_school.KuniWoundCheckSucceededListener()
        event = events.WoundCheckSucceededEvent(self.kuni, self.attacker, 1, 25)
        responses = list(listener.handle(self.kuni, event, self.context))
        lw_events = [r for r in responses if isinstance(r, events.LightWoundsDamageEvent)]
        # Only the reflection — no backlash since 1 // 2 = 0.
        self.assertEqual(1, len(lw_events))
        self.assertEqual(1, lw_events[0].damage)

    def test_no_reflect_zero_damage(self):
        listener = kuni_school.KuniWoundCheckSucceededListener()
        event = events.WoundCheckSucceededEvent(self.kuni, self.attacker, 0, 25)
        responses = list(listener.handle(self.kuni, event, self.context))
        # No LW reflection for zero damage, but should still get KeepLightWoundsEvent
        lw_damage_events = [r for r in responses if isinstance(r, events.LightWoundsDamageEvent)]
        self.assertEqual(0, len(lw_damage_events))
