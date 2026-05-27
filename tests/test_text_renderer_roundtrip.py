"""Round-trip tests verifying TextRenderer produces byte-identical text.

Spec 007 T012: For each entry type, build a synthetic event (or sequence
for composites), call:
  legacy  = formatter.format_history([events])
  entries = formatter.entries([events])
  rendered = TextRenderer().render_lines(entries)
and assert ``legacy == rendered``.

This is the per-entry-type byte-identical regression guard for FR-009
/ FR-011 / US2.
"""

import random
import unittest
from typing import Any
from unittest.mock import MagicMock

from simulation import events
from simulation.duel import (
    DuelEndedEvent,
    DuelInitiativeRolledEvent,
    DuelResheathEvent,
    DuelStrikeRolledEvent,
    IaijutsuDuelEvent,
    IaijutsuFocusEvent,
    IaijutsuStrikeEvent,
    ShowMeYourStanceDeclaredEvent,
    ShowMeYourStanceRolledEvent,
)
from web.adapters.detailed_formatter import DetailedEventFormatter
from web.adapters.text_renderer import TextRenderer


def _roundtrip(history: list[Any]) -> tuple[list[str], list[str]]:
    """Render via the legacy path and the new entries→TextRenderer path.

    Returns (legacy_lines, renderer_lines). The invariant under test is
    that these lists compare equal.
    """
    fmt1 = DetailedEventFormatter()
    legacy = fmt1.format_history(history)
    fmt2 = DetailedEventFormatter()
    entries = fmt2.entries(history)
    renderer_lines = TextRenderer().render_lines(entries)
    return legacy, renderer_lines


def _make_action(subject_name="Akodo", target_name="Bayushi", skill="attack",
                 is_hit=True, parried=False, is_success=True, vp=0,
                 extra_damage_dice=0):
    action = MagicMock()
    subject = MagicMock()
    subject.name.return_value = subject_name
    subject.get_damage_roll_params.return_value = (6, 2, 0)
    target = MagicMock()
    target.name.return_value = target_name
    action.subject.return_value = subject
    action.target.return_value = target
    action.skill.return_value = skill
    action.vp.return_value = vp
    action.is_hit.return_value = is_hit
    action.parried.return_value = parried
    action.is_success.return_value = is_success
    action.calculate_extra_damage_dice.return_value = extra_damage_dice
    # Spec 009: damage projection now reads from the action directly.
    action.damage_roll_params.return_value = (6, 2, 0)
    action.damage_breakdown.return_value = []
    return action


class TestRoundTripRoundHeader(unittest.TestCase):
    def test_single_round(self):
        legacy, rendered = _roundtrip([events.NewRoundEvent(0)])
        assert legacy == rendered

    def test_two_rounds(self):
        legacy, rendered = _roundtrip([
            events.NewRoundEvent(0),
            events.NewRoundEvent(1),
        ])
        assert legacy == rendered


class TestRoundTripStatusBlock(unittest.TestCase):
    def test_status_block(self):
        phase = events.NewPhaseEvent(0)
        phase._detail_status = {
            "Akodo": {"lw": 0, "sw": 0, "max_sw": 6, "vp": 3, "max_vp": 3,
                      "actions": [1, 2], "crippled": False},
        }
        legacy, rendered = _roundtrip([phase])
        assert legacy == rendered


class TestRoundTripInitiative(unittest.TestCase):
    def test_initiative_block(self):
        phase = events.NewPhaseEvent(0)
        phase._detail_initiative = {
            "Akodo": {
                "all_dice": [1, 2, 8],
                "actions": [1, 2, 8],
                "roll_params": (5, 4),
            },
        }
        phase._detail_status = {
            "Akodo": {"lw": 0, "sw": 0, "max_sw": 6, "vp": 3, "max_vp": 3,
                      "actions": [1, 2, 8], "crippled": False},
        }
        legacy, rendered = _roundtrip([phase])
        assert legacy == rendered


