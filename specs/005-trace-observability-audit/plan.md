# Implementation Plan: Combat Trace Observability Audit

**Branch**: `006-trace-observability-audit` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-trace-observability-audit/spec.md`

## Summary

Cross-cutting Principle VII compliance audit: ensure every multi-source roll in the user-visible combat trace (attack, damage, wound check, parry, iaijutsu, TN) renders its per-component breakdown with source attribution.

**Technical approach**:

1. **Observer-layer annotation**: extend `CombatObserver._annotate_attack` and `_annotate_damage` (and add similar for parry / WC) to attach `_detail_components: list[tuple[str, int, int]]` to each multi-source-roll event. Tuples are `(source_label, +rolled, +kept)`. The sum of components equals the total rolled/kept.
2. **Source-of-truth cooperation**: extend `DefaultRollParameterProvider.get_skill_roll_params` and `get_damage_roll_params` (and per-school overrides as needed) to expose the contributing pieces. Per OPEN_QUESTIONS Q7, two patterns are acceptable: return breakdown alongside totals, OR provide a separate accessor the observer queries.
3. **Formatter rendering**: extend `_format_attack_rolled`, `_format_combined_attack`, `_format_lw_damage`, `_format_modifier_breakdown`, `_format_tn` in `web/adapters/detailed_formatter.py` to render inline parenthetical breakdowns when `_detail_components` exists with >1 nonzero entry.
4. **Modifier-breakdown audit**: audit `explain_modifier` in `web/adapters/modifier_breakdown.py` for missing source cases (at minimum the bare-`+5` case the dry-run surfaced). Replace silent suppression with explicit `(unsourced: +K)` placeholder.
5. **Cross-roll-effect attribution**: when VP-on-attack inflates damage, the damage breakdown gets a labeled `("VP on attack", +N, +N)` entry.
6. **TN raise attribution**: extend `_format_tn` to include `(+X from K raises for {action})` rendering.
7. **Trace-auditor re-validation**: re-run the trace-auditor on representative scenarios for Mirumoto, Ishi, Akodo after each batch to confirm no regressions and that targeted gaps close.
8. **CLAUDE.md workflow update**: add trace-auditor to the per-batch checkpoint list in the "New school implementation workflow" section.

## Technical Context

**Language/Version**: Python 3.12+ (strict mypy on `simulation/` and `web/`).

**Primary Dependencies**: Existing project deps — no new imports anticipated. The fix touches:
- `web/adapters/detailed_formatter.py` (formatter, ~1026 lines)
- `web/adapters/combat_observer.py` (annotator)
- `web/adapters/modifier_breakdown.py` (`explain_modifier`)
- `simulation/mechanics/roll_params.py` (`DefaultRollParameterProvider` — may need breakdown-exposure additions)
- Per-school overrides (Bayushi, Akodo, possibly Mirumoto) — audited and updated as needed
- `tests/` — new trace-assertion tests plus updates to existing tests that lock in old trace strings.
- `CLAUDE.md` — workflow update.

**Storage**: N/A (in-memory annotations on events).

**Testing**: pytest with the established trace-string-assertion pattern from `tests/test_akodo_school.py`. Tests assert against the user-visible trace via `DetailedEventFormatter().format_history(engine.history())`.

**Target Platform**: Linux server (engine + formatter) + Streamlit dashboard (consumes the formatter output). No platform-specific concerns.

**Project Type**: Combat-simulator rules engine with Streamlit dashboard. Single-project Python layout.

**Performance Goals**: N/A. The breakdown computation runs once per event and is dominated by the engine's existing dice-rolling cost.

**Constraints**:
- Constitution coverage floor ≥ 90% globally.
- mypy strict mode.
- Engine purity (no `web/` imports from `simulation/`) — the observer + formatter live in `web/`, so they can import from `simulation/`, but `simulation/` must not import from `web/`.
- The breakdown data is observer-annotated, NOT a new field on engine events. Preserves backward compatibility.

**Scale/Scope**: cross-cutting fix touching ~5 files in `web/adapters/` + 1 file in `simulation/mechanics/` + 3 test files + 1 doc file. Estimated 15–25 new tests; net code delta ~400–600 LOC.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Test-First (Non-Negotiable) | PLANNED | Every FR has a paired test; tasks.md enforces TDD ordering. |
| II | Rules-Engine Purity | PASS | Observer + formatter live in `web/`; no new engine→`web/` imports introduced. |
| III | Upstream Rules Are Truth | PASS | This audit doesn't change rules semantics. The principle being enforced is project-internal (Principle VII), not L7R-rules-text-derived. |
| IV | Injectable Randomness | PASS | No new randomness paths introduced. |
| V | Pluggable Decisions | PASS | Per-school provider extensions (if needed) follow the existing factory pattern. |
| VI | Coverage Floor | PLANNED | Tests in trace-observability sweep keep `web/adapters/detailed_formatter.py` ≥ 90%. |
| VII | Combat Trace Self-Explanation | **THIS FEATURE** | This audit IS the Principle VII compliance work. |
| VIII | School Identity Drives Defaults | N/A | This audit doesn't affect school defaults. |
| IX | Strategy Defaults Must Be Playable | N/A | This audit doesn't affect playability. |

Quality gates 1–8 per the constitution: each verified post-implementation via Post-Change Checklist in CLAUDE.md.

**Re-check after Phase 1 design**: deferred until after data-model.md + contracts/ + quickstart.md generation.

## Project Structure

### Documentation (this feature)

```text
specs/005-trace-observability-audit/
├── spec.md                # Created
├── plan.md                # This file
├── research.md            # Phase 0 output
├── data-model.md          # Phase 1 output
├── quickstart.md          # Phase 1 output
├── contracts/             # Phase 1 output
├── checklists/
│   └── requirements.md    # Created (16/16 PASS)
├── OPEN_QUESTIONS.md      # Created (8 questions pre-resolved)
└── tasks.md               # Phase 2 output
```

### Source Code (repository root)

```text
web/
├── adapters/
│   ├── combat_observer.py        # EDIT: extend _annotate_attack, _annotate_damage; add helpers for parry/WC
│   ├── detailed_formatter.py     # EDIT: extend _format_attack_rolled, _format_combined_attack, _format_lw_damage, _format_modifier_breakdown, _format_tn
│   ├── modifier_breakdown.py     # EDIT: audit explain_modifier; add missing source cases
│   └── ...

