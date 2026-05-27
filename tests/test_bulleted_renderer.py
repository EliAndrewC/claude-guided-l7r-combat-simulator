"""Tests for BulletedRenderer (Spec 007 Phase 6).

Covers per-entry-type Markdown rendering of every TraceEntry subclass.
Verifies FR-013 to FR-022:
- Multi-source aggregates render with bullets.
- Single-source aggregates render as a single line.
- Modifier with source renders own bullet.
- Modifier with unsourced placeholder still renders the bullet visibly.
- AttackEntry with damage_projection renders the nested sub-bullets.
- TN with raises renders the raise clause on the header line.
- Round headers render as Markdown ``## Round N``.
- Status blocks render with each character on its own line.
- VP-spend on AttackEntry / WoundCheckEntry renders as part of the header.

The final end-to-end test renders the calibration combat's entries and
asserts the key strings appear (Akodo, Bayushi, double attack, etc.).
"""

from __future__ import annotations

import random
import unittest

from simulation.context import EngineContext
from simulation.groups import Group
from simulation.templates.generator import generate_template
from web.adapters.bulleted_renderer import (
    BulletedRenderer,
    _component_bullets,
    _damage_projection_bullets,
    _format_dice_inline,
    _format_tn,
    _has_breakdown,
    _modifier_bullets,
    _nonzero_components,
    _vp_prefix,
)
from web.adapters.character_adapter import config_to_character
from web.adapters.combat_observer import (
    CombatObserver,
    DetailedCombatEngine,
    TrackingRollProvider,
)
from web.adapters.detailed_formatter import DetailedEventFormatter
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

# ── Helpers tests ────────────────────────────────────────────────────


class TestFormattingHelpers(unittest.TestCase):
    def test_nonzero_components_filters(self):
        cs = [
            ComponentDelta("X", 0, 0),
            ComponentDelta("Y", 5, 0),
            ComponentDelta("Z", 0, 2),
        ]
        result = _nonzero_components(cs)
        assert len(result) == 2
        assert result[0].source == "Y"
        assert result[1].source == "Z"

    def test_has_breakdown_true_with_two(self):
        cs = [
            ComponentDelta("X", 5, 5),
            ComponentDelta("Y", 3, 0),
        ]
        assert _has_breakdown(cs) is True

    def test_has_breakdown_false_with_one(self):
        cs = [ComponentDelta("X", 5, 5), ComponentDelta("Y", 0, 0)]
        assert _has_breakdown(cs) is False

    def test_has_breakdown_false_with_empty(self):
        assert _has_breakdown([]) is False

    def test_format_dice_inline_empty(self):
        assert _format_dice_inline([], 0) == "[]"

    def test_format_dice_inline_with_kept_and_dropped(self):
        assert _format_dice_inline([10, 5, 3], 2) == "[**10**, **5**, ~~3~~]"

    def test_format_tn_with_raises(self):
        s = _format_tn(50, 30, "double attack")
        assert "TN 50" in s
        assert "4 raises" in s
        assert "double attack" in s

    def test_format_tn_no_raises(self):
        assert _format_tn(30, 30, "attack") == "TN 30"

    def test_component_bullets(self):
        cs = [
            ComponentDelta("Fire ring", 5, 5),
            ComponentDelta("attack", 3, 0),
            ComponentDelta("Zero", 0, 0),
        ]
        bullets = _component_bullets(cs)
        assert bullets == [
            "  - 5k5 Fire ring",
            "  - 3k0 attack",
        ]

    def test_modifier_bullets_zero(self):
        assert _modifier_bullets(0, []) == []

    def test_modifier_bullets_with_source(self):
        bullets = _modifier_bullets(5, [ModifierDelta("Bayushi 2nd Dan", 5)])
        assert bullets == ["  - Modifier: +5 (Bayushi 2nd Dan)"]

    def test_modifier_bullets_with_unsourced(self):
        bullets = _modifier_bullets(10, [ModifierDelta("Akodo 2nd Dan", 5)])
        assert bullets == [
            "  - Modifier: +5 (Akodo 2nd Dan)",
            "  - Modifier: +5 (unsourced)",
        ]

    def test_modifier_bullets_negative(self):
        bullets = _modifier_bullets(-5, [ModifierDelta("Penalty", -5)])
        assert bullets == ["  - Modifier: -5 (Penalty)"]

    def test_modifier_bullets_negative_unsourced(self):
        bullets = _modifier_bullets(-3, [])
        assert bullets == ["  - Modifier: -3 (unsourced)"]

    def test_damage_projection_bullets_multi(self):
        proj = DamageProjection(
            rolled=10, kept=2,
            components=[
                ComponentDelta("katana", 4, 2),
                ComponentDelta("Fire ring", 3, 0),
                ComponentDelta("margin", 3, 0),
            ],
            extra_damage_dice=3,
            margin_over_tn=15,
        )
        bullets = _damage_projection_bullets(proj)
        assert "  - Damage will be: 10k2" in bullets
        assert any("4k2 katana" in b for b in bullets)
        assert any("3k0 Fire ring" in b for b in bullets)
        assert any("+15 over TN" in b for b in bullets)
        assert any("3 extra damage dice" in b for b in bullets)

    def test_damage_projection_bullets_one_extra_die(self):
        proj = DamageProjection(
            rolled=7, kept=2,
            components=[ComponentDelta("katana", 4, 2)],
            extra_damage_dice=1,
            margin_over_tn=5,
        )
        bullets = _damage_projection_bullets(proj)
        # 1 die → singular
        assert any("1 extra damage die" in b for b in bullets)

    def test_damage_projection_bullets_single_component_no_breakdown(self):
        # Single component → no sub-bullets, no margin → no margin bullet
        proj = DamageProjection(
            rolled=7, kept=2,
            components=[ComponentDelta("katana", 4, 2)],
            extra_damage_dice=0,
            margin_over_tn=0,
        )
        bullets = _damage_projection_bullets(proj)
        assert bullets == ["  - Damage will be: 7k2"]

    def test_vp_prefix_empty(self):
        assert _vp_prefix(None, None) == ""
        assert _vp_prefix(2, None) == ""
        assert _vp_prefix(None, "attack") == ""

    def test_vp_prefix_filled(self):
        assert _vp_prefix(2, "attack") == "⬛⬛ spends 2 VP on attack → "


