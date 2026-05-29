# Plan: Shinjo Bushi School

**Branch**: `017-shinjo-bushi-school`
**Specs**: [spec.md](spec.md), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

## Architecture

Multiple BLOCKING rules-fidelity defects (Q1 extra_rolled list, Q2 double-roll-initiative, Q4 dead identity, Q5 hold-phases math) plus the standard identity-bindings + trace concerns. Q4 is the highest-impact: the entire +2X-per-phase-held identity is structurally dead.

## Phases

### Phase 1: Setup ✓
- [x] Branch created.
- [x] Confirm 13 baseline tests pass.

### Phase 2: Dispatch designers + the 4 review agents in parallel
1. `school-progression-designer` + `school-strategy-designer` for `SHINJO_PRIORITIES` + strategy bindings.
2. `rules-auditor` + `combat-simulator` + `trace-auditor` + `trace-reader` for the existing implementation.

### Phase 3: Apply must-fix findings
1. Q1 — `extra_rolled()` skill list.
2. Q2 — remove double `roll_initiative` call.
3. Q5 — hold-phases math fix (use `min(dice())`).
4. Q4 — wire Special Ability bonus into next skill roll.
5. Q3 — refactor 5th Dan listener to delegate to 3rd Dan helper.
6. Trace observability for hold bonus / 3rd Dan / 4th Dan.

### Phase 4: New test files + coverage
1. `tests/test_shinjo_school_playability.py`
2. `tests/test_shinjo_school_strategy.py` (for any new strategy classes)
3. `tests/test_shinjo_school_trace.py`
4. Drive `simulation/schools/shinjo_school.py` to 100% coverage.

### Phase 5: Final gates + squash-merge + BACKLOG.
