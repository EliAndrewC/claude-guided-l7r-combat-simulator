# Plan: Kakita Duelist School

**Branch**: `014-kakita-duelist-school`
**Specs**: [spec.md](spec.md), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

## Architecture

The Kakita skeleton is **the largest remaining** — 610 lines, 16 tests, 24 classes/functions, with its own action subclasses, listeners, providers, and 4 unused strategy variants. This is primarily an **audit-and-verify** run with targeted fixes for any rules-fidelity gaps the audit surfaces.

- Engine code: `simulation/schools/kakita_school.py` (likely minor tightening only)
- Templates: `simulation/templates/strategies.py::KAKITA_PRIORITIES`
- UI adapter code: `web/adapters/modifier_breakdown.py` (verify Kakita-specific clauses), trace entry types if 5th-Dan needs new attribution fields
- Tests: extend `tests/test_kakita_school.py`; new `tests/test_kakita_school_playability.py`, `tests/test_kakita_school_trace.py`

## Phases (mirrors Bayushi audit workflow)

### Phase 1: Setup ✓
- [x] Branch created.
- [x] Confirm 16 baseline tests pass.

### Phase 2: Apply designer proposals (if non-disruptive)
1. Dispatch `school-progression-designer` and `school-strategy-designer` in parallel.
2. Apply revisions IF they don't shift the seed=1234 calibration combat (which uses Akodo + Bayushi, NOT Kakita — so Kakita changes should be safe).
3. Verify the existing 16 tests still pass.

### Phase 3: Audit via the 4 review agents
1. Dispatch `rules-auditor` + `trace-auditor` + `trace-reader` + `combat-simulator` in parallel.
2. Address BLOCKING findings.
3. Document MINOR findings and deferrals.

### Phase 4: Coverage + new test files
1. Add `tests/test_kakita_school_playability.py` — mirror non-degeneracy + win-feasibility vs Akodo.
2. Add `tests/test_kakita_school_trace.py` — Principle VII assertions for each Kakita effect.
3. Drive `simulation/schools/kakita_school.py` to 100% coverage (mechanically enforced by `fail_under = 100`).

### Phase 5: Final gates + squash-merge + BACKLOG update.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Name discrepancy fix cascades | DEFER per Q1 — change docstring only, full rename in separate branch. |
| 5th Dan "extra free raise" gap (Q2) is real | Fix by adding +5 modifier (or `FreeRaise`) in `KakitaNewPhaseListener` when target has no iaijutsu. |
| 4 unused variants block 100% coverage | Add 4 trivial instantiation tests OR pragma per allowed category. |
| Trace observability gaps in 3rd Dan tempo / 4th Dan damage / 5th Dan contested | Add fields to relevant trace entries + render in both renderers. |
| Mirror non-degeneracy fails because phase-0 contested damages both Kakitas immediately | Should TERMINATE faster, not deadlock — verify via combat-simulator. |

## Open dependencies

- `school-progression-designer`: review `KAKITA_PRIORITIES`.
- `school-strategy-designer`: review the 4 unused strategy variants — keep, document, or remove.
