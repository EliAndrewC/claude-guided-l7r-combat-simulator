"""Analysis registry for discovering available analyses and loading results."""

import os
from collections.abc import Callable

from web.analysis.models import AnalysisDefinition, AnalysisResult

# Type for analysis builder functions
AnalysisBuilder = Callable[..., AnalysisDefinition]

# Registry: analysis_id -> (builder_function, result_file_name)
_REGISTRY: dict[str, tuple[AnalysisBuilder, str]] = {}


def register_analysis(
    analysis_id: str,
    builder: AnalysisBuilder,
    result_file: str | None = None,
) -> None:
    """Register an analysis definition builder."""
    if result_file is None:
        result_file = f"{analysis_id}_results.json"
    _REGISTRY[analysis_id] = (builder, result_file)


def list_analyses() -> list[str]:
    """Return all registered analysis IDs."""
    return list(_REGISTRY.keys())


def get_builder(analysis_id: str) -> AnalysisBuilder:
    """Return the builder function for an analysis."""
    return _REGISTRY[analysis_id][0]


def get_result_path(analysis_id: str) -> str:
    """Return the full path to the results JSON file for an analysis."""
    results_dir = os.path.join(os.path.dirname(__file__), "results")
    return os.path.join(results_dir, _REGISTRY[analysis_id][1])


def load_result(analysis_id: str) -> AnalysisResult | None:
    """Load results for an analysis, or None if not yet run."""
    path = get_result_path(analysis_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return AnalysisResult.from_json(f.read())


def has_result(analysis_id: str) -> bool:
    """Check if results exist for an analysis."""
    return os.path.exists(get_result_path(analysis_id))


# Auto-register analyses on import
def _auto_register() -> None:
    from web.analysis.definitions.kakita_interrupt import build_kakita_interrupt_analysis
    register_analysis(
        "kakita_interrupt",
        build_kakita_interrupt_analysis,
    )

    from web.analysis.definitions.kakita_study import build_kakita_study_analysis
    register_analysis(
        "kakita_study",
        build_kakita_study_analysis,
    )


_auto_register()
