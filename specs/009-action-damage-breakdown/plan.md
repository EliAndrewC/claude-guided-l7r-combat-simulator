# Implementation Plan: Action-Level Damage Breakdown

**Branch**: `010-action-damage-breakdown` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)

## Summary

Move the damage-breakdown attribution decision from the provider layer to the action layer. The formatter currently asks `subject.get_damage_roll_params(...)` and `provider.get_breakdown(kind="damage")` regardless of whether the action overrides `damage_roll_params()`. This causes projection-vs-actual mismatches and lying breakdowns for Bayushi feints.

Fix: introduce `AttackAction.damage_breakdown()` method. Default delegates to provider (transparent migration). `FeintAction` returns `[]` (zero damage). `BayushiFeintAction` returns per-source contributions matching its `damage_roll_params()` override. Formatter call sites consult `action.damage_breakdown()`.

## Constitution Check

| # | Principle | Status |
|---|-----------|--------|
| I | Test-First | PLANNED |
| II | Rules-Engine Purity | PASS (action's `damage_breakdown()` returns plain tuples; no web imports) |
| III | Upstream Rules Are Truth | PASS (engine semantics unchanged) |
| IV | Injectable Randomness | PASS |
| V | Pluggable Decisions | PASS |
| VI | Total Coverage | PLANNED |
| VII | Combat Trace Self-Explanation | FIX (this resolves the projection-vs-actual issue) |
| VIII | School Identity Drives Defaults | N/A |
| IX | Strategy Defaults Must Be Playable | N/A |

## Estimated scope

- `simulation/actions.py`: ~30 LOC (AttackAction default + FeintAction override).
- `simulation/schools/bayushi_school.py`: ~15 LOC (BayushiFeintAction override).
- `web/adapters/detailed_formatter.py`: ~30 LOC (3 call-site migrations).
- Tests: ~80 LOC (10-15 tests covering the new path + the Bayushi-specific fix + the default-delegation regression guard).

Total: ~150-200 LOC.

## Phase 2 — Tasks

`/speckit-tasks` produces tasks.md. Expected ~12 tasks across 4 phases:
- Phase 1: Setup + baseline.
- Phase 2: Action-side `damage_breakdown` accessor + overrides.
- Phase 3: Formatter call-site migrations.
- Phase 4: Polish (trace-reader re-validation + merge).
