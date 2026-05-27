# Phase 0 Research: Coverage to 100%

## Current coverage baseline (2026-05-27)

```
TOTAL                                                    11400   1732    85%
```

## Per-file uncovered breakdown

Baseline `env/bin/pytest tests/ --cov=simulation --cov=web --cov-report=term --no-header`:

### High-uncovered-count files (priority targets)

| File | Statements | Uncovered | % |
|------|-----------|-----------|---|
| `web/views/4_Analysis.py` | 451 | 451 | 0% — Category B (pragma) |
| `web/views/3_Run_Simulation.py` | 147 | 147 | 0% — Category B (pragma) |
| `web/adapters/detailed_formatter.py` | 825 | 100 | 88% — Category A (test) |
| `web/views/1_Characters.py` | 90 | 90 | 0% — Category B (pragma) |
| `web/adapters/combat_observer.py` | 315 | 50 | 84% — Category A (test) |
| `web/adapters/engine_adapter.py` | 123 | 49 | 60% — Category A (test) |
| `web/views/2_Combat_Setup.py` | 38 | 38 | 0% — Category B (pragma) |
| `web/app.py` | 35 | 35 | 0% — Category B (pragma) |
| `web/analysis/registry.py` | 32 | 32 | 0% — Category C (refactor+test) |
| `simulation/strategies/base.py` | 473 | 22 | 95% — Category A |
| `web/analysis/run_kakita_void_study.py` | 19 | 19 | 0% — Category C |
| `web/analysis/run_kakita_vp_study.py` | 19 | 19 | 0% — Category C |
| `simulation/strategies/ishi_dan_abilities.py` | 130 | 17 | 87% — Category A |
| `web/state.py` | 90 | 14 | 84% — Category A |
| `simulation/templates/generator.py` | 195 | 13 | 93% — Category A |

### Medium-uncovered-count files

Per-school files with 1-10 uncovered lines each: hiruma, hida, mirumoto, ishi, daidoji, isawa, doji_artisan, kakita, kitsuki, kuni, matsu, otaku, shiba, shinjo, shosuro_actor, yogo, ide, akodo, etc. Total ~80 uncovered lines across all schools.

`simulation/strategies/mirumoto_third_dan.py` 8, `simulation/strategies/take_action_event_factory.py` 4, `simulation/strategies/action_factory.py` 3, `simulation/strategies/target_finders.py` 2.

`web/adapters/event_formatter.py` 7, `web/adapters/character_adapter.py` 2, `web/adapters/modifier_breakdown.py` 2.

`web/analysis/aggregator.py` 10, `web/analysis/models.py` 2, `web/analysis/runner.py` 1, `web/analysis/study.py` 1.

## Coverage tool config (existing)

To be verified: `pyproject.toml::[tool.coverage]` should include `simulation/`, `web/` and exclude `tests/`, `env/`, `env_old/`. May need minor tightening.

## Pragma-category classification heuristics

Per Principle VI, allowed pragma justifications:
1. **UI entry point** (Streamlit): `web/views/*.py`, `web/app.py`. Module-level pragma.
2. **Defensive branch with reasoning**: per-line pragma. Comment specifies why unreachable.
3. **Abstract base class method**: `raise NotImplementedError`. Per-line pragma + structural test.
4. **Re-raise block**: `raise` inside `except`. Per-line pragma + comment "re-raise to preserve stack".

Any other pragma usage is a Principle VI violation and is rejected by the audit test.

## Strategy

1. **Category B first** (fastest gain): apply Streamlit pragmas. 762 lines covered in ~5 file edits.
2. **Category C next**: refactor 3 analysis files + add ~70 LOC of tests.
3. **Category A by descending uncovered count**: tackle largest gaps first.
4. **Per-school sweep**: ~80 lines across many files; can be done as a single sweep batch.
5. **Pragma-audit meta-test**: written early so it catches misuse during the audit itself.
