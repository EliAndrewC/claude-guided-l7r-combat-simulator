"""Tests for DetailedEventFormatter.entries() — structured-trace production.

Spec 007 T009: For each entry type, build a synthetic event (or sequence
for composites), call ``formatter.entries([event])``, and assert the
returned entry has the expected field values populated.

Focus is FIELD VALUES (not text output). Text output is verified by the
round-trip tests in tests/test_text_renderer_roundtrip.py.
"""

import unittest
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
from web.adapters.trace_entries import (
    AkodoFifthDanCounterEntry,
    AttackEntry,
    ComponentDelta,
    DamageProjection,
    DeathEntry,
    DuelEndedEntry,
    DuelInitiativeRolledEntry,
    DuelResheathEntry,
    DuelStrikeRolledEntry,
    GainFloatingBonusEntry,
    GainTvpEntry,
    IaijutsuDuelHeaderEntry,
    IaijutsuFocusEntry,
    IaijutsuStrikeEntry,
    InitiativeEntry,
    KeepLightWoundsEntry,
    LightWoundsDamageEntry,
    ModifierDelta,
    ParryEntry,
    RoundHeaderEntry,
    SchoolNegatedEntry,
    SeriousWoundsDamageEntry,
    ShowMeYourStanceDeclaredEntry,
    ShowMeYourStanceRolledEntry,
    SpendFloatingBonusEntry,
    SpendVpEntry,
    StatusBlockEntry,
    SurrenderEntry,
    TakeSeriousWoundEntry,
    UnconsciousEntry,
    WoundCheckEntry,
)


def _make_action(subject_name="Akodo", target_name="Bayushi", skill="attack",
                 is_hit=True, parried=False, is_success=True, vp=0):
    action = MagicMock()
    subject = MagicMock()
    subject.name.return_value = subject_name
    subject.get_damage_roll_params.return_value = (6, 2, 0)
    target = MagicMock()
    target.name.return_value = target_name
    action.subject.return_value = subject
    action.target.return_value = target
    action.skill.return_value = skill
    action.skill_roll.return_value = 29
    action.vp.return_value = vp
    action.parry_attempted.return_value = False
    action.is_hit.return_value = is_hit
    action.parried.return_value = parried
    action.is_success.return_value = is_success
    action.calculate_extra_damage_dice.return_value = 0
    return action


def _make_status(name1="Akodo", name2="Bayushi"):
    return {
        name1: {"lw": 0, "sw": 0, "max_sw": 6, "vp": 3, "max_vp": 3,
                "actions": [1, 2], "crippled": False},
        name2: {"lw": 0, "sw": 0, "max_sw": 8, "vp": 3, "max_vp": 3,
                "actions": [3, 4], "crippled": False},
    }


class TestEntriesRoundHeader(unittest.TestCase):
    def test_round_header_uses_one_based_index(self):
        fmt = DetailedEventFormatter()
        entries = fmt.entries([events.NewRoundEvent(0)])
        assert len(entries) == 1
        e = entries[0]
        assert isinstance(e, RoundHeaderEntry)
        assert e.round_number == 1

    def test_round_header_event_round_2(self):
        fmt = DetailedEventFormatter()
        entries = fmt.entries([events.NewRoundEvent(1)])
        e = entries[0]
        assert isinstance(e, RoundHeaderEntry)
        assert e.round_number == 2


class TestEntriesStatusBlock(unittest.TestCase):
    def test_status_block_emitted_on_phase_with_status(self):
        fmt = DetailedEventFormatter()
        phase = events.NewPhaseEvent(0)
        phase._detail_status = _make_status()
        entries = fmt.entries([phase])
        # NewPhaseEvent with status emits the status_block
        assert any(isinstance(e, StatusBlockEntry) for e in entries)


