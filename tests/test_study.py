"""Tests for the comprehensive school study framework.

Covers: variants, generator extension, study builder, aggregator,
and Kakita study definition.
"""

import json

import pytest

from simulation.templates.generator import generate_template
from simulation.templates.strategies import KAKITA_PRIORITIES
from simulation.templates.variants import (
    identity,
    move_before,
    move_block_before,
    swap_positions,
)
from web.adapters.character_adapter import config_to_character
from web.analysis.aggregator import compute_study_summary_with_tags
from web.analysis.definitions.kakita_study import (
    KAKITA_STUDY_CONFIG,
    _delay_dan4,
    _rush_dan4,
    _swap_earth_water,
    build_kakita_study_analysis,
)
from web.analysis.models import (
    AnalysisDefinition,
    AnalysisResult,
    AnalysisVariable,
    MatchupResult,
    VariableOption,
)
from web.analysis.study import (
    BuildVariant,
    SchoolStudyConfig,
    StrategyDimension,
    StrategyOption,
    build_study_analysis,
)

# ── Layer 1: Priority List Transforms ──────────────────────────────────


SAMPLE_PRIORITIES: list[tuple[str, str, int]] = [
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("ring", "earth", 3),
    ("skill", "attack", 3),
    ("ring", "void", 3),
]


class TestIdentity:
    def test_returns_copy(self):
        result = identity(SAMPLE_PRIORITIES)
        assert result == SAMPLE_PRIORITIES
        assert result is not SAMPLE_PRIORITIES

    def test_empty_list(self):
        assert identity([]) == []


class TestSwapPositions:
    def test_basic_swap(self):
        result = swap_positions(
            SAMPLE_PRIORITIES,
            ("skill", "attack", 2),
            ("ring", "earth", 3),
        )
        assert result[0] == ("ring", "earth", 3)
        assert result[2] == ("skill", "attack", 2)
        # Other items unchanged
        assert result[1] == ("skill", "parry", 2)
        assert result[3] == ("skill", "attack", 3)
        assert result[4] == ("ring", "void", 3)

    def test_adjacent_swap(self):
        result = swap_positions(
            SAMPLE_PRIORITIES,
            ("skill", "attack", 2),
            ("skill", "parry", 2),
        )
        assert result[0] == ("skill", "parry", 2)
        assert result[1] == ("skill", "attack", 2)

    def test_item_a_not_found(self):
        with pytest.raises(ValueError, match="Item not found"):
            swap_positions(
                SAMPLE_PRIORITIES,
                ("ring", "fire", 5),
                ("skill", "attack", 2),
            )

    def test_item_b_not_found(self):
        with pytest.raises(ValueError, match="Item not found"):
            swap_positions(
                SAMPLE_PRIORITIES,
                ("skill", "attack", 2),
                ("ring", "fire", 5),
            )

    def test_does_not_mutate_original(self):
        original = list(SAMPLE_PRIORITIES)
        swap_positions(
            SAMPLE_PRIORITIES,
            ("skill", "attack", 2),
            ("ring", "earth", 3),
        )
        assert SAMPLE_PRIORITIES == original


class TestMoveBefore:
    def test_move_later_item_earlier(self):
        result = move_before(
            SAMPLE_PRIORITIES,
            ("ring", "void", 3),
            ("ring", "earth", 3),
        )
        assert result.index(("ring", "void", 3)) == 2
        assert result.index(("ring", "earth", 3)) == 3

    def test_move_earlier_item_later(self):
        result = move_before(
            SAMPLE_PRIORITIES,
            ("skill", "attack", 2),
            ("ring", "void", 3),
        )
        # attack 2 should be just before void 3
        idx_a = result.index(("skill", "attack", 2))
        idx_v = result.index(("ring", "void", 3))
        assert idx_a == idx_v - 1

    def test_item_not_found(self):
        with pytest.raises(ValueError, match="Item not found"):
            move_before(
                SAMPLE_PRIORITIES,
                ("ring", "fire", 5),
                ("skill", "attack", 2),
            )

    def test_target_not_found(self):
        with pytest.raises(ValueError, match="Target item not found"):
            move_before(
                SAMPLE_PRIORITIES,
                ("skill", "attack", 2),
                ("ring", "fire", 5),
            )

    def test_preserves_length(self):
        result = move_before(
            SAMPLE_PRIORITIES,
            ("ring", "void", 3),
            ("skill", "attack", 2),
        )
        assert len(result) == len(SAMPLE_PRIORITIES)