# ── Round / Phase / Status / Initiative ─────────────────────────────


class TestSimpleHeaders(unittest.TestCase):
    def test_round_header(self):
        out = BulletedRenderer().render([RoundHeaderEntry(round_number=1)])
        assert "## Round 1" in out

    def test_status_block(self):
        entry = StatusBlockEntry(statuses={
            "Akodo": {
                "lw": 5, "sw": 1, "max_sw": 6, "vp": 2, "max_vp": 3,
                "actions": [1, 5], "crippled": False,
            },
        })
        out = BulletedRenderer().render([entry])
        assert "**Status:**" in out
        assert "**Akodo**" in out
        assert "Light 5" in out
        assert "Serious 1/6" in out
        assert "Void 2/3" in out

    def test_status_block_crippled(self):
        entry = StatusBlockEntry(statuses={
            "Bayushi": {
                "lw": 50, "sw": 6, "max_sw": 6, "vp": 0, "max_vp": 3,
                "actions": [], "crippled": True,
            },
        })
        out = BulletedRenderer().render([entry])
        assert "**CRIPPLED**" in out

    def test_initiative(self):
        entry = InitiativeEntry(entries=[
            {
                "name": "Akodo", "rolled": 5, "kept": 4,
                "all_dice": [1, 2, 2, 8, 10], "actions": [1, 2, 2, 8],
            },
        ])
        out = BulletedRenderer().render([entry])
        assert "🎲 Initiative" in out
        assert "**Akodo**" in out
        assert "5k4" in out
        assert "Actions: [1, 2, 2, 8]" in out


# ── Attack ──────────────────────────────────────────────────────────


def _attack_entry(
    *,
    is_combined: bool = True,
    is_take_only: bool = False,
    outcome: str = "hit",
    has_detail: bool = True,
    components: list[ComponentDelta] | None = None,
    modifier: int = 0,
    modifier_components: list[ModifierDelta] | None = None,
    tn: int = 30,
    base_tn: int = 30,
    vp_spent: int | None = None,
    vp_skill: str | None = None,
    damage_projection: DamageProjection | None = None,
    skill: str = "attack",
) -> AttackEntry:
    return AttackEntry(
        phase_prefix="Phase 2 | Bayushi |",
        actor_name="Bayushi",
        target_name="Akodo",
        skill=skill,
        vp_spent=vp_spent, vp_skill=vp_skill,
        rolled=10, kept=10, modifier=modifier,
        components=components or [],
        modifier_components=modifier_components or [],
        dice=[18, 18, 6, 4, 3, 3, 2, 1, 1, 1],
        sum_of_kept=57, total=57 + modifier,
        tn=tn, base_tn=base_tn,
        outcome=outcome,  # type: ignore[arg-type]
        damage_projection=damage_projection,
        has_detail=has_detail,
        fallback_roll=33,
        is_combined=is_combined,
        is_take_only=is_take_only,
    )


