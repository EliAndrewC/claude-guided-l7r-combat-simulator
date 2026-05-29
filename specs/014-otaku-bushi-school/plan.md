# Plan: Otaku Bushi School

**Branch**: `015-otaku-bushi-school`
**Specs**: [spec.md](spec.md), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

## Architecture

The Otaku skeleton has **multiple confirmed rules-fidelity defects** (Q2 + Q3 + Q4) plus the standard identity-bindings + trace-observability concerns. This branch is heavier on fixes than recent audits.

## Phases

### Phase 1: Setup ✓
- [x] Branch created.
- [x] Confirm 27 baseline tests pass.

### Phase 2: Dispatch designers + the 4 review agents in parallel
1. `school-progression-designer` + `school-strategy-designer` for `OTAKU_PRIORITIES` + strategy bindings.
2. `rules-auditor` + `combat-simulator` + `trace-auditor` + `trace-reader` for the existing implementation.

### Phase 3: Apply must-fix findings
1. **Q2 3rd Dan**: limit modification to the next X (= Otaku's attack skill) action dice.
2. **Q3 + Q4 5th Dan**: fix dice math; add strategic choice logic.
3. **Q1 Special Ability**: install interrupt strategy if combat-simulator confirms the wired capability isn't firing.
4. **Trace observability fixes** per audit findings.

### Phase 4: New test files + coverage
1. `tests/test_otaku_school_playability.py` — mirror + win-feasibility.
2. `tests/test_otaku_school_trace.py` — Principle VII assertions.
3. Drive `simulation/schools/otaku_school.py` to 100% coverage (mechanically enforced).

### Phase 5: Final gates + squash-merge + BACKLOG.
