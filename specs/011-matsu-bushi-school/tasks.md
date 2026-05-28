---

description: "Task list for implementing the Matsu Bushi School"
---

# Tasks: Matsu Bushi School

**Input**: Design documents from `/specs/011-matsu-bushi-school/`

**Prerequisites**: plan.md ✓, spec.md ✓, OPEN_QUESTIONS.md ✓ (with both designer proposals already applied during /speckit-plan)

**Tests**: REQUIRED (Constitution Principle I, TDD).

**Note**: Skeleton at `simulation/schools/matsu_school.py` (167 lines, 16 passing tests) is significantly more developed than Hida's was. Much of the work is *audit + tighten* rather than *build from scratch*. Total scope estimated 30-50 new tests (vs Hida's 80+).

## Phase 1: Setup ✓

- [x] T001 Branch `012-matsu-bushi-school` created.
- [x] T002 Confirm `MATSU_PRIORITIES` revision applied per school-progression-designer (Q9).
- [x] T003 Confirm strategy-designer bindings (`DefaultInterruptStrategy` + `WoundCheckStrategy04`) applied per Q10.
- [x] T004 Regenerate `simulation/data/templates/matsu/matsu_*.yaml` with new priorities.

## Phase 2: Foundational

- [ ] T005 **Q1 tightening**: change `MatsuRollProvider.get_initiative_roll` from `max(rolled, 10)` to strict `rolled=10`. Update `tests/test_matsu_school.py::TestMatsuRollProvider::test_initiative_always_10_dice` to assert exactly 10 not at-least-10. (1 existing-test update.)
- [ ] T006 [P] Verify all 16 existing tests still pass after T005.

**Checkpoint**: Q1 strictness applied; all existing tests green.

## Phase 3: User Story 1 — Dan ladder fires + trace observability (Priority: P1) 🎯 MVP

### 3rd Dan trace observability

- [ ] T007 Add explicit trace attribution: when `MatsuSpendVoidPointsListener` grants the `WoundCheckFloatingBonus`, ensure the bonus emits a `GainFloatingBonusEvent` (or equivalent) with source label `"Matsu 3rd Dan"`. Verify in trace.
- [ ] T008 [P] Add `TestMatsu3rdDanTraceObservability` to `tests/test_matsu_school.py`: assert the gain event surfaces in trace with "Matsu 3rd Dan" attribution AND the consumption later appears with the same label.

### 4th Dan near-miss trace observability

- [ ] T009 Annotate `MatsuDoubleAttackAction` with a `_is_near_miss` flag (or equivalent) set when `skill_roll < tn AND skill_roll >= tn - 20`. The `AttackEntry` rendering must surface "Matsu 4th Dan: near-miss (X below TN)" in both `TextRenderer` and `BulletedRenderer`.
- [ ] T010 [P] Add tests: `test_near_miss_attribution_in_trace`, `test_clear_hit_does_not_show_near_miss_attribution`.

### 5th Dan LW-floor trace observability

- [ ] T011 Add explicit trace attribution: `MatsuWoundCheckFailedListener` emits a trace marker (new entry `MatsuLwFloorEntry` or annotation on existing SW event) indicating "Matsu 5th Dan: defender LW set to 15 (instead of 0)".
- [ ] T012 [P] Add `TestMatsu5thDanTraceObservability`: assert the LW-floor line surfaces with "Matsu 5th Dan" attribution.

### Skeleton-bug audit

- [ ] T013 Verify `MatsuSpendVoidPointsListener` doesn't double-spend (strategy-designer says it doesn't — slot-replace semantics — but add a regression test).

**Checkpoint**: All Dan-ladder effects fire with full trace attribution per Principle VII.

## Phase 4: User Story 2 — Mirror non-degeneracy (Priority: P1)

- [ ] T014 [P] Create `tests/test_matsu_school_playability.py` with `_CappedCombatEngine(MAX_ROUNDS=18)` from the start (Hida lesson).
- [ ] T015 Add `TestMatsuMirrorMatchPlayability` class:
  - `test_mirror_match_terminates_within_safety_bound` — 5 seeds; assert strict `final_round < 18` AND at least one Matsu not fighting (no cap-saturation per Hida lessons).
  - `test_mirror_match_identity_engine_fires` — at least 1 attack action per Matsu, at least 1 double attack per match across the seeds.

