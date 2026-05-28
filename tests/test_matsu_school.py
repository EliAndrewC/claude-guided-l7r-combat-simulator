#!/usr/bin/env python3

#
# test_matsu_school.py
#
# Unit tests for the Matsu Bushi School.
#

import logging
import sys
import unittest
from typing import Any

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.schools import matsu_school
from web.adapters.bulleted_renderer import BulletedRenderer
from web.adapters.detailed_formatter import DetailedEventFormatter
from web.adapters.text_renderer import TextRenderer

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestMatsuBushiSchoolBasics(unittest.TestCase):
    def test_extra_rolled(self):
        school = matsu_school.MatsuBushiSchool()
        self.assertEqual(["double attack", "iaijutsu", "wound check"], school.extra_rolled())

    def test_school_ring(self):
        school = matsu_school.MatsuBushiSchool()
        self.assertEqual("fire", school.school_ring())

    def test_school_knacks(self):
        school = matsu_school.MatsuBushiSchool()
        self.assertEqual(["double attack", "iaijutsu", "lunge"], school.school_knacks())

    def test_free_raise_skills(self):
        school = matsu_school.MatsuBushiSchool()
        self.assertEqual(["iaijutsu"], school.free_raise_skills())

    def test_name(self):
        """``name()`` returns the canonical school name used by the
        template loader and trace formatter to identify Matsu builds."""
        school = matsu_school.MatsuBushiSchool()
        self.assertEqual("Matsu Bushi School", school.name())

    def test_ap_base_skill(self):
        """Matsu has no AP-keyed rules-text clause; ``ap_base_skill()``
        must return ``None`` so the engine's default AP routing applies.
        """
        school = matsu_school.MatsuBushiSchool()
        self.assertIsNone(school.ap_base_skill())


class TestMatsuPriorities(unittest.TestCase):
    """T018 + T019 / US4 regression guards on
    ``simulation.templates.strategies.MATSU_PRIORITIES``.

    These guards encode the Matsu identity decisions made by
    school-progression-designer: all three knacks must be purchased at
    every rank-up tier, and parry is intentionally capped at 3 (the
    Wave-Man baseline floor) because Matsu has no parry-keyed rules
    text.
    """

    def test_matsu_priorities_includes_all_knacks(self):
        """T018 / US4 regression guard.

        rules/04-schools.md "Matsu Bushi School" lists the school knacks
        as ``double attack, iaijutsu, lunge`` -- all three MUST appear
        in ``MATSU_PRIORITIES`` so the auto-build advances Dan ranks via
        knack purchases.  Mirrors the Hida ``test_no_lunge_in_hida_priorities``
        regression-guard pattern.
        """
        from simulation.templates.strategies import MATSU_PRIORITIES
        skill_names = {
            entry[1] for entry in MATSU_PRIORITIES
            if len(entry) >= 2 and entry[0] == "skill"
        }
        for knack in ("double attack", "iaijutsu", "lunge"):
            self.assertIn(
                knack, skill_names,
                f"MATSU_PRIORITIES must reference '{knack}' "
                f"(Matsu school knack per rules/04-schools.md); "
                f"found skill entries: {sorted(skill_names)}",
            )

    def test_matsu_priorities_caps_parry_at_three(self):
        """T019 / US4 regression guard.

        Per the school-progression-designer's identity rationale, Matsu
        has no parry-keyed rules text, so parry is intentionally capped
        at the rank-3 floor (the Wave-Man baseline).  No
        ``("skill", "parry", N)`` entry may have ``N > 3``.
        """
        from simulation.templates.strategies import MATSU_PRIORITIES
        late_parry_entries = [
            entry for entry in MATSU_PRIORITIES
            if (
                len(entry) >= 3
                and entry[0] == "skill"
                and entry[1] == "parry"
                and entry[2] > 3
            )
        ]
        self.assertEqual(
            [], late_parry_entries,
            f"MATSU_PRIORITIES must not raise parry above 3 (Matsu has "
            f"no parry-keyed rules text; school-progression-designer "
            f"caps it at the rank-3 floor); found: {late_parry_entries}",
        )


