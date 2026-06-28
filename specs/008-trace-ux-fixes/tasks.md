---
description: "Task list for Combat Trace UX Fixes"
---

# Tasks: Combat Trace UX Fixes

**Input**: `/specs/008-trace-ux-fixes/`

## Phase 1: Setup

- [X] T001 Verified branch `009-trace-ux-fixes`, working tree clean.
- [X] T002 Pre-fix calibration trace captured at `/tmp/pre_fix_trace.txt`.
- [X] T003 Baseline confirmed: 3739 tests PASS.

## Phase 2: Foundational — shared helper

- [X] T004 Write `/simulator/web/adapters/_breakdown_format.py`. Implements `format_breakdown_component(rolled: int, kept: int, source: str) -> str` per data-model.md.
- [X] T005 Write `/simulator/tests/test_breakdown_format.py` covering the helper at 100% (FR-018): standard NkM case, 10k10-overflow case with negative-rolled, 10k10-overflow with negative-kept, both-negative, dropped=1 singular noun, source-mismatch fallback to standard form. ~10 tests.

## Phase 3: Issue 1 — Cross-renderer consistency

- [X] T006 Migrate `text_renderer.py::_format_one_component` to delegate to the shared helper. Remove the duplicated special-case logic.
- [X] T007 Migrate `detailed_formatter.py::_format_one_component` to delegate to the shared helper. Remove its duplicated logic.
- [X] T008 Migrate `bulleted_renderer.py::_format_component_bullet` to delegate to the shared helper. The bullet wrapping (`- {content}`) stays in BulletedRenderer; the inner content comes from the helper.
- [X] T009 Audit BulletedRenderer's `_render_attack` (and `_render_lw_damage`) for any code path that builds component bullets WITHOUT going through `_format_component_bullet`. The damage-projection sub-bullets are the likely culprit per research.md. Route them through the helper.
- [X] T010 Write `tests/test_cross_renderer_consistency.py` — runs the calibration combat through both renderers, parses each multi-source aggregate's component breakdown, asserts the rendering of the 10k10-overflow component is identical across renderers (FR-004). ~5 tests.
- [X] T011 Run full suite. Update any existing tests that broke because of BulletedRenderer's old-form output. Expected: 2-4 test updates per research.md. (No regressions; all 3754 tests pass.)

## Phase 4: Issues 2/4/6 — Feint damage suppression

- [X] T012 In `detailed_formatter.py::entries()`, detect feint attacks with 0-LW-dealt damage events. When detected, set `AttackEntry.suppress_damage_projection = True` and DO NOT emit a `LightWoundsDamageEntry` for the matching damage event. (Predicate refined: feint AND ``damage_roll_params == (0,0,0)`` — Bayushi's special feint has non-zero damage params and renders normally.)
- [X] T013 In TextRenderer and BulletedRenderer's attack-rendering, honor `suppress_damage_projection` — omit the `damage will be: XkY` segment when the flag is set.
- [X] T014 Write tests: `tests/test_feint_damage_suppression.py` — 7 tests covering Akodo (zero-damage feint) suppression, Bayushi (non-zero feint) preservation, school-ability events still appear, and non-feint attacks unaffected.
- [X] T015 Run full suite. No regressions — all 3761 tests pass.

## Phase 5: Issue 3 — Floating-bonus inline integration

- [X] T016 In `detailed_formatter.py::entries()`, detect `SpendFloatingBonusEvent` PRECEDING an attack's `AttackRolledEvent` (engine actually yields the consumption BEFORE re-yielding the rolled event from ``SkillRolledStrategy.recommend``). Attached to `AttackEntry.consumed_floating_bonuses`; the standalone event is consumed.
- [X] T017 In TextRenderer's `_render_attack`, integrate the consumed_floating_bonuses into the inline arithmetic via `_build_roll_str`: `"→ kept_sum, +bonus1 (source1 floating bonus) = total vs TN N — outcome"` (or multiple bonuses).
- [X] T018 In BulletedRenderer's `_render_attack`, integrate via a new `_floating_bonus_inline_segment` helper on the header line.
- [X] T019 Write `tests/test_floating_bonus_inline.py` — 6 tests covering both renderers, multi-bonus consumption, bonus-adjusted-total reconciliation, and the absence of standalone consumption lines.
- [X] T020 Run full suite. No regressions — all 3767 tests pass.

## Phase 6: Issue 5 — "unsourced" literal + workflow update

- [X] T021 Investigated: the `+5 (unsourced)` in the calibration combat IS the Akodo 4th Dan VP-on-WC modifier (the strategy folds `5*VP` into the WC roll, which appears as a residual modifier after the 2nd Dan free raise).
- [X] T022 Added the Akodo 4th Dan VP-raises case to `explain_modifier`. Verified: the calibration trace's line 14 now reads `Akodo 4th Dan VP raises: +5` instead of `unsourced: +5`.
- [X] T023 Updated `_format_modifier_breakdown` (TextRenderer) and `_modifier_bullets` (BulletedRenderer) to use the fallback `(see preceding line)` for unattributed remainders.
- [X] T024 Wrote `tests/test_unsourced_literal_absence.py` (4 tests). Both renderers verified to produce zero `\bunsourced\b` matches on the calibration combat.
- [X] T025 Updated CLAUDE.md step 6 to add `trace-reader` to the per-batch checkpoint list, with a note that it complements `trace-auditor`.

## Phase 7: Polish + merge

- [X] T026 Re-ran the calibration combat post-fix. All four issues confirmed fixed: 11 narrative overflow segments (Issue 1), 0 `takes 0 light wounds` lines (Issue 2/4/6), 0 standalone `floating bonus consumed` lines and 3 inline integrations (Issue 3), 0 `unsourced` literal matches (Issue 5).
- [X] T027 Final gates: `ruff` PASS, `mypy` PASS strict, `pytest` 3773 PASS, coverage 100% (was 99% on `text_renderer.py` mid-implementation because spec 005 helper-shifting changed line numbers; covered the empty-dice path explicitly in the new `test_breakdown_format.py`).
- [ ] T028 Squash-merge `009-trace-ux-fixes` to master. User handles `git push` (per durable constraint).

## Implementation strategy

**Batching**:
- Batch 1 (inline): T001-T003 (setup + baseline capture).
- Batch 2 (implementer): T004-T011 (shared helper + Issue 1).
- Batch 3 (implementer): T012-T015 (feint damage suppression).
- Batch 4 (implementer): T016-T025 (floating-bonus inline + "unsourced" + workflow update).
- Batch 5 (inline): T026-T028 (trace-reader re-validation + merge).

Total: ~28 tasks across 7 phases. Estimated 3-4 implementer invocations.