class TestMoveBlockBefore:
    def test_move_block(self):
        block = [("skill", "attack", 3), ("ring", "void", 3)]
        result = move_block_before(
            SAMPLE_PRIORITIES,
            block,
            ("skill", "attack", 2),
        )
        # Block should be at the front, in order
        assert result[0] == ("skill", "attack", 3)
        assert result[1] == ("ring", "void", 3)
        assert result[2] == ("skill", "attack", 2)
        assert len(result) == len(SAMPLE_PRIORITIES)

    def test_block_item_not_found(self):
        with pytest.raises(ValueError, match="Block item not found"):
            move_block_before(
                SAMPLE_PRIORITIES,
                [("ring", "fire", 5)],
                ("skill", "attack", 2),
            )

    def test_target_not_found(self):
        with pytest.raises(ValueError, match="Target item not found"):
            move_block_before(
                SAMPLE_PRIORITIES,
                [("skill", "attack", 3)],
                ("ring", "fire", 5),
            )

    def test_preserves_all_items(self):
        block = [("ring", "void", 3)]
        result = move_block_before(
            SAMPLE_PRIORITIES,
            block,
            ("skill", "attack", 2),
        )
        assert sorted(result) == sorted(SAMPLE_PRIORITIES)


# ── Layer 2: Generator Extension ───────────────────────────────────────


class TestGeneratorPrioritiesParam:
    def test_default_priorities_unchanged(self):
        """generate_template with no priorities arg uses school defaults."""
        config, _ = generate_template("kakita", 200)
        assert config.school == "Kakita Bushi School"
        assert config.xp == 200

    def test_custom_priorities_produce_different_build(self):
        """Passing different priorities should yield different ring/skill values."""
        # Baseline: default Kakita priorities
        baseline, _ = generate_template("kakita", 350)

        # Variant: swap earth 3 before all Dan 3 knacks (earth gets bought earlier)
        custom = swap_positions(
            KAKITA_PRIORITIES,
            ("ring", "earth", 3),
            ("skill", "double attack", 3),
        )
        variant, _ = generate_template("kakita", 350, priorities=custom)

        # Both should be valid configs for the same school/xp
        assert variant.school == baseline.school
        assert variant.xp == baseline.xp

    def test_custom_priorities_config_builds_character(self):
        """Config from custom priorities should successfully build a Character."""
        config, _ = generate_template("kakita", 250, priorities=KAKITA_PRIORITIES)
        char = config_to_character(config)
        assert char.ring("fire") >= 2
        assert char.skill("attack") >= 1


# ── Layer 3: Model Extensions ──────────────────────────────────────────


class TestVariableOption:
    def test_round_trip(self):
        opt = VariableOption(name="on", label="Interrupt ON")
        rebuilt = VariableOption.from_dict(opt.to_dict())
        assert rebuilt.name == "on"
        assert rebuilt.label == "Interrupt ON"


class TestAnalysisVariable:
    def test_round_trip(self):
        var = AnalysisVariable(
            name="interrupt",
            label="Interrupt Attack",
            options=[
                VariableOption(name="off", label="No Interrupt"),
                VariableOption(name="on", label="Interrupt ON"),
            ],
        )
        rebuilt = AnalysisVariable.from_dict(var.to_dict())
        assert rebuilt.name == "interrupt"
        assert len(rebuilt.options) == 2
        assert rebuilt.options[1].name == "on"


