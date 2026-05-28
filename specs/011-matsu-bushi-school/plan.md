# Plan: Matsu Bushi School

**Branch**: `012-matsu-bushi-school`
**Specs**: [spec.md](spec.md), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

## Architecture

Single-project structure (engine + UI):
- Engine code: `simulation/schools/matsu_school.py`, `simulation/templates/strategies.py::MATSU_PRIORITIES`, possibly `simulation/events.py` (if new event types are needed for trace observability)
- UI adapter code: `web/adapters/trace_entries.py`, `web/adapters/text_renderer.py`, `web/adapters/bulleted_renderer.py`
- Tests: `tests/test_matsu_school.py` (extend), `tests/test_matsu_school_strategy.py` (new — for Principle VIII/IX strategy bindings), `tests/test_matsu_school_playability.py` (new — for Principle IX mirror + win-feasibility), `tests/test_matsu_school_trace.py` (new — for Principle VII trace assertions)

## Phases (mirrors Hida/Akodo workflow)

### Phase 1: Setup
1. Branch already created (`012-matsu-bushi-school`).
2. Confirm `MATSU_PRIORITIES` exists and is reviewable.
3. Confirm `simulation/data/templates/matsu/matsu_*.yaml` files exist (verified — 150/200/250/300/350/400/450 all present).

### Phase 2: Foundational (cross-story)
1. Tighten the Special Ability rolled-dice (Q1 strict reading): `MatsuRollProvider.get_initiative_roll` returns 10 dice exactly, not `max(rolled, 10)`.
2. Add trace entries: `MatsuNearMissEntry`, `MatsuLwResetEntry` (or annotate existing entries with Matsu-specific fields).
3. Verify the existing 16 tests still pass after Q1 tightening (update tests if needed).

### Phase 3: User Story 1 (Dan ladder)
1. Verify each Dan ability fires correctly via TDD-first targeted tests.
2. Wire trace attribution for all Matsu-specific effects.
3. Apply the school-progression-designer's `MATSU_PRIORITIES` revision (Q9).

### Phase 4: User Story 2 (mirror non-degeneracy)
1. Add `tests/test_matsu_school_playability.py` with `_CappedCombatEngine(MAX_ROUNDS=18)` from the start (Hida lesson).
2. `TestMatsuMirrorMatchPlayability`: 5 seeded mirror matches.
3. Verify termination via actual defeat (Hida lesson: strict less-than + both-fighting-False check).

### Phase 5: User Story 3 (win-feasibility)
1. Add `TestMatsuWinFeasibility` class. Matsu is offensive so this is expected to be feasible.
2. 20 seeds vs Akodo, 20 seeds vs Bushi baseline (Wave-Man).

### Phase 6: User Story 4 (regression guards)
1. `test_matsu_priorities_includes_all_knacks` — verify the three knacks are referenced.
2. `test_matsu_double_attack_action_near_miss_behavior` — explicit regression guard for the 4th-Dan near-miss carve-out.

### Phase 7: User Story 5 (trace assertions)
1. `tests/test_matsu_school_trace.py` — Principle VII assertions for all new Matsu effects.

### Phase 8: Polish + Final agent re-dispatches
1. Coverage to 100%.
2. `rules-auditor`, `combat-simulator` (Scenarios A/B/B.2/C/D), `trace-auditor`, `trace-reader` final dispatches.

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Q1 tightening breaks existing tests | Update `tests/test_matsu_school.py::TestMatsuRollProvider::test_initiative_always_10_dice` to assert exactly 10 (not at-least-10); count as 1 of the ≤ 5 existing-test updates allowed by NFR-003. |
| Q3 narrow reading vs broad reading | If combat-simulator surfaces voluntary-SW as a missed identity firing, revisit (log in deviations). |
| Mirror non-degeneracy fails | Offensive school → unlikely. If it happens, dispatch `combat-simulator` with full diagnosis. |
| Win-feasibility vs Akodo fails | Matsu's near-miss double attack should counter Akodo's parry effectiveness; 4th-Dan ring raise gives Matsu high Fire. Expected to be feasible but verify with `combat-simulator`. |
| Trace observability gap | Apply trace-auditor + trace-reader sequentially after final implementation batch. |

## Open dependencies

- `school-progression-designer`: produces revised `MATSU_PRIORITIES`. To be dispatched in parallel with strategy-designer.
- `school-strategy-designer`: produces default attack/parry/WC strategy bindings + mirror non-degeneracy assessment. To be dispatched in parallel.
