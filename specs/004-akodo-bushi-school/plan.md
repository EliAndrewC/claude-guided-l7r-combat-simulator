# Implementation Plan: Akodo Bushi School

**Branch**: `005-akodo-bushi-school` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-akodo-bushi-school/spec.md`

## Summary

Complete the Akodo Bushi School implementation in `simulation/schools/akodo_school.py`, bringing it through the validated speckit workflow (the same pattern used for Mirumoto Bushi in spec 001 and Isawa Ishi in spec 002). Akodo is one of two Principle IX playability baselines, so correctness here is load-bearing for every future school's win-feasibility check.

**Technical approach**:

1. Audit the existing 187-line skeleton against the verbatim rules text in `rules/04-schools.md`. Three concrete defects identified: (a) 4th Dan strategy off-by-one in `range(1, max_spend)`; (b) 5th Dan listener replicates default LW handling (needs verification that the slot REPLACES rather than stacks); (c) 5th Dan strategy unconditionally spends max VP (TODO-flagged in skeleton).
2. Fix the defects with TDD-first regression tests.
3. Add observability tests verifying every Akodo ability emits a user-facing trace line with both source attribution and numeric breakdown (Principle VII).
4. Dispatch `school-progression-designer` for ring/skill priorities in `simulation/templates/strategies.py` and `school-strategy-designer` for default-strategy bindings in `akodo_school.py` (in parallel — they're independent design audits).
5. Run `combat-simulator` Scenarios A (clause exercise), B (win-feasibility vs Hida + other implemented schools), B.2 (action-disadvantage), C (mirror non-degeneracy with identity-engine-firing check), D (behavioral round-robin) for Principle IX validation.
6. `rules-auditor` reviews each batched diff against the upstream rules clause.
7. Squash-merge to master; update BACKLOG.md.

## Technical Context

**Language/Version**: Python 3.12+ (strict mypy on `simulation/` and `web/`).

**Primary Dependencies**: Existing project deps — no new imports anticipated. The fix touches `simulation/schools/akodo_school.py`, `simulation/mechanics/floating_bonuses.py` (verify only, no expected refactor), `simulation/templates/strategies.py` (progression entry), and tests in `tests/test_akodo_school.py`.

**Storage**: N/A (in-memory engine state).

**Testing**: pytest with `CalvinistRollProvider` for deterministic dice; full suite must pass at 2919+ tests (baseline as of commit `89dc0bb`).

**Target Platform**: Linux server (engine) + Streamlit web UI (combat trace formatter). Engine code is platform-agnostic.

**Project Type**: Combat-simulator rules engine with Streamlit dashboard. Single-project Python layout per repo root.

**Performance Goals**: N/A for single-combat simulation. Combat-simulator runs are sub-second per matchup; round-robin scenarios complete in under a minute.

**Constraints**: Constitution coverage floor ≥ 90%. mypy strict mode. Engine purity (no `web/` imports from `simulation/`).

**Scale/Scope**: One school's worth of code (~200–300 LOC after fixes); ~20–30 new test cases in `tests/test_akodo_school.py`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution at `.specify/memory/constitution.md` v1.2.2 (2026-05-27) defines 9 principles + 8 quality gates. Walking each:

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Test-First (Non-Negotiable) | PLANNED | Every FR has a paired test; tasks.md will enforce TDD ordering. |
| II | Rules-Engine Purity | PASS | No engine→`web/` imports introduced; trace formatter remains in `web/`. |
| III | Upstream Rules Are Truth | PASS | Verbatim rules text cited in spec; Shugenja exclusion irrelevant here (Akodo is bushi). |
| IV | Injectable Randomness | PASS | Existing roll providers reused; no new direct `random.*` calls. |
| V | Pluggable Decisions | PASS | Akodo's strategies (`AkodoWoundCheckRolledStrategy`, `AkodoFifthDanStrategy`) are interchangeable per the existing factory pattern. |
| VI | Coverage Floor | PLANNED | New tests in `tests/test_akodo_school.py` will keep `simulation/schools/akodo_school.py` ≥ 95%. |
| VII | Combat Trace Self-Explanation | PLANNED | FRs 006/008/009/014/019/024/031/032 enforce trace attribution; tests assert user-visible strings. |
| VIII | School Identity Drives Defaults | PLANNED | `school-progression-designer` and `school-strategy-designer` agents will propose identity-aligned defaults. |
| IX | Strategy Defaults Must Be Playable | PLANNED | `combat-simulator` runs Scenarios A/B/B.2/C/D after implementation. |

Quality gates 1–8 from `Quality Gates` section in the constitution: each will be verified post-implementation via the Post-Change Checklist in CLAUDE.md. No expected violations.

**Re-check after Phase 1 design**: deferred until after data-model.md + contracts/ + quickstart.md generation.

## Project Structure

### Documentation (this feature)

```text
specs/004-akodo-bushi-school/
├── spec.md                # Already created (this run)
├── plan.md                # This file
├── research.md            # Phase 0 output (generated below)
├── data-model.md          # Phase 1 output
├── quickstart.md          # Phase 1 output
├── contracts/             # Phase 1 output (engine event contracts)
├── checklists/
│   └── requirements.md    # Already created
├── OPEN_QUESTIONS.md      # Autonomous-run deferred decisions
└── tasks.md               # Phase 2 output (generated by /speckit-tasks)
```

### Source Code (repository root)

This project uses a single-project Python layout (Option 1 from the template):

```text
simulation/
├── schools/
│   ├── akodo_school.py         # PRIMARY EDIT TARGET (~187 lines, will grow to ~250-300)
│   ├── base.py                 # Helpers used (e.g., _set_school_listener, apply_school_ring_raise_and_discount)
│   └── ...                     # Other school files (read-only reference)
├── mechanics/
│   └── floating_bonuses.py     # READ + VERIFY (AnyAttackFloatingBonus semantics)
├── strategies/
│   └── ...                     # Read-only reference for default strategy patterns
├── templates/
│   └── strategies.py           # EDIT: add AKODO_PRIORITIES entry per progression-designer proposal
├── listeners/                  # Read-only reference for listener patterns
└── events.py                   # Read-only (existing events: GainTemporaryVoidPointsEvent, etc.)

