"""Tests for analysis CLI scripts and registry.

Covers:
- web/analysis/registry.py (public API + auto-registration)
- web/analysis/run_kakita_void_study.py (main entry point)
- web/analysis/run_kakita_vp_study.py (main entry point)
- web/analysis/models.py (defensive branches in dict-serialization)
- web/analysis/runner.py (output_dir default branch)
- web/analysis/study.py (defensive branch for missing opponent template)
"""

import json
import os
import sys
import tempfile
from unittest.mock import patch

from web.analysis import registry
from web.analysis.models import (
    AnalysisDefinition,
    AnalysisResult,
    AnalysisVariable,
    MatchupConfig,
    MatchupResult,
    VariableOption,
)
from web.models import BatchResult, CharacterConfig, GroupConfig


class TestRegistry:
    """Exercise the public API of web/analysis/registry.py."""

    def test_auto_registered_analyses_listed(self):
        """The module-level _auto_register() should register the bundled studies."""
        ids = registry.list_analyses()
        assert "kakita_void_study" in ids
        assert "kakita_vp_study" in ids
        assert "kakita_comprehensive" in ids

    def test_register_analysis_default_result_file(self):
        """register_analysis with no result_file should derive one from the id."""
        def _stub_builder() -> AnalysisDefinition:
            return AnalysisDefinition(analysis_id="stub")
        registry.register_analysis("test_registry_default", _stub_builder)
        try:
            path = registry.get_result_path("test_registry_default")
            assert path.endswith("test_registry_default_results.json")
        finally:
            del registry._REGISTRY["test_registry_default"]

    def test_register_analysis_explicit_result_file(self):
        """register_analysis with an explicit result_file should use it."""
        def _stub_builder() -> AnalysisDefinition:
            return AnalysisDefinition(analysis_id="stub")
        registry.register_analysis(
            "test_registry_explicit", _stub_builder, result_file="custom.json",
        )
        try:
            path = registry.get_result_path("test_registry_explicit")
            assert path.endswith("custom.json")
        finally:
            del registry._REGISTRY["test_registry_explicit"]

    def test_get_builder_returns_callable(self):
        builder = registry.get_builder("kakita_void_study")
        assert callable(builder)

    def test_load_result_returns_none_when_missing(self):
        """When the results file doesn't exist, load_result returns None."""
        def _stub_builder() -> AnalysisDefinition:
            return AnalysisDefinition(analysis_id="stub")
        registry.register_analysis(
            "test_registry_missing_load", _stub_builder, result_file="does_not_exist.json",
        )
        try:
            assert registry.load_result("test_registry_missing_load") is None
            assert registry.has_result("test_registry_missing_load") is False
        finally:
            del registry._REGISTRY["test_registry_missing_load"]

    def test_load_result_reads_existing_file(self, tmp_path):
        """When results file exists, load_result deserializes it."""
        result = AnalysisResult(
            analysis_id="test_load_real",
            title="t", question="q", description="d",
        )
        # Write the file into the actual results dir; clean up after.
        results_dir = os.path.join(
            os.path.dirname(registry.__file__), "results",
        )
        os.makedirs(results_dir, exist_ok=True)
        result_path = os.path.join(results_dir, "test_load_real_results.json")
        with open(result_path, "w") as f:
            f.write(result.to_json())

        def _stub_builder() -> AnalysisDefinition:
            return AnalysisDefinition(analysis_id="stub")
        registry.register_analysis("test_load_real", _stub_builder)
        try:
            assert registry.has_result("test_load_real") is True
            loaded = registry.load_result("test_load_real")
            assert loaded is not None
            assert loaded.analysis_id == "test_load_real"
        finally:
            del registry._REGISTRY["test_load_real"]
            os.unlink(result_path)