class TestAnalysisDefinitionVariables:
    def test_variables_default_empty(self):
        defn = AnalysisDefinition(analysis_id="test")
        assert defn.variables == []

    def test_variables_set(self):
        defn = AnalysisDefinition(
            analysis_id="test",
            variables=[
                AnalysisVariable(name="interrupt", label="Interrupt"),
            ],
        )
        assert len(defn.variables) == 1


class TestAnalysisResultVariables:
    def test_json_round_trip_with_variables(self):
        result = AnalysisResult(
            analysis_id="test",
            title="Test",
            question="?",
            description="d",
            matchup_results=[
                MatchupResult(matchup_id="m1", control_victories=60,
                              test_victories=40, num_trials=100),
            ],
            variables=[
                AnalysisVariable(
                    name="interrupt",
                    label="Interrupt Attack",
                    options=[
                        VariableOption(name="off", label="OFF"),
                        VariableOption(name="on", label="ON"),
                    ],
                ),
            ],
        )
        json_str = result.to_json()
        rebuilt = AnalysisResult.from_json(json_str)
        assert len(rebuilt.variables) == 1
        assert rebuilt.variables[0].name == "interrupt"
        assert len(rebuilt.variables[0].options) == 2

    def test_json_round_trip_without_variables(self):
        """Old results without variables field should still load."""
        result = AnalysisResult(
            analysis_id="old",
            title="Old",
            question="?",
            description="d",
            matchup_results=[],
        )
        json_str = result.to_json()
        # Simulate old format by stripping variables key
        data = json.loads(json_str)
        del data["variables"]
        old_json = json.dumps(data)

        rebuilt = AnalysisResult.from_json(old_json)
        assert rebuilt.variables == []


# ── Layer 4: Study Builder ─────────────────────────────────────────────


def _minimal_study_config() -> SchoolStudyConfig:
    """A small study config for fast testing."""
    return SchoolStudyConfig(
        school_key="kakita",
        school_name="Kakita Bushi School",
        build_variants=[
            BuildVariant(name="baseline", label="Baseline", transform=identity),
        ],
        strategy_dimensions=[
            StrategyDimension(
                name="interrupt",
                label="Interrupt Attack",
                options=[
                    StrategyOption(
                        name="off", label="No Interrupt",
                        overrides={"attack": "KakitaAttackStrategy"},
                    ),
                    StrategyOption(
                        name="on", label="Interrupt ON",
                        overrides={"attack": "KakitaInterruptAttackStrategy"},
                    ),
                ],
            ),
        ],
        opponents=["akodo"],
        xp_tiers=[200],
        xp_deltas=[0],
    )


