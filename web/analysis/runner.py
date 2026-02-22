"""Analysis runner for batch matchup simulations."""

import os

from web.adapters.engine_adapter import run_batch
from web.analysis.models import AnalysisDefinition, AnalysisResult, MatchupResult


def run_analysis(
    definition: AnalysisDefinition,
    output_dir: str | None = None,
) -> AnalysisResult:
    """Run all matchups in an analysis definition and write results to JSON.

    Args:
        definition: The analysis to run
        output_dir: Directory to write results JSON. Defaults to web/analysis/results/

    Returns:
        AnalysisResult with all matchup results
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "results")
    os.makedirs(output_dir, exist_ok=True)

    matchup_results: list[MatchupResult] = []
    total = len(definition.matchups)

    for i, matchup in enumerate(definition.matchups):
        print(f"  [{i + 1}/{total}] {matchup.label}")
        characters = matchup.control_characters + matchup.test_characters
        groups = [matchup.control_group, matchup.test_group]
        batch_result = run_batch(characters, groups, matchup.num_trials)

        matchup_results.append(MatchupResult(
            matchup_id=matchup.matchup_id,
            control_victories=batch_result.control_victories,
            test_victories=batch_result.test_victories,
            num_trials=batch_result.num_trials,
        ))

    result = AnalysisResult(
        analysis_id=definition.analysis_id,
        title=definition.title,
        question=definition.question,
        description=definition.description,
        matchup_results=matchup_results,
    )

    # Write results to JSON
    output_path = os.path.join(output_dir, f"{definition.analysis_id}_results.json")
    with open(output_path, "w") as f:
        f.write(result.to_json())
    print(f"Results written to {output_path}")

    return result