class TestRoundTripAttackStandalone(unittest.TestCase):
    def test_attack_rolled_hit(self):
        action = _make_action()
        rolled = events.AttackRolledEvent(action, 33)
        rolled._detail_dice = [18, 8, 7, 6, 3, 3, 3, 2, 1]
        rolled._detail_params = (9, 3, 0)
        rolled._detail_tn = 30
        rolled._detail_base_tn = 30
        legacy, rendered = _roundtrip([rolled])
        assert legacy == rendered

    def test_attack_rolled_miss(self):
        action = _make_action(is_hit=False)
        rolled = events.AttackRolledEvent(action, 20)
        rolled._detail_dice = [5, 5, 5, 5, 5]
        rolled._detail_params = (5, 2, 0)
        rolled._detail_tn = 30
        rolled._detail_base_tn = 30
        legacy, rendered = _roundtrip([rolled])
        assert legacy == rendered

    def test_attack_rolled_no_detail_dice(self):
        action = _make_action()
        rolled = events.AttackRolledEvent(action, 25)
        legacy, rendered = _roundtrip([rolled])
        assert legacy == rendered


class TestRoundTripAttackCombined(unittest.TestCase):
    def test_combined_attack_hit_no_vp(self):
        action = _make_action()
        take = events.TakeAttackActionEvent(action)
        rolled = events.AttackRolledEvent(action, 33)
        rolled._detail_dice = [18, 8, 7, 6, 3, 3, 3, 2, 1]
        rolled._detail_params = (9, 3, 0)
        rolled._detail_tn = 30
        rolled._detail_base_tn = 30
        legacy, rendered = _roundtrip([take, rolled])
        assert legacy == rendered

    def test_combined_attack_with_vp(self):
        action = _make_action(skill="double attack", vp=2)
        take = events.TakeAttackActionEvent(action)
        spend = events.SpendVoidPointsEvent(
            action.subject(), "double attack", 2,
        )
        rolled = events.AttackRolledEvent(action, 57)
        rolled._detail_dice = [18, 18, 6, 4, 3, 3, 2, 1, 1, 1]
        rolled._detail_params = (10, 10, 5)
        rolled._detail_tn = 50
        rolled._detail_base_tn = 30
        rolled._detail_modifier_breakdown = [
            ("Bayushi 2nd Dan free raise", 5),
        ]
        legacy, rendered = _roundtrip([take, spend, rolled])
        assert legacy == rendered

    def test_combined_attack_miss(self):
        action = _make_action(is_hit=False)
        take = events.TakeAttackActionEvent(action)
        rolled = events.AttackRolledEvent(action, 25)
        rolled._detail_dice = [5, 5, 5, 5, 5]
        rolled._detail_params = (5, 2, 0)
        rolled._detail_tn = 30
        rolled._detail_base_tn = 30
        legacy, rendered = _roundtrip([take, rolled])
        assert legacy == rendered

    def test_take_attack_only_no_rolled(self):
        action = _make_action()
        take = events.TakeAttackActionEvent(action)
        legacy, rendered = _roundtrip([take])
        assert legacy == rendered


class TestRoundTripParry(unittest.TestCase):
    def test_combined_parry_failed(self):
        action = _make_action(skill="parry", is_success=False)
        take = events.TakeParryActionEvent(action)
        rolled = events.ParryRolledEvent(action, 26)
        rolled._detail_dice = [9, 9, 8, 8, 4, 2, 2, 1]
        rolled._detail_params = (8, 3, 0)
        rolled._detail_tn = 62
        legacy, rendered = _roundtrip([take, rolled])
        assert legacy == rendered

    def test_parry_rolled_standalone(self):
        action = _make_action(skill="parry", is_success=True)
        rolled = events.ParryRolledEvent(action, 35)
        rolled._detail_dice = [10, 10, 10, 5]
        rolled._detail_params = (4, 3, 0)
        rolled._detail_tn = 30
        legacy, rendered = _roundtrip([rolled])
        assert legacy == rendered

    def test_take_parry_only(self):
        action = _make_action(skill="parry")
        take = events.TakeParryActionEvent(action)
        legacy, rendered = _roundtrip([take])
        assert legacy == rendered


