"""Tests for combat-trace observability of Mirumoto-school modifiers.

These tests pin Constitution Principle VII: every applied modifier on
a combat roll appears in the user-facing combat trace with BOTH a
numeric effect AND a source attribution where the source is a known
school ability.

Specifically:

- Mirumoto Bushi School Fifth Dan ("When you spend a Void Point on an
  attack, parry, or wound check roll, that roll gets +10 instead of
  the normal +5") -- per rules/04-schools.md, this is a +10 modifier
  per VP on top of the standard void-spend dice. The trace must show
  the modifier value AND attribute it to "Mirumoto 5th Dan".
- Mirumoto Bushi School Second Dan ("Free Raise on parry") -- per
  rules/04-schools.md, this is a +5 modifier on parry rolls. The
  trace must show the modifier value AND attribute it to "Mirumoto
  2nd Dan free raise".

The reference behavior is implemented in
``web/adapters/modifier_breakdown.explain_modifier``, which is wired
into ``CombatObserver`` for attack/parry/counterattack/wound-check
events and rendered by ``DetailedEventFormatter``.
"""

from __future__ import annotations

import unittest
from typing import Any
from unittest.mock import MagicMock

from simulation import events
from simulation.character import Character
from simulation.schools import mirumoto_school
from web.adapters.combat_observer import CombatObserver
from web.adapters.detailed_formatter import DetailedEventFormatter
from web.adapters.modifier_breakdown import explain_modifier


def _make_fifth_dan_mirumoto(name: str = "Mirumoto5th") -> Character:
    """Construct a 5th-dan Mirumoto Bushi.

    Mirroring the construction pattern in tests/test_mirumoto_school.py,
    this builds knacks to rank 5 and applies all school abilities so
    that helpers reading ``character.school()`` + the knack-min derived
    rank see a true 5th-dan character. The school's parry free raise
    (2nd Dan) is also applied so combined-source attribution can be
    exercised by other tests if needed.
    """
    char = Character(name)
    char.set_ring("fire", 3)
    char.set_ring("water", 3)
    char.set_ring("void", 3)
    char.set_skill("attack", 5)
    char.set_skill("parry", 5)
    school = mirumoto_school.MirumotoBushiSchool()
    char.set_school(school)
    # Bring all school knacks to 5 so the derived school_rank (min knack)
    # equals 5; explain_modifier reads this to gate 5th Dan attribution.
    for knack in school.school_knacks():
        char.set_skill(knack, 5)
    # Apply each rank ability in sequence so the character has every
    # mechanical effect a true 5th-dan Mirumoto has installed.
    school.apply_rank_one_ability(char)
    school.apply_rank_two_ability(char)
    school.apply_rank_five_ability(char)
    return char


def _make_second_dan_mirumoto(name: str = "Mirumoto2nd") -> Character:
    """Construct a 2nd-dan Mirumoto Bushi (free raise on parry, no +10)."""
    char = Character(name)
    char.set_ring("fire", 3)
    char.set_ring("water", 3)
    char.set_ring("void", 3)
    char.set_skill("attack", 2)
    char.set_skill("parry", 2)
    school = mirumoto_school.MirumotoBushiSchool()
    char.set_school(school)
    for knack in school.school_knacks():
        char.set_skill(knack, 2)
    school.apply_rank_one_ability(char)
    school.apply_rank_two_ability(char)
    return char


def _make_first_dan_mirumoto(name: str = "Mirumoto1st") -> Character:
    """Construct a 1st-dan Mirumoto Bushi (no +5 free raise, no +10)."""
    char = Character(name)
    char.set_ring("fire", 3)
    char.set_ring("water", 3)
    char.set_ring("void", 3)
    char.set_skill("attack", 1)
    char.set_skill("parry", 1)
    school = mirumoto_school.MirumotoBushiSchool()
    char.set_school(school)
    school.apply_rank_one_ability(char)
    return char


