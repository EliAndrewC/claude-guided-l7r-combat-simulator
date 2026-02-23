"""Data models for analysis infrastructure."""

import json
from dataclasses import dataclass, field

from web.models import CharacterConfig, GroupConfig


@dataclass
class VariableOption:
    """One option within an analysis variable (e.g., 'on', 'off')."""
    name: str = ""
    label: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        d = {"name": self.name, "label": self.label}
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "VariableOption":
        return cls(
            name=data["name"],
            label=data["label"],
            description=data.get("description", ""),
        )


@dataclass
class AnalysisVariable:
    """A player-choice variable in a study (e.g., 'interrupt attack')."""
    name: str = ""
    label: str = ""
    description: str = ""
    options: list[VariableOption] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "label": self.label,
            "options": [o.to_dict() for o in self.options],
        }
        if self.description:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "AnalysisVariable":
        return cls(
            name=data["name"],
            label=data["label"],
            description=data.get("description", ""),
            options=[VariableOption.from_dict(o) for o in data.get("options", [])],
        )


@dataclass
class MatchupConfig:
    """Configuration for a single matchup to simulate."""
    matchup_id: str = ""
    label: str = ""
    control_characters: list[CharacterConfig] = field(default_factory=list)
    test_characters: list[CharacterConfig] = field(default_factory=list)
    control_group: GroupConfig = field(default_factory=GroupConfig)
    test_group: GroupConfig = field(default_factory=GroupConfig)
    num_trials: int = 100
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class MatchupResult:
    """Result of a single matchup simulation."""
    matchup_id: str = ""
    control_victories: int = 0
    test_victories: int = 0
    num_trials: int = 0

    def to_dict(self) -> dict:
        return {
            "matchup_id": self.matchup_id,
            "control_victories": self.control_victories,
            "test_victories": self.test_victories,
            "num_trials": self.num_trials,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MatchupResult":
        return cls(
            matchup_id=data["matchup_id"],
            control_victories=data["control_victories"],
            test_victories=data["test_victories"],
            num_trials=data["num_trials"],
        )


@dataclass
class AnalysisDefinition:
    """Definition of an analysis to run."""
    analysis_id: str = ""
    title: str = ""
    question: str = ""
    description: str = ""
    matchups: list[MatchupConfig] = field(default_factory=list)
    variables: list[AnalysisVariable] = field(default_factory=list)
    findings: dict[str, str] = field(default_factory=dict)
    strategy_map: dict[str, dict[str, dict[str, str]]] = field(
        default_factory=dict,
    )


@dataclass
class AnalysisResult:
    """Result of a completed analysis."""
    analysis_id: str = ""
    title: str = ""
    question: str = ""
    description: str = ""
    matchup_results: list[MatchupResult] = field(default_factory=list)
    interpretation: str = ""
    variables: list[AnalysisVariable] = field(default_factory=list)

    def to_json(self) -> str:
        data = {
            "analysis_id": self.analysis_id,
            "title": self.title,
            "question": self.question,
            "description": self.description,
            "matchup_results": [r.to_dict() for r in self.matchup_results],
            "interpretation": self.interpretation,
            "variables": [v.to_dict() for v in self.variables],
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "AnalysisResult":
        data = json.loads(json_str)
        return cls(
            analysis_id=data["analysis_id"],
            title=data["title"],
            question=data["question"],
            description=data["description"],
            matchup_results=[
                MatchupResult.from_dict(r) for r in data["matchup_results"]
            ],
            interpretation=data.get("interpretation", ""),
            variables=[
                AnalysisVariable.from_dict(v)
                for v in data.get("variables", [])
            ],
        )
