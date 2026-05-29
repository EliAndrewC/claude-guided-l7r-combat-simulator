# Plan: Shiba Bushi School

**Branch**: `016-shiba-bushi-school`
**Specs**: [spec.md](spec.md), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

## Architecture

The Shiba skeleton has rules-fidelity for the listener-level mechanics (parry damage, TN margin) but the standard identity-strategy gap (Q1) + a rolled-dice normalization issue (Q3) + the usual trace observability concerns.

## Phases

### Phase 1: Setup ✓
- [x] Branch created.
- [x] Confirm 6 baseline tests pass.

### Phase 2: Dispatch designers + the 4 review agents in parallel
1. `school-progression-designer` + `school-strategy-designer` for `SHIBA_PRIORITIES` + strategy bindings.
2. `rules-auditor` + `combat-simulator` + `trace-auditor` + `trace-reader` for the existing implementation.

### Phase 3: Apply must-fix findings
1. **Q1 interrupt-parry**: install `ShibaInterruptParryStrategy` + `add_interrupt_skill("parry")`.
2. **Q2 lowest-die semantics** in the strategy.
3. **Q3 3rd Dan normalization** via `normalize_roll_params`.
4. **Trace observability** per audit findings.

### Phase 4: New test files + coverage
1. `tests/test_shiba_school_playability.py` — mirror + win-feasibility.
2. `tests/test_shiba_school_strategy.py` — interrupt-parry unit tests.
3. `tests/test_shiba_school_trace.py` — Principle VII assertions.
4. Drive `simulation/schools/shiba_school.py` to 100% coverage (mechanically enforced).

### Phase 5: Final gates + squash-merge + BACKLOG.
