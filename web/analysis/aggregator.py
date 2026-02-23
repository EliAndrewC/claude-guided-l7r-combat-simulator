"""Result aggregator for school studies.

Computes marginal effects per variable, interaction effects between
variable pairs, and per-variable breakdowns by opponent and XP tier.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from web.analysis.models import AnalysisResult, AnalysisVariable, MatchupResult


@dataclass
class MarginalEffect:
    """Effect of one option within a variable, averaged over all conditions."""
    variable_name: str = ""
    variable_label: str = ""
    option_name: str = ""
    option_label: str = ""
    avg_win_rate: float = 0.0
    is_best: bool = False
    margin_over_next: float = 0.0
    consistency: float = 0.0


@dataclass
class InteractionEffect:
    """Interaction between two variables."""
    variable_a: str = ""
    variable_b: str = ""
    interaction_score: float = 0.0


@dataclass
class VariableDetail:
    """Per-variable breakdown by opponent and XP tier."""
    variable_name: str = ""
    # breakdown[opponent][xp_tier] = {option_name: avg_win_rate}
    breakdown: dict[str, dict[str, dict[str, float]]] = field(
        default_factory=dict,
    )


@dataclass
class StudySummary:
    """Full aggregated summary of a study."""
    marginal_effects: dict[str, list[MarginalEffect]] = field(
        default_factory=dict,
    )
    interactions: list[InteractionEffect] = field(default_factory=list)
    variable_details: dict[str, VariableDetail] = field(default_factory=dict)
    per_opponent_effects: dict[str, dict[str, list[MarginalEffect]]] = field(
        default_factory=dict,
    )


def _win_rate(result: MatchupResult) -> float:
    """Compute control win rate as a percentage."""
    if result.num_trials == 0:
        return 0.0
    return result.control_victories / result.num_trials * 100.0


def _mean(values: list[float]) -> float:
    """Compute mean, returning 0 for empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def compute_study_summary(
    result: AnalysisResult,
    variables: list[AnalysisVariable],
) -> StudySummary:
    """Compute marginal effects, interactions, and variable details.

    Args:
        result: The analysis result with matchup_results
        variables: Variable definitions with options

    Returns:
        StudySummary with all aggregated data
    """
    # This function requires tags to compute summaries.
    # Use compute_study_summary_with_tags() instead with explicit tags.
    return StudySummary()


def compute_study_summary_with_tags(
    results: list[MatchupResult],
    tags_by_id: dict[str, dict[str, str]],
    variables: list[AnalysisVariable],
) -> StudySummary:
    """Compute study summary using matchup results and their tags.

    Args:
        results: List of matchup results
        tags_by_id: Mapping of matchup_id -> tags dict
        variables: Variable definitions

    Returns:
        StudySummary with marginal effects, interactions, and details
    """
    if not results or not variables:
        return StudySummary()

    # Group results by their tag values
    tagged_results: list[tuple[dict[str, str], MatchupResult]] = []
    for r in results:
        tags = tags_by_id.get(r.matchup_id, {})
        if tags:
            tagged_results.append((tags, r))

    marginal_effects = _compute_marginal_effects(tagged_results, variables)
    interactions = _compute_interactions(tagged_results, variables)
    variable_details = _compute_variable_details(tagged_results, variables)
    per_opponent_effects = _compute_per_opponent_marginal_effects(
        tagged_results, variables,
    )

    return StudySummary(
        marginal_effects=marginal_effects,
        interactions=interactions,
        variable_details=variable_details,
        per_opponent_effects=per_opponent_effects,
    )


def _compute_marginal_effects(
    tagged_results: list[tuple[dict[str, str], MatchupResult]],
    variables: list[AnalysisVariable],
) -> dict[str, list[MarginalEffect]]:
    """Compute marginal effect of each variable option."""
    effects: dict[str, list[MarginalEffect]] = {}

    for var in variables:
        # Group win rates by option
        option_win_rates: dict[str, list[float]] = defaultdict(list)
        for tags, r in tagged_results:
            opt_value = tags.get(var.name)
            if opt_value is not None:
                option_win_rates[opt_value].append(_win_rate(r))

        if not option_win_rates:
            continue

        # Compute average win rate per option
        option_avgs: dict[str, float] = {
            opt: _mean(rates)
            for opt, rates in option_win_rates.items()
        }

        # Sort by avg win rate descending
        sorted_opts = sorted(option_avgs.items(), key=lambda x: -x[1])
        best_name = sorted_opts[0][0] if sorted_opts else ""
        best_avg = sorted_opts[0][1] if sorted_opts else 0.0
        second_avg = sorted_opts[1][1] if len(sorted_opts) > 1 else 0.0

        # Compute consistency: fraction of sub-groups where best-overall is
        # also best-in-sub-group
        subgroups: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list),
        )
        for tags, r in tagged_results:
            opt_value = tags.get(var.name)
            if opt_value is None:
                continue
            opp = tags.get("opponent", "")
            xp = tags.get("subject_xp", "")
            subgroups[(opp, xp)][opt_value].append(_win_rate(r))

        consistent_count = 0
        total_subgroups = 0
        for _key, sub_opts in subgroups.items():
            if len(sub_opts) < 2:
                continue
            total_subgroups += 1
            sub_avgs = {opt: _mean(rates) for opt, rates in sub_opts.items()}
            sub_best = max(sub_avgs, key=lambda x: sub_avgs[x])
            if sub_best == best_name:
                consistent_count += 1

        consistency = (
            consistent_count / total_subgroups
            if total_subgroups > 0
            else 0.0
        )

        # Build option label lookup
        label_lookup = {o.name: o.label for o in var.options}

        var_effects: list[MarginalEffect] = []
        for opt_name, avg in sorted_opts:
            var_effects.append(MarginalEffect(
                variable_name=var.name,
                variable_label=var.label,
                option_name=opt_name,
                option_label=label_lookup.get(opt_name, opt_name),
                avg_win_rate=avg,
                is_best=(opt_name == best_name),
                margin_over_next=(best_avg - second_avg if opt_name == best_name else 0.0),
                consistency=consistency if opt_name == best_name else 0.0,
            ))

        effects[var.name] = var_effects

    return effects


