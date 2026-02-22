"""Tests for analysis data models."""

from web.analysis.models import AnalysisDefinition, AnalysisResult, MatchupConfig, MatchupResult
from web.models import CharacterConfig, GroupConfig


class TestMatchupResult:
    def test_creation(self):
        result = MatchupResult(
            matchup_id="test_1",
            control_victories=60,
            test_victories=40,
            num_trials=100,
        )
        assert result.matchup_id == "test_1"
        assert result.control_victories == 60
        assert result.test_victories == 40
        assert result.num_trials == 100

    def test_to_dict(self):
        result = MatchupResult(
            matchup_id="test_1",
            control_victories=60,
            test_victories=40,
            num_trials=100,
        )
        d = result.to_dict()
        assert d["matchup_id"] == "test_1"
        assert d["control_victories"] == 60

    def test_from_dict(self):
        d = {
            "matchup_id": "test_2",
            "control_victories": 70,
            "test_victories": 30,
            "num_trials": 100,
        }
        result = MatchupResult.from_dict(d)
        assert result.matchup_id == "test_2"
        assert result.control_victories == 70

    def test_round_trip(self):
        original = MatchupResult(
            matchup_id="rt_1",
            control_victories=55,
            test_victories=45,
            num_trials=100,
        )
        rebuilt = MatchupResult.from_dict(original.to_dict())
        assert rebuilt.matchup_id == original.matchup_id
        assert rebuilt.control_victories == original.control_victories
        assert rebuilt.test_victories == original.test_victories
        assert rebuilt.num_trials == original.num_trials


class TestMatchupConfig:
    def test_creation(self):
        config = MatchupConfig(
            matchup_id="m1",
            label="Test matchup",
            control_characters=[CharacterConfig(name="A")],
            test_characters=[CharacterConfig(name="B")],
            control_group=GroupConfig(name="Control", is_control=True, character_names=["A"]),
            test_group=GroupConfig(name="Test", is_control=False, character_names=["B"]),
            num_trials=500,
            tags={"xp_tier": "200"},
        )
        assert config.matchup_id == "m1"
        assert config.num_trials == 500
        assert len(config.control_characters) == 1
        assert config.tags["xp_tier"] == "200"


class TestAnalysisDefinition:
    def test_creation(self):
        defn = AnalysisDefinition(
            analysis_id="test_analysis",
            title="Test",
            question="Does this work?",
            description="A test analysis.",
            matchups=[],
        )
        assert defn.analysis_id == "test_analysis"
        assert defn.question == "Does this work?"


class TestAnalysisResult:
    def test_json_round_trip(self):
        result = AnalysisResult(
            analysis_id="test_analysis",
            title="Test Analysis",
            question="Is it working?",
            description="Test description.",
            matchup_results=[
                MatchupResult(matchup_id="m1", control_victories=60, test_victories=40, num_trials=100),
                MatchupResult(matchup_id="m2", control_victories=55, test_victories=45, num_trials=100),
            ],
            interpretation="Results look good.",
        )
        json_str = result.to_json()
        rebuilt = AnalysisResult.from_json(json_str)
        assert rebuilt.analysis_id == result.analysis_id
        assert rebuilt.title == result.title
        assert rebuilt.question == result.question
        assert rebuilt.description == result.description
        assert rebuilt.interpretation == result.interpretation
        assert len(rebuilt.matchup_results) == 2
        assert rebuilt.matchup_results[0].matchup_id == "m1"
        assert rebuilt.matchup_results[1].control_victories == 55