class TestExplainModifierMirumotoFifthDan(unittest.TestCase):
    """``explain_modifier`` recognises Mirumoto 5th Dan VP-modifier contributions.

    rules/04-schools.md Mirumoto Bushi School Fifth Dan: "+10 per VP on
    combat rolls". The helper should attribute the modifier to the
    school ability when (a) the character is a 5th-dan Mirumoto, (b)
    VP was spent, and (c) the skill is in the combat-roll set.
    """

    def test_fifth_dan_attack_with_three_vp(self):
        char = _make_fifth_dan_mirumoto()
        breakdown = explain_modifier(char, "attack", modifier=30, vp=3)
        self.assertIn(("Mirumoto 5th Dan", 30), breakdown)

    def test_fifth_dan_parry_with_one_vp(self):
        char = _make_fifth_dan_mirumoto()
        # Parry triggers BOTH the 2nd-Dan free raise (+5) and the
        # 5th-Dan +10/VP. Total modifier passed in is 15 (= 5 + 10).
        breakdown = explain_modifier(char, "parry", modifier=15, vp=1)
        labels = [label for (label, _val) in breakdown]
        self.assertIn("Mirumoto 5th Dan", labels)
        self.assertIn("Mirumoto 2nd Dan free raise", labels)

    def test_fifth_dan_wound_check_with_three_vp(self):
        char = _make_fifth_dan_mirumoto()
        breakdown = explain_modifier(char, "wound check", modifier=30, vp=3)
        self.assertIn(("Mirumoto 5th Dan", 30), breakdown)

    def test_fifth_dan_no_vp_no_attribution(self):
        char = _make_fifth_dan_mirumoto()
        breakdown = explain_modifier(char, "attack", modifier=0, vp=0)
        labels = [label for (label, _val) in breakdown]
        self.assertNotIn("Mirumoto 5th Dan", labels)


class TestExplainModifierMirumotoSecondDan(unittest.TestCase):
    """``explain_modifier`` recognises Mirumoto 2nd Dan free-raise on parry."""

    def test_second_dan_parry_free_raise(self):
        char = _make_second_dan_mirumoto()
        breakdown = explain_modifier(char, "parry", modifier=5, vp=0)
        self.assertIn(("Mirumoto 2nd Dan free raise", 5), breakdown)

    def test_second_dan_attack_no_free_raise(self):
        char = _make_second_dan_mirumoto()
        breakdown = explain_modifier(char, "attack", modifier=0, vp=0)
        self.assertEqual([], breakdown)


class TestExplainModifierNonMirumoto(unittest.TestCase):
    """Non-Mirumoto characters get no school-specific attribution."""

    def test_non_mirumoto_returns_empty_list(self):
        char = Character("Plain")
        breakdown = explain_modifier(char, "attack", modifier=5, vp=1)
        self.assertEqual([], breakdown)


# ---------------------------------------------------------------------------
# End-to-end formatter trace tests
# ---------------------------------------------------------------------------


def _make_skill_action(
    subject: Any,
    target: Any,
    skill: str,
    skill_roll: int,
    tn: int,
    vp: int,
    rolled: int,
    kept: int,
    modifier: int,
    is_hit: bool = True,
    parried: bool = False,
    parry_attempted: bool = False,
) -> MagicMock:
    action = MagicMock()
    action.subject.return_value = subject
    action.target.return_value = target
    action.skill.return_value = skill
    action.skill_roll.return_value = skill_roll
    action.tn.return_value = tn
    action.vp.return_value = vp
    action.skill_roll_params.return_value = (rolled, kept, modifier)
    action.is_hit.return_value = is_hit
    action.parried.return_value = parried
    action.parry_attempted.return_value = parry_attempted
    action.is_success.return_value = is_hit  # for parry actions
    action.calculate_extra_damage_dice.return_value = 0
    return action