def _compute_interactions(
    tagged_results: list[tuple[dict[str, str], MatchupResult]],
    variables: list[AnalysisVariable],
) -> list[InteractionEffect]:
    """Compute interaction effects between all variable pairs."""
    interactions: list[InteractionEffect] = []

    for i, var_a in enumerate(variables):
        for var_b in variables[i + 1:]:
            score = _interaction_score(tagged_results, var_a, var_b)
            interactions.append(InteractionEffect(
                variable_a=var_a.name,
                variable_b=var_b.name,
                interaction_score=score,
            ))

    return interactions


def _interaction_score(
    tagged_results: list[tuple[dict[str, str], MatchupResult]],
    var_a: AnalysisVariable,
    var_b: AnalysisVariable,
) -> float:
    """Compute interaction score between two variables.

    For each option of var_b, compute the effect of var_a. If the effect
    of var_a changes depending on var_b's value, there's an interaction.
    """
    # Group by (var_a value, var_b value)
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for tags, r in tagged_results:
        a_val = tags.get(var_a.name)
        b_val = tags.get(var_b.name)
        if a_val is not None and b_val is not None:
            grouped[(a_val, b_val)].append(_win_rate(r))

    # Compute mean per (a_val, b_val)
    means: dict[tuple[str, str], float] = {
        k: _mean(v) for k, v in grouped.items()
    }

    # For each option of var_b, compute effect of var_a
    # Effect = avg(best_a option) - avg(worst_a option) conditional on b
    a_options = [o.name for o in var_a.options]
    b_options = [o.name for o in var_b.options]

    if len(a_options) < 2 or len(b_options) < 2:
        return 0.0

    # For each b option, compute the range of a effects
    conditional_effects: list[float] = []
    for b_val in b_options:
        a_avgs = []
        for a_val in a_options:
            if (a_val, b_val) in means:
                a_avgs.append(means[(a_val, b_val)])
        if len(a_avgs) >= 2:
            conditional_effects.append(max(a_avgs) - min(a_avgs))

    if len(conditional_effects) < 2:
        return 0.0

    # Interaction = max difference in conditional effects
    return max(conditional_effects) - min(conditional_effects)


def _compute_variable_details(
    tagged_results: list[tuple[dict[str, str], MatchupResult]],
    variables: list[AnalysisVariable],
) -> dict[str, VariableDetail]:
    """Compute per-variable breakdown by opponent and XP tier."""
    details: dict[str, VariableDetail] = {}

    for var in variables:
        # breakdown[opponent][xp_tier] = {option_name: avg_win_rate}
        grouped: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list)),
        )
        for tags, r in tagged_results:
            opt_value = tags.get(var.name)
            if opt_value is None:
                continue
            opp = tags.get("opponent", "unknown")
            xp = tags.get("subject_xp", "0")
            grouped[opp][xp][opt_value].append(_win_rate(r))

        breakdown: dict[str, dict[str, dict[str, float]]] = {}
        for opp, xp_data in grouped.items():
            breakdown[opp] = {}
            for xp, opt_data in xp_data.items():
                breakdown[opp][xp] = {
                    opt: _mean(rates) for opt, rates in opt_data.items()
                }

        details[var.name] = VariableDetail(
            variable_name=var.name,
            breakdown=breakdown,
        )

    return details


def _compute_per_opponent_marginal_effects(
    tagged_results: list[tuple[dict[str, str], MatchupResult]],
    variables: list[AnalysisVariable],
) -> dict[str, dict[str, list[MarginalEffect]]]:
    """Compute marginal effects per variable, broken down by opponent."""
    # Collect all opponent names
    opponents: set[str] = set()
    for tags, _r in tagged_results:
        opp = tags.get("opponent")
        if opp:
            opponents.add(opp)

    if not opponents:
        return {}

    result: dict[str, dict[str, list[MarginalEffect]]] = {}
    for var in variables:
        opp_effects: dict[str, list[MarginalEffect]] = {}
        for opp in sorted(opponents):
            subset = [(t, r) for t, r in tagged_results if t.get("opponent") == opp]
            if subset:
                effects = _compute_marginal_effects(subset, [var])
                if var.name in effects:
                    opp_effects[opp] = effects[var.name]
        if opp_effects:
            result[var.name] = opp_effects

    return result
