"""Kakita Bushi School Void Point Wound Check Threshold Study.

Investigates the impact of different VP spending thresholds on wound checks.
The comprehensive Kakita study found only +0.2% win rate for normal (0.6)
vs never spending VP — this study tests 5 threshold levels to determine
whether the threshold value matters and at what confidence level spending
becomes worthwhile.

Void Spending Dimension (5 options):
  - never: StingyWoundCheckStrategy (never spend VP on wound checks)
  - aggressive: WoundCheckStrategy02 (0.2 threshold, very liberal spending)
  - moderate: WoundCheckStrategy04 (0.4 threshold)
  - normal: WoundCheckStrategy (0.6 threshold, current default)
  - conservative: WoundCheckStrategy08 (0.8 threshold, very conservative)

Other dimensions carried from kakita_study:
  - build: 4 variants (baseline, swap_earth_water, rush_dan4, delay_dan4)
  - interrupt: KakitaAttackStrategy vs KakitaInterruptAttackStrategy
  - action_hold: HoldOneActionStrategy vs AlwaysAttackActionStrategy
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
    """Swap Earth and Water positions at ranks 3 and 4."""
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


KAKITA_VOID_STUDY_CONFIG = SchoolStudyConfig(
    school_key="kakita",
    school_name="Kakita Bushi School",
    analysis_id="kakita_void_study",
    title="Kakita Void Point Wound Check Threshold Study",
    question=(
        "Does the wound check VP spending threshold matter, "
        "and at what confidence level does spending become worthwhile?"
    ),
    description=(
        "Tests 5 different VP wound check spending thresholds (never, 0.2, "
        "0.4, 0.6, 0.8) across all build variants, strategy choices, "
        "opponents, and XP tiers for the Kakita Bushi School."
    ),
    build_variants=[
        BuildVariant(
            name="baseline",
            label="Baseline",
            description=(
                "Default Kakita priority order: raises Dan-relevant skills "
                "first, then rings in order of combat utility."
            ),
            transform=identity,
        ),
        BuildVariant(
            name="swap_earth_water",
            label="Swap Earth/Water",
            description=(
                "Swaps the priority of Earth and Water ring purchases. "
                "Water is raised early and Earth late, instead of the "
                "default Earth-first order."
            ),
            transform=_swap_earth_water,
        ),
        BuildVariant(
            name="rush_dan4",
            label="Rush Dan 4",
            description=(
                "Purchases Dan 4 skills (Double Attack, Iaijutsu 4, Lunge, "
                "Attack 4, Parry 4) before raising any rank-3 rings."
            ),
            transform=_rush_dan4,
        ),
        BuildVariant(
            name="delay_dan4",
            label="Delay Dan 4",
            description=(
                "Raises all rank-3 rings (Void, Air, Water) before purchasing "
                "any Dan 4 skills."
            ),
            transform=_delay_dan4,
        ),
    ],
    strategy_dimensions=[
        StrategyDimension(
            name="interrupt",
            label="Interrupt Attack",
            description=(
                "Whether to use the Kakita interrupt attack technique, which "
                "spends 2 future action dice to perform an iaijutsu strike "
                "outside of normal action timing."
            ),
            options=[
                StrategyOption(
                    name="off",
                    label="No Interrupt",
                    description=(
                        "Standard Kakita attacks only. Uses iaijutsu during "
                        "normal action timing but never spends future action "
                        "dice for interrupt strikes."
                    ),
                    overrides={"attack": "KakitaAttackStrategy"},
                ),
                StrategyOption(
                    name="on",
                    label="Interrupt ON",
                    description=(
                        "Spends 2 future action dice to perform an interrupt "
                        "iaijutsu strike when out of normal actions, gambling "
                        "on a decisive early hit at the cost of future turns."
                    ),
                    overrides={"attack": "KakitaInterruptAttackStrategy"},
                ),
            ],
        ),
        StrategyDimension(
            name="action_hold",
            label="Action Timing",
            description=(
                "Whether to hold one action in reserve or attack immediately "
                "whenever an action is available."
            ),
            options=[
                StrategyOption(
                    name="hold",
                    label="Hold One Action",
                    description=(
                        "Holds one action die in reserve until Phase 10 or "
                        "until multiple actions are available, preserving "
                        "flexibility to react."
                    ),
                    overrides={"action": "HoldOneActionStrategy"},
                ),
                StrategyOption(
                    name="immediate",
                    label="Always Attack",
                    description=(
                        "Attacks immediately whenever any action is available, "
                        "maximizing offensive pressure without holding back."
                    ),
                    overrides={"action": "AlwaysAttackActionStrategy"},
                ),
            ],
        ),
        StrategyDimension(
            name="void_spend",
            label="Void Spending",
            description=(
                "How aggressively Void Points are spent on wound checks. "
                "Lower thresholds mean spending VP even when the chance of "
                "benefit is small; higher thresholds only spend when highly "
                "likely to help."
            ),
            options=[
                StrategyOption(
                    name="never",
                    label="Never Spend",
                    description=(
                        "Never spends Void Points on wound checks, saving "
                        "them entirely for other uses."
                    ),
                    overrides={"wound_check": "StingyWoundCheckStrategy"},
                ),
                StrategyOption(
                    name="aggressive",
                    label="Aggressive (0.2)",
                    description=(
                        "Spends VP on wound checks with a very low 0.2 "
                        "confidence threshold — spends liberally even when "
                        "the chance of avoiding wounds is small."
                    ),
                    overrides={"wound_check": "WoundCheckStrategy02"},
                ),
                StrategyOption(
                    name="moderate",
                    label="Moderate (0.4)",
                    description=(
                        "Spends VP on wound checks with a 0.4 confidence "
                        "threshold — a balanced approach between aggressive "
                        "and conservative."
                    ),
                    overrides={"wound_check": "WoundCheckStrategy04"},
                ),
                StrategyOption(
                    name="normal",
                    label="Normal (0.6)",
                    description=(
                        "Spends VP on wound checks with the default 0.6 "
                        "confidence threshold — only spends when fairly "
                        "confident it will help."
                    ),
                    overrides={"wound_check": "WoundCheckStrategy"},
                ),
                StrategyOption(
                    name="conservative",
                    label="Conservative (0.8)",
                    description=(
                        "Spends VP on wound checks with a high 0.8 "
                        "confidence threshold — only spends when very "
                        "likely to help."
                    ),
                    overrides={"wound_check": "WoundCheckStrategy08"},
                ),
            ],
        ),
    ],
    opponents=["akodo", "bayushi", "shiba", "wave_man"],
    xp_tiers=[150, 200, 250, 300, 350, 400, 450],
    xp_deltas=[-50, 0, 50],
    findings={},
)


def build_kakita_void_study_analysis(
    num_trials: int = 100,
) -> AnalysisDefinition:
    """Build the Kakita void point wound check threshold study analysis definition."""
    return build_study_analysis(KAKITA_VOID_STUDY_CONFIG, num_trials=num_trials)