class TestFormatterShowsWoundCheckModifier(unittest.TestCase):
    """``DetailedEventFormatter`` shows the modifier on wound-check lines.

    Currently the formatter only renders the kept_sum; the modifier is
    silently dropped. Per Constitution Principle VII the modifier MUST
    be displayed so the user can audit the trace.
    """

    def test_wound_check_modifier_rendered_when_nonzero(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Mirumoto"
        attacker = MagicMock()
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 74, tn=71)
        event._detail_dice = [9, 9, 9, 7, 5, 3, 2, 2, 1]
        event._detail_params = (9, 7, 30)  # rolled, kept, modifier

        lines = fmt.format_history([event])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        # The displayed kept_sum is 9+9+9+7+5+3+2 = 44; the modifier
        # value must appear alongside it, plus the total = 74.
        self.assertIn("+30", wc_line)
        self.assertIn("74", wc_line)

    def test_wound_check_modifier_zero_not_rendered(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Mirumoto"
        attacker = MagicMock()
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 44, tn=71)
        event._detail_dice = [9, 9, 9, 7, 5, 3, 2, 2, 1]
        event._detail_params = (9, 7, 0)  # zero modifier

        lines = fmt.format_history([event])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        # No "+0" should appear (and certainly no "+5"/"+10" etc).
        self.assertNotIn("+0", wc_line)
        self.assertNotIn("+5", wc_line)

    def test_legacy_two_tuple_detail_params_still_works(self):
        """Backwards-compat: legacy ``(rolled, kept)`` 2-tuple still renders."""
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 35, tn=30)
        event._detail_dice = [9, 6, 5, 2]
        event._detail_params = (4, 3)  # old 2-tuple format

        lines = fmt.format_history([event])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        self.assertIn("PASSED", wc_line)
        self.assertIn("TN 30", wc_line)


class TestObserverAnnotatesWoundCheckModifier(unittest.TestCase):
    """``CombatObserver`` stores the modifier on wound-check events.

    Per Constitution Principle VII, the raw mechanical data (dice +
    modifier) must be captured on the event so the formatter can
    render it. The fix is to extend ``_detail_params`` from a 2-tuple
    to a 3-tuple: ``(rolled, kept, modifier)``.
    """

    def test_observer_stores_three_tuple_with_modifier(self):
        observer = CombatObserver()
        subject = MagicMock()
        subject.name.return_value = "Mirumoto"
        # Mock provider returning dice such that kept_sum < event.roll,
        # so the modifier can be inferred as (roll - kept_sum).
        provider = MagicMock()
        provider.last_wound_check_info.return_value = {
            "rolled": 9,
            "kept": 7,
            "dice": [9, 9, 9, 7, 5, 3, 2, 2, 1],
        }
        subject.roll_provider.return_value = provider

        event = events.WoundCheckRolledEvent(subject, MagicMock(), 30, 74, tn=71)
        observer._annotate_wound_check(event)

        # _detail_params should be a 3-tuple ending in the modifier.
        self.assertEqual(3, len(event._detail_params))
        rolled, kept, modifier = event._detail_params
        self.assertEqual(9, rolled)
        self.assertEqual(7, kept)
        # kept_sum = 9+9+9+7+5+3+2 = 44; modifier = 74 - 44 = 30.
        self.assertEqual(30, modifier)


