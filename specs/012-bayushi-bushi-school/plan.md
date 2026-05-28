# Plan: Bayushi Bushi School

**Branch**: `013-bayushi-bushi-school`
**Specs**: [spec.md](spec.md), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

## Architecture

The Bayushi skeleton is **the most complete bushi skeleton remaining** — 263 lines with 9 passing tests covering action factory + roll-parameter provider + wound-check provider + feint action. This is primarily an **audit-and-verify** run.

- Engine code: `simulation/schools/bayushi_school.py` (likely minor tightening only), `simulation/templates/strategies.py::BAYUSHI_PRIORITIES`
- UI adapter code: `web/adapters/modifier_breakdown.py` (Bayushi 2nd Dan attribution already present)
- Tests: `tests/test_bayushi_school.py` (extend), `tests/test_bayushi_school_strategy.py` (new), `tests/test_bayushi_school_playability.py` (new), `tests/test_bayushi_school_trace.py` (new)

## Phases (mirrors Matsu workflow, scoped for audit nature)

### Phase 1: Setup ✓
- [x] Branch `013-bayushi-bushi-school` created.
- [x] Confirm 9 baseline tests pass.

### Phase 2: Foundational (audit + identity-driven defaults)
1. Apply `school-progression-designer`'s `BAYUSHI_PRIORITIES` revision (if any).
2. Apply `school-strategy-designer`'s default bindings (likely `WoundCheckStrategy04` for the 1st Dan +1 WC die + a feint-prioritizing attack strategy).
3. Verify the existing 9 tests still pass.

### Phase 3: User Story 1 — Rules-text fidelity audit
1. Dispatch `rules-auditor` on the existing implementation. Address discrepancies.
2. Run targeted tests for each Dan ability if any rules-fidelity gap exists.

### Phase 4: User Story 2 — Mirror non-degeneracy
1. Create `tests/test_bayushi_school_playability.py` with `_CappedCombatEngine(MAX_ROUNDS=18)` (Hida/Matsu lesson).
2. `TestBayushiMirrorMatchPlayability`: 5 seeded mirror matches, strict `final_round < 18` + both-fighting-False.

### Phase 5: User Story 3 — Win-feasibility
1. `TestBayushiWinFeasibility::test_bayushi_winrate_vs_akodo_at_450_xp_ge_35_percent` (20 seeds).
2. Wave-Man test SKIPPED at creation — per Matsu's structural finding.

### Phase 6: User Story 4 — Regression guards
1. `test_bayushi_priorities_includes_all_knacks` — verify all three knacks present.
2. Other regression guards from the `school-progression-designer`'s rationale.

### Phase 7: User Story 5 — Trace assertions
1. `tests/test_bayushi_school_trace.py` — Principle VII assertions for each Bayushi-specific effect.

### Phase 8: Polish + Final agent re-dispatches
1. Coverage to 100%.
2. Re-dispatch all 4 review agents on the final state. Address blockers.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| 5th Dan half-LW WC has no trace attribution | Decide during implementation whether to add a trace marker. Q6. |
| Mirror non-degeneracy fails (Bayushi feint economy is novel) | combat-simulator Scenario C — if it fails, apply offensive-side tuning. |
| Win-feasibility vs Akodo fails | Bayushi has Special Ability VP-on-damage + 3rd Dan Xk1 feint formula; should compete. Verify via combat-simulator if needed. |
| Trace observability gaps | Existing `get_breakdown` and `damage_breakdown` overrides look solid; verify with trace-auditor. |

## Open dependencies

- `school-progression-designer`: review `BAYUSHI_PRIORITIES`.
- `school-strategy-designer`: propose default strategy bindings.