class TestAttackRendering(unittest.TestCase):
    def test_attack_take_only(self):
        entry = _attack_entry(is_take_only=True)
        out = BulletedRenderer().render([entry])
        assert "⚔️ attacks Akodo (attack)" in out

    def test_attack_single_component_no_bullets(self):
        # No components, no modifier, no damage projection → single line
        entry = _attack_entry()
        lines = BulletedRenderer().render([entry]).split("\n")
        # Should be exactly one line, no bullet sub-list.
        assert len(lines) == 1
        assert "⚔️ attacks Akodo" in lines[0]
        assert "HIT!" in lines[0]

    def test_attack_multi_component_emits_bullets(self):
        components = [
            ComponentDelta("Fire ring", 5, 5),
            ComponentDelta("double attack skill", 5, 0),
            ComponentDelta("VP on double attack", 2, 2),
        ]
        entry = _attack_entry(components=components, skill="double attack",
                              vp_spent=2, vp_skill="double attack",
                              tn=50, base_tn=30)
        out = BulletedRenderer().render([entry])
        # Header has VP prefix and raise breakdown.
        assert "⬛⬛ spends 2 VP on double attack" in out
        assert "TN 50 (base TN 30 + 4 raises × +5 for double attack)" in out
        # Bullet sub-list:
        assert "- 5k5 Fire ring" in out
        assert "- 5k0 double attack skill" in out
        assert "- 2k2 VP on double attack" in out
        # Dice line:
        assert "- Dice: " in out

    def test_attack_modifier_with_source_renders_bullet(self):
        entry = _attack_entry(
            modifier=5,
            modifier_components=[ModifierDelta("Bayushi 2nd Dan", 5)],
        )
        out = BulletedRenderer().render([entry])
        assert "Modifier: +5 (Bayushi 2nd Dan)" in out

    def test_attack_modifier_unsourced_visible(self):
        entry = _attack_entry(
            modifier=5,
            modifier_components=[],
        )
        out = BulletedRenderer().render([entry])
        # Unsourced bullet must still be visible.
        assert "Modifier: +5 (unsourced)" in out

    def test_attack_with_damage_projection_nested(self):
        proj = DamageProjection(
            rolled=10, kept=2,
            components=[
                ComponentDelta("katana", 4, 2),
                ComponentDelta("Fire ring", 3, 0),
                ComponentDelta("margin", 3, 0),
            ],
            extra_damage_dice=3,
            margin_over_tn=15,
        )
        entry = _attack_entry(damage_projection=proj)
        out = BulletedRenderer().render([entry])
        assert "Damage will be: 10k2" in out
        assert "4k2 katana" in out
        assert "+15 over TN" in out
        assert "3 extra damage dice" in out

    def test_attack_miss_no_damage_projection_rendered(self):
        proj = DamageProjection(
            rolled=10, kept=2,
            components=[ComponentDelta("katana", 4, 2)],
            extra_damage_dice=0, margin_over_tn=0,
        )
        # outcome=miss → no projection rendered (even if entry has one).
        entry = _attack_entry(outcome="miss", damage_projection=proj)
        out = BulletedRenderer().render([entry])
        assert "Damage will be" not in out
        assert "MISS" in out

    def test_attack_standalone_hit(self):
        entry = _attack_entry(is_combined=False, outcome="hit")
        out = BulletedRenderer().render([entry])
        assert "🎯 Attack:" in out

    def test_attack_standalone_miss(self):
        entry = _attack_entry(is_combined=False, outcome="miss")
        out = BulletedRenderer().render([entry])
        assert "❌ Attack:" in out

    def test_attack_no_detail_combined(self):
        entry = _attack_entry(has_detail=False)
        out = BulletedRenderer().render([entry])
        assert "Roll: 33" in out
        assert "⚔️ attacks Akodo" in out

    def test_attack_no_detail_standalone(self):
        entry = _attack_entry(has_detail=False, is_combined=False)
        out = BulletedRenderer().render([entry])
        assert "Roll: 33" in out


# ── Counterattack ──────────────────────────────────────────────────


def _counter_entry(
    *,
    is_combined: bool = True,
    is_take_only: bool = False,
    has_detail: bool = True,
    outcome: str = "hit",
    components: list[ComponentDelta] | None = None,
    modifier: int = 0,
) -> CounterattackEntry:
    return CounterattackEntry(
        phase_prefix="Phase 2 | Bayushi |",
        actor_name="Bayushi", target_name="Akodo",
        vp_spent=None, vp_skill=None,
        rolled=8, kept=4, modifier=modifier,
        components=components or [],
        modifier_components=[],
        dice=[10, 9, 8, 7, 5, 4, 3, 2],
        sum_of_kept=34, total=34 + modifier,
        tn=30,
        outcome=outcome,  # type: ignore[arg-type]
        damage_projection=None,
        has_detail=has_detail,
        fallback_roll=34,
        is_combined=is_combined, is_take_only=is_take_only,
    )