class TestFormatterShowsSourceAttribution(unittest.TestCase):
    """``DetailedEventFormatter`` appends source attribution when known.

    Per Constitution Principle VII, when ``_detail_modifier_breakdown``
    is non-empty and sums to the modifier on the roll, the formatter
    appends a parenthetical attribution like
    ``(Mirumoto 5th Dan: +10 x 3 VP)`` so the user knows where the
    modifier came from.
    """

    def test_attack_roll_with_fifth_dan_attribution(self):
        fmt = DetailedEventFormatter()
        mirumoto = _make_fifth_dan_mirumoto()
        target = MagicMock()
        target.name.return_value = "Enemy"
        target.tn_to_hit.return_value = 20
        action = _make_skill_action(
            subject=mirumoto, target=target, skill="attack",
            skill_roll=80, tn=20, vp=3,
            rolled=10, kept=6, modifier=30,
        )
        event = events.AttackRolledEvent(action, 80)
        event._detail_dice = [10, 10, 9, 8, 7, 6, 5, 4, 3, 2]
        event._detail_params = (10, 6, 30)
        event._detail_tn = 20
        event._detail_base_tn = 20
        event._detail_modifier_breakdown = [("Mirumoto 5th Dan", 30)]

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        self.assertIn("+30", attack_line)
        self.assertIn("Mirumoto 5th Dan", attack_line)

    def test_parry_roll_with_second_dan_free_raise(self):
        fmt = DetailedEventFormatter()
        mirumoto = _make_second_dan_mirumoto()
        target = MagicMock()
        target.name.return_value = "Enemy"
        action = _make_skill_action(
            subject=mirumoto, target=target, skill="parry",
            skill_roll=40, tn=20, vp=0,
            rolled=5, kept=3, modifier=5,
        )
        event = events.ParryRolledEvent(action, 40)
        event._detail_dice = [10, 9, 8, 5, 2]
        event._detail_params = (5, 3, 5)
        event._detail_tn = 20
        event._detail_modifier_breakdown = [("Mirumoto 2nd Dan free raise", 5)]

        lines = fmt.format_history([event])
        parry_line = [ln for ln in lines if "Parry:" in ln][0]
        self.assertIn("+5", parry_line)
        self.assertIn("Mirumoto 2nd Dan free raise", parry_line)

    def test_counterattack_roll_with_fifth_dan_attribution(self):
        fmt = DetailedEventFormatter()
        mirumoto = _make_fifth_dan_mirumoto()
        target = MagicMock()
        target.name.return_value = "Enemy"
        action = _make_skill_action(
            subject=mirumoto, target=target, skill="counterattack",
            skill_roll=60, tn=20, vp=2,
            rolled=10, kept=6, modifier=20,
        )
        from simulation.events import CounterattackRolledEvent
        event = CounterattackRolledEvent(action, 60)
        event._detail_dice = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
        event._detail_params = (10, 6, 20)
        event._detail_tn = 20
        event._detail_modifier_breakdown = [("Mirumoto 5th Dan", 20)]

        lines = fmt.format_history([event])
        counter_line = [ln for ln in lines if "Counterattack:" in ln][0]
        self.assertIn("+20", counter_line)
        self.assertIn("Mirumoto 5th Dan", counter_line)

    def test_wound_check_with_fifth_dan_attribution(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Mirumoto"
        attacker = MagicMock()
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 74, tn=71)
        event._detail_dice = [9, 9, 9, 7, 5, 3, 2, 2, 1]
        event._detail_params = (9, 7, 30)
        event._detail_modifier_breakdown = [("Mirumoto 5th Dan", 30)]

        lines = fmt.format_history([event])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        self.assertIn("+30", wc_line)
        self.assertIn("Mirumoto 5th Dan", wc_line)

    def test_first_dan_mirumoto_wound_check_no_vp_no_breakdown(self):
        """A 1st-dan Mirumoto's wound check with NO VP must show no
        modifier and no breakdown attribution line.
        """
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Mirumoto1st"
        attacker = MagicMock()
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 44, tn=30)
        event._detail_dice = [9, 9, 9, 7, 5, 3, 2]
        event._detail_params = (7, 7, 0)  # no modifier
        event._detail_modifier_breakdown = []

        lines = fmt.format_history([event])
        wc_line = [ln for ln in lines if "Wound Check:" in ln][0]
        # No "+N" modifier rendering, no school attribution.
        self.assertNotIn("+", wc_line.split("→")[1] if "→" in wc_line else "")
        self.assertNotIn("Mirumoto 5th Dan", wc_line)
        self.assertNotIn("Mirumoto 2nd Dan", wc_line)

    def test_breakdown_mismatch_suppresses_attribution(self):
        """When ``_detail_modifier_breakdown`` does not sum to the
        rendered modifier, no attribution line is shown -- better
        silent than wrong (per Principle VII safety clause).
        """
        fmt = DetailedEventFormatter()
        mirumoto = _make_fifth_dan_mirumoto()
        target = MagicMock()
        target.name.return_value = "Enemy"
        target.tn_to_hit.return_value = 20
        action = _make_skill_action(
            subject=mirumoto, target=target, skill="attack",
            skill_roll=80, tn=20, vp=3,
            rolled=10, kept=6, modifier=35,  # actual modifier 35
        )
        event = events.AttackRolledEvent(action, 80)
        event._detail_dice = [10, 10, 9, 8, 7, 6, 5, 4, 3, 2]
        event._detail_params = (10, 6, 35)
        event._detail_tn = 20
        event._detail_base_tn = 20
        # Breakdown only accounts for 30 of 35 -> attribution suppressed.
        event._detail_modifier_breakdown = [("Mirumoto 5th Dan", 30)]

        lines = fmt.format_history([event])
        attack_line = [ln for ln in lines if "Attack:" in ln][0]
        self.assertIn("+35", attack_line)
        self.assertNotIn("Mirumoto 5th Dan", attack_line)


if __name__ == "__main__":
    unittest.main()