class TestEntriesInitiative(unittest.TestCase):
    def test_initiative_entry_fields(self):
        fmt = DetailedEventFormatter()
        phase = events.NewPhaseEvent(0)
        phase._detail_initiative = {
            "Akodo": {
                "all_dice": [1, 2, 8],
                "actions": [1, 2, 8],
                "roll_params": (5, 4),
            },
        }
        phase._detail_status = _make_status()
        entries = fmt.entries([phase])
        init_entries = [e for e in entries if isinstance(e, InitiativeEntry)]
        assert len(init_entries) == 1
        e = init_entries[0]
        assert len(e.entries) == 1
        assert e.entries[0]["name"] == "Akodo"
        assert e.entries[0]["rolled"] == 5
        assert e.entries[0]["kept"] == 4
        assert e.entries[0]["all_dice"] == [1, 2, 8]
        assert e.entries[0]["actions"] == [1, 2, 8]


class TestEntriesAttackStandalone(unittest.TestCase):
    def test_attack_rolled_standalone_hit_with_damage_projection(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        rolled = events.AttackRolledEvent(action, 33)
        rolled._detail_dice = [18, 8, 7, 6, 3, 3, 3, 2, 1]
        rolled._detail_params = (9, 3, 0)
        rolled._detail_tn = 30
        rolled._detail_base_tn = 30
        rolled._detail_components = [
            ("Fire ring", 3, 3),
            ("attack skill", 5, 0),
            ("Akodo 1st Dan", 1, 0),
        ]
        entries = fmt.entries([rolled])
        assert len(entries) == 1
        e = entries[0]
        assert isinstance(e, AttackEntry)
        assert e.outcome == "hit"
        assert e.skill == "attack"
        assert e.rolled == 9
        assert e.kept == 3
        assert e.tn == 30
        assert e.base_tn == 30
        assert e.sum_of_kept == 33
        assert e.total == 33
        assert e.dice == [18, 8, 7, 6, 3, 3, 3, 2, 1]
        assert len(e.components) == 3
        assert e.components[0] == ComponentDelta("Fire ring", 3, 3)
        assert e.damage_projection is not None
        assert isinstance(e.damage_projection, DamageProjection)

    def test_attack_rolled_miss(self):
        fmt = DetailedEventFormatter()
        action = _make_action(is_hit=False)
        rolled = events.AttackRolledEvent(action, 20)
        rolled._detail_dice = [5, 5, 5, 5, 5]
        rolled._detail_params = (5, 2, 0)
        rolled._detail_tn = 30
        rolled._detail_base_tn = 30
        entries = fmt.entries([rolled])
        e = entries[0]
        assert isinstance(e, AttackEntry)
        assert e.outcome == "miss"
        assert e.damage_projection is None

    def test_attack_rolled_no_detail_dice(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        rolled = events.AttackRolledEvent(action, 25)
        entries = fmt.entries([rolled])
        e = entries[0]
        assert isinstance(e, AttackEntry)
        assert e.has_detail is False
        assert e.fallback_roll == 25


class TestEntriesAttackComposite(unittest.TestCase):
    def test_combined_attack_with_vp_prefix(self):
        fmt = DetailedEventFormatter()
        action = _make_action(skill="double attack", vp=2)
        take = events.TakeAttackActionEvent(action)
        spend = events.SpendVoidPointsEvent(action.subject(), "double attack", 2)
        rolled = events.AttackRolledEvent(action, 57)
        rolled._detail_dice = [18, 18, 6, 4, 3, 3, 2, 1, 1, 1]
        rolled._detail_params = (10, 10, 5)
        rolled._detail_tn = 50
        rolled._detail_base_tn = 30
        rolled._detail_components = [
            ("Fire ring", 5, 5),
            ("double attack skill", 5, 0),
        ]
        rolled._detail_modifier_breakdown = [("Bayushi 2nd Dan free raise", 5)]
        entries = fmt.entries([take, spend, rolled])
        assert len(entries) == 1
        e = entries[0]
        assert isinstance(e, AttackEntry)
        assert e.vp_spent == 2
        assert e.vp_skill == "double attack"
        assert e.skill == "double attack"
        assert e.tn == 50
        assert e.base_tn == 30
        assert e.modifier == 5
        assert e.modifier_components == [ModifierDelta("Bayushi 2nd Dan free raise", 5)]

    def test_combined_attack_no_vp(self):
        fmt = DetailedEventFormatter()
        action = _make_action()
        take = events.TakeAttackActionEvent(action)
        rolled = events.AttackRolledEvent(action, 30)
        rolled._detail_dice = [10, 10, 10]
        rolled._detail_params = (5, 2, 0)
        rolled._detail_tn = 25
        rolled._detail_base_tn = 25
        entries = fmt.entries([take, rolled])
        e = entries[0]
        assert isinstance(e, AttackEntry)
        assert e.vp_spent is None
        assert e.vp_skill is None


class TestEntriesParry(unittest.TestCase):
    def test_combined_parry_failed(self):
        fmt = DetailedEventFormatter()
        action = _make_action(subject_name="Akodo", target_name="Bayushi",
                              skill="parry", is_success=False)
        take = events.TakeParryActionEvent(action)
        rolled = events.ParryRolledEvent(action, 26)
        rolled._detail_dice = [9, 9, 8, 8, 4, 2, 2, 1]
        rolled._detail_params = (8, 3, 0)
        rolled._detail_tn = 62
        entries = fmt.entries([take, rolled])
        assert len(entries) == 1
        e = entries[0]
        assert isinstance(e, ParryEntry)
        assert e.outcome == "failed"
        assert e.tn == 62
        assert e.sum_of_kept == 26


class TestEntriesLightWoundsDamage(unittest.TestCase):
    def test_lw_damage_with_breakdown(self):
        fmt = DetailedEventFormatter()
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.LightWoundsDamageEvent(attacker, target, 15)
        event._detail_dice = [9, 6, 4, 3, 2, 2, 1]
        event._detail_params = (7, 2)
        event._detail_components = [("katana", 4, 2), ("Fire ring", 3, 0)]
        event._detail_lw_after = 15
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, LightWoundsDamageEntry)
        assert e.damage == 15
        assert e.lw_after == 15
        assert e.rolled == 7
        assert e.kept == 2
        assert len(e.components) == 2


class TestEntriesSeriousWoundsDamage(unittest.TestCase):
    def test_sw_damage_two_wounds(self):
        fmt = DetailedEventFormatter()
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        target = MagicMock()
        target.name.return_value = "Bayushi"
        event = events.SeriousWoundsDamageEvent(attacker, target, 2)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, SeriousWoundsDamageEntry)
        assert e.damage == 2
        assert e.from_double_attack is False