class TestCounterattackRendering(unittest.TestCase):
    def test_counter_take_only(self):
        entry = _counter_entry(is_take_only=True)
        out = BulletedRenderer().render([entry])
        assert "⚔️ counterattacks Akodo" in out

    def test_counter_combined_hit(self):
        entry = _counter_entry()
        out = BulletedRenderer().render([entry])
        assert "⚔️ counterattacks Akodo" in out
        assert "HIT!" in out

    def test_counter_combined_miss(self):
        entry = _counter_entry(outcome="miss")
        out = BulletedRenderer().render([entry])
        assert "MISS" in out

    def test_counter_standalone(self):
        entry = _counter_entry(is_combined=False)
        out = BulletedRenderer().render([entry])
        assert "🎯 Counterattack:" in out

    def test_counter_standalone_miss(self):
        entry = _counter_entry(is_combined=False, outcome="miss")
        out = BulletedRenderer().render([entry])
        assert "❌ Counterattack:" in out

    def test_counter_no_detail_combined(self):
        entry = _counter_entry(has_detail=False)
        out = BulletedRenderer().render([entry])
        assert "Roll: 34" in out

    def test_counter_no_detail_standalone(self):
        entry = _counter_entry(has_detail=False, is_combined=False)
        out = BulletedRenderer().render([entry])
        assert "Counterattack Roll: 34" in out

    def test_counter_with_damage_projection(self):
        proj = DamageProjection(
            rolled=5, kept=2,
            components=[ComponentDelta("katana", 4, 2),
                        ComponentDelta("Fire ring", 1, 0)],
            extra_damage_dice=0, margin_over_tn=4,
        )
        entry = CounterattackEntry(
            phase_prefix="Phase 3 | Bayushi |",
            actor_name="Bayushi", target_name="Akodo",
            vp_spent=None, vp_skill=None,
            rolled=8, kept=4, modifier=0,
            components=[],
            modifier_components=[],
            dice=[10, 9, 8, 7, 5, 4, 3, 2],
            sum_of_kept=34, total=34,
            tn=30, outcome="hit",
            damage_projection=proj,
            has_detail=True, fallback_roll=34,
            is_combined=True, is_take_only=False,
        )
        out = BulletedRenderer().render([entry])
        assert "Damage will be:" in out
        assert "4k2 katana" in out


# ── Parry ──────────────────────────────────────────────────────────


class TestParryRendering(unittest.TestCase):
    def _entry(self, *, is_combined=True, is_take_only=False,
               has_detail=True, outcome="succeeded",
               modifier=0):
        return ParryEntry(
            phase_prefix="Akodo |",
            actor_name="Akodo", target_name="Bayushi",
            rolled=8, kept=3, modifier=modifier,
            components=[], modifier_components=[],
            dice=[9, 9, 8, 8, 4, 2, 2, 1],
            sum_of_kept=26, total=26 + modifier,
            tn=30,
            outcome=outcome,
            has_detail=has_detail, fallback_roll=26,
            is_combined=is_combined, is_take_only=is_take_only,
        )

    def test_take_only(self):
        out = BulletedRenderer().render([self._entry(is_take_only=True)])
        assert "🛡️ parries Bayushi" in out

    def test_combined_succeeded(self):
        out = BulletedRenderer().render([self._entry()])
        assert "🛡️ parries Bayushi" in out
        assert "SUCCEEDED" in out

    def test_combined_failed(self):
        out = BulletedRenderer().render([self._entry(outcome="failed")])
        assert "FAILED" in out

    def test_standalone(self):
        out = BulletedRenderer().render([self._entry(is_combined=False)])
        assert "🛡️ Parry:" in out

    def test_no_detail_combined(self):
        out = BulletedRenderer().render([self._entry(has_detail=False)])
        assert "Roll: 26" in out
        assert "🛡️ parries Bayushi" in out

    def test_no_detail_standalone(self):
        out = BulletedRenderer().render([self._entry(
            has_detail=False, is_combined=False,
        )])
        assert "Parry roll: 26" in out


# ── Iaijutsu ───────────────────────────────────────────────────────


