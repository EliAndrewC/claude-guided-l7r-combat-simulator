---
description: "Task list for Combat Trace Observability Audit"
---

# Tasks: Combat Trace Observability Audit

**Input**: Design documents from `/specs/005-trace-observability-audit/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/formatter-rendering.md, quickstart.md, OPEN_QUESTIONS.md

**Tests**: Required per Constitution Principle I (Test-First, Non-Negotiable).

**Organization**: Tasks grouped by user story. The 5 stories from spec.md map to T-phases below.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Verify branch `006-trace-observability-audit` is checked out and the working tree is clean.
- [X] T002 Capture baseline test count (`env/bin/pytest tests/ --collect-only -q 2>&1 | tail -2`). Expected: 2970+ tests (after the four defect fixes from the Akodo follow-up commit `2a93c9a`).
- [X] T003 Reproduce the trace-auditor's dry-run scenario locally (`/tmp/probe.py` from the trace-auditor self-evaluation). Confirm the 5 P1 gaps are present in baseline output.

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T004 [P] Read `web/adapters/combat_observer.py` end-to-end. Document current `_annotate_attack` and `_annotate_damage` data flow (which event fields they capture; what data is available at annotation time).
- [X] T005 [P] Read `web/adapters/detailed_formatter.py` `_format_attack_rolled`, `_format_combined_attack`, `_format_lw_damage`, `_format_modifier_breakdown`, `_format_tn` end-to-end. Document the current rendering format for each (so the post-audit format can be designed against the pre-audit baseline).
- [X] T006 [P] Read `web/adapters/modifier_breakdown.py::explain_modifier` end-to-end. Enumerate the existing source cases. Identify which sources are missing per the dry-run findings (at minimum the bare-`+5` Bayushi double-attack case).
- [X] T007 [P] Read `simulation/mechanics/roll_params.py::DefaultRollParameterProvider.get_skill_roll_params` and `get_damage_roll_params`. Identify the accessors each method calls (`character.school_ring()`, `character.skill(...)`, `character.school().extra_rolled(...)`, `character.weapon().rolled()`, etc.) so the new `get_breakdown` method can mirror them.

## Phase 3: User Story 1 — Damage XkY breakdown (Priority: P1) 🎯 MVP

**Story goal**: Damage XkY expressions render with inline per-source breakdown showing weapon base + ring + margin extras + VP-on-attack inflation + school-specific extras.

### Tests for User Story 1 (write FIRST per TDD)

- [X] T008 [P] [US1] Add failing test `test_damage_xky_breakdown_inline_in_attack_predictive_line` in `tests/test_trace_observability.py`. Build a deterministic Bayushi-vs-Akodo combat (double attack, hit at +12 over TN). Assert the attack-line "damage will be" segment contains `XkY = 4k2 katana + Nk0 {ring} + 0kM margin + ...`.
- [X] T009 [P] [US1] Add failing test `test_damage_xky_breakdown_inline_in_lw_damage_event`. Same combat. Assert the final damage line contains `XkY = <breakdown>`.
- [X] T010 [P] [US1] Add failing test `test_damage_breakdown_sums_to_aggregate`. Assert `sum(rolled for c in components) == aggregate_rolled` AND same for kept, by parsing the breakdown string.

### Implementation for User Story 1

- [X] T011 [US1] Add `DefaultRollParameterProvider.get_breakdown(character, action, skill, kind="damage")` in `simulation/mechanics/roll_params.py`. Returns `list[tuple[str, int, int]]`. Walk the same accessors `get_damage_roll_params` does to compute per-source contributions.
- [X] T012 [US1] Extend `CombatObserver._annotate_damage` in `web/adapters/combat_observer.py` to call `character.roll_parameter_provider().get_breakdown(...)` and attach `_detail_components` to the event.
- [X] T013 [US1] Extend `_format_lw_damage` in `web/adapters/detailed_formatter.py` to render the inline breakdown when `_detail_components` exists with > 1 nonzero entry. Format: `XkY = N1k(M1) source-1 + N2k(M2) source-2 + ...`.
- [X] T014 [US1] Extend `_format_attack_rolled` (predictive "damage will be" projection) and `_format_combined_attack` to render the same damage breakdown inline.

**Checkpoint**: Run T008/T009/T010; they should pass. Trace-auditor on the calibration scenario reports P1 gap #1 (damage XkY) closed.

## Phase 4: User Story 2 — Attack XkY breakdown (Priority: P1)

### Tests for User Story 2

- [X] T015 [P] [US2] Add failing test `test_attack_xky_breakdown_inline`. Build deterministic combat. Assert the attack-line XkY contains `= <breakdown>` showing ring + skill + school extras + VP-on-attack effect.
- [X] T016 [P] [US2] Add failing test `test_attack_breakdown_sums_to_aggregate`. Same parsing assertion.
- [X] T017 [P] [US2] Add failing test `test_attack_breakdown_includes_school_extra_dice` for an Akodo attacker (1st Dan extra die on attack). Assert breakdown contains `1k0 Akodo 1st Dan`.

### Implementation for User Story 2

- [X] T018 [US2] Extend `DefaultRollParameterProvider.get_breakdown` to handle `kind="attack"` (mirroring `get_skill_roll_params`'s walk).
- [X] T019 [US2] Extend `CombatObserver._annotate_attack` to call `get_breakdown(..., kind="attack")` and attach `_detail_components` to the event.
- [X] T020 [US2] Extend `_format_attack_rolled` (the live attack roll, not just the damage projection) to render the inline breakdown.

**Checkpoint**: T015/T016/T017 pass. Trace-auditor reports P1 gap #2 (attack XkY) closed.

## Phase 5: User Story 3 — Bare modifier source labels (Priority: P1)

### Tests for User Story 3

- [X] T021 [P] [US3] Add failing test `test_bare_attack_modifier_has_source_label`. Build a Bayushi 5th Dan attack with the bare `+5` modifier the dry-run flagged. Assert trace contains `+5 ({source})` not just `+5`.
- [X] T022 [P] [US3] Add failing test `test_unaccounted_modifier_renders_unsourced_placeholder`. Construct a scenario where `explain_modifier` legitimately can't catalog the modifier (e.g., a mock or a deliberately-untagged source). Assert trace contains `(unsourced: +K)`.
- [X] T023 [P] [US3] Add failing test `test_partial_attribution_renders_both_known_and_unsourced`. When `explain_modifier` accounts for part of a modifier, the rendering shows both the known source(s) AND the `(unsourced: +K)` for the remainder.

### Implementation for User Story 3

- [X] T024 [US3] Replace silent suppression in `_format_modifier_breakdown` (`web/adapters/detailed_formatter.py`). When components don't sum to the modifier value, append `(unsourced: +K)` for the unaccounted portion.
- [X] T025 [US3] Audit `explain_modifier` in `web/adapters/modifier_breakdown.py`. Add case(s) for the bare-`+5` source (likely Bayushi 5th Dan double-attack bonus, confirmed via reading `simulation/schools/bayushi_school.py`). Add cases for any other missing sources the audit surfaces.

**Checkpoint**: T021/T022/T023 pass. Trace-auditor reports P1 gap #3 (bare `+5` modifier) closed.

## Phase 6: User Story 4 — TN raise attribution (Priority: P1)

### Tests for User Story 4

- [X] T026 [P] [US4] Add failing test `test_tn_raise_attribution_for_double_attack`. Force double-attack action (4 raises = +20 TN). Assert trace contains `vs TN 50 (base TN 30, +20 from 4 raises for double attack)`.
- [X] T027 [P] [US4] Add failing test `test_tn_no_raises_omits_raise_clause`. Plain attack with 0 raises. Assert trace contains `vs TN 30 (base TN 30)` without the raise clause.
- [X] T028 [P] [US4] Add failing test `test_tn_raise_attribution_for_feint`. Feint costs raises. Assert the raise clause uses `"feint"` as the action name.

### Implementation for User Story 4

- [X] T029 [US4] Extend `_format_tn` in `web/adapters/detailed_formatter.py` to render `(base TN M, +X from K raises for {action})` when `event.action.raises() > 0`. Source the raise count from `event.action.raises()` and the action name from `event.action.skill()`.

**Checkpoint**: T026/T027/T028 pass. Trace-auditor reports P1 gap #4 (TN inflation) closed.

## Phase 7: User Story 5 — VP-on-attack cross-roll attribution (Priority: P1)

### Tests for User Story 5

- [X] T030 [P] [US5] Add failing test `test_vp_on_attack_appears_in_damage_breakdown_for_bayushi`. Force a Bayushi character to spend ≥1 VP on an attack. Assert the damage line's breakdown contains `NkN VP on attack` (matching the Bayushi Special Ability's 1k1-per-VP rule).
- [X] T031 [P] [US5] Add failing test `test_no_vp_on_attack_omits_from_damage_breakdown_for_bayushi`. Bayushi attack with 0 VP spent. Damage breakdown contains NO `VP on attack` entry.
- [X] T032 [P] [US5] Add failing test `test_vp_on_attack_does_not_inflate_damage_for_non_bayushi`. Akodo attacker spending VP on attack. Assert the damage breakdown does NOT contain `VP on attack` (because the rule is Bayushi-specific per rules/04-schools.md "Bayushi Bushi School: Special Ability"; the default `get_damage_roll_params` accepts `vp` but does not use it).

### Implementation for User Story 5

- [X] T033 [US5] VERIFIED — Phase 3 (Batch 2) already implemented VP-on-attack damage attribution correctly. `DefaultRollParameterProvider.get_damage_roll_params` (simulation/mechanics/roll_params.py:354-363) accepts `vp` but does not use it — VP-on-attack does NOT inflate damage for non-Bayushi schools. `BayushiRollParameterProvider.get_damage_roll_params` (simulation/schools/bayushi_school.py:65-74) adds `vp` to both `rolled` and `kept` per the Bayushi Special Ability ("add 1k1 to the damage rolls of those attacks per void point spent"). `BayushiRollParameterProvider.get_breakdown` (simulation/schools/bayushi_school.py:76-138) renders the `("VP on attack", vp, vp)` source entry. No code changes needed — T030/T031/T032 pass as-written.
- [X] T034 [US5] VERIFIED — audited all RollParameterProvider overrides in `simulation/schools/` (Bayushi, Courtier, Isawa, Kakita, Ikoma-Bard, Mirumoto, Yogo, Kitsuki, Shosuro-Actor, Doji-Artisan). Only `BayushiRollParameterProvider.get_damage_roll_params` uses the `vp` argument to inflate damage rolled/kept. The other providers either don't override `get_damage_roll_params` at all or override it without reading `vp` (e.g., `IsawaRollParameterProvider` swaps to Water ring but ignores `vp`; `KakitaRollParameterProvider` adds +5 modifier for iaijutsu but ignores `vp`; `IkomaFourthDanRollParameterProvider` floors rolled at 10 when no extra dice but ignores `vp`; `CourtierRollParameterProvider` adds an Air-ring modifier but ignores `vp`). The Bayushi-specific behavior is correct per the rules text.

**Checkpoint**: T030/T031/T032 pass. Trace-auditor reports P1 gap #5 (VP-on-attack) closed.

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T035 [P] Re-run the trace-auditor on the calibration scenario (5th-Dan Akodo vs 5th-Dan Bayushi at seed=1234). Expected: ZERO P1 gaps.
- [X] T036 [P] Re-run the trace-auditor on a Mirumoto-vs-Hida scenario. Expected: zero NEW P1 gaps introduced; pre-existing P1s closed.
- [X] T037 [P] Re-run the trace-auditor on an Ishi-vs-Akodo scenario. Same expectation.
- [X] T038 Audit existing test files (`tests/test_mirumoto_school.py`, `tests/test_ishi_school.py`, `tests/test_akodo_school.py`, plus any general trace tests) for assertions that lock in the OLD trace strings. Update assertions to reflect new breakdowns where needed. If > 20 tests need updates, halt and flag per OPEN_QUESTIONS Q8.
- [X] T039 Update `CLAUDE.md` "New school implementation workflow" section: add `trace-auditor` to step 6's per-batch checkpoint list (peer of `rules-auditor` and `combat-simulator`).
- [X] T040 Run the full quality-gate suite:
  - `env/bin/ruff check .`
  - `env/bin/mypy`
  - `env/bin/pytest tests/ -v` (test count must be ≥ baseline + new test count, no regressions)
  - `env/bin/pytest tests/ --cov=web/adapters --cov-report=term` (coverage on affected modules ≥ 90%)
- [X] T041 Streamlit smoke check: start `env/bin/streamlit run web/app.py --server.headless true`; build a Bayushi vs Akodo combat; verify the UI shows the new breakdowns.
- [ ] T042 Squash-merge `006-trace-observability-audit` into master with a comprehensive commit message. User handles `git push` (per durable constraint).

## Dependencies

- **Phase 1 → Phase 2 → Phase 3+**: setup → foundational → user stories.
- **Phase 3 (US1) is MVP**: the user's calibration bug closes after US1 alone.
- **Phases 3–7 are mostly independent within a story** (e.g., Phase 4's attack breakdown doesn't depend on Phase 3's damage breakdown; the observer extensions are parallel).
- **Phase 8 (Polish)** depends on all prior phases.

## Parallel execution examples

Within each phase, tests are [P] (parallel). Implementation within each phase is sequential (depends on tests written first). Examples:
- T008/T009/T010 (US1 tests) — parallel.
- T015/T016/T017 (US2 tests) — parallel.
- T021/T022/T023 (US3 tests) — parallel.
- T026/T027/T028 (US4 tests) — parallel.
- T030/T031/T032 (US5 tests) — parallel.
- T035/T036/T037 (Phase 8 re-audits) — parallel.

## Implementation strategy

**MVP first**: Phase 3 alone closes the user's reported bug. Subsequent phases incrementally close the other 4 P1 gaps.

**Per workflow in CLAUDE.md**: batch tasks 3–6 per `school-implementer` invocation. After each batch, dispatch `trace-auditor` (NOT `rules-auditor` — this isn't a school) to re-validate.

**Batching plan**:
- **Batch 1**: T001–T007 (setup + foundational). Inline; no agent.
- **Batch 2**: T008–T014 (US1, damage XkY breakdown). Implementer batch. trace-auditor re-validation after.
- **Batch 3**: T015–T020 (US2, attack XkY breakdown). Implementer batch.
- **Batch 4**: T021–T025 (US3, bare modifier source labels). Implementer batch.
- **Batch 5**: T026–T029 (US4, TN raise attribution). Implementer batch.
- **Batch 6**: T030–T034 (US5, VP-on-attack cross-roll). Implementer batch.
- **Batch 7**: T035–T042 (polish + merge). Mix of inline + trace-auditor parallel runs.

Total: ~42 tasks across 8 phases. Estimated implementer effort: 5–6 `school-implementer` invocations + 3–4 `trace-auditor` runs.
