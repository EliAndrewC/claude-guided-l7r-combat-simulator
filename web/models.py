from dataclasses import dataclass, field


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
    # Optional template metadata
    template_tier: str = ""
    template_earned_xp: int = 0
    template_school: str = ""


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
    group_names: dict[str, int] = field(default_factory=dict)
    winner: int = 0
    features: dict[str, int | float] = field(default_factory=dict)
    duration_rounds: int = 0
    duration_phases: int = 0