**Checkpoint**: Mirror match terminates cleanly.

## Phase 5: User Story 3 — Win-feasibility (Priority: P1)

- [ ] T016 Add `TestMatsuWinFeasibility` class:
  - `test_matsu_winrate_vs_akodo_at_450_xp_ge_35_percent` (20 seeds)
  - `test_matsu_winrate_vs_bushi_baseline_at_450_xp_ge_35_percent` (20 seeds, vs `wave_man` per Hida-fix lesson)
- [ ] T017 If T016 fails the 35% floor: tune via combat-simulator dispatch (parallel to T030 in Hida). Document tuning in OPEN_QUESTIONS deviations log.

**Checkpoint**: Win-rates meet FR-029 floor OR documented deferral per Hida-precedent.

## Phase 6: User Story 4 — Regression guards (Priority: P1)

- [ ] T018 [P] `test_matsu_priorities_includes_all_knacks` — verify `MATSU_PRIORITIES` references `double attack`, `iaijutsu`, AND `lunge`.
- [ ] T019 [P] `test_matsu_priorities_excludes_late_parry` — assert parry is NOT bought at ranks 4 or 5 (per the strategy-designer's revision).

**Checkpoint**: Regression guards in place.

## Phase 7: User Story 5 — Trace assertions (Priority: P2)

- [ ] T020 Create `tests/test_matsu_school_trace.py` with programmatic Principle VII assertions:
  - 3rd Dan floating bonus gain + consumption rendered with source label
  - 4th Dan near-miss attribution in attack entry
  - 5th Dan LW-floor attribution
  - Both `TextRenderer` and `BulletedRenderer` coverage

**Checkpoint**: All Matsu-specific effects surface with explicit source attribution in both renderers.

## Phase 8: Polish + Final agent re-dispatches

- [ ] T021 Run `env/bin/ruff check .` — zero errors.
- [ ] T022 Run `env/bin/mypy` — zero errors.
- [ ] T023 Run `env/bin/pytest tests/ -v` — all pass.
- [ ] T024 Coverage = 100% on `simulation/schools/matsu_school.py` (pragmas justified per Principle VI v1.3.0).
- [ ] T025 Streamlit smoke test (`env/bin/streamlit run web/app.py --server.headless true`) — serves HTTP 200.
- [ ] T026 Final `rules-auditor` dispatch on the full diff.
- [ ] T027 Final `combat-simulator` dispatch (Scenarios A/B/B.2/C/D).
- [ ] T028 Final `trace-auditor` dispatch.
- [ ] T029 Final `trace-reader` dispatch.
- [ ] T030 Address any blockers from T026-T029. Defer non-blockers to OPEN_QUESTIONS deviations log.

**Checkpoint**: 8-point Constitution checklist passes.

## Phase 9: Squash-merge

- [ ] T031 Squash-merge `012-matsu-bushi-school` → master.
- [ ] T032 Update BACKLOG.md: move Matsu from "Skeleton present" to "Validated via speckit workflow" with the merge commit reference.

## Implementation Strategy

### Batch suggestions for `school-implementer`

**Batch A (foundational + trace observability)**: T005, T007, T009, T011 + their tests T008, T010, T012, T013. Trace observability is most of the work since the skeleton mechanics are already in place; we're adding source attribution + tightening Q1.

**Batch B (playability)**: T014, T015, T016. Mirror + win-feasibility. Expected to be smoother than Hida since Matsu is offensive.

**Batch C (regression guards + trace tests)**: T018, T019, T020.

**Batch D (polish + agent dispatches)**: T021-T030.

After each batch, dispatch `rules-auditor` + `combat-simulator` + `trace-auditor` + `trace-reader` per CLAUDE.md.

### MVP scope

Phases 1-3 + 6 (US1 fully functional + regression guards). Phases 4, 5 are needed for Principle IX gate.

## Notes

- [P] tasks = different files or classes within a file.
- Each user story is independently testable; commit at each checkpoint.
- ≤ 5 existing-test updates allowed; T005 is one.
- OOM-trigger containment pattern from Hida is part of T014's standard scaffold.
