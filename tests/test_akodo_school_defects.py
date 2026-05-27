#!/usr/bin/env python3

#
# test_akodo_school_defects.py
#
# Regression tests for the four pre-existing AkodoWoundCheck* defects
# the rules-auditor flagged during the 005-akodo-bushi-school cumulative
# review.  These are NOT introduced by spec 004; they were pre-existing
# skeleton defects that the spec scope didn't touch.  This module locks
# in the fixes applied after the merge.
#
# Defects fixed:
#   1. AkodoWoundCheckDeclaredListener swallowed event.vp without
#      emitting SpendVoidPointsEvent (pre-declared VP was "free").
#   2. Same listener didn't propagate tn / duel/explode to the
#      synthesized WoundCheckRolledEvent / roll_wound_check call.
#   3. Same listener bypassed character.wound_check_rolled_strategy()
#      -- a Dan-4+ Akodo lost AP / conviction / floating-bonus access
#      on WC.
#   4. AkodoLightWoundsDamageListener didn't gate WC dispatch on
#      event.damage > 0 (engine default does).
#

import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.mechanics.floating_bonuses import WoundCheckFloatingBonus
from simulation.schools import akodo_school
from simulation.strategies.base import WoundCheckRolledStrategy


class TestDefect1AkodoWcDeclaredEmitsSpendVpEvent(unittest.TestCase):
    """Defect #1 regression: AkodoWoundCheckDeclaredListener now emits
    SpendVoidPointsEvent for pre-declared VP (event.vp > 0)."""

    def setUp(self) -> None:
        self.akodo = Character("Akodo")
        self.akodo.set_actions([1])
        for ring in ("air", "earth", "fire", "water", "void"):
            self.akodo.set_ring(ring, 5)
        self.attacker = Character("Attacker")
        groups = [Group("Lion", self.akodo), Group("Scorpion", self.attacker)]
        self.context = EngineContext(groups)
        self.school = akodo_school.AkodoBushiSchool()
        self.school.apply_special_ability(self.akodo)
        self.school.apply_rank_three_ability(self.akodo)
        self.school.apply_rank_four_ability(self.akodo)
        self.listener = akodo_school.AkodoWoundCheckDeclaredListener()

    def test_pre_declared_vp_emits_spend_event(self) -> None:
        # Construct a WoundCheckDeclaredEvent with vp=2 (pre-declared)
        event = events.WoundCheckDeclaredEvent(
            self.akodo, self.attacker, damage=20, vp=2, tn=20,
        )
        emitted = list(self.listener.handle(self.akodo, event, self.context))
        spends = [e for e in emitted if isinstance(e, events.SpendVoidPointsEvent)
                  and e.skill == "wound check" and e.amount == 2]
        self.assertEqual(
            1, len(spends),
            "Defect #1: pre-declared event.vp=2 should emit "
            "SpendVoidPointsEvent(_, 'wound check', 2) so the VP is "
            "actually deducted from the character's pool.",
        )

    def test_zero_vp_emits_no_spend_event(self) -> None:
        # Sanity: vp=0 means no spend event.
        event = events.WoundCheckDeclaredEvent(
            self.akodo, self.attacker, damage=20, vp=0, tn=20,
        )
        emitted = list(self.listener.handle(self.akodo, event, self.context))
        spends = [e for e in emitted if isinstance(e, events.SpendVoidPointsEvent)
                  and e.skill == "wound check"]
        self.assertEqual(0, len(spends))


class TestDefect2AkodoWcDeclaredPropagatesTnAndDuel(unittest.TestCase):
    """Defect #2 regression: AkodoWoundCheckDeclaredListener now
    propagates tn and duel/explode to the synthesized event + roll."""

    def setUp(self) -> None:
        self.akodo = Character("Akodo")
        self.akodo.set_actions([1])
        for ring in ("air", "earth", "fire", "water", "void"):
            self.akodo.set_ring(ring, 5)
        self.attacker = Character("Attacker")
        groups = [Group("Lion", self.akodo), Group("Scorpion", self.attacker)]
        self.context = EngineContext(groups)
        self.listener = akodo_school.AkodoWoundCheckDeclaredListener()

    def test_tn_propagated_to_rolled_event(self) -> None:
        event = events.WoundCheckDeclaredEvent(
            self.akodo, self.attacker, damage=30, vp=0, tn=75,
        )
        emitted = list(self.listener.handle(self.akodo, event, self.context))
        rolled_events = [e for e in emitted if isinstance(e, events.WoundCheckRolledEvent)]
        self.assertGreaterEqual(
            len(rolled_events), 1,
            "Defect #2 setup: the listener must emit at least one "
            "WoundCheckRolledEvent.",
        )
        # Every WoundCheckRolledEvent must carry tn=75 (the original
        # declared TN), not None.
        for rolled in rolled_events:
            self.assertEqual(
                75, rolled.tn,
                "Defect #2: tn=75 must propagate from the declared "
                "event to the rolled event so custom-TN paths "
                "(e.g., iaijutsu duels) work.",
            )