class TestBuildStudyAnalysis:
    def test_basic_matchup_count(self):
        """1 build x 2 strategy options x 1 opponent x 1 tier x 1 delta = 2."""
        config = _minimal_study_config()
        defn = build_study_analysis(config, num_trials=10)
        assert len(defn.matchups) == 2

    def test_matchup_tags_present(self):
        config = _minimal_study_config()
        defn = build_study_analysis(config, num_trials=10)
        for m in defn.matchups:
            assert "build" in m.tags
            assert "opponent" in m.tags
            assert "subject_xp" in m.tags
            assert "opponent_xp" in m.tags
            assert "xp_delta" in m.tags
            assert "interrupt" in m.tags

    def test_strategy_overrides_applied(self):
        config = _minimal_study_config()
        defn = build_study_analysis(config, num_trials=10)
        strategies_seen = set()
        for m in defn.matchups:
            ctrl = m.control_characters[0]
            strategies_seen.add(ctrl.strategies.get("attack", ""))
        assert "KakitaAttackStrategy" in strategies_seen
        assert "KakitaInterruptAttackStrategy" in strategies_seen

    def test_variables_metadata(self):
        config = _minimal_study_config()
        defn = build_study_analysis(config, num_trials=10)
        assert len(defn.variables) == 2  # build + interrupt
        var_names = {v.name for v in defn.variables}
        assert "build" in var_names
        assert "interrupt" in var_names

    def test_xp_delta_clipping(self):
        """XP deltas that produce out-of-range opponent XP should be skipped."""
        config = SchoolStudyConfig(
            school_key="kakita",
            school_name="Kakita Bushi School",
            build_variants=[
                BuildVariant(name="baseline", label="Baseline", transform=identity),
            ],
            strategy_dimensions=[],
            opponents=["akodo"],
            xp_tiers=[150],
            xp_deltas=[-50, 0, 50],  # 150-50=100 invalid, 150+50=200 valid
        )
        defn = build_study_analysis(config, num_trials=10)
        # Only delta 0 and +50 should produce matchups
        assert len(defn.matchups) == 2

    def test_multiple_builds_and_strategies(self):
        """Multiple builds and strategy dimensions produce cartesian product."""
        config = SchoolStudyConfig(
            school_key="kakita",
            school_name="Kakita Bushi School",
            build_variants=[
                BuildVariant(name="base", label="Baseline", transform=identity),
                BuildVariant(name="alt", label="Alt", transform=identity),
            ],
            strategy_dimensions=[
                StrategyDimension(
                    name="interrupt",
                    label="Interrupt",
                    options=[
                        StrategyOption(name="off", label="Off", overrides={}),
                        StrategyOption(name="on", label="On", overrides={}),
                    ],
                ),
                StrategyDimension(
                    name="action",
                    label="Action",
                    options=[
                        StrategyOption(name="hold", label="Hold", overrides={}),
                        StrategyOption(name="imm", label="Immediate", overrides={}),
                    ],
                ),
            ],
            opponents=["akodo"],
            xp_tiers=[200],
            xp_deltas=[0],
        )
        defn = build_study_analysis(config, num_trials=10)
        # 2 builds x 4 strategy profiles x 1 opponent x 1 tier x 1 delta = 8
        assert len(defn.matchups) == 8

    def test_analysis_id_uses_school_key(self):
        config = _minimal_study_config()
        defn = build_study_analysis(config, num_trials=10)
        assert defn.analysis_id == "kakita_study"

    def test_matchup_configs_build_characters(self):
        """All generated configs should successfully build Character objects."""
        config = _minimal_study_config()
        defn = build_study_analysis(config, num_trials=10)
        for m in defn.matchups:
            for c in m.control_characters + m.test_characters:
                char = config_to_character(c)
                assert char is not None


# ── Layer 5: Kakita Study Definition ───────────────────────────────────


class TestKakitaTransforms:
    def test_swap_earth_water_valid(self):
        """swap_earth_water should move Water before Earth at rank 3."""
        result = _swap_earth_water(KAKITA_PRIORITIES)
        assert len(result) == len(KAKITA_PRIORITIES)
        # Water 3 should now come before Earth 3 (reversed from baseline)
        assert result.index(("ring", "water", 3)) < result.index(("ring", "earth", 3))

    def test_rush_dan4_valid(self):
        """rush_dan4 should move Dan 4 skills before Void 3."""
        result = _rush_dan4(KAKITA_PRIORITIES)
        assert len(result) == len(KAKITA_PRIORITIES)
        # Dan 4 skills should come before ring raises at rank 3
        assert result.index(("skill", "double attack", 4)) < result.index(("ring", "void", 3))

    def test_delay_dan4_valid(self):
        """delay_dan4 should move rank-3 rings before Dan 4 skills."""
        result = _delay_dan4(KAKITA_PRIORITIES)
        assert len(result) == len(KAKITA_PRIORITIES)
        # Void 3 should come before Dan 4 skills
        assert result.index(("ring", "void", 3)) < result.index(("skill", "double attack", 4))

    def test_all_transforms_preserve_items(self):
        """All transforms should contain the same items as the original."""
        for fn in [identity, _swap_earth_water, _rush_dan4, _delay_dan4]:
            result = fn(KAKITA_PRIORITIES)
            assert sorted(result) == sorted(KAKITA_PRIORITIES)


