---

description: "Task list for implementing the Hida Bushi School"
---

# Tasks: Hida Bushi School

**Input**: Design documents from `/specs/010-hida-bushi-school/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓, OPEN_QUESTIONS.md (designer proposals)

**Tests**: REQUIRED (Constitution Principle I, TDD).

**Organization**: Tasks grouped by user story per the spec; each story is independently testable per its acceptance criteria.

## Format: `[ID] [P?] [Story?] Description`

- `[P]`: Can run in parallel (different files, no dependencies on incomplete tasks)
- `[Story]`: Which user story this task belongs to (US1–US5; setup/foundational/polish have no story label)

## Path Conventions

Single-project structure (engine + UI):
- Engine code: `simulation/`
- UI adapter code: `web/adapters/`
- Tests: `tests/`

---

## Phase 1: Setup

**Purpose**: Quick prerequisites verification. (Branch + spec files already exist.)

- [ ] T001 Verify `simulation/templates/strategies.py::HIDA_PRIORITIES` already has the school-progression-designer's revised list applied (done during `/speckit-plan`). Confirm via `grep -c '"lunge"' simulation/templates/strategies.py` returns the same count as on master (no NEW lunge entries; the 5 Hida ones removed). If not, re-apply per OPEN_QUESTIONS.md Q13.

---

## Phase 2: Foundational

**Purpose**: Cross-story prerequisites — must complete before any user-story phase.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] Fix the knack-list bug in `simulation/schools/hida_school.py::school_knacks()` — change return value to `["counterattack", "double attack", "iaijutsu"]`. Update existing test `tests/test_hida_school.py::TestHidaBushiSchoolBasics::test_school_knacks` to assert the new value.
- [ ] T003 [P] Fix the knack-list bug in `simulation/templates/generator.py:35` — change Hida entry to `["counterattack", "double attack", "iaijutsu"]`. Add a regression test in `tests/test_generator.py` (or extend an existing test) asserting the Hida entry value.
- [ ] T004 [P] Update the docstring at `simulation/schools/hida_school.py` lines 11-13 to rephrase "+5" as "free raise (+5)" per Principle VII, and update the comment at line 12 to read "the attacker gets a free raise on their attack roll" (matching rules text).

**Checkpoint**: Knack list is coherent across all 3 files; docstring matches rules text.

---

## Phase 3: User Story 1 — Full Dan ladder fires end-to-end (Priority: P1) 🎯 MVP

**Goal**: Implement the 3 currently-TODO Dan abilities (3rd, 4th SW-for-LW, 5th) so a 5th-Dan Hida operates fully per rules text, with every effect sourced in the user-visible trace per Principle VII.

**Independent Test**: Run a deterministic seeded combat with a 5th-Dan Hida vs 5th-Dan Akodo. Assert the trace contains lines matching each Dan effect with proper attribution (FR-029, FR-030). Assert counterattack still costs 1 die when interrupting and attacker gets +5 free raise.

### Tests for User Story 1 (TDD — write FIRST, ensure they FAIL before implementation)

**3rd Dan reroll**:
- [ ] T005 [P] [US1] In `tests/test_hida_school.py`, add `TestHida3rdDanReroll` class with: `test_reroll_counterattack_uses_2x_attack_skill` (verifies N = 2 × attack_skill on a counterattack roll), `test_reroll_other_attacks_uses_x_attack_skill` (N = attack_skill on attack/double-attack/iaijutsu), `test_reroll_not_on_wound_check_parry_feint` (no reroll on ineligible skills), `test_reroll_greedy_picks_lowest_below_5_5`, `test_reroll_no_chain` (one reroll per die per roll), `test_reroll_when_crippled_halves_N_round_up`, `test_reroll_when_crippled_10s_still_reroll` (override impaired no-explode rule), `test_reroll_trace_attribution` (Principle VII: dice values before → after, source label).
- [ ] T006 [P] [US1] In `tests/test_hida_school.py`, add `TestHida3rdDanProviderInstallation` class with: `test_apply_rank_three_installs_provider`, `test_provider_only_for_attack_skills`.

**4th Dan SW-for-LW trade**:
- [ ] T007 [P] [US1] In `tests/test_hida_school.py`, add `TestHida4thDanSWForLW` class with: `test_trade_fires_when_lw_high_and_sw_pool_available` (LW > threshold AND SW + 2 ≤ max_SW), `test_trade_short_circuits_when_lw_zero`, `test_trade_short_circuits_when_sw_plus_2_would_exceed_max` (would kill), `test_trade_blocked_in_iaijutsu_phase` (when Hida is the duelist), `test_trade_allowed_when_bystander_to_someone_elses_duel`, `test_trade_emits_HidaSWForLWTradeEvent`, `test_trade_resets_lw_to_zero`, `test_trade_adds_two_sw`, `test_trade_trace_observability` (Principle VII).
- [ ] T008 [P] [US1] In `tests/test_hida_school.py`, add `TestHidaWoundCheckStrategy` class with: `test_strategy_extends_WoundCheckStrategy`, `test_strategy_calls_super_when_trade_not_applicable`, `test_strategy_takes_trade_when_pre_conditions_met`.

**5th Dan counterattack-excess WC bonus**:
- [ ] T009 [P] [US1] In `tests/test_hida_school.py`, add `TestHida5thDanWCBonus` class with: `test_counterattack_excess_stored_on_attack_action`, `test_wc_roll_adds_counterattack_excess_when_present`, `test_wc_bonus_sourced_in_trace` (Principle VII: "+X (Hida 5th Dan: counterattack excess +X)"), `test_wc_bonus_zero_when_no_counterattack_excess`, `test_wc_bonus_applies_only_to_hida_own_wc_on_counterattacked_damage`.

**5th Dan post-damage counterattack timing**:
- [ ] T010 [P] [US1] In `tests/test_hida_school.py`, add `TestHida5thDanPostDamageTiming` class with: `test_5th_dan_strategy_defers_pre_damage`, `test_5th_dan_strategy_decides_post_damage`, `test_damage_resolves_before_counterattack` (LW added + WC fires before counterattack roll), `test_attacker_killed_by_post_damage_counterattack_damage_still_stands`, `test_5th_dan_post_damage_uses_1_die_interrupt_cost`, `test_5th_dan_attacker_still_gets_5_free_raise`.

**Special Ability re-verification (FR-001, FR-002)**:
- [ ] T011 [P] [US1] In `tests/test_hida_school.py`, extend `TestHidaSpecialAbility` with: `test_plus_5_free_raise_sourced_in_trace` (Principle VII: trace line shows "Hida special ability: free raise (+5) for 1-die interrupt counterattack").

### Implementation for User Story 1 (after tests above FAIL)

**3rd Dan reroll provider**:
- [ ] T012 [P] [US1] Create `HidaRollProvider(DefaultRollProvider)` class in `simulation/schools/hida_school.py`. Override the roll resolution to apply the 3rd Dan reroll when the skill is in `{"counterattack", "attack", "double attack", "iaijutsu"}`. Use the Merchant `_find_dice_to_reroll` algorithm as the dice-selection starting point. Compute N = 2X for counterattack, X otherwise, where X = `character.skill("attack")`. When `character.crippled()`, halve N (round up); also pass override flag enabling 10-reroll despite crippled.
- [ ] T013 [US1] Wire the `HidaRollProvider` install into `HidaBushiSchool.apply_rank_three_ability`.

**4th Dan SW-for-LW trade**:
- [ ] T014 [P] [US1] Add `context.in_iaijutsu_phase() -> bool` accessor to the combat context. Set on `DuelInitiativeRolledEvent`, clear on `DuelEndedEvent`. (Implementer chooses: extend existing context object or add to DuelState.) Test via duel-engine integration test.
- [ ] T015 [P] [US1] Create `HidaSWForLWTradeEvent` in `simulation/events.py` (or `simulation/schools/hida_school.py`). Distinct from wound-check event; trace output: `"<name> | 🛡️ Hida 4th Dan: take 2 SW to reset LW from N → 0 (alternative wound check)"`.
- [ ] T016 [P] [US1] Create `HidaWoundCheckStrategy(WoundCheckStrategy)` in `simulation/schools/hida_school.py`. Recommend the trade only when: (i) `character.lw() > 0`, (ii) `character.sw() + 2 <= character.max_sw()`, (iii) NOT `context.in_iaijutsu_phase()` for this character, (iv) expected SW from rolling ≥ 2 (using base strategy's heuristic). Else fall through to base WC strategy.
- [ ] T017 [US1] Wire `HidaWoundCheckStrategy` install into `HidaBushiSchool.apply_rank_four_ability` (alongside existing `apply_school_ring_raise_and_discount` call).

**5th Dan post-damage interrupt slot + WC bonus**:
- [ ] T018 [P] [US1] Add `_counterattack_excess_margin` attribute support on `AttackAction` (or attack-action subclasses) in `simulation/actions.py`. Pattern: `getattr(action, '_counterattack_excess_margin', 0)`. Read by WC resolution; written by 5th-Dan counterattack-resolution flow.
- [ ] T019 [US1] Modify the WC roll resolution flow (likely in `simulation/events.py` or `simulation/character.py::take_lw`) to add `_counterattack_excess_margin` (if nonzero) to the WC roll, with trace attribution.
- [ ] T020 [P] [US1] Add `PostDamageInterruptCheckEvent` to `simulation/events.py`. Fires after `LightWoundsDamageEvent` resolves but before the attack flow concludes. No-op unless a listener (HidaCounterattackInterruptStrategy at 5th Dan) handles it.
- [ ] T021 [P] [US1] Create `HidaCounterattackInterruptStrategy(CounterattackInterruptStrategy)` in `simulation/schools/hida_school.py`. Adds: (a) mirror-recursion gate (do NOT counterattack an incoming counterattack); (b) SW-saturation gate (do NOT counterattack when `sw_remaining ≤ 1` from a +5-free-raise attack); (c) post-damage decision point (fires on `PostDamageInterruptCheckEvent`) for 5th Dan; (d) on successful counterattack at 5th Dan, store `excess = roll - TN` on the originating attack action's `_counterattack_excess_margin`.
- [ ] T022 [US1] Wire `HidaCounterattackInterruptStrategy` install into `HidaBushiSchool.apply_special_ability` (replacing the vanilla `CounterattackInterruptStrategy`). The 5th-Dan-specific behavior (post-damage timing + excess storage) is Dan-gated inside the strategy class.

**Trace observability for new Hida effects (Principle VII)**:
- [ ] T023 [US1] Update `web/adapters/detailed_formatter.py` and/or `web/adapters/trace_entries.py` to emit attributed trace lines for: (a) Hida special ability +5 free raise to attacker, (b) Hida 3rd Dan reroll (showing dice before → after, source label), (c) Hida 4th Dan SW-for-LW trade event, (d) Hida 5th Dan counterattack-excess bonus on WC rolls, (e) Hida 5th Dan post-damage counterattack timing (event ordering visible).

**Checkpoint**: User Story 1 fully functional. Run all US1 tests; assert all pass.

---

## Phase 4: User Story 2 — Mirror non-degeneracy holds (Priority: P1)

**Goal**: Default strategy bindings prevent mirror-match deadlock per Principle IX. Two 5th-Dan Hidas terminate combat within 200 phases AND each takes at least one attack action.

**Independent Test**: combat-simulator Scenario C — 5 seeded mirror matches all terminate within safety bound AND each character takes ≥ 1 attack action.

### Tests for User Story 2

- [ ] T024 [P] [US2] In `tests/test_hida_school_strategy.py` (new file), add `TestHidaAttackStrategy` class with: `test_kill_shot_branch_uses_double_attack_when_target_near_death`, `test_pressure_branch_attacks_when_full_health_with_spare_actions`, `test_reserve_branch_holds_action_when_mid_fight`, `test_strategy_avoids_lunge_skill` (lunge not a Hida knack — must not be in strategy paths).
- [ ] T025 [P] [US2] In `tests/test_hida_school_strategy.py`, add `TestHidaCounterattackInterruptStrategy` class with: `test_recursion_gate_declines_counterattacking_a_counterattack`, `test_sw_saturation_gate_declines_at_low_sw_with_inflated_attacker_tn`.

### Implementation for User Story 2

- [ ] T026 [P] [US2] Create `HidaAttackStrategy(BaseAttackStrategy)` in `simulation/schools/hida_school.py` with three branches per school-strategy-designer's proposal (kill-shot using `double attack` not lunge; pressure when full health + spare actions; reserve otherwise).
- [ ] T027 [US2] Wire `HidaAttackStrategy` and `WoundCheckStrategy04` installs into `HidaBushiSchool.apply_special_ability` per the strategy-designer's proposal documented in OPEN_QUESTIONS.md Q12.
- [ ] T028 [US2] Add `combat-simulator` Scenario C scripted test in `tests/test_hida_school_playability.py` (new file). 5 mirror-match seeds, assert termination + identity engine firing.

**Checkpoint**: User Story 2 fully functional. Mirror match terminates with identity engine firing.

---

## Phase 5: User Story 3 — Win-feasibility ≥ 35% vs Akodo + Bushi baseline (Priority: P1)

**Goal**: Default 5th-Dan Hida at 450 XP wins ≥ 35% of matches vs default 5th-Dan Akodo at 450 XP, and vs universal Bushi baseline at 450 XP, across 20 seeds.

**Independent Test**: combat-simulator Scenario B — 20 seeds Hida vs Akodo, 20 seeds Hida vs Bushi-baseline.

### Tests for User Story 3

- [ ] T029 [P] [US3] In `tests/test_hida_school_playability.py`, add `TestHidaWinFeasibility` class with: `test_hida_winrate_vs_akodo_at_450_xp_ge_35_percent` (20 seeds), `test_hida_winrate_vs_bushi_baseline_at_450_xp_ge_35_percent` (20 seeds), `test_hida_winrate_in_action_disadvantage_scenario` (Scenario B.2).

### Implementation for User Story 3

- [ ] T030 [US3] Tune `HidaAttackStrategy` pressure-branch and `HidaCounterattackInterruptStrategy` gates (from US2) to achieve the win-feasibility thresholds. May require iteration with `combat-simulator` results. Document tuning choices in OPEN_QUESTIONS.md.

**Checkpoint**: User Story 3 fully functional. Win-feasibility ≥ 35% on both matchups.

---

## Phase 6: User Story 4 — Knack list coherence regression guard (Priority: P1)

**Goal**: Defend against future regressions of the "lunge" → "double attack" fix.

**Independent Test**: grep + factory-roundtrip assertion.

### Tests for User Story 4

- [ ] T031 [P] [US4] In `tests/test_hida_school.py`, add a `test_no_lunge_in_hida_priorities` test that imports `HIDA_PRIORITIES` from `simulation/templates/strategies.py` and asserts no entry references `"lunge"`.
- [ ] T032 [P] [US4] In `tests/test_generator.py` (or wherever the template tests live), add `test_hida_knack_template_is_correct` that asserts the Hida entry in the generator template equals `["counterattack", "double attack", "iaijutsu"]`.
- [ ] T033 [P] [US4] In `tests/test_hida_school.py::TestHidaBushiSchoolBasics::test_school_knacks`, change the asserted value to `["counterattack", "double attack", "iaijutsu"]`. (This is one of the ≤ 5 existing-test updates allowed by Constitution.)

**Checkpoint**: Knack list coherence verified across all 3 sites.

---

## Phase 7: User Story 5 — trace-reader + trace-auditor approve (Priority: P2)

**Goal**: After implementation, the new trace-reader and trace-auditor agents report zero blockers on a Hida calibration combat.

**Independent Test**: Dispatch the two agents on a 5th-Dan Hida vs 5th-Dan Akodo seeded combat trace.

### Tests for User Story 5

- [ ] T034 [P] [US5] Verify trace lines for all new Hida effects have explicit source attribution (no aggregate values without source) — programmatic assertion via `tests/test_hida_school_trace.py` (new file) scanning the rendered trace for sentinel substrings: `"Hida special ability:"`, `"Hida 3rd Dan: reroll"`, `"Hida 4th Dan: take 2 SW"`, `"Hida 5th Dan: counterattack excess"`.

### Implementation for User Story 5

- [ ] T035 [US5] After all prior tasks complete, dispatch `trace-auditor` agent on a Hida calibration combat. Apply any Principle VII fixes flagged.
- [ ] T036 [US5] After T035, dispatch `trace-reader` agent on the same combat. Apply any UX intuitiveness fixes flagged.

**Checkpoint**: All 5 user stories fully functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T037 [P] Add coverage for any pragma-skipped lines in the new Hida code per Constitution Principle VI. Each pragma must have a one-line justification comment. Verify `env/bin/pytest tests/ --cov --cov-report=term` reports 100% on `simulation/schools/hida_school.py`.
- [ ] T038 [P] Run `env/bin/ruff check .` — zero errors.
- [ ] T039 [P] Run `env/bin/mypy` strict — zero errors. Strict mode applies to `simulation/` and `web/`.
- [ ] T040 Run `env/bin/pytest tests/ -v` — all tests pass (count should increase by 50-80 per spec).
- [ ] T041 Run `env/bin/pytest tests/ --cov --cov-report=term` — 100% coverage.
- [ ] T042 Restart Streamlit (`env/bin/streamlit run web/app.py --server.headless true`); spot-check a Hida combat in the dashboard renders without errors.
- [ ] T043 Run `quickstart.md` recipe end-to-end and verify each section passes.
- [ ] T044 Dispatch `rules-auditor` on the final implementation diff. Address any rules-fidelity discrepancies.
- [ ] T045 Dispatch `combat-simulator` with all 5 scenarios (A/B/B.2/C/D) per CLAUDE.md workflow.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: T001 already complete via /speckit-plan.
- **Phase 2 (Foundational)**: T002–T004 can run in parallel; must complete before user-story phases.
- **Phase 3 (US1)**: After Phase 2 complete. T005–T011 are tests that must FAIL first; then T012–T023 implement. Within: providers (T012) before T013 wiring; events (T014, T015) before WC strategy (T016) before T017 wiring; T018 + T020 before T021; T022 wires final.
- **Phase 4 (US2)**: After Phase 3 (depends on strategy classes). T024–T025 tests first; T026–T028 implementation.
- **Phase 5 (US3)**: After Phase 4. T029 test, T030 tuning.
- **Phase 6 (US4)**: After Phase 2 (depends on knack fix). Tests + the one existing-test update.
- **Phase 7 (US5)**: After all prior phases.
- **Phase 8 (Polish)**: After all user stories complete.

### Parallel Opportunities

- T002 / T003 / T004 (3 separate files) — fully parallel.
- T005–T011 (all in `tests/test_hida_school.py` but different classes) — parallel as separate test class additions.
- T012, T014, T015, T018, T020, T021 (different files / different classes) — parallel where flagged [P].
- T024 / T025, T026 — parallel.
- T031 / T032 / T033 — parallel.
- T037 / T038 / T039 — parallel.

---

## Implementation Strategy

### Batch suggestions for `school-implementer`

Per CLAUDE.md, batches of 3-6 tasks. Suggested batching:

**Batch A** (T001-T004 + T005-T006 + T011): Knack-list fixes + docstring + 3rd Dan reroll tests + special ability re-verification. Test scope: ~12 new tests.

After Batch A, dispatch `rules-auditor` + `combat-simulator` (Scenario A on knack-list verification) + `trace-auditor` (verify +5 sourcing) per CLAUDE.md.

**Batch B** (T012-T013 + T023 partial): 3rd Dan reroll implementation + trace observability for it. Tests from Batch A pass.

After Batch B, dispatch all 4 review agents per CLAUDE.md.

**Batch C** (T007-T008 + T014-T017 + T023 partial): 4th Dan SW-for-LW trade tests + implementation + trace observability.

After Batch C, dispatch all 4 review agents.

**Batch D** (T009-T010 + T018-T022 + T023 final): 5th Dan implementation (counterattack-excess + post-damage timing) + trace observability.

After Batch D, dispatch all 4 review agents.

**Batch E** (T024-T028): User Story 2 (mirror non-degeneracy strategy work).

After Batch E, dispatch all 4 review agents with emphasis on `combat-simulator` Scenario C.

**Batch F** (T029-T030): User Story 3 (win-feasibility tuning). Iterative — may require multiple combat-simulator dispatches.

**Batch G** (T031-T033): User Story 4 (regression guards). Quick, isolated.

**Batch H** (T034-T036): User Story 5 (final trace agent verification).

**Batch I** (T037-T045): Constitution gates + final agent re-dispatches.

### MVP scope

The MVP is **Phases 1–3 + Phase 6** (US1 fully functional + knack regression guard). US2, US3 are necessary for Principle IX gate but not strictly part of MVP behavior. US4 ensures the fix sticks. US5 is the closing validation.

---

## Notes

- [P] tasks = different files or different classes within a file, no dependencies on incomplete tasks.
- [Story] label maps task to specific user story for traceability.
- Each user story is independently completable; commit at checkpoint of each.
- TDD: tests written first, ensure they FAIL before implementation.
- After every substantial batch (3-6 tasks): dispatch rules-auditor + combat-simulator + trace-auditor + trace-reader per CLAUDE.md "Per-batch checkpoint".
- ≤ 5 existing-test updates allowed; T033 is one. Flag if more are needed.
- Coverage must reach 100% on new Hida code; pragmas must be justified.
