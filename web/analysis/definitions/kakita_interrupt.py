"""Kakita Interrupt Attack Analysis.

Generates matchups comparing Kakita with and without interrupt iaijutsu attacks
against each opponent type at each XP tier.
"""

import os

from web.adapters.character_adapter import load_template_directory
from web.analysis.models import AnalysisDefinition, MatchupConfig
from web.models import CharacterConfig, GroupConfig

_TEMPLATE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "simulation", "data", "templates"
)

XP_TIERS = [150, 200, 250, 300, 350, 400, 450]
OPPONENTS = ["akodo", "bayushi", "shiba", "wave_man"]
XP_DELTAS = [-50, 0, 50]


def _load_templates() -> dict[str, CharacterConfig]:
    """Load all templates into a dict keyed by '{school_key}_{xp}'."""
    configs = load_template_directory(_TEMPLATE_DIR)
    templates: dict[str, CharacterConfig] = {}
    for config in configs:
        # Derive key from template metadata
        if config.template_school and config.template_tier:
            school_key = config.template_school.lower().split()[0]
            if config.template_school == "Wave Man":
                school_key = "wave_man"
            key = f"{school_key}_{config.template_tier}"
            templates[key] = config
    return templates


def _make_kakita_config(
    base_config: CharacterConfig,
    strategy_name: str,
) -> CharacterConfig:
    """Clone a Kakita template config and set the attack strategy."""
    strategies = dict(base_config.strategies)
    strategies["attack"] = strategy_name
    return CharacterConfig(
        name=base_config.name,
        xp=base_config.xp,
        char_type=base_config.char_type,
        school=base_config.school,
        rings=dict(base_config.rings),
        skills=dict(base_config.skills),
        weapon=base_config.weapon,
        advantages=list(base_config.advantages),
        disadvantages=list(base_config.disadvantages),
        strategies=strategies,
        abilities=dict(base_config.abilities),
        template_tier=base_config.template_tier,
        template_earned_xp=base_config.template_earned_xp,
        template_school=base_config.template_school,
    )


