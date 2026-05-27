# Implementation Plan: Combat Trace UX Fixes

**Branch**: `009-trace-ux-fixes` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)

## Summary

Six UX issues surfaced by the `trace-reader` agent's dry-run, grouped into four independent fix areas:
1. **Cross-renderer consistency** (Issue 1) — extract shared `_breakdown_format.py` helper; TextRenderer + BulletedRenderer + detailed_formatter all delegate to it. Eliminates divergence.
2. **Feint damage suppression** (Issues 2, 4, 6) — three related symptoms with one root cause. When the action is a feint and damage dealt is 0, suppress the projection AND the damage event rendering entirely.
3. **Floating-bonus inline integration** (Issue 3) — detect bonus consumption at format time, integrate into attack-line inline arithmetic, suppress the standalone consumption line.
4. **"unsourced" literal removal** (Issue 5) — investigate the +5 source (likely Akodo 4th Dan VP-on-WC), add an `explain_modifier` case, use a non-alarming fallback for genuinely-unsourced cases.

Plus 1 workflow update: add `trace-reader` to the per-batch checkpoint list in CLAUDE.md.

All changes are formatter-only. No engine ordering, no new events.

## Constitution Check

| # | Principle | Status |
|---|-----------|--------|
| I | Test-First | PLANNED |
| II | Rules-Engine Purity | PASS (no engine imports of web/) |
| III | Upstream Rules Are Truth | PASS (no rules-text semantics changes) |
| IV | Injectable Randomness | PASS |
| V | Pluggable Decisions | PASS |
| VI | Total Coverage | PLANNED (100% on new module) |
| VII | Combat Trace Self-Explanation | THIS FEATURE strengthens it |
| VIII | School Identity Drives Defaults | N/A |
| IX | Strategy Defaults Must Be Playable | N/A |

## Phase 0 — Research

See [research.md](research.md). Pre-investigation:
- Locate the BulletedRenderer code paths that still use the old `-XkY` form.
- Locate the floating-bonus-consume rendering in TextRenderer / BulletedRenderer.
- Locate the feint-damage rendering path.
- Determine the source of the `+5 (unsourced)` modifier in the calibration combat.

## Phase 1 — Design

See [data-model.md](data-model.md) and [quickstart.md](quickstart.md).

## Phase 2 — Tasks

`/speckit-tasks` produces tasks.md. Expected ~25 tasks across 6 phases:
- Phase 1: Setup + baseline capture.
- Phase 2: Foundational — `_breakdown_format.py` shared helper.
- Phase 3: Issue 1 — cross-renderer consistency (FR-001 to FR-004).
- Phase 4: Issues 2/4/6 — feint damage suppression (FR-005 to FR-007).
- Phase 5: Issue 3 — floating-bonus inline integration (FR-008 to FR-011).
- Phase 6: Issue 5 — "unsourced" literal (FR-012 to FR-014) + workflow update (FR-015 to FR-016).
- Phase 7: Polish — trace-reader re-validation + final gates + merge.
