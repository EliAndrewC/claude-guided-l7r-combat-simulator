"""The plain data shape of a character build.

Lives under ``simulation`` (not ``web``) so the template generator, and any
app that installs this package to call it, does not need ``web``.
``web.models`` re-exports it for the Streamlit layer.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CharacterConfig:
    name: str = ""
    xp: int = 100
    char_type: str = "generic"  # "generic", "school", "profession"
    school: str = ""
    rings: dict[str, int] = field(default_factory=lambda: {"air": 2, "earth": 2, "fire": 2, "water": 2, "void": 2})
    skills: dict[str, int] = field(default_factory=dict)
    weapon: str = "katana"
    advantages: list[str] = field(default_factory=list)
    disadvantages: list[str] = field(default_factory=list)
    strategies: dict[str, str] = field(default_factory=dict)
    abilities: dict[str, int] = field(default_factory=dict)
    # Per-character build-time school choices (e.g., 1st Dan "any two skills",
    # Ide "any non-Void ring"). Keys are school-defined; defaults preserved
    # when absent. See specs/003-school-choices/spec.md FR-001.
    school_choices: dict[str, Any] = field(default_factory=dict)
    # Optional template metadata
    template_tier: str = ""
    template_earned_xp: int = 0
    template_school: str = ""
