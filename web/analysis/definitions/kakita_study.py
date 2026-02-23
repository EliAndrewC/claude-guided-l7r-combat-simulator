"""Kakita Bushi School Comprehensive Study.

Tests all combinations of build variants (4) and strategy choices (3 dimensions
with 2 options each = 8 profiles) against 4 opponents at 7 XP tiers with 3 XP
deltas. Total: ~2,432 matchups.

Build Variants:
  - baseline: Default Kakita priority order
  - earth_before_water: Earth ring raised before Water ring at ranks 3 and 4
  - rush_dan4: Dan 4 skill purchases before rank-3 ring raises
  - delay_dan4: All rank-3 ring raises before Dan 4 skill purchases

Strategy Dimensions:
  - interrupt: KakitaAttackStrategy vs KakitaInterruptAttackStrategy
  - action_hold: HoldOneActionStrategy vs AlwaysAttackActionStrategy
  - void_spend: WoundCheckStrategy vs StingyWoundCheckStrategy
"""

from simulation.templates.variants import (
    identity,
    move_block_before,
    swap_positions,
)
from web.analysis.models import AnalysisDefinition
from web.analysis.study import (
    BuildVariant,
    SchoolStudyConfig,
    StrategyDimension,
    StrategyOption,
    build_study_analysis,
)


def _swap_earth_water(priorities: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    """Swap Earth and Water positions at ranks 3 and 4.

    In the baseline, Earth is raised early and Water late. This variant
    reverses that, raising Water early and Earth late.
    """
    result = swap_positions(
        priorities,
        ("ring", "earth", 3),
        ("ring", "water", 3),
    )
    result = swap_positions(
        result,
        ("ring", "earth", 4),
        ("ring", "water", 4),
    )
    return result


def _rush_dan4(priorities: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    """Move Dan 4 skill block before rank-3 ring raises (Void, Air, Water)."""
    dan4_skills = [
        ("skill", "double attack", 4),
        ("skill", "iaijutsu", 4),
        ("skill", "lunge", 4),
        ("skill", "attack", 4),
        ("skill", "parry", 4),
    ]
    return move_block_before(priorities, dan4_skills, ("ring", "void", 3))


def _delay_dan4(priorities: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    """Move rank-3 rings (Void, Air, Water) before Dan 4 skill block."""
    rank3_rings = [
        ("ring", "void", 3),
        ("ring", "air", 3),
        ("ring", "water", 3),
    ]
    return move_block_before(
        priorities, rank3_rings, ("skill", "double attack", 4),
    )


KAKITA_STUDY_CONFIG = SchoolStudyConfig(
    school_key="kakita",
    school_name="Kakita Bushi School",
    build_variants=[
        BuildVariant(
            name="baseline",
            label="Baseline",
            transform=identity,
        ),
        BuildVariant(
            name="swap_earth_water",
            label="Swap Earth/Water",
            transform=_swap_earth_water,
        ),
        BuildVariant(
            name="rush_dan4",
            label="Rush Dan 4",
            transform=_rush_dan4,
        ),
        BuildVariant(
            name="delay_dan4",
            label="Delay Dan 4",
            transform=_delay_dan4,
        ),
    ],
    strategy_dimensions=[
        StrategyDimension(
            name="interrupt",
            label="Interrupt Attack",
            options=[
                StrategyOption(
                    name="off",
                    label="No Interrupt",
                    overrides={"attack": "KakitaAttackStrategy"},
                ),
                StrategyOption(
                    name="on",
                    label="Interrupt ON",
                    overrides={"attack": "KakitaInterruptAttackStrategy"},
                ),
            ],
        ),
        StrategyDimension(
            name="action_hold",
            label="Action Timing",
            options=[
                StrategyOption(
                    name="hold",
                    label="Hold One Action",
                    overrides={"action": "HoldOneActionStrategy"},
                ),
                StrategyOption(
                    name="immediate",
                    label="Always Attack",
                    overrides={"action": "AlwaysAttackActionStrategy"},
                ),
            ],
        ),
        StrategyDimension(
            name="void_spend",
            label="Void Spending",
            options=[
                StrategyOption(
                    name="normal",
                    label="Normal",
                    overrides={"wound_check": "WoundCheckStrategy"},
                ),
                StrategyOption(
                    name="stingy",
                    label="Stingy",
                    overrides={"wound_check": "StingyWoundCheckStrategy"},
                ),
            ],
        ),
    ],
    opponents=["akodo", "bayushi", "shiba", "wave_man"],
    xp_tiers=[150, 200, 250, 300, 350, 400, 450],
    xp_deltas=[-50, 0, 50],
)


def build_kakita_study_analysis(
    num_trials: int = 1000,
) -> AnalysisDefinition:
    """Build the comprehensive Kakita study analysis definition."""
    return build_study_analysis(KAKITA_STUDY_CONFIG, num_trials=num_trials)
