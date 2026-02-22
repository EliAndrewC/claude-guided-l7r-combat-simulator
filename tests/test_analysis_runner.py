"""Tests for the analysis runner."""

import os
import tempfile
from unittest.mock import patch

from web.analysis.models import AnalysisDefinition, MatchupConfig
from web.analysis.runner import run_analysis
from web.models import BatchResult, CharacterConfig, GroupConfig


def _make_matchup(matchup_id: str) -> MatchupConfig:
    """Create a simple matchup config for testing."""
    control = CharacterConfig(name="Fighter A", xp=200, char_type="generic",
                              rings={"air": 3, "earth": 3, "fire": 3, "water": 2, "void": 2},
                              skills={"attack": 3, "parry": 3})
    test = CharacterConfig(name="Fighter B", xp=200, char_type="generic",
                           rings={"air": 2, "earth": 3, "fire": 3, "water": 3, "void": 2},
                           skills={"attack": 3, "parry": 3})
    return MatchupConfig(
        matchup_id=matchup_id,
        label=f"Test {matchup_id}",
        control_characters=[control],
        test_characters=[test],
        control_group=GroupConfig(name="Control", is_control=True, character_names=["Fighter A"]),
        test_group=GroupConfig(name="Test", is_control=False, character_names=["Fighter B"]),
        num_trials=10,
        tags={},
    )


class TestRunAnalysis:
    @patch("web.analysis.runner.run_batch")
    def test_calls_run_batch_per_matchup(self, mock_run_batch):
        """Runner should call run_batch once per matchup."""
        mock_run_batch.return_value = BatchResult(
            num_trials=10, control_victories=6, test_victories=4,
        )
        definition = AnalysisDefinition(
            analysis_id="test_runner",
            title="Test",
            question="?",
            description="test",
            matchups=[_make_matchup("m1"), _make_matchup("m2"), _make_matchup("m3")],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_analysis(definition, output_dir=tmpdir)

        assert mock_run_batch.call_count == 3
        assert len(result.matchup_results) == 3

    @patch("web.analysis.runner.run_batch")
    def test_writes_json_output(self, mock_run_batch):
        """Runner should write results to a JSON file."""
        mock_run_batch.return_value = BatchResult(
            num_trials=10, control_victories=7, test_victories=3,
        )
        definition = AnalysisDefinition(
            analysis_id="test_json_output",
            title="Test",
            question="?",
            description="test",
            matchups=[_make_matchup("m1")],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_analysis(definition, output_dir=tmpdir)
            output_path = os.path.join(tmpdir, "test_json_output_results.json")
            assert os.path.exists(output_path)

        assert result.analysis_id == "test_json_output"
        assert result.matchup_results[0].control_victories == 7

    @patch("web.analysis.runner.run_batch")
    def test_result_matchup_ids_match(self, mock_run_batch):
        """Each result should have the correct matchup_id."""
        mock_run_batch.return_value = BatchResult(
            num_trials=10, control_victories=5, test_victories=5,
        )
        definition = AnalysisDefinition(
            analysis_id="test_ids",
            title="Test",
            question="?",
            description="test",
            matchups=[_make_matchup("alpha"), _make_matchup("beta")],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_analysis(definition, output_dir=tmpdir)

        ids = [r.matchup_id for r in result.matchup_results]
        assert "alpha" in ids
        assert "beta" in ids
