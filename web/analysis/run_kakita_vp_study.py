"""CLI entry point for running the Kakita VP allocation study.

Usage:
    env/bin/python -m web.analysis.run_kakita_vp_study --trials 1000
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from web.analysis.definitions.kakita_vp_study import build_kakita_vp_study_analysis
from web.analysis.runner import run_analysis


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Kakita VP allocation study (offense vs defense)",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=100,
        help="Number of trials per matchup (default: 100)",
    )
    args = parser.parse_args()

    print(f"Building study definition with {args.trials} trials per matchup...")
    definition = build_kakita_vp_study_analysis(num_trials=args.trials)
    print(f"  {len(definition.matchups)} matchups to simulate")
    print(f"  {len(definition.variables)} variables tracked")

    print("Running study...")
    result = run_analysis(definition)
    print(f"Done! {len(result.matchup_results)} matchup results collected.")


if __name__ == "__main__":
    main()
