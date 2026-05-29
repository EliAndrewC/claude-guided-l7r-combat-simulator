# Tasks: Otaku Bushi School

**Branch**: `015-otaku-bushi-school`
**Specs**: [spec.md](spec.md), [plan.md](plan.md), [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

All tasks are TDD-first. Quality gates (`ruff` + `mypy` + `pytest --cov` with `fail_under=100`) run after every batch.

## Batch A — Rules-fidelity BLOCKING fixes

### T-A1: Fix Q2 3rd Dan "next X action dice"
- **File**: `simulation/schools/otaku_school.py::OtakuLightWoundsDamageListener.handle`
- **Failing test first** in `tests/test_otaku_school.py`: a 5-action-die target whose Otaku attacker has `skill("attack") == 3` should have ONLY the first 3 dice modified, not all 5.
- **Fix**: sort `actions`, iterate `range(min(character.skill("attack"), len(actions)))`, cap each die at 10, re-sort.
- **Coverage**: cover the empty-actions branch + the `attack_skill > len(actions)` branch.

### T-A2: Fix Q4 5th Dan dice math + min-2 floor
- **File**: `simulation/schools/otaku_school.py::OtakuFifthDanTakeAttackActionEvent._roll_damage`
- **Failing test first**: a damage roll with raw_rolled = 14 (ring=6, weapon=4, my_extra_rolled=0, extras=4) should produce 4 rolled dice after the trade, with attributed components (NOT `-Nk-M reconciliation`).
- **Fix**:
  ```python
  target_rolled = max(2, raw_rolled - 10)
  effective_extra = target_rolled - (ring + weapon.rolled() + my_extra_rolled)
  # Clamp kept if necessary so kept <= rolled.
  ```
  Pass an explicit breakdown override label to `roll_damage` so the trade surfaces as `"Otaku 5th Dan trade: -10 rolled dice"` instead of `"reconciliation"`.
- **Edge cases**: raw_rolled < 12 (should not fire — see T-A3), raw_rolled == 2 (already at floor), raw_rolled = 30 (still floored at 2 after trade).

### T-A3: Add 5th Dan strategic choice (Q3)
- **File**: `simulation/schools/otaku_school.py::OtakuFifthDanTakeAttackActionEvent._should_trade`
- **Failing test first**: a low-WC target should NOT trigger the trade (expected SW from rolling >= 1); a high-WC target SHOULD trigger it.
- **Fix**: pragmatic heuristic — fire when `raw_rolled >= 12 AND expected_lw_from_rolling < target.wc_tolerable_lw()`. If a clean expected-value calc is hard, fall back to `raw_rolled >= 20` (threshold derived from combat-simulator's observed 5-13 fires/combat being too aggressive).
- Document the chosen heuristic inline.

## Batch B — Identity bindings (Q1)

### T-B1: Implement `OtakuInterruptLungeStrategy`
- **File**: new class in `simulation/schools/otaku_school.py`
- **Failing tests first**: per strategy-designer recommendations §5 (1–5):
  1. Fires on `AttackSucceededEvent` targeting Otaku, yields lunge interrupt action.
  2. Fires on `AttackFailedEvent` targeting Otaku (post-resolution trigger).
  3. **Mirror-recursion gate**: declines when incoming attack `skill() == "lunge"` AND `initiative_action().is_interrupt() == True`.
  4. **SW-saturation gate**: declines when `character.sw_remaining() <= 1`.
  5. Declines when `has_interrupt_action("lunge", context)` returns False.
- **Implementation**: subclass `Strategy`; reuses existing `take_action_event_factory()` so 4th Dan's `OtakuLungeAction` still applies.

### T-B2: Wire bindings in `apply_special_ability`
- **File**: `simulation/schools/otaku_school.py::OtakuBushiSchool.apply_special_ability`
- **Failing test first**: after `apply_special_ability(character)`, character's interrupt strategy is `OtakuInterruptLungeStrategy` and wound_check strategy is `WoundCheckStrategy04`.
- **Fix**: add `character.set_strategy("interrupt", OtakuInterruptLungeStrategy())` and `character.set_strategy("wound_check", WoundCheckStrategy04())`.

## Batch C — Trace observability (Q6, Principle VII)

### T-C1: 3rd Dan action-die shift entry (P0)
- **Files**: `simulation/schools/otaku_school.py`, `web/adapters/trace_entries.py`, `web/adapters/detailed_formatter.py`, `web/adapters/text_renderer.py`, `web/adapters/bulleted_renderer.py`
- **Failing test first**: scripted combat where 3rd Dan listener fires; assert trace surfaces `"Otaku 3rd Dan: shifted next X action dice +N (6 − target Fire min 1)"` with X and N populated.
- **Fix**: emit `OtakuThirdDanShiftEvent(target, dice_shifted, increase)` from the listener; add corresponding entry type + formatter clauses in both renderers.

### T-C2: 5th Dan dice-trade label + SW attribution (P0)
- **Files**: same trio as T-C1
- **Failing tests first**:
  - The SW emitted by `OtakuFifthDanTakeAttackActionEvent` MUST surface with `"Otaku 5th Dan dice trade"` source attribution (not bare "takes 1 serious wound").
  - The damage roll's rolled-dice reduction MUST surface labeled "Otaku 5th Dan trade: -10 rolled dice", NOT generic "reconciliation".
- **Fix**: mark `SeriousWoundsDamageEvent` with `_from_otaku_5th_dan = True`; surface in `_entry_sw_damage`. Pass explicit breakdown override to `roll_damage`.

### T-C3: 4th Dan parry-still-+1 attribution (P1)
- **Files**: `simulation/schools/otaku_school.py`, `web/adapters/modifier_breakdown.py`
- **Failing test first**: a parried Otaku lunge whose damage shows the +1 die MUST surface "Otaku 4th Dan: +1 lunge die (parried carve-out)".
- **Fix**: tag the action with `_otaku_4th_dan_parried_lunge_bonus = 1` when the branch fires; surface in `explain_modifier`.

### T-C4: Special Ability interrupt-lunge attribution (P1)
- **Files**: `simulation/schools/otaku_school.py`
- **Failing test first**: when `OtakuInterruptLungeStrategy` fires, the resulting attack event MUST surface "Otaku Special Ability: interrupt-lunge after attack resolved".
- **Fix**: tag the action with `_otaku_special_ability_interrupt = True`; surface via existing interrupt-action rendering path.

## Batch D — Playability + win-feasibility

### T-D1: `tests/test_otaku_school_playability.py`
- **Failing test first**: mirror non-degeneracy — 5 seeded mirrors at 300 XP, 18-round cap (`_CappedCombatEngine` pattern). All terminate via defeat. At least one interrupt-lunge fires per match.
- **Failing test first**: win-feasibility vs Akodo 450 — 20 seeds, Otaku ≥ 35% win rate.
- Add fail-fast assertion that combat-simulator's "0 interrupt-lunges" pre-fix observation is no longer true.

### T-D2: `tests/test_otaku_school_strategy.py`
- Unit tests for `OtakuInterruptLungeStrategy` decline paths (mirror-recursion gate, SW-saturation gate, no-future-action-die gate, target-not-Otaku gate).

## Batch E — Coverage + final gates

### T-E1: Drive `otaku_school.py` to 100% coverage
- Cover any uncovered branches (likely the edge cases in T-A2 + T-A3 + T-B1 declines).
- Allowed pragmas: defensive type guards (e.g., `# pragma: no cover` on `assert isinstance(...)` lines that can't fail under engine invariants).

### T-E2: Streamlit smoke
- `env/bin/streamlit run web/app.py --server.headless true` in background; verify "You can now view" appears.

### T-E3: BACKLOG.md update
- Move Otaku from "Skeleton present" to "Validated via speckit workflow".
- Document the two deferrals: `OTAKU_PRIORITIES` revision + (potentially) the base `LungeAction.calculate_extra_damage_dice` redundancy flagged by rules-auditor.

## Execution order

A1 → A2 → A3 → B1 → B2 → C1 → C2 → C3 → C4 → D1 → D2 → E1 → E2 → E3

Batches A+B can interleave; C depends on A+B for the test triggers; D depends on B; E is last.