class TestIaijutsuRendering(unittest.TestCase):
    def test_challenger_won(self):
        entry = IaijutsuEntry(
            phase_prefix="Kakita |",
            actor_name="Kakita", is_challenger=True,
            skill="iaijutsu",
            skill_roll=35, opponent_skill_roll=20,
            extra_damage_dice=3,
            rolled=8, kept=3, dice=[10, 9, 8, 5, 4, 3, 2, 1],
            sum_of_kept=27, effective_modifier=8,
            has_detail=True,
        )
        out = BulletedRenderer().render([entry])
        assert "5th Dan" in out
        assert "WON" in out
        assert "(+15, 3 extra damage dice)" in out

    def test_challenger_lost_negative_extra(self):
        entry = IaijutsuEntry(
            phase_prefix="Kakita |",
            actor_name="Kakita", is_challenger=True,
            skill="iaijutsu",
            skill_roll=10, opponent_skill_roll=25,
            extra_damage_dice=-3,
            rolled=8, kept=3, dice=[],
            sum_of_kept=10, effective_modifier=0,
            has_detail=False,
        )
        out = BulletedRenderer().render([entry])
        assert "LOST" in out
        assert "3 fewer damage dice" in out

    def test_defender_tied(self):
        entry = IaijutsuEntry(
            phase_prefix="Kakita |",
            actor_name="Kakita", is_challenger=False,
            skill="defense",
            skill_roll=20, opponent_skill_roll=20,
            extra_damage_dice=0,
            rolled=5, kept=3, dice=[],
            sum_of_kept=20, effective_modifier=0,
            has_detail=False,
        )
        out = BulletedRenderer().render([entry])
        assert "Contested Iaijutsu (defense)" in out
        assert "TIED" in out

    def test_challenger_with_detail_one_extra_die(self):
        entry = IaijutsuEntry(
            phase_prefix="Kakita |",
            actor_name="Kakita", is_challenger=True,
            skill="iaijutsu",
            skill_roll=27, opponent_skill_roll=20,
            extra_damage_dice=1,
            rolled=5, kept=3, dice=[],
            sum_of_kept=20, effective_modifier=0,
            has_detail=False,
        )
        out = BulletedRenderer().render([entry])
        assert "1 extra damage die" in out


# ── LW / SW damage ─────────────────────────────────────────────────


class TestLwDamageRendering(unittest.TestCase):
    def test_lw_damage_with_components(self):
        entry = LightWoundsDamageEntry(
            phase_prefix="Bayushi |",
            attacker_name="Bayushi", target_name="Akodo",
            rolled=10, kept=7,
            components=[
                ComponentDelta("katana", 4, 2),
                ComponentDelta("Fire ring", 5, 0),
                ComponentDelta("margin", 1, 5),
            ],
            dice=[12, 11, 9, 9, 8, 6, 5, 5, 2, 2],
            sum_of_kept=60, damage=60, lw_after=60,
            has_detail=True,
        )
        out = BulletedRenderer().render([entry])
        assert "💥 Damage:" in out
        assert "60 light wounds" in out
        assert "4k2 katana" in out
        assert "5k0 Fire ring" in out
        assert "1k5 margin" in out

    def test_lw_damage_no_breakdown(self):
        entry = LightWoundsDamageEntry(
            phase_prefix="Akodo |",
            attacker_name="Akodo", target_name="Bayushi",
            rolled=7, kept=2,
            components=[ComponentDelta("katana", 4, 2)],
            dice=[9, 6, 4, 3, 2, 2, 1],
            sum_of_kept=15, damage=15, lw_after=15,
            has_detail=True,
        )
        out = BulletedRenderer().render([entry])
        assert "💥 Damage:" in out
        assert "Dice:" in out
        # Single component → no per-component sub-bullet expansion
        assert "4k2 katana\n" not in out  # would have been a bullet

    def test_lw_damage_no_detail(self):
        entry = LightWoundsDamageEntry(
            phase_prefix="Akodo |",
            attacker_name="Akodo", target_name="Bayushi",
            rolled=0, kept=0,
            components=[],
            dice=[],
            sum_of_kept=0, damage=15, lw_after=None,
            has_detail=False,
        )
        out = BulletedRenderer().render([entry])
        assert "💥 takes 15 light wounds" in out


class TestSwDamageRendering(unittest.TestCase):
    def test_one_wound(self):
        entry = SeriousWoundsDamageEntry(
            phase_prefix="Akodo |", target_name="Bayushi",
            damage=1, from_double_attack=False,
        )
        out = BulletedRenderer().render([entry])
        assert "💔 Bayushi takes 1 serious wound" in out

    def test_multi_wounds_double_attack(self):
        entry = SeriousWoundsDamageEntry(
            phase_prefix="Bayushi |", target_name="Akodo",
            damage=2, from_double_attack=True,
        )
        out = BulletedRenderer().render([entry])
        assert "💔💔" in out
        assert "2 serious wounds (double attack penalty)" in out