class TestKakitaStudyDefinition:
    def test_config_has_expected_structure(self):
        assert KAKITA_STUDY_CONFIG.school_key == "kakita"
        assert len(KAKITA_STUDY_CONFIG.build_variants) == 4
        assert len(KAKITA_STUDY_CONFIG.strategy_dimensions) == 3
        assert len(KAKITA_STUDY_CONFIG.opponents) == 4
        assert len(KAKITA_STUDY_CONFIG.xp_tiers) == 7
        assert len(KAKITA_STUDY_CONFIG.xp_deltas) == 3

    def test_builds_analysis_definition(self):
        defn = build_kakita_study_analysis(num_trials=10)
        assert defn.analysis_id == "kakita_study"
        assert len(defn.variables) > 0

    def test_matchup_count_in_expected_range(self):
        """Should be ~2,432 matchups (with edge clipping)."""
        defn = build_kakita_study_analysis(num_trials=10)
        # 4 builds x 8 profiles x 4 opponents x 7 tiers x 3 deltas = 2688
        # minus clipping at edges: expect roughly 2400-2500
        assert 2000 < len(defn.matchups) < 2700

    def test_all_variant_configs_build_characters(self):
        """Every build variant at every XP tier produces a buildable config."""
        for variant in KAKITA_STUDY_CONFIG.build_variants:
            priorities = variant.transform(KAKITA_PRIORITIES)
            for xp in KAKITA_STUDY_CONFIG.xp_tiers:
                config, _ = generate_template("kakita", xp, priorities=priorities)
                char = config_to_character(config)
                assert char is not None, f"Failed: {variant.name} @ {xp}XP"


# ── Layer 6: Aggregator ───────────────────────────────────────────────


def _make_tagged_results() -> tuple[
    list[MatchupResult],
    dict[str, dict[str, str]],
    list[AnalysisVariable],
]:
    """Create synthetic results for aggregator testing.

    2 options for 'interrupt' (on/off), 2 opponents, 1 xp tier.
    """
    variables = [
        AnalysisVariable(
            name="interrupt",
            label="Interrupt Attack",
            options=[
                VariableOption(name="off", label="Off"),
                VariableOption(name="on", label="On"),
            ],
        ),
    ]
    results = []
    tags_by_id: dict[str, dict[str, str]] = {}

    # interrupt=off vs akodo: 55% win
    mid = "m_off_akodo_200"
    results.append(MatchupResult(matchup_id=mid, control_victories=55,
                                  test_victories=45, num_trials=100))
    tags_by_id[mid] = {"interrupt": "off", "opponent": "akodo",
                       "subject_xp": "200", "xp_delta": "0"}

    # interrupt=on vs akodo: 60% win
    mid = "m_on_akodo_200"
    results.append(MatchupResult(matchup_id=mid, control_victories=60,
                                  test_victories=40, num_trials=100))
    tags_by_id[mid] = {"interrupt": "on", "opponent": "akodo",
                       "subject_xp": "200", "xp_delta": "0"}

    # interrupt=off vs bayushi: 50% win
    mid = "m_off_bayushi_200"
    results.append(MatchupResult(matchup_id=mid, control_victories=50,
                                  test_victories=50, num_trials=100))
    tags_by_id[mid] = {"interrupt": "off", "opponent": "bayushi",
                       "subject_xp": "200", "xp_delta": "0"}

    # interrupt=on vs bayushi: 58% win
    mid = "m_on_bayushi_200"
    results.append(MatchupResult(matchup_id=mid, control_victories=58,
                                  test_victories=42, num_trials=100))
    tags_by_id[mid] = {"interrupt": "on", "opponent": "bayushi",
                       "subject_xp": "200", "xp_delta": "0"}

    return results, tags_by_id, variables


