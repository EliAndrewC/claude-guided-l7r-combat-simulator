"""School study configuration and builder.

Defines the data structures for comprehensive school studies that test all
combinations of build variants and strategy choices against all opponents.
"""

import itertools
import os
from collections.abc import Callable
from dataclasses import dataclass, field

from simulation.templates.generator import generate_template
from simulation.templates.strategies import SCHOOL_NAMES, SCHOOL_PRIORITIES, XP_TIERS
from simulation.templates.variants import PriorityList
from web.adapters.character_adapter import load_template_directory
from web.analysis.models import (
    AnalysisDefinition,
    AnalysisVariable,
    MatchupConfig,
    VariableOption,
)
from web.models import CharacterConfig, GroupConfig

_TEMPLATE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "simulation", "data", "templates"
)


@dataclass
class StrategyOption:
    """One option within a strategy dimension."""
    name: str = ""
    label: str = ""
    description: str = ""
    overrides: dict[str, str] = field(default_factory=dict)
    extra_tags: dict[str, str] = field(default_factory=dict)


@dataclass
class StrategyDimension:
    """A strategy choice axis (e.g., interrupt on/off)."""
    name: str = ""
    label: str = ""
    description: str = ""
    options: list[StrategyOption] = field(default_factory=list)


@dataclass
class BuildVariant:
    """A build order variant (different XP spending priorities)."""
    name: str = ""
    label: str = ""
    description: str = ""
    transform: Callable[[PriorityList], PriorityList] = field(
        default_factory=lambda: lambda p: list(p)
    )


@dataclass
class SchoolStudyConfig:
    """Full configuration for a school study."""
    school_key: str = ""
    school_name: str = ""
    analysis_id: str = ""
    title: str = ""
    question: str = ""
    description: str = ""
    build_variants: list[BuildVariant] = field(default_factory=list)
    strategy_dimensions: list[StrategyDimension] = field(default_factory=list)
    opponents: list[str] = field(default_factory=list)
    xp_tiers: list[int] = field(default_factory=list)
    xp_deltas: list[int] = field(default_factory=list)
    findings: dict[str, str] = field(default_factory=dict)
    extra_variables: list[AnalysisVariable] = field(default_factory=list)


def _clone_config(
    config: CharacterConfig,
    strategy_overrides: dict[str, str] | None = None,
    name: str | None = None,
) -> CharacterConfig:
    """Deep-copy a CharacterConfig, optionally applying strategy overrides."""
    strategies = dict(config.strategies)
    if strategy_overrides:
        strategies.update(strategy_overrides)
    return CharacterConfig(
        name=name if name is not None else config.name,
        xp=config.xp,
        char_type=config.char_type,
        school=config.school,
        rings=dict(config.rings),
        skills=dict(config.skills),
        weapon=config.weapon,
        advantages=list(config.advantages),
        disadvantages=list(config.disadvantages),
        strategies=strategies,
        abilities=dict(config.abilities),
        template_tier=config.template_tier,
        template_earned_xp=config.template_earned_xp,
        template_school=config.template_school,
    )


def _load_opponent_templates() -> dict[str, CharacterConfig]:
    """Load all baseline templates, keyed by '{school_key}_{xp}'."""
    configs = load_template_directory(_TEMPLATE_DIR)
    templates: dict[str, CharacterConfig] = {}
    for config in configs:
        if config.template_school and config.template_tier:
            school_key = config.template_school.lower().split()[0]
            if config.template_school == "Wave Man":
                school_key = "wave_man"
            key = f"{school_key}_{config.template_tier}"
            templates[key] = config
    return templates