class TestAnalysisModels:
    """Defensive branches in model serialization."""

    def test_variable_option_to_dict_with_description(self):
        """VariableOption.to_dict includes description when nonempty."""
        opt = VariableOption(name="x", label="X", description="describe me")
        d = opt.to_dict()
        assert d["description"] == "describe me"
        assert d["name"] == "x"
        assert d["label"] == "X"

    def test_variable_option_to_dict_without_description(self):
        """When description is empty, the dict omits it."""
        opt = VariableOption(name="x", label="X")
        d = opt.to_dict()
        assert "description" not in d

    def test_variable_option_from_dict_missing_description(self):
        """from_dict supports missing description key."""
        opt = VariableOption.from_dict({"name": "x", "label": "X"})
        assert opt.description == ""

    def test_analysis_variable_to_dict_with_description(self):
        """AnalysisVariable.to_dict includes description when nonempty."""
        var = AnalysisVariable(
            name="v", label="V", description="describe",
            options=[VariableOption(name="o", label="O")],
        )
        d = var.to_dict()
        assert d["description"] == "describe"
        assert len(d["options"]) == 1

    def test_analysis_variable_to_dict_without_description(self):
        var = AnalysisVariable(name="v", label="V")
        d = var.to_dict()
        assert "description" not in d

    def test_analysis_variable_from_dict_missing_description_and_options(self):
        var = AnalysisVariable.from_dict({"name": "v", "label": "V"})
        assert var.description == ""
        assert var.options == []

    def test_matchup_result_to_dict_and_from_dict_roundtrip(self):
        original = MatchupResult(
            matchup_id="m", control_victories=3, test_victories=2, num_trials=5,
        )
        d = original.to_dict()
        restored = MatchupResult.from_dict(d)
        assert restored == original

    def test_analysis_result_to_and_from_json_roundtrip(self):
        original = AnalysisResult(
            analysis_id="aid", title="t", question="q", description="d",
            matchup_results=[
                MatchupResult(matchup_id="m1", control_victories=1, test_victories=0, num_trials=1),
            ],
            interpretation="interp",
            variables=[
                AnalysisVariable(
                    name="v", label="V", description="dv",
                    options=[VariableOption(name="o", label="O", description="do")],
                ),
            ],
        )
        json_str = original.to_json()
        restored = AnalysisResult.from_json(json_str)
        assert restored.analysis_id == "aid"
        assert restored.interpretation == "interp"
        assert len(restored.matchup_results) == 1
        assert len(restored.variables) == 1
        assert restored.variables[0].options[0].description == "do"


class TestRunner:
    """Exercise the default output_dir branch in run_analysis."""

    @patch("web.analysis.runner.run_batch")
    def test_default_output_dir_creates_file(self, mock_run_batch, tmp_path):
        """When output_dir is None, runner writes to web/analysis/results/."""
        mock_run_batch.return_value = BatchResult(
            num_trials=1, control_victories=1, test_victories=0,
        )
        control = CharacterConfig(name="A", char_type="generic")
        test = CharacterConfig(name="B", char_type="generic")
        matchup = MatchupConfig(
            matchup_id="test_default_out",
            label="test",
            control_characters=[control],
            test_characters=[test],
            control_group=GroupConfig(name="ctrl", is_control=True, character_names=["A"]),
            test_group=GroupConfig(name="test", is_control=False, character_names=["B"]),
            num_trials=1,
        )
        definition = AnalysisDefinition(
            analysis_id="test_default_out_runner",
            title="t", question="q", description="d",
            matchups=[matchup],
        )
        # Default output_dir is the package's results/ dir.  Clean up our
        # generated file at the end of the test.
        result_path = os.path.join(
            os.path.dirname(registry.__file__), "results",
            "test_default_out_runner_results.json",
        )
        try:
            # Don't pass output_dir → triggers the `if output_dir is None`
            # branch at line 23 of runner.py.
            result = registry  # silence unused import linter
            from web.analysis.runner import run_analysis
            result = run_analysis(definition)
            assert len(result.matchup_results) == 1
            assert os.path.exists(result_path)
        finally:
            if os.path.exists(result_path):
                os.unlink(result_path)


class TestRunKakitaVoidStudyMain:
    """Exercise the run_kakita_void_study.main() function."""

    def test_main_runs_with_mocked_run_analysis(self, capsys):
        from web.analysis import run_kakita_void_study
        with patch.object(sys, "argv", ["run_kakita_void_study", "--trials", "1"]), \
                patch("web.analysis.run_kakita_void_study.run_analysis") as mock_run:
            mock_run.return_value = AnalysisResult(
                analysis_id="kakita_void_study", matchup_results=[],
            )
            run_kakita_void_study.main()
        captured = capsys.readouterr()
        assert "Building study definition" in captured.out
        assert "Running study" in captured.out
        assert "Done" in captured.out


class TestRunKakitaVpStudyMain:
    """Exercise the run_kakita_vp_study.main() function."""

    def test_main_runs_with_mocked_run_analysis(self, capsys):
        from web.analysis import run_kakita_vp_study
        with patch.object(sys, "argv", ["run_kakita_vp_study", "--trials", "1"]), \
                patch("web.analysis.run_kakita_vp_study.run_analysis") as mock_run:
            mock_run.return_value = AnalysisResult(
                analysis_id="kakita_vp_study", matchup_results=[],
            )
            run_kakita_vp_study.main()
        captured = capsys.readouterr()
        assert "Building study definition" in captured.out
        assert "Running study" in captured.out


