# Implementation Plan: Achieve 100% Code Coverage

**Branch**: `007-coverage-to-100` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)

## Summary

Push global test coverage from 85% (1732 uncovered lines of 11400) to 100% per Constitution Principle VI v1.3.0. Three approaches per uncovered area:
1. **Hand-write tests** for genuine gaps (~900 LOC expected).
2. **Pragma-skip** Streamlit page modules with documented rationale (~5 markers).
3. **Refactor + test** analysis runnable scripts as library code (~70 LOC).

A new meta-test (`tests/test_coverage_pragma_audit.py`) enforces pragma discipline: every `# pragma: no cover` must have a paired justification comment matching one of four allowed categories.

## Constitution Check

| # | Principle | Status |
|---|-----------|--------|
| I | Test-First | PLANNED |
| II | Rules-Engine Purity | PASS |
| III | Upstream Rules Are Truth | PASS |
| IV | Injectable Randomness | PASS |
| V | Pluggable Decisions | PASS |
| VI | Total Coverage | **THIS FEATURE** |
| VII | Combat Trace Self-Explanation | PASS |
| VIII | School Identity Drives Defaults | N/A |
| IX | Strategy Defaults Must Be Playable | N/A |

## Phase 0 — Research

See [research.md](research.md).

## Phase 1 — Design

See [data-model.md](data-model.md) (minimal — no new engine entities) and [quickstart.md](quickstart.md).

## Phase 2 — Tasks

`/speckit-tasks` produces tasks.md. Expected ~50 tasks across 8 phases:
- Setup
- Foundational (pragma-audit meta-test)
- Category B (Streamlit pragmas, fastest)
- Category C (analysis script refactor + tests)
- Category A.1 (web/adapters/* tests)
- Category A.2 (simulation/strategies/* tests)
- Category A.3 (simulation/schools/* + simulation/* tests)
- Polish (final verification + merge)
