---

description: "Task list for Isawa Ishi School implementation (autonomous run)"
---

# Tasks: Isawa Ishi School

**Input**: Design documents from `/specs/002-isawa-ishi-school/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/interfaces.md, quickstart.md, OPEN_QUESTIONS.md

**Tests**: Mandatory per Constitution Principle I.

**Run Mode**: Autonomous — `school-implementer` agent makes implementation calls, `rules-auditor` + `combat-simulator` review, fix cycles capped at 3 per task, deferred questions logged in OPEN_QUESTIONS.md.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Baseline Verification)

- [X] T001 Capture baseline by running `env/bin/ruff check .`, `env/bin/mypy`, `env/bin/pytest tests/ -v`. Confirm the existing skeleton tests pass (the `IshiAllyBoostListener` tests currently lock in the wrong behavior — note explicitly which ones will need updating during the rewrite). Workspace: `/workspace`.

---

## Phase 2: Foundational (Engine surface for 5th Dan)

**Purpose**: Add the per-character negation flag and the BaseSchool short-circuit helper. These are prerequisites for the 5th Dan implementation (US5).

- [X] T002 Add `Character._school_negated_by: Optional[Character]` attribute (default `None`) to `simulation/character.py`. Reset in `Character.reset()`. Files: `simulation/character.py`, `tests/test_character.py` (add unit test).

- [X] T003 Add `_check_negated_short_circuit` helper to `simulation/schools/base.py`. When `character._school_negated_by is not None`, the helper returns `True` (caller should yield nothing). Apply the check at the top of each `apply_special_ability`, `apply_rank_one_ability` ... `apply_rank_five_ability` in `BaseSchool` (or via a decorator pattern — implementer chooses per OAD-1). Files: `simulation/schools/base.py`, `tests/test_school_negation.py` (NEW — verify negation short-circuits).

- [X] T004 Add `SchoolNegatedEvent` class to `simulation/events.py`. Carries `(negator, target, vp_cost, target_school_name)`. Files: `simulation/events.py`, tests.

**Checkpoint**: Engine has the surface to support 5th Dan negation; no school uses it yet.

---

## Phase 3: User Story 1 — Special Ability (Priority: P1) 🎯 MVP

**Goal**: Verify the existing `IshiMaxVPProvider` correctly computes `max_vp` and `max_vp_per_roll` for an Ishi character at any school rank, including edge cases.

**Independent Test**: Construct an Isawa Ishi at school rank 3 with `rings = {void: 4, fire: 3, water: 2, air: 3, earth: 3}`. Assert `character.max_vp() == 7` and `character.max_vp_per_roll() == 1`.

- [X] T005 [US1] Add `TestIshiMaxVPProvider` unit tests covering `max_vp = highest + school_rank`, `max_vp_per_roll = max(0, lowest - 1)`, and the edge case where lowest_ring = 1 → cap = 0. File: `tests/test_ishi_school.py` (NEW).

- [X] T006 [US1] Add `TestIshiSpecialAbilityIntegration` end-to-end: build a character via the school's apply_*_ability chain, set rings, assert `character.max_vp()` and `character.max_vp_per_roll()` reflect Special Ability semantics. File: `tests/test_ishi_school.py`.

---

## Phase 4: User Story 2 — 1st & 2nd Dan passive bonuses (Priority: P1)

**Goal**: Fix `free_raise_skills` to return `["precepts"]` (was `["attack"]`); verify 1st Dan extra-die behavior on `precepts`, `wound check`, `initiative`; add trace observability for the 2nd Dan free raise.

- [X] T007 [US2] Fix `IsawaIshiSchool.free_raise_skills` to return `["precepts"]`. Add test asserting the new value. Update any existing test that asserts the old `["attack"]` value. File: `simulation/schools/ishi_school.py`, `tests/test_ishi_school.py`.

- [X] T008 [US2] Add `TestIshiFirstDanExtraDice` covering extra die on `precepts`, `wound check`, `initiative` rolls. Use `DefaultRollParameterProvider` to verify rolled-dice count is `+1` vs baseline. File: `tests/test_ishi_school.py`.

- [X] T009 [US2] Extend `web/adapters/modifier_breakdown.py::explain_modifier` to attribute the 2nd Dan free raise on precepts rolls (when character has Ishi at rank ≥ 2 and skill == "precepts", append `("Isawa Ishi 2nd Dan free raise", 5)` to the breakdown). Add test asserting the user-visible trace contains the attribution. Files: `web/adapters/modifier_breakdown.py`, `tests/test_combat_trace_attribution.py`.

**Checkpoint**: 1st- and 2nd-dan Isawa Ishi pass passive-ability tests; trace observability for 2nd Dan working.

---

## Phase 5: User Story 3 — 3rd Dan ally-boost (Priority: P2)

**Goal**: Fix all 4 high-severity skeleton bugs in `IshiAllyBoostListener` and split the decision into a pluggable `IshiAllyBoostStrategy`. Add comprehensive tests including the 8 combat-roll event types and the once-per-roll guard.

- [X] T010 [US3] Create `simulation/strategies/ishi_dan_abilities.py` with `IshiAllyBoostStrategy(Strategy)` ABC and `EagerAllyBoostStrategy(IshiAllyBoostStrategy)` default concrete implementation. The strategy's `recommend` method takes `(character, event, context)` and yields a `SpendVoidPointsEvent` + mutates the ally's roll if: (a) ally is in-group, (b) ally's roll is below TN, (c) `character.vp() >= 1`, (d) `character.skill("precepts") > 0`, (e) per-roll guard not set. Add helper `_already_boosted(action) -> bool`. Files: `simulation/strategies/ishi_dan_abilities.py`, `tests/test_ishi_school.py`.

- [X] T011 [US3] Rewrite `IshiAllyBoostListener` in `simulation/schools/ishi_school.py`:
  - Remove the wholesale override of `attack_rolled` — instead, chain WITH the default `AttackRolledListener` (call default's logic first OR install on a different slot per OAD-4).
  - Drop the `formation().is_adjacent` requirement.
  - Subscribe to all 8 combat roll event types: `AttackRolledEvent`, `ParryRolledEvent`, `DoubleAttackRolledEvent`, `CounterattackRolledEvent`, `IaijutsuRolledEvent` (if exists), `FeintRolledEvent` (if exists), `LungeRolledEvent` (if exists), `WoundCheckRolledEvent`. Implementer: read `simulation/events.py` to find the canonical event class names.
  - Delegate the spend decision to `character.strategies["ishi_ally_boost"]`.
  - Mark the action with `_ishi_boosted_by = character` after firing (once-per-roll guard).
  - DO NOT call `interrupt_strategy().recommend()` in any branch (skeleton bug).
  Update existing `TestMirumotoParryAction` parry-side test if it leaked here from skeleton. Files: `simulation/schools/ishi_school.py`, `tests/test_ishi_school.py`.

- [X] T012 [US3] Wire `IshiAllyBoostStrategy` into `apply_rank_three_ability` via `character.set_strategy("ishi_ally_boost", EagerAllyBoostStrategy())`. Install the rewritten `IshiAllyBoostListener` on the appropriate slot(s). Add integration test (`TestIshiUS3Integration`) that runs a 3rd-dan Ishi + ally + enemy through `CombatEngine` with `CalvinistRollProvider`; assert the boost fires on a failing ally roll. Files: `simulation/schools/ishi_school.py`, `tests/test_ishi_school.py`.

- [X] T013 [US3] Extend `web/adapters/modifier_breakdown.py::explain_modifier` to attribute the 3rd Dan ally boost when an action has `_ishi_boosted_by` set: append `("Isawa Ishi 3rd Dan ally boost from {ishi_name}", boost_value)` to the breakdown. Add test asserting the user-visible trace contains the attribution. Files: `web/adapters/modifier_breakdown.py`, `tests/test_combat_trace_attribution.py`.

**Checkpoint**: 3rd-dan Isawa Ishi correctly boosts ally rolls across all 8 combat roll types; per-roll guard works; trace shows attribution.

---

## Phase 6: User Story 4 — 4th Dan Void modifications (Priority: P2)

- [X] T014 [US4] Add `TestIshiFourthDanVoidRaiseAndDiscount` covering Void+1 (current and max) and Void XP cost −5 with floor 0. The implementation already exists via `apply_school_ring_raise_and_discount`; this task makes the coverage explicit. File: `tests/test_ishi_school.py`.

---

## Phase 7: User Story 5 — 5th Dan school negation (Priority: P3)

**Goal**: Implement the school-negation mechanism. Requires the engine surface from Phase 2.

- [X] T015 [US5] Add `IshiNegateSchoolStrategy(Strategy)` ABC and `EagerNegationStrategy(IshiNegateSchoolStrategy)` default to `simulation/strategies/ishi_dan_abilities.py`. The strategy's `recommend` method: only on `YourMoveEvent`, only if `_ishi_negation_done` flag not set, only if `character.school_rank() >= 5`. Find highest-rank opposing schooled enemy; compute cost (`2 × opponent.school_rank()` or `floor(opponent_xp / 50)` for schoolless); if affordable, yield `SpendVoidPointsEvent`, set `opponent._school_negated_by = character`, yield `SchoolNegatedEvent`, set `character._ishi_negation_done = True`. Add helper `_negation_cost(target) -> int`. Files: `simulation/strategies/ishi_dan_abilities.py`, `tests/test_ishi_school.py`.

- [X] T016 [US5] Create `IshiYourMoveListener` in `simulation/schools/ishi_school.py` (or install as a chained strategy on the action slot — implementer chooses). Consults `character.strategies["ishi_negate_school"]` on `YourMoveEvent` BEFORE the normal action strategy. File: `simulation/schools/ishi_school.py`.

- [X] T017 [US5] Implement `apply_rank_five_ability` in `IsawaIshiSchool`: install `EagerNegationStrategy` on `"ishi_negate_school"` slot, install `IshiYourMoveListener` on the appropriate slot. Files: `simulation/schools/ishi_school.py`, `tests/test_ishi_school.py`.

- [X] T018 [US5] Extend `web/adapters/detailed_formatter.py` to format `SchoolNegatedEvent`. The user-facing trace string should read: `Phase X | {negator} | ⛔ negates {target}'s {school_name} ({cost} VP — Isawa Ishi 5th Dan)`. Add test. Files: `web/adapters/detailed_formatter.py`, `tests/test_combat_trace_attribution.py`.