# ── Wound check ────────────────────────────────────────────────────


class TestWoundCheckRendering(unittest.TestCase):
    def _wc(self, **kw):
        defaults = dict(
            phase_prefix="Akodo |",
            character_name="Akodo",
            vp_spent=None, vp_source=None, vp_skill=None,
            vp_breakdown=None,
            rolled=7, kept=5, modifier=0,
            components=[], modifier_components=[],
            dice=[9, 9, 8, 6, 4, 4, 4],
            sum_of_kept=36, total=36,
            tn=23, outcome="passed",
            has_detail=True, fallback_roll=36,
            follow_up="none", follow_up_sw_count=0,
            follow_up_lw_total=0, follow_up_voluntary=False,
        )
        defaults.update(kw)
        return WoundCheckEntry(**defaults)

    def test_wc_passed_standalone(self):
        out = BulletedRenderer().render([self._wc()])
        assert "💔 Wound Check:" in out
        assert "PASSED" in out

    def test_wc_failed_standalone(self):
        out = BulletedRenderer().render([self._wc(outcome="failed",
                                                  follow_up="none")])
        assert "🖤 Wound Check:" in out
        assert "FAILED" in out

    def test_wc_keep_lw_followup(self):
        out = BulletedRenderer().render([self._wc(
            follow_up="keep_lw", follow_up_lw_total=15,
        )])
        assert "🖤 Wound Check:" in out
        assert "keeping 15 light wounds" in out

    def test_wc_take_sw_voluntary(self):
        out = BulletedRenderer().render([self._wc(
            follow_up="take_sw",
            follow_up_sw_count=1, follow_up_voluntary=True,
        )])
        assert "💔 Wound Check:" in out
        assert "chooses to take 1 serious wound" in out

    def test_wc_take_sw_involuntary_two(self):
        out = BulletedRenderer().render([self._wc(
            outcome="failed", follow_up="take_sw",
            follow_up_sw_count=2, follow_up_voluntary=False,
        )])
        assert "💔💔" in out
        assert "takes 2 serious wounds" in out

    def test_wc_with_vp_prefix(self):
        out = BulletedRenderer().render([self._wc(
            vp_spent=2, vp_skill="wound check",
        )])
        assert "⬛⬛ spends 2 VP on wound check" in out

    def test_wc_with_akodo_4th_dan_vp_prefix(self):
        out = BulletedRenderer().render([self._wc(
            vp_spent=1, vp_skill="wound check",
            vp_source="Akodo 4th Dan",
            vp_breakdown="+5 per VP = +5 (46→51)",
        )])
        assert "Akodo 4th Dan: spends 1 VP on wound check" in out
        assert "+5 per VP = +5 (46→51)" in out

    def test_wc_no_detail(self):
        out = BulletedRenderer().render([self._wc(
            has_detail=False, fallback_roll=22,
        )])
        assert "rolled 22 vs TN 23" in out


# ── Standalone keep_lw / take_sw ──────────────────────────────────


class TestStandaloneOutcomes(unittest.TestCase):
    def test_keep_lw_standalone(self):
        entry = KeepLightWoundsEntry(
            phase_prefix="Akodo |", character_name="Akodo", lw_total=18,
        )
        out = BulletedRenderer().render([entry])
        assert "🖤 keeping 18 light wounds" in out

    def test_take_sw_voluntary(self):
        entry = TakeSeriousWoundEntry(
            phase_prefix="Akodo |", character_name="Akodo", voluntary=True,
        )
        out = BulletedRenderer().render([entry])
        assert "💔 chooses to take 1 serious wound" in out

    def test_take_sw_involuntary(self):
        entry = TakeSeriousWoundEntry(
            phase_prefix="Akodo |", character_name="Akodo", voluntary=False,
        )
        out = BulletedRenderer().render([entry])
        assert "💔 takes 1 serious wound" in out


# ── VP / TVP / Floating bonus / School-negated / Akodo 5th ─────────


