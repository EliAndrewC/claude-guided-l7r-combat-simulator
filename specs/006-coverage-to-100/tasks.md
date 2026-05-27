---
description: "Task list for Coverage to 100% audit"
---

# Tasks: Achieve 100% Code Coverage

**Input**: Design documents from `/specs/006-coverage-to-100/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md, OPEN_QUESTIONS.md

**Tests**: Required per Constitution Principle I (test-first) AND Principle VI (100% coverage).

## Phase 1: Setup

- [ ] T001 Verify branch `007-coverage-to-100` is checked out, working tree clean.
- [ ] T002 Capture baseline coverage report: `env/bin/pytest tests/ --cov=simulation --cov=web --cov-report=term --no-header -q 2>&1 | tail -50`. Save baseline state for comparison.
- [ ] T003 Verify `pyproject.toml::[tool.coverage]` excludes `tests/`, `env/`, `env_old/`. If misconfigured, adjust minimally.

## Phase 2: Foundational — pragma-audit meta-test

- [ ] T004 Write `tests/test_coverage_pragma_audit.py`. Walks `simulation/` and `web/` for `# pragma: no cover` markers; for each, asserts (a) a justification comment exists (same line or line immediately above), (b) the comment matches one of four allowed-category tokens (Streamlit, defensive, abstract method, re-raise). Test fails with file:line + offending comment if violated.

## Phase 3: Category B — Streamlit pragmas (fastest gain, ~762 lines)

- [ ] T005 [P] Apply module-level `# pragma: no cover` + header comment to `web/views/1_Characters.py` (90 lines).
- [ ] T006 [P] Apply same to `web/views/2_Combat_Setup.py` (38 lines).
- [ ] T007 [P] Apply same to `web/views/3_Run_Simulation.py` (147 lines).
- [ ] T008 [P] Apply same to `web/views/4_Analysis.py` (451 lines).
- [ ] T009 [P] Apply same to `web/app.py` (35 lines).
- [ ] T010 Verify Streamlit files now show 100% coverage. Verify the pragma-audit meta-test passes.

## Phase 4: Category C — analysis scripts (refactor + test, ~70 lines)

- [ ] T011 Refactor `web/analysis/run_kakita_void_study.py` to expose `main()`. Top-level code becomes `if __name__ == "__main__": main()`.
- [ ] T012 Refactor `web/analysis/run_kakita_vp_study.py` to expose `main()`.
- [ ] T013 Read `web/analysis/registry.py` to understand its public API.
- [ ] T014 Write `tests/test_analysis_scripts.py`: tests for both `main()` invocations + registry API tests. Use mocks for filesystem / stdout output. Each test asserts no exception + (where applicable) non-empty result.
- [ ] T015 Verify Category C files now at 100% via real tests.

## Phase 5: Category A — web/adapters/* (biggest gap; ~210 uncovered lines)

- [ ] T016 Read `web/adapters/engine_adapter.py` to identify uncovered lines (60% → 100%; 49 lines). Write `tests/test_coverage_audit_adapters.py::TestEngineAdapter` covering each uncovered branch.
- [ ] T017 Read `web/adapters/detailed_formatter.py` (88% → 100%; 100 lines). Extend `tests/test_coverage_audit_adapters.py::TestDetailedFormatter` covering each uncovered branch.
- [ ] T018 Read `web/adapters/combat_observer.py` (84% → 100%; 50 lines). Extend `tests/test_coverage_audit_adapters.py::TestCombatObserver`.
- [ ] T019 Read `web/adapters/event_formatter.py` (87% → 100%; 7 lines). Extend test class.
- [ ] T020 Read `web/adapters/character_adapter.py` and `web/adapters/modifier_breakdown.py` (98% / 97%; 2-4 lines total). Extend test class.
- [ ] T021 Verify all `web/adapters/*.py` files at 100% coverage.

## Phase 6: Category A — simulation/strategies/* (~56 uncovered lines)

- [ ] T022 Read `simulation/strategies/base.py` (95% → 100%; 22 lines). Write `tests/test_coverage_audit_strategies.py::TestStrategiesBase` covering each uncovered branch.
- [ ] T023 Read `simulation/strategies/ishi_dan_abilities.py` (87% → 100%; 17 lines). Extend test class.
- [ ] T024 Read `simulation/strategies/mirumoto_third_dan.py` (91% → 100%; 8 lines). Extend.
- [ ] T025 Read `simulation/strategies/take_action_event_factory.py`, `action_factory.py`, `target_finders.py` (small gaps). Extend.
- [ ] T026 Verify all `simulation/strategies/*.py` at 100%.

## Phase 7: Category A — simulation/schools/* + simulation/* (~120 lines across many files)

- [ ] T027 Audit each `simulation/schools/<school>_school.py` file for uncovered lines. Write tests in `tests/test_coverage_audit_schools.py` covering them. Group by school for clarity (one test class per school with > 3 uncovered lines).
- [ ] T028 Audit `simulation/character.py`, `simulation/events.py`, `simulation/listeners.py`, `simulation/context.py`, `simulation/engine.py`, etc. Write tests in `tests/test_coverage_audit_misc.py`.
- [ ] T029 Audit `simulation/templates/generator.py` (93% → 100%; 13 lines). Extend `tests/test_coverage_audit_misc.py`.
- [ ] T030 Verify all `simulation/` files at 100%.

## Phase 8: Category A — web/state.py + web/analysis/*

- [ ] T031 Read `web/state.py` (84% → 100%; 14 lines). Extend tests appropriately (likely `tests/test_coverage_audit_misc.py` or a new file).
- [ ] T032 Read `web/analysis/aggregator.py` (94% → 100%; 10 lines), `models.py`, `runner.py`, `study.py`. Extend tests.
- [ ] T033 Verify all `web/` files at 100% (excluding Streamlit views which are pragma'd).

## Phase 9: Polish + merge

- [ ] T034 Run full quality-gate suite:
  - `env/bin/ruff check .`
  - `env/bin/mypy`
  - `env/bin/pytest tests/ -v`
  - `env/bin/pytest tests/ --cov=simulation --cov=web --cov-report=term --no-header` — global 100%
- [ ] T035 Run `tests/test_coverage_pragma_audit.py` to verify every pragma has a valid justification.
- [ ] T036 Grep audit: `grep -rn "# pragma: no cover" simulation/ web/` — list every pragma + justification for the user's review.
- [ ] T037 Squash-merge `007-coverage-to-100` into master. User handles push.

## Implementation strategy

**Batching plan**:
- Batch 1 (inline): T001–T010 (setup + Streamlit pragmas — mostly file edits).
- Batch 2 (implementer): T011–T015 (analysis scripts).
- Batch 3 (implementer): T016–T021 (web/adapters/*).
- Batch 4 (implementer): T022–T026 (simulation/strategies/*).
- Batch 5 (implementer): T027–T030 (simulation/schools/* + simulation/*).
- Batch 6 (implementer): T031–T033 (web/state.py + web/analysis/*).
- Batch 7 (inline): T034–T037 (polish + merge).

Total: ~37 tasks. Estimated effort: 5–7 implementer invocations.
