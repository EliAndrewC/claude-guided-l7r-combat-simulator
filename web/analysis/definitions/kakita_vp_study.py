"""Kakita Bushi School VP Allocation Study (Offense vs Defense).

Investigates whether Void Points are better spent offensively (on attack rolls)
or defensively (on wound checks). The previous void study found that wound check
VP threshold barely matters (+0.2%). This study compares attack VP spending
against wound check VP spending to understand optimal VP allocation.

Dimensions:
  - build: 4 variants (baseline, swap_earth_water, rush_dan4, delay_dan4)
  - attack_style: 6 options (flattened: 2 interrupt x 3 attack VP levels)
    Each option carries extra_tags for independent 'interrupt' and 'attack_vp'
    analysis.
  - action_hold: 2 options (hold vs immediate)
  - wound_check_vp: 2 options (never vs threshold 0.5)

Total profiles: 4 x 6 x 2 x 2 = 96
Matchups: 96 x 4 opponents x ~19 XP combos ~ 7,296
"""

from simulation.templates.variants import (
    identity,
    move_block_before,
    swap_positions,
)
from web.analysis.models import AnalysisDefinition, AnalysisVariable, VariableOption
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


# Flattened attack_style dimension: 2 interrupt x 3 attack VP levels = 6 options
# Each option sets the 'attack' strategy override and carries extra_tags
# for independent aggregation of 'interrupt' and 'attack_vp'.
_ATTACK_STYLE_OPTIONS = [
    # No interrupt, no VP on attacks
    StrategyOption(
        name="std_novp",
        label="Standard, No Attack VP",
        description=(
            "Standard Kakita attacks (no interrupt), never spending VP on "
            "attack rolls."
        ),
        overrides={"attack": "KakitaNoVPAttackStrategy"},
        extra_tags={"interrupt": "off", "attack_vp": "never"},
    ),
    # No interrupt, VP threshold 0.5
    StrategyOption(
        name="std_vp05",
        label="Standard, Attack VP 0.5",
        description=(
            "Standard Kakita attacks (no interrupt), spending VP on attack "
            "rolls with a 0.5 confidence threshold."
        ),
        overrides={"attack": "KakitaAttackStrategy05"},
        extra_tags={"interrupt": "off", "attack_vp": "threshold_05"},
    ),
    # No interrupt, VP threshold 0.7 (default)
    StrategyOption(
        name="std_vp07",
        label="Standard, Attack VP 0.7",
        description=(
            "Standard Kakita attacks (no interrupt), spending VP on attack "
            "rolls with the default 0.7 confidence threshold."
        ),
        overrides={"attack": "KakitaAttackStrategy"},
        extra_tags={"interrupt": "off", "attack_vp": "threshold_07"},
    ),
    # Interrupt, no VP on attacks
    StrategyOption(
        name="int_novp",
        label="Interrupt, No Attack VP",
        description=(
            "Kakita interrupt attacks enabled, never spending VP on "
            "attack rolls."
        ),
        overrides={"attack": "KakitaNoVPInterruptAttackStrategy"},
        extra_tags={"interrupt": "on", "attack_vp": "never"},
    ),
    # Interrupt, VP threshold 0.5
    StrategyOption(
        name="int_vp05",
        label="Interrupt, Attack VP 0.5",
        description=(
            "Kakita interrupt attacks enabled, spending VP on attack "
            "rolls with a 0.5 confidence threshold."
        ),
        overrides={"attack": "KakitaInterruptAttackStrategy05"},
        extra_tags={"interrupt": "on", "attack_vp": "threshold_05"},
    ),
    # Interrupt, VP threshold 0.7 (default)
    StrategyOption(
        name="int_vp07",
        label="Interrupt, Attack VP 0.7",
        description=(
            "Kakita interrupt attacks enabled, spending VP on attack "
            "rolls with the default 0.7 confidence threshold."
        ),
        overrides={"attack": "KakitaInterruptAttackStrategy"},
        extra_tags={"interrupt": "on", "attack_vp": "threshold_07"},
    ),
]

KAKITA_VP_STUDY_CONFIG = SchoolStudyConfig(
    school_key="kakita",
    school_name="Kakita Bushi School",
    analysis_id="kakita_vp_study",
    title="Kakita VP Allocation Study (Offense vs Defense)",
    question=(
        "Are Void Points better spent offensively (on attack rolls) or "
        "defensively (on wound checks)?"
    ),
    description=(
        "Tests combinations of attack VP spending (never, 0.5, 0.7 threshold) "
        "and wound check VP spending (never, 0.5 threshold) across all build "
        "variants, interrupt modes, action timing choices, opponents, and XP "
        "tiers for the Kakita Bushi School."
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
            name="attack_style",
            label="Attack Style",
            description=(
                "Combined interrupt mode and attack VP spending. Flattened "
                "from 2 interrupt options x 3 attack VP options to avoid "
                "conflicting 'attack' strategy overrides."
            ),
            options=_ATTACK_STYLE_OPTIONS,
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
            name="wound_check_vp",
            label="Wound Check VP",
            description=(
                "Whether to spend Void Points on wound checks and at what "
                "confidence threshold."
            ),
            options=[
                StrategyOption(
                    name="never",
                    label="Never Spend",
                    description=(
                        "Never spends Void Points on wound checks, saving "
                        "them entirely for attack rolls."
                    ),
                    overrides={"wound_check": "StingyWoundCheckStrategy"},
                ),
                StrategyOption(
                    name="threshold_05",
                    label="Threshold 0.5",
                    description=(
                        "Spends VP on wound checks with a 0.5 confidence "
                        "threshold — spends when moderately likely to help."
                    ),
                    overrides={"wound_check": "WoundCheckStrategy05"},
                ),
            ],
        ),
    ],
    # Extra variables for the sub-dimensions encoded in extra_tags
    extra_variables=[
        AnalysisVariable(
            name="interrupt",
            label="Interrupt Attack",
            description=(
                "Whether to use the Kakita interrupt attack technique "
                "(extracted from the flattened attack_style dimension)."
            ),
            options=[
                VariableOption(
                    name="off",
                    label="No Interrupt",
                    description="Standard Kakita attacks only.",
                ),
                VariableOption(
                    name="on",
                    label="Interrupt ON",
                    description="Interrupt iaijutsu attacks enabled.",
                ),
            ],
        ),
        AnalysisVariable(
            name="attack_vp",
            label="Attack VP Spending",
            description=(
                "How aggressively Void Points are spent on attack rolls "
                "(extracted from the flattened attack_style dimension)."
            ),
            options=[
                VariableOption(
                    name="never",
                    label="Never",
                    description="Never spend VP on attack rolls.",
                ),
                VariableOption(
                    name="threshold_05",
                    label="Threshold 0.5",
                    description="Spend VP on attacks with 0.5 confidence threshold.",
                ),
                VariableOption(
                    name="threshold_07",
                    label="Threshold 0.7",
                    description="Spend VP on attacks with 0.7 confidence threshold (default).",
                ),
            ],
        ),
    ],
    opponents=["akodo", "bayushi", "shiba", "wave_man"],
    xp_tiers=[150, 200, 250, 300, 350, 400, 450],
    xp_deltas=[-50, 0, 50],
    findings={},
)


def build_kakita_vp_study_analysis(
    num_trials: int = 100,
) -> AnalysisDefinition:
    """Build the Kakita VP allocation study analysis definition."""
    return build_study_analysis(KAKITA_VP_STUDY_CONFIG, num_trials=num_trials)