class TestVpTvpAndBonus(unittest.TestCase):
    def test_spend_vp(self):
        entry = SpendVpEntry(
            phase_prefix="Akodo |", character_name="Akodo",
            amount=2, skill="wound check",
        )
        out = BulletedRenderer().render([entry])
        assert "⬛⬛ spends 2 VP on wound check" in out

    def test_gain_tvp_akodo_success(self):
        entry = GainTvpEntry(
            phase_prefix="Akodo |", character_name="Akodo",
            amount=4, source="Akodo Special Ability",
        )
        out = BulletedRenderer().render([entry])
        assert "Akodo Special Ability:" in out
        assert "+4 TVP on successful feint" in out

    def test_gain_tvp_akodo_failure(self):
        entry = GainTvpEntry(
            phase_prefix="Akodo |", character_name="Akodo",
            amount=1, source="Akodo Special Ability",
        )
        out = BulletedRenderer().render([entry])
        assert "+1 TVP on failed feint" in out

    def test_gain_tvp_other_source(self):
        entry = GainTvpEntry(
            phase_prefix="X |", character_name="X",
            amount=2, source="Misc",
        )
        out = BulletedRenderer().render([entry])
        assert "✨ Misc: +2 TVP" in out

    def test_gain_tvp_no_source(self):
        entry = GainTvpEntry(
            phase_prefix="X |", character_name="X",
            amount=2, source=None,
        )
        out = BulletedRenderer().render([entry])
        assert "✨ gains +2 TVP" in out

    def test_gain_floating_bonus_with_source_and_breakdown(self):
        entry = GainFloatingBonusEntry(
            phase_prefix="Akodo |", character_name="Akodo",
            amount=15, source="Akodo 3rd Dan",
            breakdown="margin 18 ÷ 5 × attack 5",
        )
        out = BulletedRenderer().render([entry])
        assert "Akodo 3rd Dan" in out
        assert "+15" in out
        assert "(margin 18 ÷ 5 × attack 5)" in out

    def test_gain_floating_bonus_no_breakdown(self):
        entry = GainFloatingBonusEntry(
            phase_prefix="Akodo |", character_name="Akodo",
            amount=10, source="Test", breakdown=None,
        )
        out = BulletedRenderer().render([entry])
        assert "Test: gained floating bonus +10" in out

    def test_gain_floating_bonus_no_source(self):
        entry = GainFloatingBonusEntry(
            phase_prefix="X |", character_name="X",
            amount=5, source=None, breakdown=None,
        )
        out = BulletedRenderer().render([entry])
        assert "✨ gains floating bonus +5" in out

    def test_spend_floating_bonus_with_source(self):
        entry = SpendFloatingBonusEntry(
            phase_prefix="Akodo |", character_name="Akodo",
            amount=15, source="Akodo 3rd Dan",
        )
        out = BulletedRenderer().render([entry])
        assert "✨ +15 (Akodo 3rd Dan floating bonus consumed)" in out

    def test_spend_floating_bonus_no_source(self):
        entry = SpendFloatingBonusEntry(
            phase_prefix="X |", character_name="X",
            amount=5, source=None,
        )
        out = BulletedRenderer().render([entry])
        assert "✨ +5 (floating bonus consumed)" in out


class TestSchoolAndAkodo5(unittest.TestCase):
    def test_school_negated(self):
        entry = SchoolNegatedEntry(
            phase_prefix="Ishi |", negator_name="Ishi",
            target_name="Akodo", target_school_name="Akodo Bushi",
            vp_cost=10,
        )
        out = BulletedRenderer().render([entry])
        assert "⛔ negates Akodo's Akodo Bushi (10 VP — Isawa Ishi 5th Dan)" in out

    def test_akodo_5th_dan_counter(self):
        entry = AkodoFifthDanCounterEntry(
            phase_prefix="Akodo |", akodo_name="Akodo",
            vp_spent=3, damage=30, target_name="Bayushi",
        )
        out = BulletedRenderer().render([entry])
        assert "⬛⬛⬛ Akodo 5th Dan: spends 3 VP on counter-damage" in out
        assert "10 LW × 3 = 30 LW dealt to Bayushi" in out


# ── Duel entries ───────────────────────────────────────────────────