class TestMatsuRollProvider(unittest.TestCase):
    def test_initiative_always_10_dice(self):
        """rules/04-schools.md "Matsu Bushi School: Special Ability":
        "You always roll 10 dice when rolling initiative".  Strict
        canonical reading per OPEN_QUESTIONS Q1 — EXACTLY 10, not
        at-least-10.  FR-001."""
        provider = matsu_school.MatsuRollProvider()
        # Even with rolled=3, should use exactly 10 (not max(rolled, 10)).
        result = provider.get_initiative_roll(3, 2)
        # Result is a list of action dice
        self.assertTrue(isinstance(result, list))
        info = provider.last_initiative_info()
        self.assertIsNotNone(info)
        assert info is not None  # for mypy
        # The "rolled" actually passed through to the underlying roll
        # MUST be exactly 10, regardless of the input ``rolled`` value.
        self.assertEqual(10, info["rolled"])
        self.assertEqual(2, info["kept"])

    def test_initiative_strict_10_even_when_input_exceeds_10(self):
        """rules/04-schools.md "Matsu Bushi School: Special Ability":
        "You always roll 10 dice".  A high-XP build whose base rolled
        count would exceed 10 (e.g., Fire 7 + bonuses) MUST drop to
        exactly 10 -- this is the strict rules-as-written reading per
        OPEN_QUESTIONS Q1.  FR-001."""
        provider = matsu_school.MatsuRollProvider()
        # Input rolled=12 (above 10) should be clamped down to exactly 10.
        result = provider.get_initiative_roll(12, 4)
        self.assertTrue(isinstance(result, list))
        info = provider.last_initiative_info()
        assert info is not None
        self.assertEqual(10, info["rolled"])
        self.assertEqual(4, info["kept"])


class TestMatsuSpendVoidPointsListener(unittest.TestCase):
    def setUp(self):
        self.matsu = Character("Matsu")
        self.matsu.set_skill("attack", 4)
        self.matsu.gain_tvp(5)
        self.enemy = Character("enemy")
        groups = [Group("Lion", self.matsu), Group("Enemy", self.enemy)]
        self.context = EngineContext(groups)

    def test_gain_wound_check_bonus_on_vp_spend(self):
        listener = matsu_school.MatsuSpendVoidPointsListener()
        event = events.SpendVoidPointsEvent(self.matsu, "attack", 1)
        list(listener.handle(self.matsu, event, self.context))
        # Should gain WoundCheckFloatingBonus(3 * 4 = 12)
        bonuses = self.matsu.floating_bonuses("wound check")
        self.assertEqual(1, len(bonuses))
        self.assertEqual(12, bonuses[0].bonus())
        self.assertTrue(isinstance(bonuses[0], WoundCheckFloatingBonus))

    def test_vp_spend_not_double_spent(self):
        """T013 regression -- the Matsu 3rd Dan listener slot-replaces
        the default SpendVoidPointsListener.  Verify a 1-VP spend
        decreases ``vp()`` by exactly 1, not 2.  rules/04-schools.md
        "Matsu Bushi School: Third Dan"."""
        # Apply the 3rd Dan ability via the school (slot-replace
        # semantics) so the wiring matches a real combat.
        school = matsu_school.MatsuBushiSchool()
        self.matsu.set_school(school)
        school.apply_rank_three_ability(self.matsu)
        vp_before = self.matsu.vp()
        # Dispatch the event through the character so the slot-replaced
        # listener fires (and the default does NOT fire alongside it).
        event = events.SpendVoidPointsEvent(self.matsu, "attack", 1)
        list(self.matsu.event(event, self.context))
        vp_after = self.matsu.vp()
        # Exactly 1 VP spent -- not 2 (default + Matsu duplicate).
        self.assertEqual(vp_before - 1, vp_after)
        # The bonus was still granted.
        bonuses = self.matsu.floating_bonuses("wound check")
        self.assertEqual(1, len(bonuses))


