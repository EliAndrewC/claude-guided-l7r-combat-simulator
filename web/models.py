from dataclasses import dataclass, field
from typing import Any

from simulation.character_config import CharacterConfig

__all__ = ["BatchResult", "CharacterConfig", "GroupConfig", "SingleCombatResult"]


@dataclass
class GroupConfig:
    name: str = ""
    is_control: bool = False
    character_names: list[str] = field(default_factory=list)


@dataclass
class BatchResult:
    num_trials: int = 0
    control_victories: int = 0
    test_victories: int = 0
    summary: dict[str, float] = field(default_factory=dict)
    per_trial_winners: list[int] = field(default_factory=list)


@dataclass
class SingleCombatResult:
    play_by_play: list[str] = field(default_factory=list)
    # Structured trace entries (spec 007) — list of TraceEntry; consumed by
    # BulletedRenderer in the Streamlit UI. ``play_by_play`` remains for
    # back-compat (callers that consume the text form directly).
    # Typed as ``list[Any]`` here so this module can stay pure (no
    # import from ``web.adapters.trace_entries``); the engine_adapter
    # populates it with proper TraceEntry instances.
    trace_entries: list[Any] = field(default_factory=list)
    group_names: dict[str, int] = field(default_factory=dict)
    winner: int = 0
    features: dict[str, int | float] = field(default_factory=dict)
    duration_rounds: int = 0
    duration_phases: int = 0
