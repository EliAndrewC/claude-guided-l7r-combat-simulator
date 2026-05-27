---
description: "Task list for Action-Level Damage Breakdown"
---

# Tasks: Action-Level Damage Breakdown

**Input**: `/specs/009-action-damage-breakdown/`

## Phase 1: Setup

- [X] T001 Verify branch `010-action-damage-breakdown`, working tree clean.
- [X] T002 Capture pre-fix calibration trace at `/tmp/pre_fix_trace.txt` for diff comparison.
- [X] T003 Baseline: `env/bin/pytest tests/ -q` — expected 3773 PASS.

## Phase 2: Action-side accessor

- [X] T004 Add `AttackAction.damage_breakdown(self) -> list[tuple[str, int, int]]` default method to `simulation/actions.py`. Default body delegates to `self.subject().roll_parameter_provider().get_breakdown(kind="damage", ...)` with the same arguments the formatter currently uses. Preserves existing behavior for any AttackAction subclass that doesn't override.
- [X] T005 Override `FeintAction.damage_breakdown(self) -> list[tuple[str, int, int]]` to return `[]`.
- [X] T006 Override `BayushiFeintAction.damage_breakdown(self) -> list[tuple[str, int, int]]` in `simulation/schools/bayushi_school.py`. Returns the per-source contributions matching `damage_roll_params()`: `("attack skill", attack_skill, 0)` + `("base feint kept die", 0, 1)` + optional `("VP on feint", vp, vp)`.
- [X] T007 Write unit tests `tests/test_action_damage_breakdown.py` (~10 tests): default behavior, FeintAction empty list, BayushiFeintAction without VP, with VP, with different attack skills, etc.

## Phase 3: Formatter call-site migrations

- [X] T008 Migrate `web/adapters/detailed_formatter.py` attack-line damage projection (line ~878): use `action.damage_roll_params()` for the XkY total AND `action.damage_breakdown()` for the components. Replace the `subject.get_damage_roll_params(...)` + `_compute_damage_breakdown(subject, target, action, extra)` calls.
- [X] T009 Migrate LightWoundsDamageEntry production (line ~1002): same pattern.
- [X] T010 Migrate counterattack damage projection (line ~1119): same pattern.
- [X] T011 Run full suite. Update existing trace tests that broke because of Bayushi feint trace changes. Expected: ≤ 5 updates.
- [X] T012 Capture post-fix calibration trace. Diff against pre-fix; verify the only changes are on Bayushi feint lines (projection 9k2 → 5k1, breakdown katana+Fire+reconciliation → attack skill+base feint kept die).

## Phase 4: Polish + merge

- [X] T013 Dispatch `trace-reader` on the calibration combat. Expected: zero `projection-vs-actual mismatch` issues for Bayushi feints.
- [X] T014 Run final gates: ruff PASS, mypy PASS, pytest PASS, coverage 100%.
- [ ] T015 Squash-merge `010-action-damage-breakdown` to master. User handles push.

## Implementation strategy

Single implementer batch covers T004-T012. Polish phase T013-T015 inline.

Total: ~15 tasks across 4 phases. Estimated 1 implementer invocation + ~30 min inline polish/merge.
