---

description: "Task list for Mirumoto Bushi school implementation"
---

# Tasks: Mirumoto Bushi School

**Input**: Design documents from `/specs/001-mirumoto-bushi-school/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/interfaces.md, quickstart.md

**Tests**: Tests are MANDATORY for this feature. Constitution Principle I is non-negotiable — every task lands a failing test before any production code change. The `school-implementer` agent handles the red → green → refactor cycle inside each task.

**Organization**: Tasks are grouped by user story (US1 = P1, US2 = P2 (Third Dan), US3 = P2 (Fourth Dan), US4 = P3 (Fifth Dan)). Each story is independently testable per the spec.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks). Sparingly used in this feature because most work concentrates in two files.
- **[Story]**: Story label (US1–US4) for story-phase tasks. Setup/Foundational/Polish tasks carry no story label.
- Every task names exact file path(s).

## Path Conventions

- Engine library: `simulation/`
- Tests: `tests/`
- New strategy module: `simulation/strategies/mirumoto_third_dan.py`
- Touched school file: `simulation/schools/mirumoto_school.py`
- Touched test file: `tests/test_mirumoto_school.py`

---

## Phase 1: Setup (Baseline Verification)

**Purpose**: Establish the starting state before any modifications. The skeleton already exists; this phase confirms the baseline so subsequent task verdicts are interpretable.

- [X] T001 Capture the baseline by running `env/bin/ruff check .`, `env/bin/mypy`, and `env/bin/pytest tests/test_mirumoto_school.py -v`. Baseline (2026-05-25): ruff PASS, mypy PASS (186 source files), pytest 11/11 PASS. Buggy `test_extra_rolled` currently passes with `["attack", "double attack", "parry"]` (will go RED in T002). `TestMirumotoParryAction::test_half_extra_damage_dice_on_failed_parry` exists and locks in the wrong-side behavior (will be removed in T012).

---

## Phase 2: Foundational

**Purpose**: None — this feature has no truly cross-cutting prerequisites because the school is already factory-registered and the constitution's principles (RollProvider, Strategy, Listener) are existing engine machinery. Foundational phase is intentionally empty.

**Checkpoint**: Ready to begin US1.

---

## Phase 3: User Story 1 — Passive Abilities (Priority: P1) 🎯 MVP

**Goal**: A Mirumoto Bushi at any dan 1–5 can be instantiated and runs in the combat harness with its Special Ability, First Dan dice bonus, and Second Dan free raise all firing automatically.

**Independent Test**: Instantiate a 1st-dan Mirumoto Bushi, schedule scripted parry/double-attack/wound-check rolls, assert via combat trace that (a) the school registers and reports `void` + correct knacks, (b) every parry/double-attack/wound-check rolls one extra die, (c) every parry roll gets a free raise, (d) every parry attempt grants a temporary void point usable that same round and stacking above the normal pool cap.

### Tasks for User Story 1

- [X] T002 [US1] Fix `MirumotoBushiSchool.extra_rolled()` to return the rules-correct list `["parry", "double attack", "wound check"]` (FR-005). Commit `5277ba2`. Both reviewers PASS. Simulator suggested adding live-engine and action-level assertions for T003/T006.

- [X] T003 [US1] Add `TestMirumotoFirstDanExtraDie`. Commit `01ee14d`. Auditor PASS; only the wound-check test is a true regression for T002, parry/double-attack tests are positive FR-005 coverage.

- [X] T004 [US1] Add `TestMirumotoSecondDanFreeRaise`. Commit `25ce778`. 6 tests added; auditor PASS.

- [X] T005 [US1] Extend `TestMirumotoParryTVPListener`. Commit `7f5e724`. 5 new tests (subject guard, success/fail pipelines, cap-bypass, multi-parry); auditor PASS. Existing 2 tests strengthened (behavior-neutral).

- [X] T006 [US1] Add `TestMirumotoUS1Integration`. Commit `763c6a9`. 4 tests added (factory, ring+knacks, scripted-parry +1 die + TVP, failed-parry TVP). Both reviewers PASS. Simulator flagged 3 stronger E2E scenarios (live 2nd-dan free raise tipping a parry vs TN, live double-attack, live wound check) as out-of-scope coverage gaps — candidates for Polish or follow-up.

**Checkpoint**: 1st- and 2nd-dan Mirumoto Bushi run end-to-end. The MVP slice is shippable here.

---

## Phase 4: User Story 2 — Third Dan Pool with Active Spend Decisions (Priority: P2)

**Goal**: A 3rd-dan-or-higher Mirumoto Bushi gets a per-round pool of `2 × attack-skill` points, and pluggable strategies decide when to spend them (mode A = lower an action's phase by 1 to parry, mode B = +2 to a roll after seeing it). The two modes stack on themselves and combine across one action.

**Independent Test**: Construct a 3rd-dan Mirumoto with attack-skill 4 (pool = 8). Run a scripted combat; confirm via trace that (a) the pool is populated at round start, (b) the active strategies spend points in both modes against scripted scenarios, (c) the pool resets to 8 at the next round start (unspent points discarded), (d) attack-skill 0 yields a pool of 0 with no spend offers.

### Tasks for User Story 2

- [X] T007 [US2] Add `TestMirumotoThirdDanPool`. Commit `ad60818`. 3 tests; auditor PASS. Minor: partial overlap with existing `TestMirumotoNewRoundListener::test_grants_resource_pool` (consolidate in Polish).

- [X] T008 [US2] Create `MirumotoPhaseLowerStrategy` + `EagerPhaseLowerStrategy` + pool helpers + stub for `MirumotoPostRollBonusStrategy`. Commit `ba37d43`. 16 new tests; both reviewers PASS. See Review Notes T008 items 1–4 for architectural decisions and deviations from contracts/interfaces.md.

- [X] T009 [US2] Implement `MarginalBonusStrategy`. Commit `084d553` (after 1 fix cycle for counterattack support). 11 new tests; auditor PASS post-fix. See Review Notes T009 for the fix cycle and the critical T010 guidance from simulator about event suppression.

- [X] T010 [US2] Wire Third Dan strategies into school. Commit `2ce1aa4` (after 1 fix cycle for parry-reservation gap). 11 new tests; reviewers PASS post-fix. See Review Notes T010 for design decisions and the critical bug the simulator caught.

**Checkpoint**: 3rd-dan Mirumoto runs end-to-end with active spend decisions.

---

## Phase 5: User Story 3 — Fourth Dan Damage and Void Modifiers (Priority: P2)

**Goal**: A 4th-dan-or-higher Mirumoto Bushi has Void +1 (current and max), Void XP cost −5 (floor 0), defenders who fail to parry their double attacks still take the automatic serious wound (narrow scope: only auto-SW prevention removed, other failed-parry mitigation works normally), and defenders who fail to parry their regular attacks receive only half (rounded down) the standard failed-parry damage-die reduction.

**Independent Test**: Construct a 4th-dan Mirumoto alongside a baseline same-rank non-Mirumoto. Confirm Void stat +1, XP cost −5 with 0 floor. Run two scripted combats (Mirumoto-as-double-attacker vs failing-parry defender; Mirumoto-as-regular-attacker vs failing-parry defender) and assert defender outcomes match FR-012 (auto-SW lands) and FR-013 (damage-die reduction halved with `1 → 0` rounding).

### Tasks for User Story 3

- [X] T011 [US3] Add `TestMirumotoFourthDanVoidRaiseAndDiscount`. Commit `3feaec2`. 4 tests; auditor PASS. Two flags in Review Notes T011.

- [X] T012 [US3] BUG fix + attack-side scaffolding. Commit `87d47af` (after 1 fix cycle for swapped FR labels in docstrings). Wrong-side `MirumotoParryAction` removed; new `MirumotoAttackAction` and `MirumotoDoubleAttackAction` stubs in place; factory dispatches on skill string. 80 tests; reviewers PASS post-fix.

- [X] T013 [US3] Override `MirumotoDoubleAttackAction.direct_damage` for FR-012. Commit `d0eee44`. 6 new tests; both reviewers PASS. Simulator validated third-party parry case (auto-SW lands on the attack target regardless of who failed to parry).

- [X] T014 [US3] Override `MirumotoAttackAction.calculate_extra_damage_dice` for FR-013. Commit `5caa0b1`. 10 new tests; both reviewers PASS. Edge cases (5→2, 3→1, 1→0) all covered.

**Checkpoint**: 4th-dan Mirumoto runs end-to-end with all FR-010 through FR-013 active.

---

## Phase 6: User Story 4 — Fifth Dan Void Bonus on Combat Rolls (Priority: P3)

**Goal**: A 5th-dan Mirumoto Bushi gets +10 (in addition to the standard +5 per VP) on every combat roll where a void point is spent — attack, parry, wound check. Temporary void points (from the Special Ability) trigger this bonus identically to normal pool points (FR-004a). Non-combat rolls are unaffected.

**Independent Test**: Construct a 5th-dan Mirumoto, force VP spends on each of the three combat roll types, and assert each total includes the +10. Force a VP spend on a non-combat roll and assert the +10 does NOT apply.

### Tasks for User Story 4

- [X] T015 [US4] Add `TestMirumotoFifthDanPlusTen`. Commit `c301275`. 5 tests pin the existing implementation. **RULES-INTERPRETATION QUESTION FOR REVIEW** — see Review Notes T015 (the existing implementation adds +5 mod per VP, but the literal rules text + Yogo 4th Dan parallel suggest it should be +10 mod per VP).

- [X] T016 [US4] Add `TestMirumotoFifthDanWithTempVP`. Commit `b91124c`. 3 tests; auditor PASS. Pins temp-VP-spent-first ordering and provider provenance neutrality.

- [X] T017 [US4] Add `TestMirumotoFifthDanNonCombatRolls`. Commit `d45660a`. 4 new tests + a **REAL BUG FIX**: the existing skeleton applied the +5 mod to ALL skill rolls (not just combat). Implementer added a `{"attack", "parry"}` whitelist matching spec wording. **SCOPE QUESTION FOR REVIEW** — see Review Notes T017 (the whitelist probably should include `double attack`, `counterattack`, `iaijutsu` etc. since those are the school's own knacks).

**Checkpoint**: 5th-dan Mirumoto runs end-to-end. All four user stories independently testable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Trace observability (SC-006), coverage gate (SC-004), and full-suite regression.

- [X] T018 Trace logging for Mirumoto-specific effects (SC-006). Commit `e7244e8`. 8 new tests in `TestMirumotoTraceClarity` plus distinctive log markers on 3rd/4th/5th Dan effects.

- [X] T019 Coverage check. Project-wide coverage 93% (Mirumoto school 95%, Mirumoto third_dan strategies 92%). All uncovered lines are defensive guards (race-safety, strategy-not-installed, abstract NotImplementedError) — no new tests warranted.

- [X] T020 Quickstart walkthrough. Commit `48863e3`. Steps 4 + 5 + 6 + 8 updated to match actual API (set_school takes no rank arg; school methods called on school not character; pointed Step 6 at the test file as reference patterns).

- [X] T021 Full-suite regression. ruff PASS, mypy PASS (187 source files), pytest 2745/2745 PASS. SC-005 satisfied.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies. T001 first.
- **Phase 2 (Foundational)**: Empty — proceed directly to Phase 3.
- **Phase 3 (US1, P1)**: Begin after T001. Internal task order is T002 → T003 → T004 → T005 → T006 (mostly sequential due to shared file `tests/test_mirumoto_school.py`).
- **Phase 4 (US2, P2 — Third Dan)**: Logically independent of US1, but practically sequenced after US1 because the agent loop is single-threaded. Internal: T007 → T008 → T009 → T010.
- **Phase 5 (US3, P2 — Fourth Dan)**: Logically independent of US1 and US2. Internal: T011 → T012 → T013 → T014 (T013 and T014 both depend on T012's stubs).
- **Phase 6 (US4, P3 — Fifth Dan)**: Logically independent of US1–US3. Internal: T015 → T016 → T017.
- **Phase 7 (Polish)**: Depends on Phases 3–6. T018 → T019 → T020 → T021.

### Inter-Story Dependencies

None. The four user stories are independently testable per the spec's `Independent Test` clauses. They are sequenced here only because the implementation loop is one agent at a time.

### Within-Task TDD Order (enforced by `school-implementer` agent)

For every task touching production code:
1. Write the failing test(s) first in `tests/test_mirumoto_school.py` (or relevant test file).
2. Run `env/bin/pytest <test_file> -v` and confirm the new test(s) FAIL for the expected reason.
3. Implement the production code change.
4. Re-run the test(s); confirm they PASS.
5. Run `env/bin/ruff check .` and `env/bin/mypy`; resolve any errors.
6. Re-run the school's full test file; confirm no regressions in adjacent tests.

### Parallel Opportunities

Real parallel opportunities are limited because most tasks touch `simulation/schools/mirumoto_school.py` and/or `tests/test_mirumoto_school.py`. Two windows where parallelism *would* be possible if multiple developers were involved:

- T008 (`simulation/strategies/mirumoto_third_dan.py`) and any task in US3 that only touches `simulation/schools/mirumoto_school.py` could run in parallel by different developers because the files don't overlap.
- T020 (quickstart.md) is independent of code changes after Phase 6 finishes.

For the single-loop agent execution model proposed in this feature (one `school-implementer` invocation per task), all tasks run sequentially.

---

## Per-Task Agent Loop (used by `/speckit-implement`)

For each task, the main session orchestrates:

1. Spawn `school-implementer` with the task text, the FR/spec citation, and the rules clause from `rules/04-schools.md`.
2. Wait for the implementer to return with quality gates passing.
3. **In parallel**, spawn `rules-auditor` and `combat-simulator` against the resulting diff.
4. If either reviewer reports discrepancies, re-spawn `school-implementer` with the findings. Cap at 3 fix cycles per task; on the fourth iteration, escalate to the user.
5. When both reviewers return PASS (or INCONCLUSIVE with reasoning), commit the diff and advance to the next task.

The orchestrator (main session) is also responsible for:
- Reading the rules clause to quote into prompts.
- Running pre-flight checks (`git status` clean) at task start.
- Committing the green diff (using the existing speckit commit-message convention).

---

## Implementation Strategy

### MVP-First Delivery

1. Phase 1 baseline.
2. Phase 3 (US1) end-to-end. Stop and validate — the school is shippable as a 1st-/2nd-dan Bushi at this point.
3. Phase 4 (US2) — adds Third Dan. Shippable as 3rd-dan.
4. Phase 5 (US3) — adds Fourth Dan. Shippable as 4th-dan.
5. Phase 6 (US4) — adds Fifth Dan. Full school.
6. Phase 7 polish + coverage + full regression.

### Stop-and-Review Gates

After each phase's checkpoint, the orchestrator may pause and request a human-readable status before continuing — appropriate moments are: end of US1 (MVP), end of US3 (most complex changes), and start of Phase 7 (regression sweep).

---

## Review Notes (for end-of-run review)

Architectural decisions, deviations from plan/contracts, and follow-up candidates collected during `/speckit-implement`. Each item references the task that surfaced it. The user reviews these after the full run.

### T008 — Third Dan phase-lowering strategy (new code)

1. **Heuristic simplification**: `contracts/interfaces.md` § "MirumotoPhaseLowerStrategy" specifies `EagerPhaseLowerStrategy` should spend "whenever the pool has ≥ 1 point AND any enemy in the same group has a pending attack this round." The implementation simplified to "spend whenever the pool has ≥ 1 point and a non-phase-1 action exists," dropping the enemy-attack guard. Not a rules violation (FR-008 says spends are *permitted*, not *triggered* by enemy action), but the default strategy will burn points eagerly even when no parry is needed. **Decision needed**: keep simplified, or restore the enemy-attack gate in a follow-up?
2. **"In order to parry" deferral**: The rules say "decrease the phase of one of your actions by 1 **in order to parry**." T008's strategy lowers the phase but leaves no in-band marker that the action is parry-reserved. After the spend, the lowered action is an indistinguishable `int` in `character._actions`. Risk: if the character's attack strategy fires at the lowered phase before any enemy attack arrives, the action gets spent as an attack — using a point paid "in order to parry." T010 needs to either (a) add a sidecar attribute recording parry-reserved phase entries, or (b) relocate the spend hook to fire on incoming-attack events instead of `NewPhaseEvent`. **Decision deferred to T010**.
3. **Lost original-phase info**: The strategy mutates `_actions` in place (`actions[i] = original - 1; actions.sort()`), destroying the original phase value. No way to reconstruct "this entry was phase 7, lowered to 6 for parry" if a future erratum or refund mechanic needs it. Low immediate risk; flagging for forward-compatibility.
4. **Helper placement**: `_pool_remaining` and `_try_spend_pool_point` were placed in `simulation/strategies/mirumoto_third_dan.py` (with the only consumer) instead of `simulation/schools/mirumoto_school.py` as proposed in `contracts/interfaces.md`. Avoids a `strategies → schools` import. Acceptable architectural choice; flagging for visibility.

### T009 — Third Dan post-roll +2 strategy (MarginalBonusStrategy)

5. **Fix cycle 1**: rules-auditor caught that `_is_post_roll_event` whitelisted only `AttackRolledEvent` and `ParryRolledEvent`. Counterattack is a Mirumoto school knack (FR-003) and the rules text says "any type of attack." Implementer added `CounterattackRolledEvent` to the whitelist + test; re-audit PASS. **Note**: the engine's stock `AttackRolledStrategy` in `simulation/strategies/base.py` also doesn't cover counterattacks — this may be a wider engine convention to revisit in a separate feature.
6. **CRITICAL T010 GUIDANCE — event-suppression risk**: `MarginalBonusStrategy.recommend()` ends with `yield from ()` (returns empty iterator) rather than `yield event`. This is incompatible with installing the strategy as `attack_rolled_strategy` / `parry_rolled_strategy` / `counterattack_rolled_strategy`, because the engine in `simulation/events.py:163/204` does `yield from ...attack_rolled_strategy().recommend(...)` — meaning whatever the strategy yields becomes the public event stream. If `MarginalBonusStrategy` is naively swapped in, the original `AttackRolledEvent` etc. get suppressed, which breaks downstream consumers (enemy parries via `AttackRolledListener` + `DefaultInterruptStrategy`, AP/conviction spending, etc.). T010 must either (a) install on a NEW strategy slot, or (b) wrap with the default strategy so the event is re-emitted. The simulator demonstrated this concretely in Scenario 6: when MarginalBonusStrategy is installed as `attack_rolled_strategy`, enemy parries stop firing entirely.
7. **Heuristic note**: `MarginalBonusStrategy` does best-effort partial spends — if pool < ceil(margin/2), it spends what it has even though the roll won't clear the TN. Possible follow-up: should the strategy abstain when it can't close the gap? Currently it burns points "for nothing." Flagging.

### T010 — Third Dan strategy wiring (integration)

8. **Design decision — Mode A wiring**: chose option (b) from the prompt — reactive on `AttackDeclaredEvent` (not proactive on `NewPhaseEvent`). Rationale: rules say "in order to parry" — the parry is the trigger. `MirumotoAttackDeclaredListener` catches enemy attacks targeting the Mirumoto, synthesizes a `NewPhaseEvent(context.phase())`, and dispatches to the existing `EagerPhaseLowerStrategy`. The listener delegates to the stock `AttackDeclaredListener` first to preserve counterattack interrupts + lunge handling.
9. **Design decision — Mode B wiring**: subclassed `AttackRolledStrategy` and `ParryRolledStrategy` with a chaining mixin that runs `MarginalBonusStrategy` first then `super().recommend(...)`. Order matters: bonus first so the default's AP/conviction logic sees the post-bonus margin. `super()` re-emits the (mutated) event so enemy parry cascades still fire. Explicit regression test (`test_attack_rolled_event_still_reaches_enemy_listener`) locks this in.
10. **Design decision — Counterattack mode B via listener**: engine has no `counterattack_rolled_strategy` hook, so added `MirumotoCounterattackRolledListener` (set on `set_listener("counterattack_rolled", ...)`) that calls the strategy and mutates the roll. Cleanest option without an engine-wide change.
11. **CRITICAL BUG caught by simulator — fix cycle 1**: original `EagerPhaseLowerStrategy` spent 1 point per `recommend()` call. With action `[5]` at combat phase 3 and pool=4, it would lower 5→4 (still > 3, not usable for parry) and burn a point for nothing. Per rules "in order to parry" + FR-008 "converting that action into a parry", the spend must actually enable a parry. **Fix**: strategy now spends multiple points iteratively until action ≤ context.phase() OR pool exhausted OR phase-1 floor reached. If usability can't be achieved with current pool, spends NOTHING (no partial waste). New regression tests + integration tests cover the fix. Re-audit PASS.
12. **Parry-reservation gap (deferred)**: T008 raised the concern that a phase-lowered action isn't marked parry-reserved. T010 verified that in the current engine flow `AttackDeclaredEvent` and `AttackRolledEvent` fire in the same `TakeAttackActionEvent.play` generator with no intervening `YourMoveEvent`, so a lowered action can't be consumed by the wrong path. Adversarial scheduling could expose the gap, but the current engine doesn't support that. **No fix needed unless engine ordering changes** — flagging for future awareness.
13. **EagerPhaseLowerStrategy unspent-point quality issue**: even after fix cycle 1, the strategy will still spend points to lower an action whose current phase is already ≤ context.phase() (wasteful no-op-for-parry-purposes). The simulator flagged this as a strategy-quality issue (not a rules violation). Possible follow-up — refine the heuristic to skip such cases.

### T011 — Fourth Dan Void+1 / -5 XP tests

14. **Spec wording imprecision (US3.1)**: spec says "exactly 1 higher than the baseline character's" for current Void at 4th dan, but the actual delta vs any non-Mirumoto 4th-dan is +2 (Mirumoto school-ring bump of +1, plus Fourth Dan +1). The test handles this honestly by pinning absolute value `mirumoto.ring("void") == 4` instead, with a docstring explaining the breakdown. Spec wording should arguably be corrected to "+2" or rephrased.
15. **Engine-wide XP-cost floor concern**: `_BaseCharacterBuilder.calculate_ring_cost` returns `sum(...) - discount` with no `max(0, ...)` clamp. Harmless for Mirumoto alone (minimum standard = discount = 5), but if a future school/archetype stacks ring discounts, XP cost could go negative without any test catching it. Wider engine concern — possible follow-up.

### T012 — BUG fix: wrong-side parry removal + attack-side scaffolding

16. **Fix cycle 1**: rules-auditor caught SWAPPED FR labels in stub docstrings/TODO comments (MirumotoAttackAction labeled FR-012 when it should be FR-013, and vice versa) plus a wrong rule description in the MirumotoDoubleAttackAction docstring (described as "additional direct damage" when the rule is actually "removes the suppression of the existing auto-SW on parry attempts"). Fix-cycle 1 corrected the labels and the description. **This is a load-bearing-comment fix** — if T013/T014 had been driven by the wrong TODOs, they would have implemented the wrong mechanics. The orchestration caught this before downstream tasks consumed the bad guidance.

### T013 — FR-012 auto-SW on failed parry vs double attack

17. **Third-party parry edge** (simulator validated): if an ally parries on behalf of the target and fails, the auto-SW lands on the original target (not the failed parrier). This matches the rules-faithful reading of "the defender". The override's `self.target()` correctly points at the attack's target regardless of who parried. No discrepancy.
18. **Coverage gap noted by simulator**: no committed test pins the rank-gate (i.e., a 3rd-dan Mirumoto's double attack should NOT use MirumotoDoubleAttackAction). The simulator verified runtime behavior is correct but suggested adding a permanent regression test in Polish.

### T014 — FR-013 halving of damage-die reduction

19. **Implementation gotcha resolved**: `AttackAction.calculate_extra_damage_dice` returns 0 when `parry_attempted` is True. The Mirumoto override correctly computes the pre-cap `would_be_extra` and halves the reduction (rather than naively halving the already-zeroed return). Verified via tests covering 5→2, 3→1, 1→0, and skill-roll-below-TN floor cases.
20. **Coverage gap noted by simulator** (same family as T013): no committed test pins the rank-gate (a 3rd-dan Mirumoto's regular attack should NOT use MirumotoAttackAction). Polish candidate.

### T015 — HIGH-PRIORITY RULES INTERPRETATION QUESTION (Fifth Dan +10 magnitude)

21. **CRITICAL — the existing implementation is probably 5 short per VP.** The skeleton (predates this work) does `modifier += 5 * vp` in MirumotoRollParameterProvider, yielding +5 mod per VP on top of the standard +1 rolled / +1 kept dice from a VP. The codebase comment rationalizes this as "+10 instead of +5" by valuing the +1r/+1k as ~+5.
    - **Rules text** (rules/04-schools.md Fifth Dan): "Your void points provide an extra +10 when spent on combat rolls."
    - **Parallel precedent** (rules/04-schools.md Yogo 4th Dan): "an extra free raise per VP" = +5 mod per VP ON TOP OF the standard +1r/+1k. By parallel construction, Mirumoto 5th Dan's "extra +10" → +10 mod per VP on top of standard. Auditor's analysis: **the implementation is half the rule.**
    - **Spec FR-014** wording: "additional +10 on top of the standard void-spend bonus" — matches the literal rules reading, NOT the implementation's value-shorthand reading.
    - **Decision needed**: should the implementation be `modifier += 10 * vp` (matching rules text + spec wording + Yogo parallel) or stay at `modifier += 5 * vp` (matching pre-existing skeleton + codebase shorthand)? T015/T016/T017 all pin the existing behavior; flipping the implementation would require updating those tests.

### T016 — Special × Fifth Dan interaction (temp VP)

22. **FR-004a behavior pinned**: temp VPs and normal VPs are indistinguishable through the provider (both consult only the `vp` integer). Tests pin: (a) same modifier delta from temp vs normal, (b) temp spent before normal (engine invariant), (c) temp + normal combinable on same roll. Inherits the T015 +5/+10 question — if the user resolves T015 toward +10 mod, T016's tests need to update too.

### T017 — Non-combat rolls + UNEXPECTED BUG FIX

23. **Real BUG in pre-existing skeleton found and fixed**: `MirumotoRollParameterProvider.get_skill_roll_params` was adding the +5 mod to ALL skill rolls, not just combat ones — a 5th-dan Mirumoto spending a VP on `investigation` or `etiquette` was incorrectly receiving the bonus. Fix: added `_MIRUMOTO_FIFTH_DAN_COMBAT_SKILLS = frozenset({"attack", "parry"})` whitelist. The wound-check path has its own dedicated provider method and remains correctly always-on.
24. **SCOPE QUESTION FOR REVIEW** — the whitelist is currently `{"attack", "parry"}` matching FR-014's literal wording. But the engine's own taxonomy classifies `{attack, counterattack, double attack, feint, iaijutsu, lunge}` all as `ATTACK_SKILLS`, and three of those (`counterattack, double attack, iaijutsu`) are Mirumoto's school knacks (FR-003). It is implausible that the 5th Dan +10 doesn't apply when a Mirumoto spends VP on their *own* double attack or iaijutsu strike. **Decision needed**: broaden whitelist to `frozenset(ATTACK_SKILLS) | {"parry"}` (or equivalent)? If yes, also reword spec FR-014.

### T018–T021 — Polish phase

25. **Coverage all green**: 93% project-wide, 95% Mirumoto school, 92% Mirumoto third_dan strategies. The 14 uncovered Mirumoto lines are all defensive guards (race conditions, strategy-not-installed safety branches, abstract `raise NotImplementedError()`). These are good to have, awkward to test — accepted.
26. **Quickstart had broken API calls**: original `c.set_school(school, rank=1)` was wrong (set_school takes no rank arg in the actual engine) and `c.school_ring()` / `c.school_knacks()` are school methods, not character methods. Fixed in T020. Original quickstart was written against plan.md's predictions; reality slightly differed.
27. **Final regression**: ruff PASS, mypy PASS (187 source files, zero errors, strict mode on `simulation/` + `web/`), pytest 2745/2745 PASS. Constitution quality gates fully satisfied.