def build_study_analysis(
    config: SchoolStudyConfig,
    num_trials: int = 100,
) -> AnalysisDefinition:
    """Build an AnalysisDefinition from a SchoolStudyConfig.

    Generates matchups for all combinations of:
      build variants x strategy profiles x opponents x XP tiers x XP deltas

    Args:
        config: The study configuration
        num_trials: Trials per matchup

    Returns:
        AnalysisDefinition with all matchups and variable metadata
    """
    opponent_templates = _load_opponent_templates()
    baseline_priorities = SCHOOL_PRIORITIES[SCHOOL_NAMES[config.school_key]]

    # Pre-generate subject configs for each (build_variant, xp_tier)
    subject_configs: dict[tuple[str, int], CharacterConfig] = {}
    for variant in config.build_variants:
        transformed = variant.transform(baseline_priorities)
        for xp in config.xp_tiers:
            cfg, _ = generate_template(
                config.school_key, xp, priorities=transformed,
            )
            subject_configs[(variant.name, xp)] = cfg

    # Build strategy profiles = cartesian product of dimension options
    dimension_options = [dim.options for dim in config.strategy_dimensions]
    if dimension_options:
        strategy_profiles = list(itertools.product(*dimension_options))
    else:
        strategy_profiles = [()]

    matchups: list[MatchupConfig] = []
    subject_label = config.school_key.replace("_", " ").title()

    for variant in config.build_variants:
        for profile in strategy_profiles:
            # Merge all strategy overrides from this profile
            merged_overrides: dict[str, str] = {}
            for opt in profile:
                merged_overrides.update(opt.overrides)

            for xp in config.xp_tiers:
                base_config = subject_configs[(variant.name, xp)]

                for opponent_key in config.opponents:
                    for delta in config.xp_deltas:
                        opp_xp = xp + delta
                        if opp_xp < min(XP_TIERS) or opp_xp > max(XP_TIERS):
                            continue

                        opp_template_key = f"{opponent_key}_{opp_xp}"
                        opp_config = opponent_templates.get(opp_template_key)
                        if opp_config is None:
                            continue

                        # Build tags
                        tags: dict[str, str] = {
                            "build": variant.name,
                            "opponent": opponent_key,
                            "subject_xp": str(xp),
                            "opponent_xp": str(opp_xp),
                            "xp_delta": str(delta),
                        }
                        for dim, opt in zip(
                            config.strategy_dimensions, profile,
                        ):
                            tags[dim.name] = opt.name
                            if opt.extra_tags:
                                tags.update(opt.extra_tags)

                        # Build matchup ID
                        strategy_parts = "_".join(
                            opt.name for opt in profile
                        )
                        matchup_id = (
                            f"{config.school_key}_{xp}_{variant.name}"
                            f"_{strategy_parts}_vs_{opponent_key}_{opp_xp}"
                        )

                        # Build label
                        opp_label = opponent_key.replace("_", " ").title()
                        label = (
                            f"{subject_label} ({variant.label}"
                            f", {strategy_parts}) vs {opp_label}"
                            f" @ {xp}/{opp_xp}XP"
                        )

                        subject = _clone_config(
                            base_config,
                            strategy_overrides=merged_overrides,
                            name=subject_label,
                        )
                        opponent = _clone_config(opp_config, name=opp_label)

                        control_group = GroupConfig(
                            name=f"{subject_label} with {xp}XP",
                            is_control=True,
                            character_names=[subject.name],
                        )
                        test_group = GroupConfig(
                            name=f"{opp_label} with {opp_xp}XP",
                            is_control=False,
                            character_names=[opponent.name],
                        )

                        matchups.append(MatchupConfig(
                            matchup_id=matchup_id,
                            label=label,
                            control_characters=[subject],
                            test_characters=[opponent],
                            control_group=control_group,
                            test_group=test_group,
                            num_trials=num_trials,
                            tags=tags,
                        ))

    # Build AnalysisVariable metadata
    variables: list[AnalysisVariable] = []
    # Build variant as a variable
    build_desc = "The order in which XP is spent on rings, skills, and Dan advancement"
    variables.append(AnalysisVariable(
        name="build",
        label="Build Order",
        description=build_desc,
        options=[
            VariableOption(name=v.name, label=v.label, description=v.description)
            for v in config.build_variants
        ],
    ))
    for dim in config.strategy_dimensions:
        variables.append(AnalysisVariable(
            name=dim.name,
            label=dim.label,
            description=dim.description,
            options=[
                VariableOption(
                    name=opt.name, label=opt.label, description=opt.description,
                )
                for opt in dim.options
            ],
        ))
    # Add any extra variables defined by the study config
    variables.extend(config.extra_variables)

    study_id = config.analysis_id or f"{config.school_key}_study"
    study_title = config.title or f"{config.school_name} Comprehensive Study"
    study_question = config.question or (
        f"What are the optimal tactical choices for a {subject_label}?"
    )
    study_description = config.description or (
        f"Tests all combinations of build variants and strategy choices "
        f"for {config.school_name} against all opponents at all XP tiers. "
        f"{len(matchups)} total matchups."
    )

    return AnalysisDefinition(
        analysis_id=study_id,
        title=study_title,
        question=study_question,
        description=study_description,
        matchups=matchups,
        variables=variables,
        findings=dict(config.findings),
    )