- [X] T019 [US5] Add `TestIshiFifthDanNegation` integration test: 5th-dan Ishi vs 4th-dan Mirumoto Bushi. Verify (a) Ishi's VP decreases by 8, (b) `mirumoto._school_negated_by == ishi`, (c) Mirumoto's `MirumotoParryTVPListener` no longer fires on subsequent parries (because `BaseSchool.apply_special_ability` short-circuits when the flag is set — but wait, that's set at construction; need to ALSO check the listener path). Implementer: figure out the correct semantics — the negation flag should prevent NEW ability triggers, but listeners already installed at construction time are a different concern. Document the resolution in OPEN_QUESTIONS.md if it surfaces an ambiguity. File: `tests/test_ishi_school.py`.

**Checkpoint**: 5th-dan Isawa Ishi can negate an opposing school; trace shows the event; Mirumoto's parry-TVP economy stops firing post-negation.

---

## Phase 8: Progression refresh

- [X] T020 Rewrite `ISHI_PRIORITIES` in `simulation/templates/strategies.py` per the school-progression-designer's proposal (see research.md § R2). Verify the existing parametrized `test_template_generator.py` tests still pass for Ishi. File: `simulation/templates/strategies.py`.

- [X] T021 Regenerate all 7 Ishi YAML templates via `generate_template` + `write_template_yaml`. Verify the test_template_generator parametrized tests pass for the new Ishi templates. Files: `simulation/data/templates/ishi/ishi_{150,200,250,300,350,400,450}.yaml`.

---

## Phase 9: Polish — Trace, Coverage, Principle IX validation

- [X] T022 Add `TestIshiTraceClarity` covering all Ishi ability trace annotations (Special Ability cap when reached, 1st Dan extra die source, 2nd Dan free raise attribution, 3rd Dan boost attribution, 4th Dan stats visible, 5th Dan negation event rendered). Principle VII regression guard. File: `tests/test_ishi_school.py`.

- [X] T023 Run `combat-simulator` for Principle IX playability validation: Scenario A (Ishi vs Akodo at 300 XP), Scenario B.1 (1v1 mirror — accept 3rd Dan inert per Layer-3 caveat), Scenario B.2 (2v2 mirror — verify 3rd Dan fires), Scenario C (action-disadvantage), Scenario D (behavioral round-robin vs implemented schools). Surface any defects to a follow-up task.

- [X] T024 Coverage check (`env/bin/pytest tests/ --cov=simulation --cov-report=term-missing`). Verify ≥ 90% project-wide; Ishi files specifically ≥ 90%. Add tests for any uncovered branches.

- [X] T025 Full-suite regression: `env/bin/ruff check .`, `env/bin/mypy`, `env/bin/pytest tests/ -v`. All zero-error.

---

## Dependencies & Execution Order

- Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (US4) → Phase 7 (US5) → Phase 8 (Progression) → Phase 9 (Polish).
- Phase 2 is a hard prerequisite for Phase 7 (US5 needs the negation flag + base-class helper + event class).
- US3 (Phase 5) is the most complex; the most fix-cycle risk lives there.

## Per-Task Agent Loop

For each implementation task:
1. Spawn `school-implementer` with task text, FRs, rules clause.
2. In parallel, spawn `rules-auditor` and `combat-simulator` against the diff.
3. If discrepancies, send back to implementer. Cap at 3 fix cycles. Beyond that, log to OPEN_QUESTIONS.md and continue (autonomous-run mode).
4. Commit on clean reviewer reports.

## Notes (autonomous run)

- The orchestrator (main session) will NOT pause to ask the user during this run. All ambiguities flow into OPEN_QUESTIONS.md.
- If the agent loop hits a hard impasse (3 fix cycles fail or the agents disagree intractably), the orchestrator skips the task with a `[BLOCKED]` annotation in tasks.md and logs to OPEN_QUESTIONS.md.
- Scope-creep findings (unrelated bugs, engine gaps, opportunities for improvement) go in OPEN_QUESTIONS.md "Scope-creep findings" section — NOT fixed mid-run unless they block the school.