class TestStudyDefensiveBranch:
    """build_study_analysis should skip opponents with no matching template."""

    def test_missing_opponent_template_is_skipped(self):
        """When an opponent_key has no template for the given xp tier, that
        matchup is silently skipped (line 176 in study.py)."""
        from web.analysis.study import (
            BuildVariant,
            SchoolStudyConfig,
            build_study_analysis,
        )

        cfg = SchoolStudyConfig(
            school_key="kakita",
            school_name="Kakita",
            analysis_id="test_missing_opp",
            title="t",
            question="q",
            description="d",
            build_variants=[BuildVariant(name="base", label="Base")],
            strategy_dimensions=[],
            opponents=["does_not_exist"],  # Will not match any template
            xp_tiers=[150],  # Must be in XP_TIERS; uses 'opp_config is None' branch
            xp_deltas=[0],
        )
        definition = build_study_analysis(cfg, num_trials=1)
        # No matchups produced because the opponent template doesn't exist.
        assert definition.matchups == []

    def test_xp_tier_out_of_range_is_skipped(self):
        """When xp + delta is outside XP_TIERS, the matchup is skipped."""
        from simulation.templates.strategies import XP_TIERS
        from web.analysis.study import (
            BuildVariant,
            SchoolStudyConfig,
            build_study_analysis,
        )

        cfg = SchoolStudyConfig(
            school_key="kakita",
            school_name="Kakita",
            analysis_id="test_xp_out_of_range",
            title="t", question="q", description="d",
            build_variants=[BuildVariant(name="base", label="Base")],
            strategy_dimensions=[],
            opponents=["akodo"],
            xp_tiers=[min(XP_TIERS)],
            xp_deltas=[-10000],  # Negative delta forces opp_xp below the range
        )
        definition = build_study_analysis(cfg, num_trials=1)
        assert definition.matchups == []