tests/
├── test_akodo_school.py        # PRIMARY TEST FILE (NEW or extend; ~25-30 new test methods)
└── ...                         # Other tests remain untouched

web/
├── formatters/                 # READ + VERIFY trace attribution for Akodo abilities (Principle VII)
└── ...

BACKLOG.md                       # EDIT post-merge: move Akodo entry to "Validated"
```

**Structure Decision**: Single-project Python layout is preserved. No new top-level directories. The edit footprint is intentionally narrow — engine module + test module + one strategies.py entry. This is consistent with the prior speckit runs (specs 001 and 002 followed the same shape).

## Complexity Tracking

No constitution violations identified. No alternative-rejection table needed.

## Phase 0 — Outline & Research

See [research.md](research.md). Phase 0 resolves:

- The exact verbatim rules-text for Akodo Bushi (offline-cached from upstream).
- The engine entities and event types used by Akodo (cross-referenced with `simulation/events.py` and `simulation/mechanics/floating_bonuses.py`).
- The skeleton audit findings (defect inventory) with severity rankings.
- The pattern-precedent from specs 001 and 002 (what worked, what to reuse).
- Existing `simulation/templates/strategies.py` priority schemas for reference.

## Phase 1 — Design & Contracts

See [data-model.md](data-model.md), [quickstart.md](quickstart.md), and [contracts/](contracts/).

- `data-model.md`: lifecycle of Akodo-specific state (floating bonuses, TVP counters, VP spend hooks).
- `contracts/`: the engine-event contracts Akodo's listeners depend on (`AttackSucceededEvent`, `WoundCheckSucceededEvent`, `LightWoundsDamageEvent`, etc. — fields and invariants only, not refactoring them).
- `quickstart.md`: how to verify the school works end-to-end (build a character, run a deterministic combat, inspect the trace).

## Phase 2 (planning preview, NOT executed here)

`/speckit-tasks` will produce a `tasks.md` with the following expected shape (informing the implementer):

- **Setup phase** (T001–T002): branch verified, skeleton baseline tests captured.
- **Foundational phase** (T003–T005): existing tests still pass; floating-bonus subsystem verified.
- **User Story 1 phase** (T006–T010): TVP economy + 1st/2nd Dan extra-rolled/free-raise (P1).
- **User Story 2 phase** (T011–T015): 3rd Dan floating bonus (P1).
- **User Story 3 phase** (T016–T020): 4th Dan VP-for-WC + off-by-one fix (P1).
- **User Story 4 phase** (T021–T025): 5th Dan counter-damage (P1).
- **User Story 5 phase** (T026–T030): Principle IX playability validation (P1).
- **Polish phase** (T031–T035): trace observability sweep + progression-designer + strategy-designer integration.

Final count expected: ~30–35 tasks total. `/speckit-tasks` will assign exact IDs and dependencies.