class TestDuelEntries(unittest.TestCase):
    def test_duel_header(self):
        out = BulletedRenderer().render([IaijutsuDuelHeaderEntry()])
        assert "## Iaijutsu Duel" in out

    def test_stance_declared(self):
        out = BulletedRenderer().render([ShowMeYourStanceDeclaredEntry(
            character_name="Kakita",
        )])
        assert "Kakita | 🔍 prepares to assess opponent's stance" in out

    def test_stance_rolled_no_dice(self):
        out = BulletedRenderer().render([ShowMeYourStanceRolledEntry(
            character_name="Kakita", roll=12,
            discerned_fire=3, discerned_tn=30,
            rolled=None, kept=None, dice=[],
        )])
        assert "🔍 Stance: rolled 12" in out
        assert "discerns Fire ~3" in out
        assert "TN ~30" in out

    def test_stance_rolled_with_dice(self):
        out = BulletedRenderer().render([ShowMeYourStanceRolledEntry(
            character_name="Kakita", roll=15,
            discerned_fire=3, discerned_tn=30,
            rolled=5, kept=2, dice=[8, 7, 5, 3, 2],
        )])
        assert "(5k2 [**8**, **7**, ~~5~~, ~~3~~, ~~2~~])" in out

    def test_duel_initiative(self):
        out = BulletedRenderer().render([DuelInitiativeRolledEntry(
            challenger_name="Kakita", defender_name="Bayushi",
            challenger_roll=20, defender_roll=15, winner_name="Kakita",
        )])
        assert "Contested Iaijutsu: Kakita 20 vs Bayushi 15" in out
        assert "Kakita chooses first" in out

    def test_iaijutsu_focus(self):
        out = BulletedRenderer().render([IaijutsuFocusEntry(
            character_name="Kakita",
            challenger_name="Kakita", defender_name="Bayushi",
            challenger_tn=30, defender_tn=25,
        )])
        assert "🎯 focuses" in out
        assert "Kakita 30, Bayushi 25" in out

    def test_iaijutsu_strike(self):
        out = BulletedRenderer().render([IaijutsuStrikeEntry(
            character_name="Kakita",
            challenger_name="Kakita", defender_name="Bayushi",
            challenger_tn=30, defender_tn=25,
        )])
        assert "⚔️ declares strike" in out

    def test_duel_strike_hit(self):
        out = BulletedRenderer().render([DuelStrikeRolledEntry(
            character_name="Kakita", target_name="Bayushi",
            roll=35, tn=30, is_hit=True, extra_damage_dice=2,
            rolled=None, kept=None, dice=[],
        )])
        assert "⚔️ Strike vs Bayushi" in out
        assert "HIT! (+2 extra damage dice)" in out

    def test_duel_strike_miss_with_dice(self):
        out = BulletedRenderer().render([DuelStrikeRolledEntry(
            character_name="Kakita", target_name="Bayushi",
            roll=20, tn=30, is_hit=False, extra_damage_dice=0,
            rolled=5, kept=3, dice=[8, 7, 5, 3, 2],
        )])
        assert "❌ Strike vs Bayushi" in out
        assert "5k3" in out
        assert "MISS" in out

    def test_duel_resheath(self):
        out = BulletedRenderer().render([DuelResheathEntry(
            higher_roller_name="Kakita",
        )])
        assert "Neither hit — resheathe. Kakita gains a free raise" in out

    def test_duel_ended(self):
        out = BulletedRenderer().render([DuelEndedEntry()])
        assert "Duel ended — transitioning to melee combat" in out


# ── End-of-life entries ────────────────────────────────────────────


class TestEndOfLifeEntries(unittest.TestCase):
    def test_death(self):
        out = BulletedRenderer().render([DeathEntry(
            phase_prefix="Akodo |", character_name="Akodo",
        )])
        assert "☠️ is killed!" in out

    def test_unconscious(self):
        out = BulletedRenderer().render([UnconsciousEntry(
            phase_prefix="Akodo |", character_name="Akodo",
        )])
        assert "💀 falls unconscious!" in out

    def test_surrender(self):
        out = BulletedRenderer().render([SurrenderEntry(
            phase_prefix="Akodo |", character_name="Akodo",
        )])
        assert "🏳️ surrenders!" in out


# ── End-to-end calibration combat ────────────────────────────────


class TestCalibrationCombat(unittest.TestCase):
    """Render the calibration combat through BulletedRenderer.

    Verifies SC-002: the bulleted output produced by
    ``BulletedRenderer().render(entries(history))`` contains a bullet
    structure for every attack/damage roll with > 1 source component.
    Specifically asserts the trace contains both characters' names,
    the double-attack mechanic, and standard combat lines.
    """

    def test_calibration_combat_renders(self):
        # Save/restore global RNG state so this test doesn't leak random
        # state into subsequent tests (which can shift coverage of
        # stochastic branches in simulation.duel and engine_adapter).
        saved_state = random.getstate()
        try:
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

            formatter = DetailedEventFormatter()
            entries = formatter.entries(engine.history())
            text = BulletedRenderer().render(entries)

            # Round 1 must be present.
            assert "## Round 1" in text
            # Both combatants must appear.
            assert "Akodo" in text
            assert "Bayushi" in text
            # Double attack feature is in the trace (Bayushi's choice).
            assert "double attack" in text
            # At least one bulleted breakdown of a multi-source roll.
            assert "- Dice:" in text
            # Status block must be present.
            assert "**Status:**" in text
            # Initiative roll for Round 1.
            assert "🎲 Initiative" in text
        finally:
            random.setstate(saved_state)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
