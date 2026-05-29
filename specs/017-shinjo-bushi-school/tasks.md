# Tasks: Shinjo Bushi School

**Branch**: `017-shinjo-bushi-school`

All tasks are TDD-first. Quality gates after every batch.

## Batch A — Rules-fidelity BLOCKING fixes

### T-A1: Fix Q1 — `extra_rolled()` returns correct skill list
- **Failing test first**: `school.extra_rolled() == ["initiative", "parry", "wound check"]`.
- **Fix**: replace skeleton's `["double attack", "initiative", "parry"]` with the rules-text list.

### T-A2: Fix 4th Dan tie handling
- **Failing test first**: with initial actions `[2, 3, 5, 5]`, after `ShinjoNewRoundListener.handle`, the result is `[1, 1, 2, 3]` (all tied max dice set to 1) — NOT `[1, 2, 3, 5]`.
- **Fix**: replace `actions.index(max(actions))` with a loop that reduces all dice tied at max.

### T-A3: Wire Q4 — Special Ability bonus consumption (BLOCKING IDENTITY)
- **Failing test first**: spending a held die produces an `AddModifierEvent` for the Shinjo with adjustment = `2 * (current_phase - original_die_value)` on ATTACK_SKILLS.
- **Fix**: `ShinjoSpendActionListener.handle` yields an `AddModifierEvent` with `Modifier(character, None, ATTACK_SKILLS, +2X)` paired with `ExpireAfterNextAttackByCharacterListener` (Daidoji precedent). Remove the dead `character._shinjo_hold_bonus = bonus` write and the redundant `character.spend_action(...)` call (engine's default `SpendActionListener` already handles that; verify via testing).
- **Existing-test update**: the 4 `TestShinjoSpendActionListener` tests assert on `_shinjo_hold_bonus` (the dead attribute). Rewrite them to assert on the yielded `AddModifierEvent`.

## Batch B — Identity bindings

### T-B1: Wire default strategies in `apply_special_ability`
- **Failing test first**: after `apply_special_ability(character)`:
  - action strategy is `HoldOneActionStrategy`
  - wound_check strategy is `WoundCheckStrategy04`
- **Failing test first**: after `apply_rank_one_ability` (or wherever appropriate), parry strategy is `AlwaysParryStrategy`.

## Batch C — Trace observability + Q3 refactor

### T-C1: 5th Dan listener subclasses 3rd Dan
- Refactor `ShinjoFifthDanParryListener` to subclass `ShinjoParryListener`, calling super for the 3rd Dan effect.

### T-C2: Special Ability modifier source label
- The `AddModifierEvent` from T-A3 should carry a source-attribution tag for trace observability — defer renderer-side surfacing per Otaku/Shiba precedent if it requires broader trace infrastructure, but at minimum tag the modifier with `_shinjo_special_ability = True` so future trace work can surface it.

## Batch D — Playability

### T-D1: `tests/test_shinjo_school_playability.py`
- Mirror non-degeneracy at 300 XP (5 seeds, 18-round cap).
- Identity-engine firing: hold-bonus modifier appears at least once across a 10-seed sweep vs Akodo.

### T-D2: `tests/test_shinjo_school_strategy.py` if any new strategy classes added (TBD — probably not since we reuse `HoldOneActionStrategy` etc).

## Batch E — Coverage + final gates

### T-E1: Drive `shinjo_school.py` to 100%.
### T-E2: Streamlit smoke.
### T-E3: BACKLOG.md update.

## Execution order

A1 → A2 → A3 → B1 → C1 → D1 → E1 → E2 → E3
