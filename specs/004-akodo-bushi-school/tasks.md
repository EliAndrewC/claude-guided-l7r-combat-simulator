---
description: "Task list for Akodo Bushi School implementation"
---

# Tasks: Akodo Bushi School

**Input**: Design documents from `/specs/004-akodo-bushi-school/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/engine-events.md, quickstart.md, OPEN_QUESTIONS.md

**Tests**: Required per Constitution Principle I (Test-First, Non-Negotiable). Every implementation task has a paired test task that MUST be written first.

**Organization**: Tasks are grouped by user story. The 5 stories from spec.md map to T-phases below.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US5 maps to the user stories in spec.md
- Paths are absolute or repo-relative

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Baseline verification before any school edits.

- [X] T001 Verify branch `005-akodo-bushi-school` is checked out and the working tree is clean (no uncommitted edits outside this spec dir). Run `git status`; if dirty work outside `specs/004-akodo-bushi-school/` exists, stop and reconcile.
- [X] T002 Capture the baseline test count by running `env/bin/pytest tests/ --collect-only -q 2>&1 | tail -2` and record it in the implementation log. Expected: 2919+ tests (per commit `89dc0bb`). This is the regression-floor: post-implementation count MUST be greater than or equal to baseline.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Verify shared engine entities the Akodo refactor depends on. These tasks unblock all user stories.

- [X] T003 [P] Verify `AnyAttackFloatingBonus` semantics in `simulation/mechanics/floating_bonuses.py`: read the file and confirm (a) single-use consumption per `AttackRolledEvent`, (b) combat-boundary clearing via `Character.reset()`, (c) FIFO ordering or whatever ordering the engine implements. Document findings in a comment block at the top of `tests/test_akodo_school.py` (or extend the existing test file if present).
- [X] T004 [P] Inventory the trace formatter in `web/formatters/` for existing Akodo-event attribution. Grep for `Akodo` and for `GainTemporaryVoidPointsEvent`. Document gaps where source attribution is missing — these become trace-observability tasks in Phase 7.
- [X] T005 Confirm `_set_school_strategy` helper exists in `simulation/schools/base.py` and lives in the same registration pattern as `_set_school_listener` (per the post-negation-refactor lifecycle). If not present, raise blocking issue — the AkodoAttackStrategy install path depends on it.

---

## Phase 3: User Story 1 — Special Ability TVP economy (Priority: P1) 🎯 MVP

**Story goal**: A 1st-Dan Akodo's feint success and failure correctly emit GainTemporaryVoidPointsEvent with values 4 and 1 respectively, and the trace attributes both to "Akodo Special Ability".

**Independent test**: per spec.md User Story 1 — deterministic combat with successful and failed feints, assert TVP gain and trace attribution.

### Tests for User Story 1 (write FIRST per TDD)

- [X] T006 [P] [US1] Add failing test `test_akodo_special_ability_grants_4_tvp_on_successful_feint` to `tests/test_akodo_school.py`. Build a 1st-Dan Akodo with feint=4, set up deterministic rolls where feint succeeds, assert TVP increments by 4 AND combat trace contains a line with both "Akodo Special Ability" attribution AND "+4 TVP".
- [X] T007 [P] [US1] Add failing test `test_akodo_special_ability_grants_1_tvp_on_failed_feint`. Symmetric to T006 but failed feint, +1 TVP.
- [X] T008 [P] [US1] Add failing test `test_akodo_1st_dan_extra_die_on_attack_double_attack_wound_check`. Verify `school.extra_rolled() == ["attack", "double attack", "wound check"]` AND trace contains "+1k0 (Akodo 1st Dan)" or equivalent attribution at each relevant roll.
- [X] T009 [P] [US1] Add failing test `test_akodo_2nd_dan_free_raise_on_wound_check`. Verify `school.free_raise_skills() == ["wound check"]` AND the WC roll trace shows "FR (Akodo 2nd Dan)" or equivalent.

### Implementation for User Story 1

- [X] T010 [US1] Verify the existing `AkodoAttackSucceededListener` and `AkodoAttackFailedListener` in `simulation/schools/akodo_school.py` continue to emit the correct events; no implementation change expected — these tasks are pass-through. Tests T006 & T007 lock in the contract.
- [X] T011 [US1] If T006 or T007 reveals the listener is mis-wired (e.g., subject filter wrong), fix in `simulation/schools/akodo_school.py` AkodoAttackSucceededListener / AkodoAttackFailedListener.
- [X] T012 [US1] Add trace formatter attribution for `GainTemporaryVoidPointsEvent` sourced from Akodo Special Ability if T004 found it missing. Edit `web/formatters/*` to add the Akodo-specific case.

**Checkpoint**: At this point, MVP works — a 1st-Dan Akodo can play out a combat with TVP economy firing correctly, fully observable in the trace.

---

## Phase 4: User Story 2 — 3rd Dan floating bonus from WC margins (Priority: P1)

**Story goal**: A 3rd-Dan Akodo gains and consumes floating attack bonuses correctly, with both events visible in the trace.

### Tests for User Story 2

- [X] T013 [P] [US2] Add failing test `test_akodo_3rd_dan_grants_floating_bonus_on_wc_success`. Build a 3rd-Dan Akodo with attack=5; force WC roll=50 against damage=30; assert one `AnyAttackFloatingBonus(20)` was added AND trace shows "Akodo 3rd Dan: gained floating bonus +20" or equivalent with numeric breakdown.
- [X] T014 [P] [US2] Add failing test `test_akodo_3rd_dan_floating_bonus_consumed_on_next_attack`. Continue T013 setup; verify the next AttackRolledEvent consumes the bonus (only one consumption, not multiple) AND the trace shows "+20 (Akodo 3rd Dan floating bonus consumed)" or equivalent.
- [X] T015 [P] [US2] Add failing test `test_akodo_3rd_dan_multi_bonuses_independent_fifo`. Set up 3 successful WCs in a single combat; verify 3 independent bonuses created; verify next 3 attacks consume them in FIFO order (or align with engine if different — per OPEN_QUESTIONS.md Q6 the test follows the engine).
- [X] T016 [P] [US2] Add failing test `test_akodo_3rd_dan_floating_bonus_does_not_persist_across_combats`. Build a 3rd-Dan Akodo; gain a bonus in combat 1; call `character.reset()`; assert bonus collection is empty before combat 2 starts.
- [X] T017 [P] [US2] Add failing test `test_akodo_3rd_dan_zero_margin_yields_zero_bonus`. If WC roll exactly equals damage, the floor-division yields 0 — verify no bonus is added OR a zero-value bonus that's effectively inert.

### Implementation for User Story 2

- [X] T018 [US2] Verify the existing `AkodoWoundCheckSucceededListener` in `simulation/schools/akodo_school.py` computes the right formula and gains the bonus correctly. Tests T013-T017 will surface any defects.
- [X] T019 [US2] If T014 reveals that bonus is being double-consumed or not consumed at AttackRolledEvent, fix the consumption path (likely in `simulation/mechanics/floating_bonuses.py` — verify-only, NOT a refactor — OR in the `attack_rolled` strategy slot). Per OPEN_QUESTIONS.md Q4, consumption fires at `AttackRolledEvent`.
- [X] T020 [US2] If T016 reveals bonuses persist across combats, add a clear in `Character.reset()` or wherever combat-boundary lifecycle hooks live.
- [X] T021 [US2] Add trace formatter attribution for floating-bonus acquisition AND consumption if T004 found these missing.

**Checkpoint**: 3rd-Dan Akodo's mid-game floating-bonus economy works end-to-end.

---

## Phase 5: User Story 3 — 4th Dan VP-for-WC-raise + off-by-one fix (Priority: P1)

**Story goal**: A 4th-Dan Akodo can spend VP after rolling a WC; the strategy reaches `max_spend` (off-by-one fix) and selects the minimum-sufficient spend.

### Tests for User Story 3

- [X] T022 [P] [US3] Add failing test `test_akodo_4th_dan_strategy_reaches_max_spend` (off-by-one regression). Build a 4th-Dan Akodo with `available_vp_for_wc=5`, `max_vp_per_roll=5`; force a damage event where spending all 5 VP is needed to reach tolerable SW; assert the strategy emits `SpendVoidPointsEvent(character, "wound check", 5)` — exactly 5, not 4.
- [X] T023 [P] [US3] Add failing test `test_akodo_4th_dan_strategy_minimum_sufficient`. Setup where spending 2 VP brings expected SW to tolerable, but spending 3 or 4 would also work; assert strategy spends exactly 2, NOT more. Per FR-018.
- [X] T024 [P] [US3] Add failing test `test_akodo_4th_dan_strategy_minimizes_when_no_tolerable`. Setup where no spend amount achieves tolerable SW (too much damage); assert strategy spends the amount that minimizes expected SW; when ties, picks smallest (preserve VP). Per OPEN_QUESTIONS.md Q2.
- [X] T025 [P] [US3] Add failing test `test_akodo_4th_dan_zero_vp_no_spend`. With `max_spend=0`, assert no SpendVoidPointsEvent yielded; assert the original WoundCheckRolledEvent passes through unchanged.
- [X] T026 [P] [US3] Add failing test `test_akodo_4th_dan_water_ring_raise_and_discount`. Build a 4th-Dan Akodo; verify water ring increased by 1 (vs. pre-Dan-4 baseline) AND subsequent water raises cost 5 less than the un-discounted price.
- [X] T027 [P] [US3] Add failing test `test_akodo_4th_dan_spend_trace_attribution`. Verify trace contains "Akodo 4th Dan: spent N VP on wound check, +5 per VP = +5N to roll" or equivalent attribution + breakdown.

### Implementation for User Story 3

- [X] T028 [US3] Fix the off-by-one in `simulation/schools/akodo_school.py` `AkodoWoundCheckRolledStrategy.recommend`: change `for vp in range(1, max_spend)` to `for vp in range(1, max_spend + 1)`. Verify T022 passes after change.
- [X] T029 [US3] If T023/T024 reveal the chosen_spend logic doesn't select minimum-sufficient correctly, refactor the iteration to track minimum spend that achieves tolerable, falling back to spend that minimizes expected SW (smallest-tie-break per OPEN_QUESTIONS.md Q2).
- [X] T030 [US3] If T026 reveals `apply_school_ring_raise_and_discount` doesn't fire correctly, verify via `simulation/schools/base.py` that the helper is correct AND that `apply_rank_four_ability` calls it.
- [X] T031 [US3] Add trace formatter attribution for `SpendVoidPointsEvent` sourced from Akodo 4th Dan WC raise (separate from generic VP spending).

**Checkpoint**: 4th-Dan WC survivability works; the off-by-one is fixed; the trace explains every VP spend.

---

## Phase 6: User Story 4 — 5th Dan counter-damage (Priority: P1, includes the P0 double-damage verification)

**Story goal**: A 5th-Dan Akodo applies incoming damage exactly once, dispatches WC exactly once, and counter-damages the attacker at 10 LW per VP spent.

### Tests for User Story 4

- [X] T032 [P] [US4] **P0 verification**: Add failing test `test_akodo_5th_dan_listener_does_not_double_apply_damage`. Build a 5th-Dan Akodo with LW=0; have attacker deal exactly 30 LW; assert `akodo.lw() == 30` (not 60). This is the highest-impact correctness check.
- [X] T033 [P] [US4] Add failing test `test_akodo_5th_dan_wound_check_dispatched_once_only`. Continue T032 setup; assert exactly ONE WoundCheckDeclaredEvent fires for the Akodo per single damage event, not two.
- [X] T034 [P] [US4] Add failing test `test_akodo_5th_dan_counter_damage_amount`. Continue T032 setup; assert AkodoFifthDanStrategy emits `SpendVoidPointsEvent(akodo, "damage", 3)` (30 ÷ 10 = 3) followed by `LightWoundsDamageEvent(akodo, attacker, 30)` (10 × 3).
- [X] T035 [P] [US4] Add failing test `test_akodo_5th_dan_counter_damage_cap_by_available_vp`. Same scenario but Akodo has only 2 VP available; assert spend=2, counter-damage=20 (not 30).
- [X] T036 [P] [US4] Add failing test `test_akodo_5th_dan_zero_damage_no_counter`. Damage event with `damage=5` (< 10); `max_vp = 5 // 10 = 0`; assert no SpendVoidPointsEvent and no counter-damage emitted.
- [X] T037 [P] [US4] Add failing test `test_akodo_5th_dan_mirror_recursion_terminates`. Two 5th-Dan Akodos, max VP each; force one to take 50 damage; assert combat resolves without infinite recursion AND VP pools strictly decrease across the counter chain.
- [X] T038 [P] [US4] Add failing test `test_akodo_5th_dan_counter_damage_trace_attribution`. Verify trace contains "Akodo 5th Dan: spent N VP on counter-damage, 10 LW × N = +N0 LW dealt to <attacker>" or equivalent.

### Implementation for User Story 4

- [X] T039 [US4] Verify the existing `AkodoLightWoundsDamageListener` in `simulation/schools/akodo_school.py` does not stack with a default listener. Per the negation refactor at commit `89dc0bb`, `_set_school_listener` writes to a single slot in `_school_owned_listener_slots`, meaning it REPLACES rather than stacks. T032 will lock this in. If somehow it stacks, this is P0 escalation. **Verified**: T032 passes with NO source-code change to lw_damage handling. Slot-replacement semantics hold.
- [X] T040 [US4] Verify the existing `AkodoFifthDanStrategy.recommend` formula matches FR-022: `max_vp = min(available_vp_for_damage, max_vp_per_roll, event.damage // 10)`. T034 + T035 will lock this in. **Verified** via T034 (damage=30, full VP → spend=3) and T035 (damage=30, VP=2 → spend=2).
- [X] T041 [US4] If T037 reveals the recursion doesn't terminate (e.g., VP is replenished mid-chain or damage somehow regenerates), the test surfaces the engine-level bug; investigate and fix. **No defect**: T037 passes; recursion terminates naturally via VP exhaustion + `damage < 10` cutoff. VP spends are non-increasing across the chain.
- [X] T042 [US4] Add trace formatter attribution for the counter-damage `LightWoundsDamageEvent` distinguishing it from primary damage. Likely needs a flag on the event (e.g., `source="Akodo 5th Dan"`) or the formatter inspects the issuing strategy class. **Implemented**: added optional `source` field to `LightWoundsDamageEvent`; `AkodoFifthDanStrategy` tags both the SpendVoidPointsEvent and LightWoundsDamageEvent with `source="Akodo 5th Dan"`; added `_find_akodo_5th_counter_damage` lookahead and `_format_akodo_5th_dan_counter` combined renderer in `web/adapters/detailed_formatter.py`.

**Checkpoint**: 5th-Dan counter-damage works; no double-damage; mirror recursion terminates.

---

## Phase 7: User Story 5 — Principle IX playability validation (Priority: P1, includes the AkodoAttackStrategy implementation)

**Story goal**: A 300-XP default Akodo is winnable against Hida baseline; mirror non-degeneracy holds; action-disadvantage is handled. The signature feint economy actually fires under defaults.

### Tests for User Story 5

- [X] T043 [P] [US5] Add failing test `test_akodo_default_attack_strategy_is_AkodoAttackStrategy` (regression). Build a 1st-Dan Akodo; assert `character._strategies["attack"].__class__.__name__ == "AkodoAttackStrategy"`. Without this, `UniversalAttackStrategy` (the engine default) gates feint behind `vp() == 0` and Akodo's identity engine never fires — Principle IX failure.
- [X] T044 [P] [US5] Add failing test `test_akodo_default_interrupt_does_not_counterattack`. Assert `character._strategies["interrupt"].__class__.__name__ != "CounterattackInterruptStrategy"` (Akodo has no counterattack knack; this is the Mirumoto-precedent regression guard).
- [X] T045 [P] [US5] Add failing test `test_akodo_attack_strategy_kill_shot_branch`. Setup: target has `sw_remaining() <= 1` AND Akodo has `vp() >= 1`. Assert AkodoAttackStrategy.recommend returns a double-attack OR plain-attack event, NOT a feint.
- [X] T046 [P] [US5] Add failing test `test_akodo_attack_strategy_feint_first_branch`. Setup: target's `sw_remaining() > 1`, Akodo has any VP. Assert AkodoAttackStrategy.recommend returns a feint event at threshold 0.6.
- [X] T047 [P] [US5] Add failing test `test_akodo_attack_strategy_plain_attack_fallback`. Setup: feint skill = 0 (or feint check fails at 0.6 threshold). Assert AkodoAttackStrategy.recommend falls back to plain attack at 0.7, then desperation 0.01, then HoldActionEvent.
- [X] T048 [P] [US5] Add scenario test `test_akodo_300xp_wins_at_least_one_of_five_vs_hida_300xp` per FR-028 / SC-004. Use 5 deterministic seeds; assert Akodo wins ≥ 1; collect TVP gain count per combat; assert sum > 0 for every seed (proves feint engine fired).
- [X] T049 [P] [US5] Add scenario test `test_akodo_mirror_300xp_terminates_within_20_rounds` per FR-029 / SC-005. Two 300-XP Akodos with deterministic seed; assert combat terminates within 20 rounds.
- [X] T050 [P] [US5] Add scenario test `test_akodo_mirror_identity_engine_fires` per FR-029 / Principle IX 2(b). Same mirror setup; assert trace contains ≥ 1 TVP gain, ≥ 1 floating-bonus acquisition (if Dan ≥ 3), ≥ 1 SpendVoidPointsEvent (if Dan ≥ 4), ≥ 1 counter-damage LightWoundsDamageEvent (if Dan ≥ 5) — scaled to the Dan rank in the build.
- [X] T051 [P] [US5] Add scenario test `test_akodo_action_disadvantage_eventually_attacks` per FR-030 / SC-006. Build 5th-Dan Akodo at -1 action; assert within 3 rounds the Akodo emits at least one offensive action (TakeAttackActionEvent). Bonus assertion per strategy-designer recommendation: if opponent's `sw_remaining() <= 1`, next Akodo action is double attack or attack (not feint).

### Implementation for User Story 5

- [X] T052 [US5] Write `AkodoAttackStrategy` appended to `simulation/schools/akodo_school.py` (chosen over a new `simulation/strategies/akodo.py` file because the strategy is school-specific and won't be reused). Class inherits from `BaseAttackStrategy`. Implements per the strategy-designer's spec PLUS a **TVP-saturation gate** added at the feint-first branch as a 2026-05-27 mirror-non-degeneracy fix (see Notes below): (1) **Kill-shot branch**: target.sw_remaining() ≤ 1 AND character.vp() ≥ 1 → try double_attack at threshold 0.6, then attack at 0.7. (2) **Feint-first branch**: feint skill > 0 AND `character.tvp() < TVP_SATURATION_CAP (=4)` → try feint at threshold 0.6. (3) **Plain-attack fallback**: attack at 0.7, then 0.01, then HoldActionEvent. The TVP cap is necessary because an empirical seed=7 mirror match with the bare 3-branch policy ran 30 rounds with 238 feints / 2 attacks / 0 damage, a Principle IX 2(a) violation. Documented in the class docstring and OPEN_QUESTIONS.md.
- [X] T053 [US5] Install `AkodoAttackStrategy` via `_set_school_strategy(character, "attack", AkodoAttackStrategy())` in `apply_special_ability` in `simulation/schools/akodo_school.py`. Docstring comment block added per the Mirumoto precedent explaining (a) why feint is first-class (TVP economy fuels every higher-Dan ability), (b) why NO `CounterattackInterruptStrategy` is installed (Akodo has no counterattack knack — anti-Mirumoto-precedent regression guard), (c) why `ReluctantParryStrategy` at the parry slot is the engine default and is correct.
- [X] T054 [US5] Verified T043-T047 (strategy-class unit tests) pass. All 5 pass.
- [X] T055 [US5] Verified T048-T051 (Principle IX scenario tests) pass after adding the **TVP-saturation gate** in T052 (a 2026-05-27 mirror-non-degeneracy fix beyond the strategy-designer's original 3-branch spec). T048 (win-feasibility vs Hida): PASS on first try with TVP cap; without the cap T049 (mirror termination) hangs at seed=7 due to infinite feinting. Tuning documented in `AkodoAttackStrategy.TVP_SATURATION_CAP` and in OPEN_QUESTIONS.md.

**Checkpoint**: Akodo's defaults are identity-aligned AND playable. Principle IX baseline assumptions hold.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, trace observability sweep, BACKLOG.md update, constitution-gates verification.

- [X] T056 [P] Run `combat-simulator` Scenario A (clause exercise): every Akodo ability fires at least once in a scripted multi-Dan combat. Verify via the agent's trace report.
- [X] T057 [P] Run `combat-simulator` Scenario B (win-feasibility): 300-XP Akodo vs Hida, Mirumoto, Ishi. ≥ 1 win per opponent.
- [X] T058 [P] Run `combat-simulator` Scenario B.2 (action-disadvantage): Akodo at -1 action eventually attacks offensively per FR-030.
- [X] T059 [P] Run `combat-simulator` Scenario C (mirror non-degeneracy with identity-engine-firing check): two 5th-Dan Akodos. Termination ≤ 20 rounds AND trace shows all 5 identity-engine events fire.
- [X] T060 [P] Run `combat-simulator` Scenario D (behavioral round-robin): Akodo plays a combat against each currently-implemented school (Mirumoto, Ishi). Verify trace shows feint count ≥ 30% of offensive actions per the strategy-designer's behavioral fingerprint.
- [X] T061 Dispatch `rules-auditor` to review the entire Akodo diff (HEAD vs master) against the upstream rules text. Address any flagged discrepancies.
- [X] T062 Trace observability sweep (Principle VII): manually generate a 5th-Dan-vs-5th-Dan combat trace; walk through every line; verify every Akodo-sourced numeric effect has both source attribution AND numeric breakdown. Items missing attribution are P0.
- [X] T063 Run the full quality-gate suite:
  - `env/bin/ruff check .` — must pass.
  - `env/bin/mypy` — must pass strict mode.
  - `env/bin/pytest tests/ -v` — full suite must pass. Test count MUST be ≥ baseline + new tests (T006–T051 ≈ 30 new tests).
  - `env/bin/pytest tests/test_akodo_school.py --cov=simulation/schools/akodo_school --cov-report=term-missing` — Akodo file coverage ≥ 95%.
- [X] T064 Streamlit smoke check (Principle VII visual confirmation): start `env/bin/streamlit run web/app.py --server.headless true`; build an Akodo character; run a combat; verify the trace renders all Akodo-attributed lines in the UI.
- [X] T065 Update BACKLOG.md: move "Akodo Bushi School" entry from "Skeleton present — needs full audit + completion" to "Validated via speckit workflow" with the squash-merge commit hash (filled in after T067).
- [X] T066 Update `OPEN_QUESTIONS.md` final status: mark Q1 (TVP-vs-VP-on-fail) and Q3 (5th Dan always-spend-max) as final pre-resolutions for end-of-run user review; Q5, Q6, Q7 as resolved during the run.
- [ ] T067 Squash-merge `005-akodo-bushi-school` into `master` with a comprehensive commit message documenting the bug fixes (4th Dan off-by-one), the new `AkodoAttackStrategy`, the strategy-binding additions, and the test count delta. User handles `git push` (per durable constraint).

---

## Dependencies

- **Phase 1 → Phase 2 → Phase 3+**: setup → foundational → user stories.
- **Phase 3 (US1) is MVP**: completing US1 alone delivers a runnable 1st-Dan Akodo with feint TVP economy.
- **Phases 3–7 are mostly story-independent** within each Dan rank (TVP for 1st Dan, floating bonus for 3rd Dan, etc.). Tests within each phase can run in parallel; implementation within each phase is gated by the tests existing first.
- **Phase 7 (US5)**: depends on Phases 3–6 implementations being complete because Principle IX scenarios exercise every ability.
- **Phase 8 (Polish)**: depends on all prior phases.

## Parallel execution examples

Within each user story's test block, the tests are independent (different test functions in the same file or related files) — they CAN run in parallel during implementation. Examples:

- T006, T007, T008, T009 (US1 tests) — parallel.
- T013, T014, T015, T016, T017 (US2 tests) — parallel.
- T022, T023, T024, T025, T026, T027 (US3 tests) — parallel.
- T032, T033, T034, T035, T036, T037, T038 (US4 tests) — parallel.
- T043, T044, T045, T046, T047, T048, T049, T050, T051 (US5 tests) — parallel.

Tasks marked [P] in the same phase are intended for parallel execution within a single `school-implementer` batch invocation.

## Implementation strategy

**MVP first**: Phase 3 alone delivers a working 1st-Dan Akodo with feint economy. Subsequent phases are incremental — Phase 4 adds 3rd Dan, Phase 5 adds 4th Dan, Phase 6 adds 5th Dan, Phase 7 adds Principle IX defaults.

**Per workflow in CLAUDE.md**: batch tasks 3–6 per `school-implementer` invocation. After each batch:
1. `rules-auditor` reviews the diff.
2. `combat-simulator` runs the relevant Scenario A/B/C/D check.
3. Address any defects before proceeding to the next batch.

**Batching plan** (suggested for the orchestrator):
- **Batch 1**: T001–T005 (setup + foundational). Single batch, no need for agent review yet.
- **Batch 2**: T006–T012 (US1 — TVP economy). After batch, run `rules-auditor` + `combat-simulator` Scenario A for Special Ability.
- **Batch 3**: T013–T021 (US2 — 3rd Dan floating bonus). Review batch.
- **Batch 4**: T022–T031 (US3 — 4th Dan WC raise + off-by-one fix). Review batch.
- **Batch 5**: T032–T042 (US4 — 5th Dan counter-damage). **P0 verification of double-damage on T032**. Review batch with extra emphasis on the lw_damage listener stacking question.
- **Batch 6**: T043–T055 (US5 — Principle IX defaults + AkodoAttackStrategy). Review batch with `combat-simulator` Scenarios B/C.
- **Batch 7**: T056–T067 (Polish + merge).

Total: ~67 tasks across 7 phases. Estimated implementer effort: 6–8 `school-implementer` invocations + 4–5 `rules-auditor` + 4–5 `combat-simulator` invocations.
