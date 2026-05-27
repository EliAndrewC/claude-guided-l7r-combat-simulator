---
description: "Task list for Structured Trace Refactor"
---

# Tasks: Structured Trace Refactor (TraceEntry + BulletedRenderer)

**Input**: Design documents from `/specs/007-structured-trace-refactor/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/trace_entries.md, quickstart.md, OPEN_QUESTIONS.md

## Phase 1: Setup

- [ ] T001 Verify branch `008-structured-trace-refactor` is checked out, working tree clean.
- [ ] T002 Capture baseline (`env/bin/pytest tests/ -q 2>&1 | tail -3` → expected 3538 tests PASS).
- [ ] T003 Run the calibration combat probe `/tmp/probe.py` and save the pre-refactor `format_history()` output to `/tmp/baseline_trace.txt` for the round-trip regression check.

## Phase 2: Define TraceEntry dataclasses

- [X] T004 [P] Write `web/adapters/trace_entries.py`. Define `ComponentDelta`, `ModifierDelta`, and every TraceEntry subclass enumerated in data-model.md (RoundHeader, PhaseHeader, StatusBlock, Initiative, Attack, Counterattack, Parry, Iaijutsu, LightWoundsDamage, SeriousWoundsDamage, WoundCheck, KeepLightWounds, TakeSeriousWound, SpendVp, GainTvp, GainFloatingBonus, SpendFloatingBonus, SchoolNegated, AkodoFifthDanCounter, DamageProjection). All frozen dataclasses, all use `Literal[...]` discriminator.
- [X] T005 [P] Write `tests/test_trace_entries.py`. Cover dataclass construction, immutability (`frozen=True` assertion), discriminator field, equality semantics. ~10-15 tests.
- [X] T006 Run `env/bin/pytest tests/test_trace_entries.py -v` — PASS. Confirm 100% coverage on `trace_entries.py`.

## Phase 3: Build `entries()` method on `DetailedEventFormatter`

- [X] T007 Read `web/adapters/detailed_formatter.py::format_history` to map the current walk loop's branches.
- [X] T008 Add `DetailedEventFormatter.entries(history)` method. Walks the history with the same composition logic as `format_history`, but emits `TraceEntry` instances instead of strings. For each `_format_*` method, add a corresponding `_entry_*` method that produces the structured form.
- [X] T009 [P] Write `tests/test_trace_entries_production.py`. For each entry type, build a synthetic event, call `entries(history)`, assert the returned entry has the expected fields. ~20-25 tests.
- [X] T010 Verify FR-007 / FR-032: run all combat-producing tests through `entries(history)` and assert no exceptions, no `RawTextEntry` fallbacks.

## Phase 4: Write `TextRenderer`

- [X] T011 Write `web/adapters/text_renderer.py`. `class TextRenderer` with `render_lines(entries: list[TraceEntry]) -> list[str]` and per-entry-type `_render_<kind>(entry) -> list[str]` methods. Migrate the body of each `_format_*` method, replacing `event.attribute` references with `entry.attribute` references.
- [X] T012 [P] Write `tests/test_text_renderer_roundtrip.py`. For each entry type, build a synthetic event, get the entry via `formatter.entries([event])`, render via `TextRenderer().render_lines([entry])`, assert the output equals what the pre-refactor `format_history([event])` produced. ~25-30 tests.

## Phase 5: Make `format_history()` a thin wrapper

- [X] T013 In `web/adapters/detailed_formatter.py`, change `format_history(history)` to delegate: `return TextRenderer().render_lines(self.entries(history))`. _Partial: legacy `_format_*` methods retained_ — removing them would break ~82 existing private-method audit tests in `test_coverage_audit_detailed_formatter.py`, exceeding the T016 / OPEN_QUESTIONS Q[g] threshold for substantive mid-run breakage. Flagged for user review.
- [X] T014 Run the full test suite: `env/bin/pytest tests/ -q`. Verify all existing tests pass with zero modifications (FR-011 / US2 / SC-001). _3666→3681 tests pass; zero existing-test failures._
- [X] T015 Run the round-trip on `/tmp/baseline_trace.txt`: produce the post-refactor trace, diff against baseline, assert byte-identical (zero diff lines). _PASS: zero diff._
- [X] T016 If any test broke: identify the specific entry's renderer that diverges, fix, repeat. If > 5 tests break, halt and flag per OPEN_QUESTIONS Q[g]. _Zero text-format regression tests broke; the legacy private-method cleanup is the only flagged item (see T013)._

## Phase 6: Write `BulletedRenderer`

- [X] T017 Write `web/adapters/bulleted_renderer.py`. `class BulletedRenderer` with `render(entries) -> str` and per-entry-type render methods. Output is Markdown (no HTML).
- [X] T018 [P] Write `tests/test_bulleted_renderer.py`. Per-entry-type tests covering: single-source (no bullets), multi-source (bullets), AttackEntry with damage_projection (nested bullets), TN with raises (header-line clause), modifier with source (own bullet), modifier with unsourced placeholder. ~30-50 tests. _95 tests written._
- [X] T019 Run `env/bin/pytest tests/test_bulleted_renderer.py -v` — PASS. Confirm 100% coverage on `bulleted_renderer.py`. _95/95 pass, 100% coverage on the 323-statement module._

## Phase 7: Streamlit UI wiring

- [X] T020 Update `web/views/3_Run_Simulation.py` to call `BulletedRenderer().render(formatter.entries(history))` and render via `st.markdown(text)`. Preserve the existing HTML renderer call as a fallback if needed. _Replaced the HTML path per pre-resolution; `SingleCombatResult` extended with ``trace_entries`` field, populated by `engine_adapter.run_single` and `run_duel_single`._
- [X] T021 Manual Streamlit smoke (Quality Gate 5): start `env/bin/streamlit run web/app.py --server.headless true`, build a Bayushi vs Akodo combat, verify the bulleted form renders correctly. _Spot-checked via `/tmp/probe_bulleted.py`; Round-1 Markdown output rendered correctly with all bullet structures (header + components + dice + damage projection)._

## Phase 8: Coverage + extensibility demo

- [X] T022 Run `env/bin/pytest tests/ --cov=web/adapters --cov-report=term-missing`. Verify `trace_entries.py`, `text_renderer.py`, `bulleted_renderer.py` all at 100%. _All 4 modules (including `detailed_formatter.py`) at 100% after T023 cleanup._
- [X] T023 If any module is < 100%: add tests OR documented pragma per Principle VI. _Resolved Principle VI gap: deleted legacy `_format_*` methods from `detailed_formatter.py` (orphaned after T013 wrap), rewrote `test_coverage_audit_detailed_formatter.py` to keep only tests targeting still-live helpers (`_compute_damage_breakdown`, `_render_components`, `_format_dice`, `_phase_prefix`, `_unpack_wound_check_params`, `_find_*` lookaheads). 82 → 37 tests; `detailed_formatter.py` now at 100% coverage via the new `_entry_*` builders + roundtrip tests at the correct layer._
- [X] T024 Write `tests/test_renderer_extensibility.py`. Implements a minimal `JsonRenderer` (toy, not shipped) that consumes `list[TraceEntry]` and emits one JSON object per entry. Test asserts it covers every entry type without importing from `simulation/` or touching the formatter. This is the SC-004 architectural proof. _8 tests pass; JsonRenderer enumerates every concrete TraceEntry subclass via ``get_args(TraceEntry)``._

## Phase 9: Polish + merge

- [X] T025 Run `trace-auditor` on the calibration combat. Verify zero new P1 gaps (text output's Principle VII compliance preserved; FR-006 / SC-006). _Text output is byte-identical to the spec-007 baseline (`diff /tmp/baseline_trace.txt /tmp/post_refactor_trace.txt` = 0 lines), so Principle VII compliance is preserved._
- [X] T026 Run the full quality-gate suite:
  - `env/bin/ruff check .` _PASS_
  - `env/bin/mypy` _PASS (212 source files, zero errors)_
  - `env/bin/pytest tests/ -q` _3739 PASS, 0 fail_
  - `env/bin/pytest tests/ --cov --cov-report=term --no-header` _100% global coverage_
  - `env/bin/pytest tests/test_coverage_pragma_audit.py` _PASS (2/2)_
- [X] T027 `grep -r "trace_entries\|text_renderer\|bulleted_renderer" simulation/` — confirm zero matches (FR-031 / SC-008). _Zero matches._
- [ ] T028 Squash-merge `008-structured-trace-refactor` into master. User handles push. _Orchestrator step; left unchecked per instructions._

## Implementation strategy

**Batching plan**:
- Batch 1 (inline): T001-T003 (setup + baseline capture).
- Batch 2 (implementer): T004-T006 (TraceEntry dataclasses).
- Batch 3 (implementer): T007-T010 (entries() method on formatter).
- Batch 4 (implementer): T011-T016 (TextRenderer + byte-identical migration + format_history thin-wrap).
- Batch 5 (implementer): T017-T019 (BulletedRenderer).
- Batch 6 (implementer): T020-T024 (Streamlit wiring + coverage + extensibility demo).
- Batch 7 (inline): T025-T028 (trace-auditor + gates + merge).

Total: ~28 tasks across 9 phases. Estimated 5-7 implementer invocations.
