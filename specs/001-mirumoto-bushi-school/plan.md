# Implementation Plan: Mirumoto Bushi School

**Branch**: `001-mirumoto-bushi-school` | **Date**: 2026-05-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-mirumoto-bushi-school/spec.md`

## Summary

Complete the existing skeleton implementation of the Mirumoto Bushi school at `simulation/schools/mirumoto_school.py` so it conforms to the upstream rules text (`rules/04-schools.md`) and the spec's 17 functional requirements. The skeleton already wires up the school class, factory registration, the Special Ability TVP listener, a Third Dan `NewRoundEvent` listener that creates the per-round pool, the Fourth Dan Void-ring-raise-and-discount, and a Fifth Dan `RollParameterProvider` that adds the +10 bonus on combat rolls. Three classes of work remain:

1. **Correctness fixes** to existing skeleton code (and its test file) where it diverges from the rules text — most notably `extra_rolled()` lists the wrong skills and `MirumotoParryAction` modifies the *wrong side* of combat (Mirumoto-as-defender instead of Mirumoto-as-attacker).
2. **Net-new mechanics** for the Third Dan pool's two spend modes (phase-lowering, post-roll +2) — pool creation works but no spending logic exists.
3. **Net-new mechanic** for the Fourth Dan auto-serious-wound clause on double attacks — currently missing entirely.

TDD-first: every fix and addition lands a failing test before the code change.

## Technical Context

**Language/Version**: Python 3.12+ (per `CLAUDE.md` and existing pyproject.toml)

**Primary Dependencies**: Engine has no runtime dependencies outside the standard library for the rules engine; `streamlit` for the UI (not touched by this feature).

**Storage**: N/A — pure in-memory engine logic.

**Testing**: `pytest` (`env/bin/pytest tests/ -v`), with deterministic dice via `CalvinistRollProvider` (existing) for reproducibility (Constitution Principle IV).

**Target Platform**: Linux server (Fly.io deployment) for the Streamlit dashboard; engine itself is platform-agnostic.

**Project Type**: Library + Streamlit web UI. This feature touches only the library (`simulation/`), not the UI (`web/`).

**Performance Goals**: Not relevant for this feature — combat simulation runs are short (single-digit ms per round). No new perf-sensitive code is introduced.

**Constraints**: Coverage must remain >90% (Constitution Principle VI). `ruff check` and `mypy` strict mode must pass on `simulation/` (Constitution Quality Gates).

**Scale/Scope**: One school, five dan ranks + one special ability, ~17 FRs. Implementation surface is `simulation/schools/mirumoto_school.py` plus possibly one or two new modules under `simulation/strategies/` for the Third Dan spend strategies.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance | Notes |
|---|---|---|
| I. Test-First | ✅ Required by plan | Plan mandates failing test → code for every change. The existing test file `tests/test_mirumoto_school.py` has tests that currently *pass* against a buggy skeleton — those tests will be updated to assert the correct behavior (making them fail), then the skeleton will be fixed (making them pass). |
| II. Rules-Engine Purity | ✅ Compliant | All code lives in `simulation/`; no imports from `web/`; no UI, env, or disk access introduced. |
| III. Upstream Rules Are Truth | ✅ Compliant | FR-017 mandates that every FR cites its rules clause. Spec already does this. Skeleton's known bugs (`extra_rolled` list) will be fixed *to the rules text*, not preserved for back-compat. |
| IV. Injectable Randomness | ✅ Compliant | All dice flow through the existing `RollProvider` and `RollParameterProvider`. The Fifth Dan provider is already implemented via subclass of `DefaultRollParameterProvider`. No new `random.*` call sites are introduced. |
| V. Pluggable Decisions | ✅ Compliant | The Third Dan pool's two spend modes will be implemented as separate **strategy** classes (one for phase-lowering, one for post-roll +2), interchangeable with strategies for other schools. Pool state is a character attribute (matching the engine's existing pattern for per-round resources), accessed through a typed interface so playtesters can substitute alternate strategies without touching the pool itself. |
| VI. Coverage Floor | ✅ Required by plan | New code paths (3rd Dan spends, 4th Dan auto-SW) come with tests under `tests/test_mirumoto_school.py`. Project coverage will be re-measured post-implementation; ≥ 90% is a merge blocker. |

**Result**: PASS. No violations. No entries needed in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-mirumoto-bushi-school/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (this command) — resolves the 3 deferred clarify items
├── data-model.md        # Phase 1 output (this command)
├── quickstart.md        # Phase 1 output (this command)
├── contracts/           # Phase 1 output (this command)
│   └── interfaces.md    #   Python protocols touched by this feature
├── spec.md              # Already exists
├── checklists/
│   └── requirements.md  # Already exists
└── tasks.md             # Phase 2 output (/speckit-tasks command — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
simulation/
├── schools/
│   ├── base.py                          # (existing) BaseSchool ABC — not modified
│   ├── factory.py                       # (existing) Mirumoto already registered — not modified
│   └── mirumoto_school.py               # (existing skeleton) — modified extensively
├── strategies/
│   ├── base.py                          # (existing) — not modified
│   ├── action_factory.py                # (existing) ActionFactory ABC — Mirumoto's subclass extended
│   └── mirumoto_third_dan.py            # (NEW) two strategy classes for the 3rd Dan spend modes
├── mechanics/
│   ├── roll_params.py                   # (existing) — not modified (Mirumoto subclass already in mirumoto_school.py)
│   └── roll_provider.py                 # (existing) — not modified
├── actions.py                           # (existing) AttackAction/DoubleAttackAction/ParryAction — not modified directly; subclassed inside mirumoto_school.py if needed for 4th Dan auto-SW
├── character.py                         # (existing) _tvp / _vp / discount machinery — not modified; relied upon
├── events.py                            # (existing) — not modified
├── engine.py                            # (existing) combat loop — not modified
└── listeners.py                         # (existing) Listener ABC — Mirumoto's listeners are inside mirumoto_school.py

tests/
└── test_mirumoto_school.py              # (existing skeleton) — corrected and extended
```