class TestRoundTripLightWoundsDamage(unittest.TestCase):
    def test_lw_damage(self):
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.LightWoundsDamageEvent(attacker, target, 15)
        event._detail_dice = [9, 6, 4, 3, 2, 2, 1]
        event._detail_params = (7, 2)
        event._detail_components = [("katana", 4, 2), ("Fire ring", 3, 0)]
        event._detail_lw_after = 15
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_lw_damage_no_detail(self):
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.LightWoundsDamageEvent(attacker, target, 15)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered


class TestRoundTripSeriousWoundsDamage(unittest.TestCase):
    def test_sw_damage(self):
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.SeriousWoundsDamageEvent(attacker, target, 2)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered


class TestRoundTripWoundCheck(unittest.TestCase):
    def test_wc_failed_standalone(self):
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 23, tn=30)
        event._detail_dice = [9, 8, 6, 6, 6]
        event._detail_params = (5, 3, 0)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_wc_passed_with_keep_lw(self):
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        wc = events.WoundCheckRolledEvent(subject, attacker, 18, 31, tn=18)
        wc._detail_dice = [14, 9, 8, 6, 2]
        wc._detail_params = (5, 3, 0)
        keep = events.KeepLightWoundsEvent(subject, attacker, 18)
        keep._detail_lw_total = 18
        legacy, rendered = _roundtrip([wc, keep])
        assert legacy == rendered

    def test_wc_with_vp_prefix_akodo_4th_dan(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        attacker = MagicMock()
        attacker.name.return_value = "Bayushi"
        spend = events.SpendVoidPointsEvent(
            subject, "wound check", 1, source="Akodo 4th Dan",
        )
        wc = events.WoundCheckRolledEvent(subject, attacker, 60, 51, tn=60)
        wc._detail_dice = [9, 9, 8, 5, 4, 4, 2, 1, 1]
        wc._detail_params = (9, 7, 10)
        wc._detail_modifier_breakdown = [
            ("Akodo 2nd Dan free raise", 5),
        ]
        legacy, rendered = _roundtrip([spend, wc])
        assert legacy == rendered

    def test_wc_failed_with_take_sw(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        attacker = MagicMock()
        attacker.name.return_value = "Bayushi"
        wc = events.WoundCheckRolledEvent(subject, attacker, 60, 41, tn=60)
        wc._detail_dice = [9, 9, 8]
        wc._detail_params = (9, 7, 0)
        take_sw = events.TakeSeriousWoundEvent(subject, attacker, 60)
        target = MagicMock()
        target.name.return_value = "Akodo"
        sw_dmg = events.SeriousWoundsDamageEvent(attacker, target, 1)
        legacy, rendered = _roundtrip([wc, take_sw, sw_dmg])
        assert legacy == rendered


class TestRoundTripStandaloneTakeSwKeepLw(unittest.TestCase):
    def test_take_sw_standalone(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        attacker = MagicMock()
        attacker.name.return_value = "Bayushi"
        event = events.TakeSeriousWoundEvent(subject, attacker, 30)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_keep_lw_standalone(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        attacker = MagicMock()
        attacker.name.return_value = "Bayushi"
        event = events.KeepLightWoundsEvent(subject, attacker, 15)
        event._detail_lw_total = 15
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered


class TestRoundTripSpendVp(unittest.TestCase):
    def test_spend_vp(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.SpendVoidPointsEvent(subject, "wound check", 2)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered


class TestRoundTripGainTvp(unittest.TestCase):
    def test_gain_tvp_with_akodo_source(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.GainTemporaryVoidPointsEvent(
            subject, 4, source="Akodo Special Ability",
        )
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_gain_tvp_no_source(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.GainTemporaryVoidPointsEvent(subject, 2)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_gain_tvp_with_other_source(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.GainTemporaryVoidPointsEvent(
            subject, 3, source="Some Other School",
        )
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered


class TestRoundTripFloatingBonus(unittest.TestCase):
    def test_gain_floating_bonus_with_source_and_breakdown(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        bonus = MagicMock()
        bonus.bonus.return_value = 15
        event = events.GainFloatingBonusEvent(
            subject, bonus, source="Akodo 3rd Dan",
            breakdown="margin 18 ÷ 5 × attack 5",
        )
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_gain_floating_bonus_no_source(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        bonus = MagicMock()
        bonus.bonus.return_value = 5
        event = events.GainFloatingBonusEvent(subject, bonus)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_spend_floating_bonus_with_source(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        bonus = MagicMock()
        bonus.bonus.return_value = 15
        bonus.source.return_value = "Akodo 3rd Dan"
        event = events.SpendFloatingBonusEvent(subject, bonus)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered


class TestRoundTripSchoolNegated(unittest.TestCase):
    def test_school_negated(self):
        negator = MagicMock()
        negator.name.return_value = "Ishi"
        target = MagicMock()
        target.name.return_value = "Akodo"
        event = events.SchoolNegatedEvent(
            negator, target, 10, "Akodo Bushi School",
        )
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered


class TestRoundTripAkodo5thDanCounter(unittest.TestCase):
    def test_akodo_5th_dan_counter(self):
        akodo = MagicMock()
        akodo.name.return_value = "Akodo"
        bayushi = MagicMock()
        bayushi.name.return_value = "Bayushi"
        spend = events.SpendVoidPointsEvent(
            akodo, "damage", 3, source="Akodo 5th Dan",
        )
        lw = events.LightWoundsDamageEvent(
            akodo, bayushi, 30, source="Akodo 5th Dan",
        )
        legacy, rendered = _roundtrip([spend, lw])
        assert legacy == rendered


class TestRoundTripDefeat(unittest.TestCase):
    def test_death(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.DeathEvent(subject)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_unconscious(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.UnconsciousEvent(subject)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_surrender(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.SurrenderEvent(subject)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered


class TestRoundTripDuelEvents(unittest.TestCase):
    def test_iaijutsu_duel_header(self):
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = IaijutsuDuelEvent(c, d)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_stance_declared(self):
        subject = MagicMock()
        subject.name.return_value = "A"
        event = ShowMeYourStanceDeclaredEvent(subject)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_stance_rolled(self):
        subject = MagicMock()
        subject.name.return_value = "A"
        event = ShowMeYourStanceRolledEvent(subject, 20, 3, 30)
        event._detail_dice = [10, 8, 2]
        event._detail_roll_params = {"rolled": 3, "kept": 2}
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_stance_rolled_no_detail(self):
        subject = MagicMock()
        subject.name.return_value = "A"
        event = ShowMeYourStanceRolledEvent(subject, 20, 3, 30)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_duel_initiative(self):
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = DuelInitiativeRolledEvent(c, d, 20, 15, c)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_iaijutsu_focus(self):
        s = MagicMock()
        s.name.return_value = "A"
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = IaijutsuFocusEvent(s, c, d, 30, 35)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_iaijutsu_strike(self):
        s = MagicMock()
        s.name.return_value = "A"
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = IaijutsuStrikeEvent(s, c, d, 30, 35)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_duel_strike_rolled_hit_with_extra(self):
        s = MagicMock()
        s.name.return_value = "A"
        t = MagicMock()
        t.name.return_value = "B"
        event = DuelStrikeRolledEvent(s, t, 35, 30, True, 1)
        event._detail_dice = [10, 9, 8]
        event._detail_roll_params = {"rolled": 5, "kept": 3}
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_duel_strike_rolled_miss(self):
        s = MagicMock()
        s.name.return_value = "A"
        t = MagicMock()
        t.name.return_value = "B"
        event = DuelStrikeRolledEvent(s, t, 25, 30, False, 0)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_duel_resheath(self):
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = DuelResheathEvent(c, d, c)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_duel_ended(self):
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = DuelEndedEvent(c, d)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered


class TestRoundTripEdgeCases(unittest.TestCase):
    """Cover the small branches that the per-entry-type tests miss."""

    def test_render_components_filtered_empty(self):
        from web.adapters.text_renderer import _render_components
        assert _render_components([]) == ""
        # Only zero-contribution components → filtered to empty
        from web.adapters.trace_entries import ComponentDelta
        assert _render_components([
            ComponentDelta("X", 0, 0), ComponentDelta("Y", 0, 0),
        ]) == ""

    def test_build_roll_str_negative_modifier(self):
        from web.adapters.text_renderer import _build_roll_str
        roll_str, total = _build_roll_str(
            [9, 8, 7], 3, 2, -3, 0, components=None,
        )
        assert ", -3" in roll_str
        assert total == 17 + (-3)

    def test_combined_attack_no_detail_dice(self):
        action = _make_action()
        take = events.TakeAttackActionEvent(action)
        rolled = events.AttackRolledEvent(action, 22)
        legacy, rendered = _roundtrip([take, rolled])
        assert legacy == rendered

    def test_combined_counterattack_no_detail_dice(self):
        action = _make_action()
        take = events.TakeCounterattackActionEvent(action)
        rolled = events.CounterattackRolledEvent(action, 17)
        legacy, rendered = _roundtrip([take, rolled])
        assert legacy == rendered

    def test_take_counterattack_only(self):
        action = _make_action()
        take = events.TakeCounterattackActionEvent(action)
        legacy, rendered = _roundtrip([take])
        assert legacy == rendered

    def test_standalone_counterattack_no_detail(self):
        action = _make_action()
        rolled = events.CounterattackRolledEvent(action, 17)
        legacy, rendered = _roundtrip([rolled])
        assert legacy == rendered

    def test_standalone_counterattack_hit_with_detail(self):
        action = _make_action()
        rolled = events.CounterattackRolledEvent(action, 30)
        rolled._detail_dice = [10, 10, 8]
        rolled._detail_params = (3, 2, 0)
        rolled._detail_tn = 25
        legacy, rendered = _roundtrip([rolled])
        assert legacy == rendered

    def test_standalone_counterattack_miss(self):
        action = _make_action(is_hit=False)
        rolled = events.CounterattackRolledEvent(action, 10)
        rolled._detail_dice = [3, 3, 3]
        rolled._detail_params = (3, 2, 0)
        rolled._detail_tn = 25
        legacy, rendered = _roundtrip([rolled])
        assert legacy == rendered

    def test_combined_parry_no_detail_dice(self):
        action = _make_action(skill="parry", is_success=False)
        take = events.TakeParryActionEvent(action)
        rolled = events.ParryRolledEvent(action, 11)
        legacy, rendered = _roundtrip([take, rolled])
        assert legacy == rendered

    def test_parry_with_negative_modifier(self):
        action = _make_action(skill="parry", is_success=False)
        rolled = events.ParryRolledEvent(action, 21)
        rolled._detail_dice = [10, 9, 8]
        rolled._detail_params = (3, 2, -3)
        rolled._detail_tn = 30
        legacy, rendered = _roundtrip([rolled])
        assert legacy == rendered

    def test_wc_with_negative_modifier(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        attacker = MagicMock()
        attacker.name.return_value = "Bayushi"
        wc = events.WoundCheckRolledEvent(subject, attacker, 30, 22, tn=30)
        wc._detail_dice = [10, 8, 5]
        wc._detail_params = (3, 2, -3)
        legacy, rendered = _roundtrip([wc])
        assert legacy == rendered

    def test_gain_floating_bonus_source_no_breakdown(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        bonus = MagicMock()
        bonus.bonus.return_value = 5
        event = events.GainFloatingBonusEvent(
            subject, bonus, source="Akodo 3rd Dan",
        )
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_spend_floating_bonus_no_source(self):
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        bonus = MagicMock()
        bonus.bonus.return_value = 10
        bonus.source.return_value = None
        event = events.SpendFloatingBonusEvent(subject, bonus)
        legacy, rendered = _roundtrip([event])
        assert legacy == rendered

    def test_combined_counterattack_with_damage_breakdown(self):
        """Counterattack hit with multi-source damage projection
        (covers text_renderer.py line 432 ``damage will be X = breakdown``).

        Spec 009: damage params and breakdown now come from the action
        directly (was: from subject's provider).
        """
        action = _make_action()
        # Force the action's damage params and a non-empty breakdown so
        # the "damage will be XkY = ..." rendering branch fires.
        action.damage_roll_params.return_value = (9, 2, 0)
        action.damage_breakdown.return_value = [
            ("katana", 4, 2), ("Fire ring", 5, 0),
        ]
        take = events.TakeCounterattackActionEvent(action)
        rolled = events.CounterattackRolledEvent(action, 35)
        rolled._detail_dice = [10, 10, 8, 5, 2]
        rolled._detail_params = (5, 3, 0)
        rolled._detail_tn = 30
        legacy, rendered = _roundtrip([take, rolled])
        assert legacy == rendered

    def test_combined_attack_no_damage_breakdown(self):
        """Attack hit where damage_projection has 0/1 component → no breakdown."""
        action = _make_action()
        # Damage params returned by provider, but components is single-source
        action.subject().get_damage_roll_params.return_value = (5, 2, 0)
        take = events.TakeAttackActionEvent(action)
        rolled = events.AttackRolledEvent(action, 33)
        rolled._detail_dice = [18, 8, 7, 6, 3, 3, 3, 2, 1]
        rolled._detail_params = (9, 3, 0)
        rolled._detail_tn = 30
        rolled._detail_base_tn = 30
        legacy, rendered = _roundtrip([take, rolled])
        assert legacy == rendered


class TestRoundTripFullCalibrationCombat(unittest.TestCase):
    """The big one: run a full Akodo-vs-Bayushi 300-XP combat and assert
    every line of the legacy output matches the renderer output. This
    is the comprehensive byte-identical-text regression guard.
    """

    def test_full_combat_byte_identical(self):
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.templates.generator import generate_template
        from web.adapters.character_adapter import config_to_character
        from web.adapters.combat_observer import (
            CombatObserver,
            DetailedCombatEngine,
            TrackingRollProvider,
        )

        random.seed(1234)
        akodo_config, _ = generate_template("akodo", 300)
        akodo = config_to_character(akodo_config)
        akodo._name = "Akodo"
        akodo.set_roll_provider(TrackingRollProvider(akodo.roll_provider()))
        bayushi_config, _ = generate_template("bayushi", 300)
        bayushi = config_to_character(bayushi_config)
        bayushi._name = "Bayushi"
        bayushi.set_roll_provider(TrackingRollProvider(bayushi.roll_provider()))

        groups = [Group("Lion", akodo), Group("Scorpion", bayushi)]
        context = EngineContext(groups)
        context.initialize()
        observer = CombatObserver()
        engine = DetailedCombatEngine(context, observer)
        engine.run()

        history = engine.history()
        legacy = DetailedEventFormatter().format_history(history)
        entries = DetailedEventFormatter().entries(history)
        rendered = TextRenderer().render_lines(entries)

        # Report first diverging line for diagnosis.
        for i, (a, b) in enumerate(zip(legacy, rendered)):
            assert a == b, (
                f"Line {i} differs.\nLegacy:   {a!r}\nRendered: {b!r}"
            )
        assert len(legacy) == len(rendered), (
            f"Length differs: legacy={len(legacy)}, rendered={len(rendered)}"
        )


if __name__ == "__main__":
    unittest.main()