simulation/
├── mechanics/
│   └── roll_params.py            # EDIT: extend DefaultRollParameterProvider to expose breakdown
├── schools/
│   ├── bayushi_school.py         # READ + AUDIT (the bare-+5 source likely lives here per dry-run finding)
│   ├── akodo_school.py           # READ + AUDIT (per-school overrides if any)
│   ├── mirumoto_school.py        # READ + AUDIT
│   └── ...

tests/
├── test_trace_observability.py   # NEW: 15–25 trace-assertion tests covering each FR
├── test_akodo_school.py          # MAYBE EDIT: update assertions that lock in old trace strings
├── test_ishi_school.py           # MAYBE EDIT: same
├── test_mirumoto_school.py       # MAYBE EDIT: same

CLAUDE.md                          # EDIT: add trace-auditor to per-batch workflow checkpoint
```

**Structure Decision**: Single-project Python layout preserved.

## Complexity Tracking

No constitution violations. No alternative-rejection table needed.

## Phase 0 — Outline & Research

See [research.md](research.md). Phase 0 resolves:

- The current state of `_annotate_attack` and `_annotate_damage` (what data they already capture).
- The `DefaultRollParameterProvider`'s return-shape options for exposing breakdown.
- The `explain_modifier` catalog: current cases + the missing case for the bare-`+5` Bayushi attack modifier.
- The trace-auditor dry-run findings consolidated into a fix-by-fix table.

## Phase 1 — Design & Contracts

See [data-model.md](data-model.md), [quickstart.md](quickstart.md), and [contracts/](contracts/).

## Phase 2 (planning preview, NOT executed here)

`/speckit-tasks` produces tasks.md. Expected ~40–45 tasks across 7 phases (Setup, Foundational, US1–US5, Polish).