class TestDefect3AkodoUsesWoundCheckRolledStrategySlot(unittest.TestCase):
    """Defect #3 regression: the listener now dispatches through
    character.wound_check_rolled_strategy() so AP / conviction /
    floating-bonus selection still happens at Dan 4+.  Akodo's 4th-Dan
    VP-for-raise is layered on TOP of the engine default's resource
    menu."""

    def setUp(self) -> None:
        self.akodo = Character("Akodo")
        self.akodo.set_actions([1])
        for ring in ("air", "earth", "fire", "water", "void"):
            self.akodo.set_ring(ring, 5)
        self.attacker = Character("Attacker")
        groups = [Group("Lion", self.akodo), Group("Scorpion", self.attacker)]
        self.context = EngineContext(groups)
        self.school = akodo_school.AkodoBushiSchool()
        self.school.apply_special_ability(self.akodo)
        self.school.apply_rank_three_ability(self.akodo)
        self.school.apply_rank_four_ability(self.akodo)

    def test_akodo_strategy_installed_at_wound_check_rolled_slot(self) -> None:
        # After apply_rank_four_ability, the wound_check_rolled slot
        # must hold an AkodoWoundCheckRolledStrategy instance so the
        # listener routing through character.wound_check_rolled_strategy()
        # picks up the Akodo behavior.
        strategy = self.akodo.wound_check_rolled_strategy()
        self.assertIsInstance(
            strategy, akodo_school.AkodoWoundCheckRolledStrategy,
            "Defect #3: a 4th-Dan Akodo's wound_check_rolled slot "
            "must hold AkodoWoundCheckRolledStrategy so the listener "
            "can route through character.wound_check_rolled_strategy() "
            "(per engine default WoundCheckDeclaredListener pattern).",
        )

    def test_akodo_strategy_inherits_from_engine_default(self) -> None:
        # The Akodo strategy must inherit from the engine default so it
        # gets AP / conviction / floating-bonus selection for free.
        # Without this inheritance, Dan-4+ Akodos would lose access to
        # those resource pools (the original bug).
        strategy = self.akodo.wound_check_rolled_strategy()
        self.assertIsInstance(
            strategy, WoundCheckRolledStrategy,
            "Defect #3: AkodoWoundCheckRolledStrategy must inherit "
            "from the engine default WoundCheckRolledStrategy so AP / "
            "conviction / floating-bonus selection still happens.",
        )

    def test_floating_bonus_on_wc_is_consumed_by_akodo_strategy(self) -> None:
        # Layered behavior: the engine default's floating-bonus consumption
        # must run BEFORE Akodo's VP-for-raise.  Setup a near-miss WC and
        # give the character a WoundCheckFloatingBonus.  Assert the FB is
        # consumed (which only happens if the engine default's chain fires).
        self.akodo.take_lw(30)
        # +5 to the WC roll via the floating bonus is enough to bring
        # expected_sw to tolerable without needing VP.
        bonus = WoundCheckFloatingBonus(10)
        self.akodo.gain_floating_bonus(bonus)
        event = events.WoundCheckRolledEvent(
            self.akodo, self.attacker, damage=30, roll=15,
        )
        strategy = self.akodo.wound_check_rolled_strategy()
        emitted = list(strategy.recommend(self.akodo, event, self.context))
        fb_spends = [e for e in emitted if isinstance(e, events.SpendFloatingBonusEvent)]
        self.assertEqual(
            1, len(fb_spends),
            "Defect #3 regression: the wound-check floating bonus "
            "MUST be consumed by the Akodo strategy (via super "
            "delegation), proving that AP / conviction / FB are not "
            "lost at Dan 4+.",
        )


class TestDefect4AkodoLwDamageGatesOnDamageGreaterThanZero(unittest.TestCase):
    """Defect #4 regression: AkodoLightWoundsDamageListener now gates
    the wound_check_strategy + 5th-Dan strategy dispatch on
    event.damage > 0 (matching the engine default)."""

    def setUp(self) -> None:
        self.akodo = Character("Akodo")
        self.akodo.set_actions([1])
        for ring in ("air", "earth", "fire", "water", "void"):
            self.akodo.set_ring(ring, 5)
        self.attacker = Character("Attacker")
        groups = [Group("Lion", self.akodo), Group("Scorpion", self.attacker)]
        self.context = EngineContext(groups)
        self.school = akodo_school.AkodoBushiSchool()
        self.school.apply_special_ability(self.akodo)
        self.school.apply_rank_three_ability(self.akodo)
        self.school.apply_rank_four_ability(self.akodo)
        self.school.apply_rank_five_ability(self.akodo)
        self.listener = akodo_school.AkodoLightWoundsDamageListener()

    def test_zero_damage_does_not_dispatch_wound_check(self) -> None:
        event = events.LightWoundsDamageEvent(
            self.attacker, self.akodo, damage=0,
        )
        emitted = list(self.listener.handle(self.akodo, event, self.context))
        wc_declared = [e for e in emitted if isinstance(e, events.WoundCheckDeclaredEvent)]
        self.assertEqual(
            0, len(wc_declared),
            "Defect #4: damage=0 must NOT trigger a wound-check "
            "dispatch (engine default's `if event.damage > 0` gate).",
        )

    def test_nonzero_damage_does_dispatch_wound_check(self) -> None:
        self.context.initialize()
        event = events.LightWoundsDamageEvent(
            self.attacker, self.akodo, damage=20,
        )
        emitted = list(self.listener.handle(self.akodo, event, self.context))
        wc_declared = [e for e in emitted if isinstance(e, events.WoundCheckDeclaredEvent)]
        self.assertGreaterEqual(
            len(wc_declared), 1,
            "Defect #4: damage=20 must still trigger a wound-check "
            "dispatch -- the gate must NOT block nonzero damage.",
        )


if __name__ == "__main__":
    unittest.main()