class TestEntriesWoundCheck(unittest.TestCase):
    def test_wc_failed_standalone(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        event = events.WoundCheckRolledEvent(subject, attacker, 30, 23, tn=30)
        event._detail_dice = [9, 8, 6, 6, 6]
        event._detail_params = (5, 3, 0)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, WoundCheckEntry)
        assert e.outcome == "failed"
        assert e.tn == 30
        assert e.follow_up == "none"

    def test_wc_passed_with_keep_lw_followup(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Bayushi"
        attacker = MagicMock()
        attacker.name.return_value = "Akodo"
        wc = events.WoundCheckRolledEvent(subject, attacker, 18, 31, tn=18)
        wc._detail_dice = [14, 9, 8, 6, 2]
        wc._detail_params = (5, 3, 0)
        keep = events.KeepLightWoundsEvent(subject, attacker, 18)
        keep._detail_lw_total = 18
        entries = fmt.entries([wc, keep])
        assert len(entries) == 1  # composed into one wound_check entry
        e = entries[0]
        assert isinstance(e, WoundCheckEntry)
        assert e.outcome == "passed"
        assert e.follow_up == "keep_lw"
        assert e.follow_up_lw_total == 18

    def test_wc_with_vp_prefix_akodo_4th_dan(self):
        fmt = DetailedEventFormatter()
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
        entries = fmt.entries([spend, wc])
        assert len(entries) == 1
        e = entries[0]
        assert isinstance(e, WoundCheckEntry)
        assert e.vp_spent == 1
        assert e.vp_source == "Akodo 4th Dan"
        assert e.vp_breakdown is not None
        assert "+5 per VP" in e.vp_breakdown

    def test_wc_with_take_sw_followup(self):
        fmt = DetailedEventFormatter()
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
        entries = fmt.entries([wc, take_sw, sw_dmg])
        assert len(entries) == 1
        e = entries[0]
        assert isinstance(e, WoundCheckEntry)
        assert e.follow_up == "take_sw"
        assert e.follow_up_sw_count == 1


class TestEntriesSpendVp(unittest.TestCase):
    def test_spend_vp_standalone(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.SpendVoidPointsEvent(subject, "wound check", 2)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, SpendVpEntry)
        assert e.amount == 2
        assert e.skill == "wound check"


class TestEntriesGainTvp(unittest.TestCase):
    def test_gain_tvp_with_source(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.GainTemporaryVoidPointsEvent(subject, 4)
        event.source = "Akodo Special Ability"
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, GainTvpEntry)
        assert e.amount == 4
        assert e.source == "Akodo Special Ability"

    def test_gain_tvp_zero_amount_suppressed(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.GainTemporaryVoidPointsEvent(subject, 0)
        entries = fmt.entries([event])
        assert entries == []


class TestEntriesFloatingBonus(unittest.TestCase):
    def test_gain_floating_bonus(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        bonus = MagicMock()
        bonus.bonus.return_value = 15
        bonus.source.return_value = "Akodo 3rd Dan"
        event = events.GainFloatingBonusEvent(
            subject, bonus, source="Akodo 3rd Dan",
            breakdown="margin 18 ÷ 5 × attack 5",
        )
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, GainFloatingBonusEntry)
        assert e.amount == 15
        assert e.source == "Akodo 3rd Dan"
        assert e.breakdown == "margin 18 ÷ 5 × attack 5"

    def test_spend_floating_bonus(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        bonus = MagicMock()
        bonus.bonus.return_value = 15
        bonus.source.return_value = "Akodo 3rd Dan"
        event = events.SpendFloatingBonusEvent(subject, bonus)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, SpendFloatingBonusEntry)
        assert e.amount == 15
        assert e.source == "Akodo 3rd Dan"

    def test_gain_floating_bonus_zero_suppressed(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        bonus = MagicMock()
        bonus.bonus.return_value = 0
        event = events.GainFloatingBonusEvent(
            subject, bonus, source="Akodo 3rd Dan",
        )
        entries = fmt.entries([event])
        assert entries == []


class TestEntriesSchoolNegated(unittest.TestCase):
    def test_school_negated_entry(self):
        fmt = DetailedEventFormatter()
        negator = MagicMock()
        negator.name.return_value = "Ishi"
        target = MagicMock()
        target.name.return_value = "Akodo"
        event = events.SchoolNegatedEvent(
            negator, target, 10, "Akodo Bushi School",
        )
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, SchoolNegatedEntry)
        assert e.negator_name == "Ishi"
        assert e.target_school_name == "Akodo Bushi School"
        assert e.vp_cost == 10


class TestEntriesAkodo5thDanCounter(unittest.TestCase):
    def test_akodo_5th_dan_counter_composes_spend_plus_lw_damage(self):
        fmt = DetailedEventFormatter()
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
        entries = fmt.entries([spend, lw])
        assert len(entries) == 1
        e = entries[0]
        assert isinstance(e, AkodoFifthDanCounterEntry)
        assert e.vp_spent == 3
        assert e.damage == 30
        assert e.target_name == "Bayushi"


class TestEntriesKeepLw(unittest.TestCase):
    def test_keep_lw_standalone(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        attacker = MagicMock()
        attacker.name.return_value = "Bayushi"
        event = events.KeepLightWoundsEvent(subject, attacker, 15)
        event._detail_lw_total = 15
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, KeepLightWoundsEntry)
        assert e.lw_total == 15


class TestEntriesTakeSw(unittest.TestCase):
    def test_take_sw_standalone(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        attacker = MagicMock()
        attacker.name.return_value = "Bayushi"
        event = events.TakeSeriousWoundEvent(subject, attacker, 30)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, TakeSeriousWoundEntry)
        assert e.voluntary is False


class TestEntriesDeath(unittest.TestCase):
    def test_death_entry(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.DeathEvent(subject)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, DeathEntry)
        assert e.character_name == "Akodo"

    def test_unconscious_entry(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.UnconsciousEvent(subject)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, UnconsciousEntry)

    def test_surrender_entry(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "Akodo"
        event = events.SurrenderEvent(subject)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, SurrenderEntry)


class TestEntriesDuel(unittest.TestCase):
    def test_iaijutsu_duel_header(self):
        fmt = DetailedEventFormatter()
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = IaijutsuDuelEvent(c, d)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, IaijutsuDuelHeaderEntry)

    def test_stance_declared(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "A"
        event = ShowMeYourStanceDeclaredEvent(subject)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, ShowMeYourStanceDeclaredEntry)
        assert e.character_name == "A"

    def test_stance_rolled(self):
        fmt = DetailedEventFormatter()
        subject = MagicMock()
        subject.name.return_value = "A"
        event = ShowMeYourStanceRolledEvent(subject, 20, 3, 30)
        event._detail_dice = [10, 8, 2]
        event._detail_roll_params = {"rolled": 3, "kept": 2}
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, ShowMeYourStanceRolledEntry)
        assert e.roll == 20
        assert e.discerned_fire == 3
        assert e.discerned_tn == 30

    def test_duel_initiative(self):
        fmt = DetailedEventFormatter()
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = DuelInitiativeRolledEvent(c, d, 20, 15, c)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, DuelInitiativeRolledEntry)
        assert e.winner_name == "A"

    def test_iaijutsu_focus(self):
        fmt = DetailedEventFormatter()
        s = MagicMock()
        s.name.return_value = "A"
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = IaijutsuFocusEvent(s, c, d, 30, 35)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, IaijutsuFocusEntry)

    def test_iaijutsu_strike(self):
        fmt = DetailedEventFormatter()
        s = MagicMock()
        s.name.return_value = "A"
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = IaijutsuStrikeEvent(s, c, d, 30, 35)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, IaijutsuStrikeEntry)

    def test_duel_strike_rolled(self):
        fmt = DetailedEventFormatter()
        s = MagicMock()
        s.name.return_value = "A"
        t = MagicMock()
        t.name.return_value = "B"
        event = DuelStrikeRolledEvent(s, t, 35, 30, True, 1)
        event._detail_dice = [10, 9, 8]
        event._detail_roll_params = {"rolled": 5, "kept": 3}
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, DuelStrikeRolledEntry)
        assert e.is_hit is True
        assert e.extra_damage_dice == 1

    def test_duel_resheath(self):
        fmt = DetailedEventFormatter()
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = DuelResheathEvent(c, d, c)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, DuelResheathEntry)
        assert e.higher_roller_name == "A"

    def test_duel_ended(self):
        fmt = DetailedEventFormatter()
        c = MagicMock()
        c.name.return_value = "A"
        d = MagicMock()
        d.name.return_value = "B"
        event = DuelEndedEvent(c, d)
        entries = fmt.entries([event])
        e = entries[0]
        assert isinstance(e, DuelEndedEntry)


class TestEntriesIntegration(unittest.TestCase):
    """Smoke: live calibration combat produces only valid entries (no
    RawTextEntry fallbacks), proving FR-007."""

    def test_no_raw_text_fallbacks_in_full_combat(self):
        import random

        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.templates.generator import generate_template
        from web.adapters.character_adapter import config_to_character
        from web.adapters.combat_observer import (
            CombatObserver,
            DetailedCombatEngine,
            TrackingRollProvider,
        )
        from web.adapters.trace_entries import RawTextEntry

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

        fmt = DetailedEventFormatter()
        entries = fmt.entries(engine.history())

        assert len(entries) > 0
        for e in entries:
            assert not isinstance(e, RawTextEntry), (
                f"RawTextEntry fallback emitted: {e}"
            )


if __name__ == "__main__":
    unittest.main()
