#!/usr/bin/env python3

#
# test_yogo_school.py
#
# Unit tests for the Yogo Warden School.
#

import logging
import sys
import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.schools import yogo_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestYogoWardenSchoolMisc(unittest.TestCase):
    """Coverage for trivial accessors."""

    def test_name(self):
        school = yogo_school.YogoWardenSchool()
        self.assertEqual("Yogo Warden School", school.name())

    def test_ap_base_skill_returns_none(self):
        school = yogo_school.YogoWardenSchool()
        self.assertIsNone(school.ap_base_skill())

    def test_free_raise_skills(self):
        school = yogo_school.YogoWardenSchool()
        self.assertEqual(["wound check"], school.free_raise_skills())


class TestYogoWardenSchoolExtraRolled(unittest.TestCase):
    def test_extra_rolled_returns_correct_skills(self):
        school = yogo_school.YogoWardenSchool()
        extra = school.extra_rolled()
        self.assertEqual(["attack", "damage", "wound check"], extra)

    def test_school_ring(self):
        school = yogo_school.YogoWardenSchool()
        self.assertEqual("earth", school.school_ring())

    def test_school_knacks(self):
        school = yogo_school.YogoWardenSchool()
        self.assertEqual(["double attack", "feint", "iaijutsu"], school.school_knacks())


class TestYogoSeriousWoundsDamageListener(unittest.TestCase):
    def setUp(self):
        self.yogo = Character("Yogo")
        self.attacker = Character("attacker")
        groups = [Group("Scorpion", self.yogo), Group("Attacker", self.attacker)]
        self.context = EngineContext(groups)

    def test_gain_tvp_on_serious_wound(self):
        listener = yogo_school.YogoSeriousWoundsDamageListener()
        event = events.SeriousWoundsDamageEvent(self.attacker, self.yogo, 1)
        responses = list(listener.handle(self.yogo, event, self.context))
        self.assertEqual(1, len(responses))
        response = responses[0]
        self.assertTrue(isinstance(response, events.GainTemporaryVoidPointsEvent))
        self.assertEqual(self.yogo, response.subject)
        self.assertEqual(1, response.amount)

    def test_no_tvp_on_defeat(self):
        # Give Yogo enough SW to be near death
        self.yogo.take_sw(3)
        listener = yogo_school.YogoSeriousWoundsDamageListener()
        event = events.SeriousWoundsDamageEvent(self.attacker, self.yogo, 2)
        responses = list(listener.handle(self.yogo, event, self.context))
        # Should get death/unconscious event, not TVP
        self.assertEqual(1, len(responses))
        self.assertFalse(isinstance(responses[0], events.GainTemporaryVoidPointsEvent))


