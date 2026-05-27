"""Tests for the TraceEntry dataclass module (spec 007 T005).

Locks in the dataclass shape so downstream code (DetailedEventFormatter.entries,
TextRenderer, BulletedRenderer, JsonRenderer) can rely on it.
"""

from dataclasses import FrozenInstanceError

import pytest

from web.adapters.trace_entries import (
    AkodoFifthDanCounterEntry,
    AttackEntry,
    ComponentDelta,
    CounterattackEntry,
    DamageProjection,
    DeathEntry,
    DuelEndedEntry,
    DuelInitiativeRolledEntry,
    DuelResheathEntry,
    DuelStrikeRolledEntry,
    GainFloatingBonusEntry,
    GainTvpEntry,
    IaijutsuDuelHeaderEntry,
    IaijutsuEntry,
    IaijutsuFocusEntry,
    IaijutsuStrikeEntry,
    InitiativeEntry,
    KeepLightWoundsEntry,
    LightWoundsDamageEntry,
    ModifierDelta,
    ParryEntry,
    PhaseHeaderEntry,
    RawTextEntry,
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


def test_component_delta_construction() -> None:
    cd = ComponentDelta(source="Fire ring", rolled=5, kept=5)
    assert cd.source == "Fire ring"
    assert cd.rolled == 5
    assert cd.kept == 5


def test_component_delta_is_frozen() -> None:
    cd = ComponentDelta(source="Fire ring", rolled=5, kept=5)
    with pytest.raises(FrozenInstanceError):
        cd.rolled = 99  # type: ignore[misc]


def test_modifier_delta_construction_and_frozen() -> None:
    md = ModifierDelta(source="Akodo 2nd Dan", amount=5)
    assert md.source == "Akodo 2nd Dan"
    assert md.amount == 5
    with pytest.raises(FrozenInstanceError):
        md.amount = 10  # type: ignore[misc]


def test_round_header_entry_discriminator() -> None:
    entry = RoundHeaderEntry(round_number=3)
    assert entry.kind == "round_header"
    assert entry.round_number == 3
    with pytest.raises(FrozenInstanceError):
        entry.round_number = 4  # type: ignore[misc]


def test_phase_header_entry_discriminator() -> None:
    entry = PhaseHeaderEntry(phase=5)
    assert entry.kind == "phase_header"
    assert entry.phase == 5


def test_status_block_entry_construction() -> None:
    statuses = {"Akodo": {"lw": 0, "sw": 0, "max_sw": 6, "vp": 3, "max_vp": 3,
                          "actions": [1, 2, 2], "crippled": False}}
    entry = StatusBlockEntry(statuses=statuses)
    assert entry.kind == "status_block"
    assert entry.statuses == statuses


def test_initiative_entry_construction() -> None:
    entry = InitiativeEntry(entries=[
        {"name": "Akodo", "rolled": 5, "kept": 4, "all_dice": [1, 2, 3, 4, 5], "actions": [1, 2, 3]},
    ])
    assert entry.kind == "initiative"
    assert len(entry.entries) == 1


def test_damage_projection_construction() -> None:
    proj = DamageProjection(
        rolled=10, kept=2,
        components=[ComponentDelta(source="katana", rolled=4, kept=2)],
        extra_damage_dice=0, margin_over_tn=5,
    )
    assert proj.rolled == 10
    assert proj.kept == 2
    assert len(proj.components) == 1


def test_attack_entry_construction_full() -> None:
    proj = DamageProjection(
        rolled=7, kept=2, components=[], extra_damage_dice=0, margin_over_tn=3,
    )
    entry = AttackEntry(
        phase_prefix="Phase 2 | Akodo |",
        actor_name="Akodo", target_name="Bayushi", skill="attack",
        vp_spent=None, vp_skill=None,
        rolled=9, kept=3, modifier=0,
        components=[ComponentDelta(source="Fire ring", rolled=3, kept=3)],
        modifier_components=[],
        dice=[18, 8, 7, 6, 3, 3, 3, 2, 1],
        sum_of_kept=33, total=33,
        tn=30, base_tn=30,
        outcome="hit",
        damage_projection=proj,
    )
    assert entry.kind == "attack"
    assert entry.outcome == "hit"
    assert entry.damage_projection is proj


def test_attack_entry_is_frozen() -> None:
    entry = AttackEntry(
        phase_prefix="P | A |", actor_name="A", target_name="B", skill="attack",
        vp_spent=None, vp_skill=None,
        rolled=5, kept=2, modifier=0,
        components=[], modifier_components=[],
        dice=[1, 2, 3, 4, 5], sum_of_kept=3, total=3,
        tn=10, base_tn=10, outcome="miss",
        damage_projection=None,
    )
    with pytest.raises(FrozenInstanceError):
        entry.outcome = "hit"  # type: ignore[misc]


def test_counterattack_entry_construction() -> None:
    entry = CounterattackEntry(
        phase_prefix="P | A |", actor_name="A", target_name="B",
        vp_spent=None, vp_skill=None,
        rolled=5, kept=2, modifier=5,
        components=[], modifier_components=[],
        dice=[1, 2, 3, 4, 5], sum_of_kept=3, total=8,
        tn=15, outcome="hit", damage_projection=None,
    )
    assert entry.kind == "counterattack"


def test_parry_entry_construction() -> None:
    entry = ParryEntry(
        phase_prefix="P | A |", actor_name="A", target_name="B",
        rolled=8, kept=3, modifier=0,
        components=[], modifier_components=[],
        dice=[9, 9, 8], sum_of_kept=26, total=26,
        tn=30, outcome="failed",
    )
    assert entry.kind == "parry"


def test_iaijutsu_entry_construction() -> None:
    entry = IaijutsuEntry(
        phase_prefix="P | A |", actor_name="A", is_challenger=True, skill="iaijutsu",
        skill_roll=42, opponent_skill_roll=30, extra_damage_dice=2,
        rolled=8, kept=3, dice=[10, 9, 8, 7], sum_of_kept=27, effective_modifier=15,
    )
    assert entry.kind == "iaijutsu"
    assert entry.is_challenger


def test_lw_damage_entry_construction() -> None:
    entry = LightWoundsDamageEntry(
        phase_prefix="P | A |", attacker_name="A", target_name="B",
        rolled=7, kept=2, components=[],
        dice=[9, 6, 4, 3, 2, 2, 1], sum_of_kept=15,
        damage=15, lw_after=15,
    )
    assert entry.kind == "lw_damage"
    assert entry.damage == 15


def test_sw_damage_entry_construction() -> None:
    entry = SeriousWoundsDamageEntry(
        phase_prefix="P | A |", target_name="A",
        damage=2, from_double_attack=False,
    )
    assert entry.kind == "sw_damage"


def test_wound_check_entry_construction() -> None:
    entry = WoundCheckEntry(
        phase_prefix="P | A |", character_name="A",
        vp_spent=None, vp_source=None, vp_skill=None, vp_breakdown=None,
        rolled=7, kept=5, modifier=5,
        components=[], modifier_components=[],
        dice=[9, 9, 8, 6, 4, 4, 4], sum_of_kept=36, total=41,
        tn=23, outcome="passed",
    )
    assert entry.kind == "wound_check"
    assert entry.follow_up == "none"


def test_keep_lw_entry_construction() -> None:
    entry = KeepLightWoundsEntry(
        phase_prefix="P | A |", character_name="A", lw_total=15,
    )
    assert entry.kind == "keep_lw"


def test_take_sw_entry_construction() -> None:
    entry = TakeSeriousWoundEntry(
        phase_prefix="P | A |", character_name="A", voluntary=True,
    )
    assert entry.kind == "take_sw"


def test_spend_vp_entry_construction() -> None:
    entry = SpendVpEntry(
        phase_prefix="P | A |", character_name="A", amount=2, skill="attack",
    )
    assert entry.kind == "spend_vp"


def test_gain_tvp_entry_construction() -> None:
    entry = GainTvpEntry(
        phase_prefix="P | A |", character_name="A", amount=4,
        source="Akodo Special Ability",
    )
    assert entry.kind == "gain_tvp"
    assert entry.source == "Akodo Special Ability"


def test_gain_floating_bonus_entry_construction() -> None:
    entry = GainFloatingBonusEntry(
        phase_prefix="P | A |", character_name="A", amount=15,
        source="Akodo 3rd Dan", breakdown="margin 18 ÷ 5 × attack 5",
    )
    assert entry.kind == "gain_floating_bonus"


def test_spend_floating_bonus_entry_construction() -> None:
    entry = SpendFloatingBonusEntry(
        phase_prefix="P | A |", character_name="A", amount=15,
        source="Akodo 3rd Dan",
    )
    assert entry.kind == "spend_floating_bonus"


def test_school_negated_entry_construction() -> None:
    entry = SchoolNegatedEntry(
        phase_prefix="P | A |", negator_name="A", target_name="B",
        target_school_name="Akodo Bushi School", vp_cost=10,
    )
    assert entry.kind == "school_negated"


def test_akodo_5th_dan_counter_entry_construction() -> None:
    entry = AkodoFifthDanCounterEntry(
        phase_prefix="P | A |", akodo_name="A", vp_spent=3, damage=30,
        target_name="B",
    )
    assert entry.kind == "akodo_5th_dan_counter"


def test_iaijutsu_duel_header_entry() -> None:
    entry = IaijutsuDuelHeaderEntry()
    assert entry.kind == "iaijutsu_duel_header"


def test_stance_declared_entry() -> None:
    entry = ShowMeYourStanceDeclaredEntry(character_name="A")
    assert entry.kind == "stance_declared"


def test_stance_rolled_entry() -> None:
    entry = ShowMeYourStanceRolledEntry(
        character_name="A", roll=20, discerned_fire=3, discerned_tn=30,
        rolled=5, kept=2, dice=[10, 8, 2, 1, 1],
    )
    assert entry.kind == "stance_rolled"


def test_duel_initiative_entry() -> None:
    entry = DuelInitiativeRolledEntry(
        challenger_name="A", defender_name="B",
        challenger_roll=20, defender_roll=15, winner_name="A",
    )
    assert entry.kind == "duel_initiative"


def test_iaijutsu_focus_entry() -> None:
    entry = IaijutsuFocusEntry(
        character_name="A", challenger_name="A", defender_name="B",
        challenger_tn=30, defender_tn=35,
    )
    assert entry.kind == "iaijutsu_focus"


def test_iaijutsu_strike_entry() -> None:
    entry = IaijutsuStrikeEntry(
        character_name="A", challenger_name="A", defender_name="B",
        challenger_tn=30, defender_tn=35,
    )
    assert entry.kind == "iaijutsu_strike"


def test_duel_strike_rolled_entry() -> None:
    entry = DuelStrikeRolledEntry(
        character_name="A", target_name="B", roll=35, tn=30,
        is_hit=True, extra_damage_dice=1, rolled=8, kept=3,
        dice=[10, 9, 8, 4, 3, 2, 1, 1],
    )
    assert entry.kind == "duel_strike_rolled"


def test_duel_resheath_entry() -> None:
    entry = DuelResheathEntry(higher_roller_name="A")
    assert entry.kind == "duel_resheath"


def test_duel_ended_entry() -> None:
    entry = DuelEndedEntry()
    assert entry.kind == "duel_ended"


def test_death_entry() -> None:
    entry = DeathEntry(phase_prefix="P | A |", character_name="A")
    assert entry.kind == "death"


def test_unconscious_entry() -> None:
    entry = UnconsciousEntry(phase_prefix="P | A |", character_name="A")
    assert entry.kind == "unconscious"


def test_surrender_entry() -> None:
    entry = SurrenderEntry(phase_prefix="P | A |", character_name="A")
    assert entry.kind == "surrender"


def test_raw_text_entry_default_empty() -> None:
    entry = RawTextEntry()
    assert entry.kind == "raw_text"
    assert entry.lines == []


def test_raw_text_entry_with_lines() -> None:
    entry = RawTextEntry(lines=["a", "b"])
    assert entry.lines == ["a", "b"]


def test_equality_semantics_same_fields() -> None:
    a = ComponentDelta(source="Fire ring", rolled=5, kept=5)
    b = ComponentDelta(source="Fire ring", rolled=5, kept=5)
    assert a == b


def test_equality_semantics_different_fields() -> None:
    a = ComponentDelta(source="Fire ring", rolled=5, kept=5)
    b = ComponentDelta(source="Water ring", rolled=5, kept=5)
    assert a != b


def test_attack_entry_equality() -> None:
    def make() -> AttackEntry:
        return AttackEntry(
            phase_prefix="P | A |", actor_name="A", target_name="B", skill="attack",
            vp_spent=None, vp_skill=None,
            rolled=5, kept=2, modifier=0,
            components=[], modifier_components=[],
            dice=[1, 2, 3, 4, 5], sum_of_kept=3, total=3,
            tn=10, base_tn=10, outcome="miss",
            damage_projection=None,
        )

    assert make() == make()


def test_kind_field_is_literal_discriminator() -> None:
    """The kind field is the discriminator for renderer dispatch."""
    assert RoundHeaderEntry(round_number=1).kind == "round_header"
    assert PhaseHeaderEntry(phase=1).kind == "phase_header"
    assert StatusBlockEntry(statuses={}).kind == "status_block"
    assert InitiativeEntry(entries=[]).kind == "initiative"
