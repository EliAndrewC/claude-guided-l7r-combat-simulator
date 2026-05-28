# Implementation Plan: Hida Bushi School

**Branch**: `011-hida-bushi-school` | **Date**: 2026-05-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-hida-bushi-school/spec.md`

## Summary

Implement the Hida Bushi School fully. Skeleton at `simulation/schools/hida_school.py` has the Special Ability + 1st Dan + 2nd Dan + half of 4th Dan wired correctly, plus a `HidaTakeCounterattackActionEvent` mechanism for the +5 free raise to attackers. Three Dan abilities remain TODO: 3rd Dan reroll (2X dice on counterattack / X on other attacks), 4th Dan alternative wound check (2 SW for LW reset), and 5th Dan (counterattack-excess WC bonus + post-damage counterattack timing). The knack list is wrong in three places ("lunge" instead of rules-text "double attack") and `HIDA_PRIORITIES` needs identity-driven revision. Strategy bindings need school-strategy-designer review for Principle IX mirror non-degeneracy.

Technical approach: extend the roll-extension pipeline with a "reroll N selected dice" capability for 3rd Dan; subclass `WoundCheckStrategy` for 4th Dan SW-for-LW decision branch with a new `HidaSWForLWTradeEvent`; refactor the counterattack interrupt sequencing to support a post-damage-roll slot for 5th Dan; thread "counterattack excess" margin from the counterattack resolution into the WC roll bonus storage on the originating attack action.

## Technical Context

**Language/Version**: Python 3.12+

**Primary Dependencies**: existing `simulation/` engine. No new third-party dependencies.

**Storage**: N/A (engine state in-memory; no persistence).

**Testing**: pytest, pytest-cov (100% coverage required).

**Target Platform**: Linux (engine is platform-agnostic; the Streamlit UI is the only platform-specific layer and is not directly touched by this feature).

**Project Type**: library/engine (combat simulator).

**Performance Goals**: per-combat runtime under 100ms for the calibration combats; the implementation must not introduce per-roll O(N²) algorithms in the hot path.

**Constraints**: 100% test coverage, strict mypy, ruff lint zero errors, no `simulation/ → web/` imports (Principle II), every Dan ability must be visible in the user-facing trace with source attribution (Principle VII).

**Scale/Scope**: ~50-80 new tests, 1 new file extension to the roll pipeline (or modification of an existing one), 1 new event type or extension, 3 new strategy subclasses, knack-list correction across 3 files, HIDA_PRIORITIES revision (≈40 entries).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Test-First | PASS | Tests will be written first per TDD; speckit-implement enforces this. |
| II. Rules-Engine Purity | PASS | All changes are engine-side; no web/ imports added. Trace observability requires updating `web/adapters/` formatters as well — those are UI-side and listed separately in the engine touchpoints. |
| III. Upstream Rules Are Truth | PASS | Verbatim Hida rules text quoted in spec. Knack-list correction is a Principle III fidelity fix. No shugenja or out-of-scope mechanics. |
| IV. Injectable Randomness | PASS | The 3rd Dan reroll capability MUST go through the roll provider — no direct `random.*` calls in the new code. |
| V. Pluggable Decisions | PASS | New `HidaWoundCheckStrategy` and `HidaCounterattackInterruptStrategy` are pluggable per the existing Strategy infrastructure. |
| VI. Total Coverage | PASS | 100% required on all new code; pragma comments where genuinely needed (per pragma-audit meta-test). |
| VII. Combat Trace Self-Explanation | PASS | FR-029, FR-030 enforce trace observability; tests assert against user-visible trace strings. |
| VIII. School Identity Drives Defaults | PASS | school-progression-designer + school-strategy-designer dispatch in Phase 1 will produce identity-driven proposals. |
| IX. Strategy Defaults Must Be Playable | PASS | SC-005, SC-006, SC-007 enforce playability; combat-simulator verifies at runtime. school-strategy-designer verifies at design time. |

| Quality Gate | Coverage in spec |
|--------------|------------------|
| ruff PASS | enforced in CI |
| mypy strict PASS | enforced in CI |
| pytest PASS | SC-012 |
| 100% coverage | FR-037 + SC-003 |
| Streamlit smoke | manual after UI-touching changes |
| Trace observability | FR-029, FR-030, SC-010 |
| Identity defaults | FR-024, FR-025, FR-028, SC-009 |
| Playability | SC-005, SC-006, SC-007 |

**Gate verdict**: PASS. No constitutional violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/010-hida-bushi-school/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (if applicable)
├── checklists/
│   └── requirements.md  # Spec quality checklist
├── OPEN_QUESTIONS.md    # Pre-resolutions + deviations log
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
simulation/
├── schools/
│   └── hida_school.py                  # Fix knack list; complete 3rd/4th/5th Dan
├── strategies/
│   └── base.py                         # Existing WoundCheckStrategy + CounterattackInterruptStrategy — subclass for Hida
├── templates/
│   ├── generator.py                    # Line 35 knack list fix
│   └── strategies.py                   # HIDA_PRIORITIES revision (per school-progression-designer)
├── events.py                           # Possibly extend with HidaSWForLWTradeEvent + post-damage interrupt slot
├── actions.py                          # Possibly extend with _counterattack_excess_margin storage on attack actions
└── mechanics/                          # Possibly extend roll-params pipeline with "reroll N selected dice"

web/
└── adapters/
    └── detailed_formatter.py           # Trace observability for new Hida effects (per Principle VII)

tests/
├── test_hida_school.py                 # Extend with new ability tests
└── test_hida_school_*.py               # Possibly focused-suite files for 3rd/4th/5th Dan
```

**Structure Decision**: Single-project structure. No new top-level directories. Change set is additive over the existing skeleton + a few crosscutting fixes (knack list, HIDA_PRIORITIES).

## Complexity Tracking

(No constitutional violations to justify.)