class TestComputeStudySummary:
    def test_marginal_effects_computed(self):
        results, tags, variables = _make_tagged_results()
        summary = compute_study_summary_with_tags(results, tags, variables)
        assert "interrupt" in summary.marginal_effects
        effects = summary.marginal_effects["interrupt"]
        assert len(effects) == 2

    def test_best_option_identified(self):
        results, tags, variables = _make_tagged_results()
        summary = compute_study_summary_with_tags(results, tags, variables)
        effects = summary.marginal_effects["interrupt"]
        best = [e for e in effects if e.is_best][0]
        # on has higher avg: (60 + 58) / 2 = 59%
        assert best.option_name == "on"
        assert best.avg_win_rate == pytest.approx(59.0)

    def test_margin_over_next(self):
        results, tags, variables = _make_tagged_results()
        summary = compute_study_summary_with_tags(results, tags, variables)
        effects = summary.marginal_effects["interrupt"]
        best = [e for e in effects if e.is_best][0]
        # off avg: (55 + 50) / 2 = 52.5%, on avg: 59%, margin: 6.5%
        assert best.margin_over_next == pytest.approx(6.5)

    def test_consistency(self):
        results, tags, variables = _make_tagged_results()
        summary = compute_study_summary_with_tags(results, tags, variables)
        effects = summary.marginal_effects["interrupt"]
        best = [e for e in effects if e.is_best][0]
        # "on" is better in both subgroups (akodo, bayushi), so consistency = 1.0
        assert best.consistency == pytest.approx(1.0)

    def test_variable_details_breakdown(self):
        results, tags, variables = _make_tagged_results()
        summary = compute_study_summary_with_tags(results, tags, variables)
        detail = summary.variable_details["interrupt"]
        assert "akodo" in detail.breakdown
        assert "200" in detail.breakdown["akodo"]
        assert detail.breakdown["akodo"]["200"]["on"] == pytest.approx(60.0)
        assert detail.breakdown["akodo"]["200"]["off"] == pytest.approx(55.0)

    def test_empty_results(self):
        summary = compute_study_summary_with_tags([], {}, [])
        assert summary.marginal_effects == {}
        assert summary.interactions == []

    def test_interactions_computed(self):
        """Two-variable interaction test."""
        variables = [
            AnalysisVariable(
                name="interrupt",
                label="Interrupt",
                options=[
                    VariableOption(name="off", label="Off"),
                    VariableOption(name="on", label="On"),
                ],
            ),
            AnalysisVariable(
                name="action",
                label="Action",
                options=[
                    VariableOption(name="hold", label="Hold"),
                    VariableOption(name="imm", label="Immediate"),
                ],
            ),
        ]
        results = []
        tags_by_id: dict[str, dict[str, str]] = {}

        # Create results with a strong interaction:
        # interrupt effect is large when action=hold, small when action=imm
        combos = [
            ("off", "hold", 50), ("on", "hold", 70),  # effect of int: +20
            ("off", "imm", 48), ("on", "imm", 52),    # effect of int: +4
        ]
        for int_val, act_val, wins in combos:
            mid = f"m_{int_val}_{act_val}"
            results.append(MatchupResult(
                matchup_id=mid, control_victories=wins,
                test_victories=100 - wins, num_trials=100,
            ))
            tags_by_id[mid] = {
                "interrupt": int_val, "action": act_val,
                "opponent": "akodo", "subject_xp": "200", "xp_delta": "0",
            }

        summary = compute_study_summary_with_tags(results, tags_by_id, variables)
        assert len(summary.interactions) == 1
        # Interaction: |20 - 4| = 16
        assert summary.interactions[0].interaction_score == pytest.approx(16.0)