class TestMatsuDoubleAttackAction(unittest.TestCase):
    def setUp(self):
        self.matsu = Character("Matsu")
        self.matsu.set_actions([1])
        self.target = Character("target")
        self.target.set_skill("parry", 3)
        groups = [Group("Lion", self.matsu), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_near_miss_is_hit(self):
        # TN = target TN + 20 = 20 + 20 = 40
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(25)  # Below TN of 40 but within 20
        self.assertTrue(action.is_hit())

    def test_near_miss_zero_extra_dice(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(25)  # Below TN of 40
        self.assertEqual(0, action.calculate_extra_damage_dice())

    def test_near_miss_no_direct_damage(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(25)  # Below TN of 40
        self.assertIsNone(action.direct_damage())

    def test_normal_hit_has_direct_damage(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(45)  # Above TN of 40
        self.assertIsNotNone(action.direct_damage())

    def test_miss_not_hit(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(19)  # Below TN-20 of 20
        self.assertFalse(action.is_hit())

    def test_miss_by_exactly_20_is_not_a_hit(self):
        """rules-auditor #2 boundary fix (2026-05-28): rules text says
        "by LESS THAN 20", which is strict ``<``.  A roll exactly 20
        below TN is a MISS (miss-by-20 is NOT miss-by-less-than-20).

        rules/04-schools.md "Matsu Bushi School: Fourth Dan".
        """
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        # TN of 40 → exact-20-below = 20.  Must be a MISS, not a hit.
        action.set_skill_roll(20)
        self.assertFalse(
            action.is_hit(),
            "Miss by exactly 20 must NOT be a hit (rules text: 'by less "
            "than 20', strict <).",
        )
        # And not a near-miss either.
        self.assertFalse(
            action._is_near_miss,
            "Miss by exactly 20 must NOT count as a near-miss.",
        )

    def test_miss_by_19_is_a_near_miss_hit(self):
        """Boundary check: roll exactly 19 below TN IS a near-miss hit
        per the strict ``<`` boundary.  rules/04-schools.md "Matsu Bushi
        School: Fourth Dan"."""
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(21)  # 19 below TN of 40
        self.assertTrue(action.is_hit())
        self.assertTrue(action._is_near_miss)


class TestMatsuSeriousWoundsDamageListener(unittest.TestCase):
    """rules-auditor BLOCKING fix (2026-05-28): the 5th Dan listener
    now lives on the ``sw_damage`` slot, NOT ``wound_check_failed``.
    The prior design produced double-SW emissions and a LW race
    condition against the defender's default ``WoundCheckFailedListener``.
    """

    def setUp(self):
        self.matsu = Character("Matsu")
        self.matsu.set_ring("earth", 5)  # max_sw 10 so SW take is meaningful
        self.defender = Character("defender")
        self.defender.set_ring("earth", 5)
        self.defender._lw = 0
        groups = [Group("Lion", self.matsu), Group("Enemy", self.defender)]
        self.context = EngineContext(groups)

    def test_listener_sets_defender_lw_to_15_when_matsu_is_attacker(self):
        """When a SeriousWoundsDamageEvent fires with the Matsu as
        attacker and someone else as target, the target's LW is set
        to 15 and a trace-observability event is yielded.

        rules/04-schools.md "Matsu Bushi School: Fifth Dan" + FR-022.
        """
        # Pre-condition: defender just took LW dose; default WCF
        # listener already called reset_lw (LW=0).
        listener = matsu_school.MatsuSeriousWoundsDamageListener()
        sw_event = events.SeriousWoundsDamageEvent(
            self.matsu, self.defender, 2,
        )
        responses = list(listener.handle(self.matsu, sw_event, self.context))
        # Defender's LW should now be set to 15.
        self.assertEqual(15, self.defender.lw())
        # First yielded event is the trace-observability marker.
        self.assertTrue(any(
            isinstance(r, events.MatsuLightWoundsFloorEvent)
            for r in responses
        ))

    def test_listener_delegates_to_default_for_take_sw(self):
        """The listener subclasses the default ``SeriousWoundsDamageListener``
        so the standard ``take_sw`` + status checks still fire when
        the Matsu attacks.  Without delegation a 5th Dan Matsu would
        silently fail to apply the SW to the target.
        """
        listener = matsu_school.MatsuSeriousWoundsDamageListener()
        sw_event = events.SeriousWoundsDamageEvent(
            self.matsu, self.defender, 2,
        )
        sw_before = self.defender.sw()
        list(listener.handle(self.defender, sw_event, self.context))
        # The default listener fires for the TARGET character (the
        # defender), so take_sw was called when we dispatch on the
        # defender side.  Matsu side does the LW=15 set; defender
        # side does the take_sw.
        self.assertGreater(self.defender.sw(), sw_before)

    def test_listener_does_not_fire_when_matsu_is_target(self):
        """When Matsu is the SW target (someone attacked Matsu), the
        5th Dan LW-floor MUST NOT fire on Matsu's own LW.  Matsu's
        own LW must reset to 0 per standard behavior."""
        listener = matsu_school.MatsuSeriousWoundsDamageListener()
        other = Character("other")
        sw_event = events.SeriousWoundsDamageEvent(other, self.matsu, 1)
        list(listener.handle(self.matsu, sw_event, self.context))
        # No MatsuLightWoundsFloorEvent should fire when Matsu is the
        # target (only when Matsu is the attacker).  Matsu's own LW
        # should NOT be set to 15.
        self.assertNotEqual(15, self.matsu.lw())

    def test_listener_does_not_double_emit_sw_event(self):
        """The prior implementation slot-replaced the ``wound_check_failed``
        slot AND emitted a SW event from the attacker side, while the
        defender's default ``WoundCheckFailedListener`` also emitted a
        SW event from the defender side — net result was DOUBLE SW.
        The new implementation listens on ``sw_damage`` (which already
        fires from the default WCF path), so only ONE SW is emitted.
        Regression-guard via direct invocation: confirm the new
        listener does NOT itself emit a SeriousWoundsDamageEvent
        (it only adds the LW-floor + trace marker)."""
        listener = matsu_school.MatsuSeriousWoundsDamageListener()
        sw_event = events.SeriousWoundsDamageEvent(
            self.matsu, self.defender, 2,
        )
        responses = list(listener.handle(self.matsu, sw_event, self.context))
        # No NEW SeriousWoundsDamageEvent should be yielded — the
        # only SW event is the one the default WCF listener already
        # emitted (and which is being processed by this handler).
        new_sw_events = [
            r for r in responses
            if isinstance(r, events.SeriousWoundsDamageEvent)
        ]
        self.assertEqual(
            [], new_sw_events,
            f"Matsu 5th Dan listener must NOT emit additional SW events "
            f"(double-emission was the prior bug per rules-auditor "
            f"BLOCKING).  Got: {new_sw_events}",
        )

    def test_end_to_end_via_engine_no_double_sw_and_lw_set_to_15(self):
        """Full-engine integration test: a Matsu's attack causes a
        failed WC, the engine dispatches the WoundCheckFailedEvent,
        and the resulting state must be:
          - Defender LW == 15 (5th Dan floor applied)
          - Defender has taken exactly the WC-computed SW (no double-count)
          - Exactly ONE SeriousWoundsDamageEvent in history for this WC failure
        """
        from simulation.character_builder import CharacterBuilder
        from simulation.engine import CombatEngine
        # Build a 5th-Dan Matsu via the builder (so all listeners install).
        builder = (
            CharacterBuilder(9001)
            .with_name("Matsu5")
            .with_school(matsu_school.MatsuBushiSchool())
            .buy_skill("double attack", 5)
            .buy_skill("iaijutsu", 5)
            .buy_skill("lunge", 5)
        )
        matsu5 = builder.build()
        self.assertEqual(5, matsu5.school_rank())
        defender = Character("defender")
        defender.set_ring("earth", 5)  # max_sw 10
        defender._lw = 30  # ensure WC could fail
        groups = [Group("Lion", matsu5), Group("Enemy", defender)]
        context = EngineContext(groups)
        engine = CombatEngine(context)
        # Dispatch WCF event (simulates defender's WC failing).
        wcf = events.WoundCheckFailedEvent(defender, matsu5, 30, 10)
        engine.event(wcf)
        # Defender's LW must end at 15 (5th Dan floor), not 0.
        self.assertEqual(
            15, defender.lw(),
            f"Defender LW must end at 15 (5th Dan floor); got {defender.lw()}.  "
            f"rules-auditor BLOCKING regression — the LW must not race "
            f"between defender's reset_lw and Matsu's 5th Dan set.",
        )
        # The history must contain EXACTLY ONE SeriousWoundsDamageEvent
        # for this failed WC (not two — the prior bug double-emitted).
        sw_events = [
            e for e in engine.history()
            if isinstance(e, events.SeriousWoundsDamageEvent)
        ]
        self.assertEqual(
            1, len(sw_events),
            f"Exactly one SeriousWoundsDamageEvent expected per failed "
            f"WC; got {len(sw_events)}.  rules-auditor BLOCKING "
            f"regression — listener slot-misplacement double-emitted SW.",
        )

    def test_matsu_own_failed_wc_uses_default_behavior(self):
        """Matsu's own failed WC must use the standard reset-LW-to-0
        behavior (the 5th Dan only applies to defenders OTHER THAN
        Matsu).  Via the engine integration path: the default
        ``WoundCheckFailedListener`` is no longer slot-replaced (the
        rules-auditor fix removed the ``wound_check_failed`` slot
        installation in ``apply_rank_five_ability``), so the default
        handles Matsu's own failed WC correctly.
        """
        from simulation.character_builder import CharacterBuilder
        from simulation.engine import CombatEngine
        builder = (
            CharacterBuilder(9001)
            .with_name("Matsu5")
            .with_school(matsu_school.MatsuBushiSchool())
            .buy_skill("double attack", 5)
            .buy_skill("iaijutsu", 5)
            .buy_skill("lunge", 5)
        )
        matsu5 = builder.build()
        attacker = Character("other")
        matsu5._lw = 20
        groups = [Group("Lion", matsu5), Group("Enemy", attacker)]
        context = EngineContext(groups)
        engine = CombatEngine(context)
        wcf = events.WoundCheckFailedEvent(matsu5, attacker, 20, 10)
        engine.event(wcf)
        # Matsu's LW must reset to 0 (standard behavior), not 15.
        self.assertEqual(
            0, matsu5.lw(),
            f"Matsu's own failed WC must use standard reset-to-0 "
            f"behavior; got LW={matsu5.lw()}.",
        )


class TestMatsuDoubleAttackParried(unittest.TestCase):
    def setUp(self):
        self.matsu = Character("Matsu")
        self.matsu.set_actions([1])
        self.target = Character("target")
        self.target.set_skill("parry", 3)
        groups = [Group("Lion", self.matsu), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_parried_not_hit(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(25)
        # Simulate successful parry
        action.set_parried()
        self.assertFalse(action.is_hit())

    def test_parry_attempted_no_direct_damage(self):
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        action.set_skill_roll(45)  # Above TN
        action.set_parry_attempted()
        self.assertIsNone(action.direct_damage())

    def test_normal_hit_extra_dice(self):
        """A clean hit on `MatsuDoubleAttackAction` must yield the
        SAME extra-damage-dice count as the parent ``DoubleAttackAction``.

        Rules-auditor #1 (2026-05-28): the earlier version of this
        test pinned a bug — it asserted 2 extra dice based on the
        Matsu code passing the inflated DA TN (``self.tn()``, =
        base + 20) to the parent's ``(roll - tn) // 5`` formula.  The
        parent expects the BASE TN (``self.tn() - 20``); passing the
        inflated TN under-counted the extra dice by 4.  The correct
        formula for a roll of ``tn() + 10`` (i.e., 30 above the BASE
        hit TN) yields ``30 // 5 = 6`` extra dice.
        """
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack", self.initiative_action, self.context,
        )
        tn = action.tn()
        action.set_skill_roll(tn + 10)  # Exceed DA TN by 10 (= base TN + 30)
        # Normal hit: extra dice = (roll - base_tn) // 5 = (tn + 10 - (tn - 20)) // 5 = 30 // 5 = 6
        self.assertEqual(6, action.calculate_extra_damage_dice())

    def test_is_near_miss_false_when_parried(self):
        """The ``_is_near_miss`` property MUST return False for parried
        actions -- the 4th Dan carve-out does not apply when the attack
        was successfully parried.  rules/04-schools.md "Matsu Bushi
        School: Fourth Dan"."""
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack",
            self.initiative_action, self.context,
        )
        action.set_skill_roll(25)  # would be a near-miss if unparried
        action.set_parried()
        # Even though the roll lies in the near-miss band, a parried
        # attack is NOT a near-miss for trace-attribution purposes.
        self.assertFalse(action._is_near_miss)

    def test_is_near_miss_true_for_near_miss_roll(self):
        """The ``_is_near_miss`` property MUST return True when the
        skill_roll lies in the carve-out band ``tn-20 <= roll < tn``.
        rules/04-schools.md "Matsu Bushi School: Fourth Dan"."""
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack",
            self.initiative_action, self.context,
        )
        action.set_skill_roll(25)  # TN = 40, near-miss band 20..39
        self.assertTrue(action._is_near_miss)

    def test_is_near_miss_false_for_clean_hit(self):
        """The ``_is_near_miss`` property MUST return False for a
        clean hit (skill_roll >= TN).  FR-021."""
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack",
            self.initiative_action, self.context,
        )
        action.set_skill_roll(45)  # TN = 40, this is a clean hit
        self.assertFalse(action._is_near_miss)


class TestMatsu3rdDanTraceObservability(unittest.TestCase):
    """T008 — verify the Matsu 3rd Dan trace surfaces both the
    floating-bonus gain (on VP spend) AND its consumption (on a
    later WC roll), both with explicit "Matsu 3rd Dan" attribution
    per Constitution Principle VII / FR-013.

    rules/04-schools.md "Matsu Bushi School: Third Dan".
    """

    def setUp(self) -> None:
        self.matsu = Character("Matsu")
        self.matsu.set_skill("attack", 4)
        self.matsu.gain_tvp(5)
        self.enemy = Character("enemy")
        groups = [Group("Lion", self.matsu), Group("Enemy", self.enemy)]
        self.context = EngineContext(groups)
        school = matsu_school.MatsuBushiSchool()
        self.matsu.set_school(school)
        school.apply_rank_three_ability(self.matsu)

    def test_vp_spend_emits_gain_floating_bonus_event_with_source(self) -> None:
        """The 3rd Dan listener MUST yield a ``GainFloatingBonusEvent``
        with ``source="Matsu 3rd Dan"`` so the trace formatter can
        attribute the gain.  FR-013."""
        listener = matsu_school.MatsuSpendVoidPointsListener()
        event = events.SpendVoidPointsEvent(self.matsu, "attack", 1)
        responses = list(listener.handle(self.matsu, event, self.context))
        gain_events = [
            e for e in responses
            if isinstance(e, events.GainFloatingBonusEvent)
        ]
        self.assertEqual(1, len(gain_events))
        gain = gain_events[0]
        self.assertEqual(self.matsu, gain.subject)
        self.assertEqual(12, gain.bonus.bonus())
        self.assertEqual("Matsu 3rd Dan", gain.source)

    def test_floating_bonus_carries_matsu_3rd_dan_source(self) -> None:
        """The granted ``WoundCheckFloatingBonus`` itself MUST carry
        ``source="Matsu 3rd Dan"`` so that ``SpendFloatingBonusEvent``
        consumption picks up the source from the bonus.  FR-013."""
        listener = matsu_school.MatsuSpendVoidPointsListener()
        event = events.SpendVoidPointsEvent(self.matsu, "attack", 1)
        list(listener.handle(self.matsu, event, self.context))
        bonuses = self.matsu.floating_bonuses("wound check")
        self.assertEqual(1, len(bonuses))
        self.assertEqual("Matsu 3rd Dan", bonuses[0].source())

    def test_gain_surfaces_in_text_renderer_trace(self) -> None:
        """A combat trace containing the gain event surfaces "Matsu 3rd
        Dan" in the user-visible text rendering.  FR-013."""
        listener = matsu_school.MatsuSpendVoidPointsListener()
        spend_event = events.SpendVoidPointsEvent(self.matsu, "attack", 1)
        responses = list(listener.handle(self.matsu, spend_event, self.context))
        gain = next(
            e for e in responses
            if isinstance(e, events.GainFloatingBonusEvent)
        )
        fmt = DetailedEventFormatter()
        joined = "\n".join(fmt.format_history([
            events.NewPhaseEvent(phase=1), gain,
        ]))
        self.assertIn("Matsu 3rd Dan", joined)
        self.assertIn("+12", joined)

    def test_gain_surfaces_in_bulleted_renderer_trace(self) -> None:
        """Same trace assertion as above but for the bulleted renderer.
        Both renderers MUST surface the attribution per Principle VII.
        FR-013."""
        listener = matsu_school.MatsuSpendVoidPointsListener()
        spend_event = events.SpendVoidPointsEvent(self.matsu, "attack", 1)
        responses = list(listener.handle(self.matsu, spend_event, self.context))
        gain = next(
            e for e in responses
            if isinstance(e, events.GainFloatingBonusEvent)
        )
        fmt = DetailedEventFormatter()
        entries = fmt.entries([events.NewPhaseEvent(phase=1), gain])
        joined = BulletedRenderer().render(entries)
        self.assertIn("Matsu 3rd Dan", joined)
        self.assertIn("+12", joined)

    def test_consumption_surfaces_with_matsu_3rd_dan_attribution(self) -> None:
        """When the WC floating bonus is later consumed (via a
        ``SpendFloatingBonusEvent``), the trace MUST attribute the
        consumption to "Matsu 3rd Dan" -- the source carried on the
        bonus instance.  FR-013."""
        # Grant the bonus first.
        listener = matsu_school.MatsuSpendVoidPointsListener()
        spend_event = events.SpendVoidPointsEvent(self.matsu, "attack", 1)
        list(listener.handle(self.matsu, spend_event, self.context))
        bonus = self.matsu.floating_bonuses("wound check")[0]
        # Now emit a consumption event (as the WC strategy would).
        consume_event = events.SpendFloatingBonusEvent(self.matsu, bonus)
        fmt = DetailedEventFormatter()
        entries = fmt.entries([
            events.NewPhaseEvent(phase=1), consume_event,
        ])
        text = "\n".join(TextRenderer().render_lines(entries))
        self.assertIn("Matsu 3rd Dan", text)
        bulleted = BulletedRenderer().render(entries)
        self.assertIn("Matsu 3rd Dan", bulleted)


class TestMatsu4thDanNearMissTraceObservability(unittest.TestCase):
    """T010 — the 4th Dan near-miss double attack MUST surface in the
    attack-entry rendering with explicit "Matsu 4th Dan: near-miss"
    attribution in both renderers.  A clean hit MUST NOT show the
    attribution.  FR-021 / Constitution Principle VII.

    rules/04-schools.md "Matsu Bushi School: Fourth Dan".
    """

    def setUp(self) -> None:
        self.matsu = Character("Matsu")
        self.matsu.set_actions([1])
        self.matsu.set_skill("double attack", 5)
        self.matsu.set_skill("fire", 4)
        self.target = Character("target")
        self.target.set_skill("parry", 3)
        groups = [Group("Lion", self.matsu), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def _build_attack_history(self, skill_roll: int) -> list[Any]:
        """Build a minimal event history containing a near-miss /
        clean-hit ``MatsuDoubleAttackAction`` so the formatter can
        synthesize an ``AttackEntry`` from it."""
        action = matsu_school.MatsuDoubleAttackAction(
            self.matsu, self.target, "double attack",
            self.initiative_action, self.context,
        )
        action.set_skill_roll(skill_roll)
        # Manually annotate the rolled event with the detail fields the
        # combat-observer normally adds (so the formatter exercises the
        # full has_detail path).
        rolled = events.AttackRolledEvent(action, skill_roll)
        rolled._detail_dice = [skill_roll]  # type: ignore[attr-defined]
        rolled._detail_params = (1, 1, 0)  # type: ignore[attr-defined]
        rolled._detail_tn = action.tn()  # type: ignore[attr-defined]
        rolled._detail_base_tn = self.target.tn_to_hit()  # type: ignore[attr-defined]
        rolled._detail_modifier_breakdown = []  # type: ignore[attr-defined]
        rolled._detail_components = []  # type: ignore[attr-defined]
        take = events.TakeAttackActionEvent(action)
        return [
            events.NewPhaseEvent(phase=1),
            take, rolled,
        ]

    def test_near_miss_attribution_in_text_renderer(self) -> None:
        """A near-miss double attack (skill_roll = TN - 10) MUST render
        with "Matsu 4th Dan: near-miss" attribution in the text trace.
        FR-021."""
        tn = self.target.tn_to_hit() + 20  # double attack TN
        history = self._build_attack_history(tn - 10)
        fmt = DetailedEventFormatter()
        text = "\n".join(fmt.format_history(history))
        self.assertIn("Matsu 4th Dan", text)
        self.assertIn("near-miss", text)
        # The numeric "below TN" annotation surfaces the margin.
        self.assertIn("10 below TN", text)
        # trace-reader #1 (2026-05-28) — explicit mechanical framing:
        # the line MUST say "counts as hit" so a fresh reader doesn't
        # see "HIT!" + "near-miss" and think the renderer is wrong.
        self.assertIn("counts as hit", text)

    def test_near_miss_attribution_in_bulleted_renderer(self) -> None:
        """Same attribution check as above but for the bulleted
        renderer (Principle VII cross-renderer coverage).  FR-021."""
        tn = self.target.tn_to_hit() + 20
        history = self._build_attack_history(tn - 10)
        fmt = DetailedEventFormatter()
        entries = fmt.entries(history)
        bulleted = BulletedRenderer().render(entries)
        self.assertIn("Matsu 4th Dan", bulleted)
        self.assertIn("near-miss", bulleted)
        self.assertIn("10 below TN", bulleted)
        # Same mechanical framing as TextRenderer.
        self.assertIn("counts as hit", bulleted)

    def test_clear_hit_does_not_show_near_miss_attribution(self) -> None:
        """A clean hit (skill_roll >= TN) MUST NOT show the "near-miss"
        attribution -- the 4th Dan carve-out only applies when the roll
        was below TN.  FR-021."""
        tn = self.target.tn_to_hit() + 20
        history = self._build_attack_history(tn + 5)  # clean hit
        fmt = DetailedEventFormatter()
        text = "\n".join(fmt.format_history(history))
        self.assertNotIn("near-miss", text)
        self.assertNotIn("Matsu 4th Dan", text)
        # Same check for the bulleted renderer.
        entries = fmt.entries(history)
        bulleted = BulletedRenderer().render(entries)
        self.assertNotIn("near-miss", bulleted)
        self.assertNotIn("Matsu 4th Dan", bulleted)


class TestMatsu5thDanTraceObservability(unittest.TestCase):
    """T012 — when a Matsu's attack causes a failed WC, the LW-floor
    behavior (LW set to 15 instead of 0) MUST surface in the trace
    with "Matsu 5th Dan" attribution in both renderers.  A non-Matsu
    attacker keeps the standard rendering (no Matsu attribution).
    Constitution Principle VII / FR-023.

    rules/04-schools.md "Matsu Bushi School: Fifth Dan".
    """

    def setUp(self) -> None:
        self.matsu = Character("Matsu")
        self.matsu.set_actions([1])
        self.defender = Character("defender")
        self.defender._lw = 20
        groups = [Group("Lion", self.matsu), Group("Enemy", self.defender)]
        self.context = EngineContext(groups)

    def _build_5th_dan_history(self) -> list[Any]:
        """Build a minimal history containing the SW event + the
        Matsu 5th Dan LW-floor event so the formatter can render it.

        Updated 2026-05-28 per rules-auditor BLOCKING fix: the
        listener slot moved from ``wound_check_failed`` to
        ``sw_damage``; trace history now constructs a SW event and
        passes it through the new listener.
        """
        sw_event = events.SeriousWoundsDamageEvent(
            self.matsu, self.defender, 2,
        )
        listener = matsu_school.MatsuSeriousWoundsDamageListener()
        responses = list(listener.handle(self.matsu, sw_event, self.context))
        # Only include the Matsu trace marker, not the SW event itself
        # (the SW event would normally be in the history from the
        # default WCF path; we synthesize that path here by emitting
        # the SW event and the resulting floor event).
        floor_events = [
            r for r in responses
            if isinstance(r, events.MatsuLightWoundsFloorEvent)
        ]
        return [events.NewPhaseEvent(phase=1), sw_event, *floor_events]

    def test_lw_floor_attribution_in_text_renderer(self) -> None:
        """The Matsu 5th Dan LW-floor MUST surface with "Matsu 5th Dan"
        attribution in the text trace.  FR-023."""
        history = self._build_5th_dan_history()
        fmt = DetailedEventFormatter()
        text = "\n".join(fmt.format_history(history))
        self.assertIn("Matsu 5th Dan", text)
        self.assertIn("15", text)
        # The "instead of 0" comparison clause surfaces the rules-text
        # baseline so the playtester sees what changed.
        self.assertIn("instead of 0", text)

    def test_lw_floor_attribution_in_bulleted_renderer(self) -> None:
        """Cross-renderer coverage of the 5th Dan attribution.
        FR-023."""
        history = self._build_5th_dan_history()
        fmt = DetailedEventFormatter()
        entries = fmt.entries(history)
        bulleted = BulletedRenderer().render(entries)
        self.assertIn("Matsu 5th Dan", bulleted)
        self.assertIn("15", bulleted)
        self.assertIn("instead of 0", bulleted)

    def test_non_matsu_attacker_no_5th_dan_attribution(self) -> None:
        """When a non-Matsu (e.g., Akodo) causes the failed WC, the
        standard "LW reset to 0" rendering applies -- NO Matsu
        attribution leaks into other schools' traces.  FR-025."""
        non_matsu = Character("Akodo")
        defender = Character("victim")
        defender._lw = 30
        wc_failed = events.WoundCheckFailedEvent(
            defender, non_matsu, damage=30, roll=10,
        )
        # Use the engine default listener (the path for a non-Matsu
        # attacker) -- defender's reset_lw and yielded SW only.
        from simulation import listeners
        default = listeners.WoundCheckFailedListener()
        responses = list(default.handle(defender, wc_failed, self.context))
        history = [events.NewPhaseEvent(phase=1), *responses]
        fmt = DetailedEventFormatter()
        text = "\n".join(fmt.format_history(history))
        self.assertNotIn("Matsu 5th Dan", text)
        entries = fmt.entries(history)
        bulleted = BulletedRenderer().render(entries)
        self.assertNotIn("Matsu 5th Dan", bulleted)