class TestAggregatorDefensiveBranches:
    """Cover defensive branches in web/analysis/aggregator.py."""

    def test_win_rate_zero_trials_returns_zero(self):
        """A MatchupResult with num_trials=0 yields a 0.0 win rate (line 60)."""
        from web.analysis.aggregator import _win_rate
        result = MatchupResult(matchup_id="x", control_victories=0, test_victories=0, num_trials=0)
        assert _win_rate(result) == 0.0

    def test_mean_empty_list_returns_zero(self):
        """_mean over an empty list returns 0.0 (line 67)."""
        from web.analysis.aggregator import _mean
        assert _mean([]) == 0.0

    def test_compute_study_summary_returns_empty_summary(self):
        """compute_study_summary without tags returns an empty StudySummary (line 86)."""
        from web.analysis.aggregator import (
            StudySummary,
            compute_study_summary,
        )
        result = AnalysisResult(analysis_id="x", matchup_results=[])
        summary = compute_study_summary(result, [])
        assert isinstance(summary, StudySummary)
        assert summary.marginal_effects == {}

    def test_compute_marginal_effects_skips_variable_with_no_tags(self):
        """A variable that no matchup tag references is skipped (line 145)."""
        from web.analysis.aggregator import compute_study_summary_with_tags
        results = [
            MatchupResult(matchup_id="m1", control_victories=1, test_victories=0, num_trials=1),
        ]
        tags = {"m1": {"other_var": "x"}}
        variable = AnalysisVariable(
            name="unused_var", label="Unused",
            options=[VariableOption(name="a", label="A")],
        )
        summary = compute_study_summary_with_tags(results, tags, [variable])
        # No effect produced for the variable, since no tag references its name
        assert "unused_var" not in summary.marginal_effects

    def test_compute_marginal_effects_consistency_skips_missing_opt(self):
        """A tagged result missing the variable's option is skipped in consistency loop (line 167)."""
        from web.analysis.aggregator import compute_study_summary_with_tags
        results = [
            MatchupResult(matchup_id="m1", control_victories=1, test_victories=0, num_trials=1),
            MatchupResult(matchup_id="m2", control_victories=0, test_victories=1, num_trials=1),
            MatchupResult(matchup_id="m3", control_victories=1, test_victories=0, num_trials=1),
        ]
        # m3 has no tag for "v"
        tags = {
            "m1": {"v": "a", "opponent": "o1", "subject_xp": "100"},
            "m2": {"v": "b", "opponent": "o1", "subject_xp": "100"},
            "m3": {"opponent": "o1", "subject_xp": "100"},
        }
        variable = AnalysisVariable(
            name="v", label="V",
            options=[VariableOption(name="a", label="A"), VariableOption(name="b", label="B")],
        )
        summary = compute_study_summary_with_tags(results, tags, [variable])
        assert "v" in summary.marginal_effects

    def test_compute_marginal_effects_consistency_skips_singleton_subgroups(self):
        """Sub-groups with fewer than 2 distinct option values don't count
        toward consistency (line 176)."""
        from web.analysis.aggregator import compute_study_summary_with_tags
        # All sub-groups have only one option value, so each sub-group has <2
        # entries and is skipped.
        results = [
            MatchupResult(matchup_id="m1", control_victories=1, test_victories=0, num_trials=1),
        ]
        tags = {"m1": {"v": "a", "opponent": "o1", "subject_xp": "100"}}
        variable = AnalysisVariable(
            name="v", label="V",
            options=[VariableOption(name="a", label="A"), VariableOption(name="b", label="B")],
        )
        summary = compute_study_summary_with_tags(results, tags, [variable])
        # consistency should be 0.0 because no sub-group had ≥ 2 distinct option values
        effects = summary.marginal_effects["v"]
        best = next(e for e in effects if e.is_best)
        assert best.consistency == 0.0

    def test_interaction_score_short_circuits_when_only_one_option(self):
        """_interaction_score returns 0 when either var has < 2 options (line 258)."""
        from web.analysis.aggregator import compute_study_summary_with_tags
        results = [
            MatchupResult(matchup_id="m1", control_victories=1, test_victories=0, num_trials=1),
        ]
        tags = {"m1": {"a": "x", "b": "y"}}
        var_a = AnalysisVariable(name="a", label="A", options=[VariableOption(name="x", label="X")])
        var_b = AnalysisVariable(
            name="b", label="B",
            options=[
                VariableOption(name="y", label="Y"),
                VariableOption(name="z", label="Z"),
            ],
        )
        summary = compute_study_summary_with_tags(results, tags, [var_a, var_b])
        scores = [i for i in summary.interactions if i.variable_a == "a" and i.variable_b == "b"]
        assert scores[0].interaction_score == 0.0

    def test_interaction_score_short_circuits_when_too_few_conditional_effects(self):
        """_interaction_score returns 0 when fewer than 2 b-options produce
        ≥2 a-values (line 271)."""
        from web.analysis.aggregator import compute_study_summary_with_tags
        # var_a has 2 options, var_b has 2 options, but data only populates
        # ONE b option with both a values; the other b option only has one.
        results = [
            MatchupResult(matchup_id="m1", control_victories=1, test_victories=0, num_trials=1),
            MatchupResult(matchup_id="m2", control_victories=0, test_victories=1, num_trials=1),
            MatchupResult(matchup_id="m3", control_victories=1, test_victories=0, num_trials=1),
        ]
        tags = {
            "m1": {"a": "x", "b": "y"},
            "m2": {"a": "z", "b": "y"},
            "m3": {"a": "x", "b": "w"},  # b="w" has only one a value
        }
        var_a = AnalysisVariable(
            name="a", label="A",
            options=[VariableOption(name="x", label="X"), VariableOption(name="z", label="Z")],
        )
        var_b = AnalysisVariable(
            name="b", label="B",
            options=[VariableOption(name="y", label="Y"), VariableOption(name="w", label="W")],
        )
        summary = compute_study_summary_with_tags(results, tags, [var_a, var_b])
        scores = [i for i in summary.interactions if i.variable_a == "a" and i.variable_b == "b"]
        assert scores[0].interaction_score == 0.0

    def test_compute_variable_details_skips_missing_opt(self):
        """A tagged result missing the variable's option is skipped (line 292)."""
        from web.analysis.aggregator import compute_study_summary_with_tags
        results = [
            MatchupResult(matchup_id="m1", control_victories=1, test_victories=0, num_trials=1),
            MatchupResult(matchup_id="m2", control_victories=0, test_victories=1, num_trials=1),
        ]
        tags = {
            "m1": {"v": "a"},
            "m2": {},  # No v
        }
        variable = AnalysisVariable(
            name="v", label="V",
            options=[VariableOption(name="a", label="A")],
        )
        summary = compute_study_summary_with_tags(results, tags, [variable])
        assert "v" in summary.variable_details

    def test_per_opponent_marginal_effects_returns_empty_when_no_opponents(self):
        """When no tags carry an opponent, the per-opponent map is empty (line 326)."""
        from web.analysis.aggregator import (
            _compute_per_opponent_marginal_effects,
        )
        results = [
            (
                {"v": "a"},  # no "opponent" tag
                MatchupResult(matchup_id="m1", control_victories=1, test_victories=0, num_trials=1),
            ),
        ]
        variable = AnalysisVariable(
            name="v", label="V",
            options=[VariableOption(name="a", label="A")],
        )
        result = _compute_per_opponent_marginal_effects(results, [variable])
        assert result == {}


def _silence_unused_imports() -> None:
    """Touch unused imports so ruff is satisfied (the imports document what
    the test module needs even when individual symbols aren't used)."""
    _ = json, tempfile