class TestYogoSpendVoidPointsListener(unittest.TestCase):
    def setUp(self):
        self.yogo = Character("Yogo")
        self.yogo.set_skill("attack", 4)
        self.yogo._lw = 20
        self.yogo.gain_tvp(5)
        self.enemy = Character("enemy")
        self.context = EngineContext([Group("Scorpion", self.yogo), Group("Enemy", self.enemy)])

    def test_reduce_lw_on_single_vp_spend(self):
        """Spec 021 Q2 BLOCKING fix: per-VP scaling.  Spending 1 VP
        reduces LW by 2 * attack_skill * 1 = 8."""
        listener = yogo_school.YogoSpendVoidPointsListener()
        event = events.SpendVoidPointsEvent(self.yogo, "attack", 1)
        list(listener.handle(self.yogo, event, self.context))
        # attack skill 4, 1 VP spent, reduction = 2 * 4 * 1 = 8.
        # 20 - 8 = 12.
        self.assertEqual(12, self.yogo.lw())
        # Trace attribution tag (spec 021 FR-005).
        self.assertEqual(
            8, getattr(self.yogo, "_yogo_3rd_dan_last_reduction", 0),
        )

    def test_reduce_lw_scales_per_vp_spent(self):
        """Spec 021 Q2 BLOCKING fix: spending 2 VP at once MUST
        reduce LW by 2 * attack_skill * 2 (not just 2 * attack_skill).
        The previous skeleton applied the reduction once per event
        regardless of amount."""
        listener = yogo_school.YogoSpendVoidPointsListener()
        event = events.SpendVoidPointsEvent(self.yogo, "attack", 2)
        list(listener.handle(self.yogo, event, self.context))
        # attack skill 4, 2 VP spent, reduction = 2 * 4 * 2 = 16.
        # 20 - 16 = 4.
        self.assertEqual(4, self.yogo.lw())
        self.assertEqual(
            16, getattr(self.yogo, "_yogo_3rd_dan_last_reduction", 0),
        )

    def test_emits_lw_reduction_event(self):
        """Trace-reader cat#10 fix (2026-05-30): the listener must
        emit a ``YogoThirdDanLwReductionEvent`` so the trace surfaces
        the reduction that was previously a silent ``_lw`` mutation."""
        listener = yogo_school.YogoSpendVoidPointsListener()
        event = events.SpendVoidPointsEvent(self.yogo, "attack", 2)
        emitted = list(listener.handle(self.yogo, event, self.context))
        reduction_events = [
            e for e in emitted
            if isinstance(e, events.YogoThirdDanLwReductionEvent)
        ]
        self.assertEqual(1, len(reduction_events))
        ev = reduction_events[0]
        self.assertEqual(self.yogo, ev.subject)
        self.assertEqual(2, ev.vp_spent)
        self.assertEqual(4, ev.attack_skill)
        self.assertEqual(16, ev.reduction)
        self.assertEqual(4, ev.lw_after)

    def test_no_event_when_lw_already_zero(self):
        """When the Yogo has 0 LW, the reduction caps to 0 and no
        ``YogoThirdDanLwReductionEvent`` is emitted (avoid noise)."""
        self.yogo._lw = 0
        listener = yogo_school.YogoSpendVoidPointsListener()
        event = events.SpendVoidPointsEvent(self.yogo, "attack", 1)
        emitted = list(listener.handle(self.yogo, event, self.context))
        reduction_events = [
            e for e in emitted
            if isinstance(e, events.YogoThirdDanLwReductionEvent)
        ]
        self.assertEqual(0, len(reduction_events))

    def test_reduction_caps_at_current_lw(self):
        """When the reduction formula exceeds current LW, the trace
        event reports the EFFECTIVE reduction (capped at current LW)
        so ``lw_after`` matches the post-mutation state."""
        self.yogo._lw = 3  # less than reduction (2*4*1=8)
        listener = yogo_school.YogoSpendVoidPointsListener()
        event = events.SpendVoidPointsEvent(self.yogo, "attack", 1)
        emitted = list(listener.handle(self.yogo, event, self.context))
        reduction_events = [
            e for e in emitted
            if isinstance(e, events.YogoThirdDanLwReductionEvent)
        ]
        self.assertEqual(1, len(reduction_events))
        ev = reduction_events[0]
        self.assertEqual(3, ev.reduction)
        self.assertEqual(0, ev.lw_after)
        self.assertEqual(0, self.yogo.lw())


class TestYogoRollParameterProvider(unittest.TestCase):
    def test_wound_check_extra_vp_bonus(self):
        yogo = Character("Yogo")
        yogo.set_ring("water", 3)
        provider = yogo_school.YogoRollParameterProvider()
        # With 1 VP: standard gives +5 modifier, Yogo gives +10 total
        (rolled, kept, modifier) = provider.get_wound_check_roll_params(yogo, vp=1)
        # rolled = 3 + 1 + 0 + 1 = 5, kept = 3 + 0 + 1 = 4, modifier = 0 + 5 = 5
        self.assertEqual(5, rolled)
        self.assertEqual(4, kept)
        self.assertEqual(5, modifier)

    def test_wound_check_no_vp(self):
        yogo = Character("Yogo")
        yogo.set_ring("water", 3)
        provider = yogo_school.YogoRollParameterProvider()
        (rolled, kept, modifier) = provider.get_wound_check_roll_params(yogo, vp=0)
        self.assertEqual(4, rolled)
        self.assertEqual(3, kept)
        self.assertEqual(0, modifier)
