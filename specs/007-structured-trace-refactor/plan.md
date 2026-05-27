# Implementation Plan: Structured Trace Refactor

**Branch**: `008-structured-trace-refactor` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)

## Summary

Introduce a `TraceEntry` intermediate representation between observer-annotated engine events and rendered output. Refactor the existing `DetailedEventFormatter` so it emits structured `TraceEntry` objects first, then renders them via a `TextRenderer` (byte-identical to current output). Add a `BulletedRenderer` that consumes the same entries to produce Markdown for the Streamlit UI's bulleted layout.

Architectural shift: **structure early, format late**. The structured form (`_detail_components`, `_detail_modifier_breakdown`, `_detail_dice`) already exists on events but gets flattened by the formatter; this refactor exposes it as a first-class data model.

## Technical Context

**Language/Version**: Python 3.12+, mypy strict on `simulation/` and `web/`.

**Primary Dependencies**: Existing project deps. New module uses `dataclasses` from stdlib.

**Storage**: N/A (in-memory entry objects).

**Testing**: pytest. New test files for the new modules; existing trace-assertion tests are the regression guard for the TextRenderer.

**Constraints**:
- Constitution Principle II (engine purity): `simulation/` must not import from `web/`.
- Constitution Principle VI v1.3.0: 100% coverage on new modules.
- Byte-identical text output is the critical invariant (FR-009/FR-011).

**Scale/Scope**: ~12-20 entry types + 2 component types in `trace_entries.py`. ~25 `_format_*` → `_entry_*` + `_render_*` method conversions. Estimated 1500-2400 LOC delta.

## Constitution Check

| # | Principle | Status |
|---|-----------|--------|
| I | Test-First | PLANNED |
| II | Rules-Engine Purity | PASS (verified by FR-031) |
| III | Upstream Rules Are Truth | PASS (no rules changes) |
| IV | Injectable Randomness | PASS |
| V | Pluggable Decisions | PASS |
| VI | Total Coverage | PLANNED (100% on new modules) |
| VII | Combat Trace Self-Explanation | PASS (text output byte-identical; trace-auditor re-validates) |
| VIII | School Identity Drives Defaults | N/A |
| IX | Strategy Defaults Must Be Playable | N/A |

## Phase 0 — Research

See [research.md](research.md). Phase 0 enumerates:
- Every `_format_*` method in the existing formatter (the exhaustive list of trace-event categories).
- The exact fields each method reads from its event (the "round-trip" surface).
- The composition rules between events (e.g., VP-spend + TakeAttack → one combined line).

## Phase 1 — Design

See [data-model.md](data-model.md), [contracts/trace_entries.md](contracts/trace_entries.md), [quickstart.md](quickstart.md).

- `data-model.md`: the full set of `TraceEntry` subclasses + their fields.
- `contracts/trace_entries.md`: the byte-identical-text contract per entry type.
- `quickstart.md`: how to verify the refactor.

## Phase 2 (planning preview)

`/speckit-tasks` produces tasks.md. Expected ~50 tasks across 9 phases:
- Phase 1: Setup + baseline.
- Phase 2: Define `TraceEntry` dataclasses (FR-001 to FR-005).
- Phase 3: Build `entries()` method on `DetailedEventFormatter` (FR-006 to FR-008).
- Phase 4: Write `TextRenderer` from `_format_*` migration (FR-009 to FR-011).
- Phase 5: Make `format_history()` a thin wrapper (FR-010).
- Phase 6: Write `BulletedRenderer` (FR-012 to FR-022).
- Phase 7: Wire Streamlit page (FR-023 to FR-024).
- Phase 8: Coverage push to 100% on new modules + extensibility demo test (FR-025 to FR-030, SC-004).
- Phase 9: trace-auditor re-validation + final gates + merge.