def build_kakita_interrupt_analysis(
    num_trials: int = 1000,
) -> AnalysisDefinition:
    """Build the analysis definition for Kakita interrupt vs no-interrupt.

    Generates matchups:
      7 XP tiers x 4 opponent types x 3 XP deltas x 2 strategies = 168 matchups

    Args:
        num_trials: Number of simulation trials per matchup

    Returns:
        AnalysisDefinition with all matchups configured
    """
    templates = _load_templates()
    matchups: list[MatchupConfig] = []

    for kakita_xp in XP_TIERS:
        kakita_key = f"kakita_{kakita_xp}"
        kakita_base = templates.get(kakita_key)
        if kakita_base is None:
            continue

        for opponent in OPPONENTS:
            for delta in XP_DELTAS:
                opponent_xp = kakita_xp + delta
                if opponent_xp < 150 or opponent_xp > 450:
                    continue

                opponent_key = f"{opponent}_{opponent_xp}"
                opponent_config = templates.get(opponent_key)
                if opponent_config is None:
                    continue

                opponent_name = opponent.replace("_", " ").title()
                kakita_group_label = f"Kakita with {kakita_xp}XP"
                opponent_group_label = f"{opponent_name} with {opponent_xp}XP"

                # Matchup: Kakita (no interrupt) vs opponent
                kakita_no_interrupt = _make_kakita_config(
                    kakita_base, "KakitaAttackStrategy",
                )
                kakita_no_interrupt.name = "Kakita"

                control_group = GroupConfig(
                    name=f"{kakita_group_label} (no interrupt)",
                    is_control=True,
                    character_names=[kakita_no_interrupt.name],
                )

                opponent_copy = CharacterConfig(
                    name=opponent_name,
                    xp=opponent_config.xp,
                    char_type=opponent_config.char_type,
                    school=opponent_config.school,
                    rings=dict(opponent_config.rings),
                    skills=dict(opponent_config.skills),
                    weapon=opponent_config.weapon,
                    advantages=list(opponent_config.advantages),
                    disadvantages=list(opponent_config.disadvantages),
                    strategies=dict(opponent_config.strategies),
                    abilities=dict(opponent_config.abilities),
                    template_tier=opponent_config.template_tier,
                    template_earned_xp=opponent_config.template_earned_xp,
                    template_school=opponent_config.template_school,
                )

                test_group_no = GroupConfig(
                    name=opponent_group_label,
                    is_control=False,
                    character_names=[opponent_copy.name],
                )

                no_interrupt_id = (
                    f"kakita_{kakita_xp}_vs_{opponent}_{opponent_xp}_no_interrupt"
                )
                matchups.append(MatchupConfig(
                    matchup_id=no_interrupt_id,
                    label=f"Kakita (no interrupt) vs {opponent_name} @ {kakita_xp}/{opponent_xp}XP",
                    control_characters=[kakita_no_interrupt],
                    test_characters=[opponent_copy],
                    control_group=control_group,
                    test_group=test_group_no,
                    num_trials=num_trials,
                    tags={
                        "kakita_xp": str(kakita_xp),
                        "opponent": opponent,
                        "opponent_xp": str(opponent_xp),
                        "xp_delta": str(delta),
                        "strategy": "no_interrupt",
                    },
                ))

                # Matchup: Kakita (interrupt) vs same opponent
                kakita_interrupt = _make_kakita_config(
                    kakita_base, "KakitaInterruptAttackStrategy",
                )
                kakita_interrupt.name = "Kakita"

                control_group_int = GroupConfig(
                    name=f"{kakita_group_label} (interrupt)",
                    is_control=True,
                    character_names=[kakita_interrupt.name],
                )

                opponent_copy_int = CharacterConfig(
                    name=opponent_name,
                    xp=opponent_config.xp,
                    char_type=opponent_config.char_type,
                    school=opponent_config.school,
                    rings=dict(opponent_config.rings),
                    skills=dict(opponent_config.skills),
                    weapon=opponent_config.weapon,
                    advantages=list(opponent_config.advantages),
                    disadvantages=list(opponent_config.disadvantages),
                    strategies=dict(opponent_config.strategies),
                    abilities=dict(opponent_config.abilities),
                    template_tier=opponent_config.template_tier,
                    template_earned_xp=opponent_config.template_earned_xp,
                    template_school=opponent_config.template_school,
                )

                test_group_int = GroupConfig(
                    name=opponent_group_label,
                    is_control=False,
                    character_names=[opponent_copy_int.name],
                )

                interrupt_id = (
                    f"kakita_{kakita_xp}_vs_{opponent}_{opponent_xp}_interrupt"
                )
                matchups.append(MatchupConfig(
                    matchup_id=interrupt_id,
                    label=f"Kakita (interrupt) vs {opponent_name} @ {kakita_xp}/{opponent_xp}XP",
                    control_characters=[kakita_interrupt],
                    test_characters=[opponent_copy_int],
                    control_group=control_group_int,
                    test_group=test_group_int,
                    num_trials=num_trials,
                    tags={
                        "kakita_xp": str(kakita_xp),
                        "opponent": opponent,
                        "opponent_xp": str(opponent_xp),
                        "xp_delta": str(delta),
                        "strategy": "interrupt",
                    },
                ))

    return AnalysisDefinition(
        analysis_id="kakita_interrupt",
        title="Kakita Interrupt Attack Analysis",
        question="Should a Kakita Bushi use interrupt attacks?",
        description=(
            "Compares Kakita Bushi win rates with and without interrupt iaijutsu "
            "attacks across multiple XP tiers and opponent types. "
            "Interrupt attacks spend 2 future action dice to attack out of turn "
            "using the Kakita's iaijutsu skill."
        ),
        matchups=matchups,
    )