**Structure Decision**: This feature lives almost entirely in `simulation/schools/mirumoto_school.py` (extending the existing skeleton) plus one new module `simulation/strategies/mirumoto_third_dan.py` for the Third Dan spend strategies (kept separate so the strategy classes can be swapped by playtesters without editing the school class). No new top-level packages. All test work concentrates in `tests/test_mirumoto_school.py`.

## Phase 0 — Research

The clarify pass deferred three items to plan-time, to be resolved against the actual codebase rather than by user judgment. Each is resolved in [research.md](./research.md):

1. **First Dan — what string identifies "wound check" in the engine?** → `"wound check"` (literal). `RollParameterProvider.get_wound_check_roll_params` calls `character.extra_rolled("wound check")`. Confirms FR-005 expects `extra_rolled()` to include the literal string `"wound check"`.
2. **Third Dan — phase tie-breaker convention.** → Existing engine convention via `EngineContext.reevaluate_initiative()` sorts characters by cached initiative priority. No new tie-breaker introduced; phase-lowering inherits the same convention.
3. **Implementation directory layout.** → `simulation/schools/mirumoto_school.py` (already exists as a partial skeleton). Mirumoto school is already registered in `simulation/schools/factory.py` line 75-76.

Additionally, research.md documents:

4. **Skeleton state audit** — what the existing `mirumoto_school.py` already does correctly, what it does incorrectly, and what is missing entirely. This is the load-bearing artifact for `/speckit-tasks`.

## Phase 1 — Design & Contracts

[data-model.md](./data-model.md) maps the spec's six Key Entities to concrete Python classes and their existing-or-new status, including the state machine for the Third Dan pool.

[contracts/interfaces.md](./contracts/interfaces.md) documents the Python protocols this feature consumes (existing) and adds (new strategy interfaces for the Third Dan spends).

[quickstart.md](./quickstart.md) is the developer-facing recipe for verifying the feature works: how to instantiate a Mirumoto Bushi at each dan, what tests to run, and how to read a combat trace for the school's effects.

## Complexity Tracking

No constitution violations to justify. This section is empty.
