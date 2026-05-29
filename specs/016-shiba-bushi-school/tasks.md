# Tasks: Shiba Bushi School

**Branch**: `016-shiba-bushi-school`

All tasks are TDD-first. Quality gates after every batch.

## Batch A — Rules-fidelity BLOCKING fixes

### T-A1: Fix `ShibaParryAction.roll_parry` dead-code bug
- **File**: `simulation/schools/shiba_school.py::ShibaParryAction`
- **Failing test first**: an end-to-end engine test where Shiba parries an attack against an ally; assert the parry roll does NOT include the `-5 * attacker.skill("attack")` penalty.
- **Fix**: rename `roll_parry` → `roll_skill` (the method the engine actually calls), OR override `roll_skill` to skip the parry-other penalty.

### T-A2: Fix Q3 3rd Dan normalization
- **File**: `simulation/schools/shiba_school.py::ShibaTakeParryEvent._roll_damage`
- **Failing test first**: a Shiba with `attack = 6` (rolled=12) should produce a normalized 10k3 (10 rolled, 3 kept) damage roll, NOT a raw 12k1.
- **Fix**: pass `(2*attack_skill, 1, 0)` through `normalize_roll_params`; apply the resulting `(rolled, kept, bonus)` consistently.

## Batch B — Identity bindings (Q1+Q2)

### T-B1: Implement `ShibaInterruptParryStrategy`
- **File**: new class in `simulation/schools/shiba_school.py`
- **Failing tests first**:
  1. Fires on `AttackRolledEvent` targeting Shiba (yields `SpendActionEvent` + `take_parry_action_event`).
  2. Fires on `AttackRolledEvent` targeting adjacent ally (parry-other clause).
  3. **Lowest-die selection**: with `actions = [2, 7]`, the interrupt consumes die `2`, NOT `7`.
  4. Declines when `parry skill == 0`.
  5. Declines when no interrupt action available (`has_interrupt_action` returns False).
  6. Declines at SW-saturation (`sw_remaining ≤ 1`).
  7. Declines when attack already parried.

### T-B2: Wire bindings in `apply_special_ability`
- **File**: `simulation/schools/shiba_school.py::ShibaBushiSchool.apply_special_ability`
- **Failing test first**: after `apply_special_ability(character)`, character's interrupt strategy is `ShibaInterruptParryStrategy` and wound_check strategy is `WoundCheckStrategy04`.

## Batch C — Trace observability

### T-C1: 3rd Dan parry damage source attribution (P0)
- **Files**: `simulation/schools/shiba_school.py`, `web/adapters/trace_entries.py`, `web/adapters/detailed_formatter.py`, `web/adapters/text_renderer.py`, `web/adapters/bulleted_renderer.py`
- **Failing test first**: a `LightWoundsDamageEvent` emitted by `ShibaTakeParryEvent._roll_damage` MUST surface with "Shiba 3rd Dan parry damage (2 × attack skill = N rolled / 1 kept)" attribution.
- **Fix**: tag the event with `_from_shiba_3rd_dan = True`; surface via new field on `LightWoundsDamageEntry` + renderer suffix.

### T-C2: 5th Dan TN modifier trace label (P0)
- **Failing test first**: a successful parry that adds a `tn to hit` modifier MUST produce a labeled trace line "Shiba 5th Dan: lowers Akodo's TN to hit by N (parry margin, expires after next attack)".
- **Fix**: tag the `AddModifierEvent` (or modifier itself) with `_source = "Shiba 5th Dan"`; add an `AddModifierEvent` entry type if needed (or extend an existing one).

## Batch D — Playability + win-feasibility

### T-D1: `tests/test_shiba_school_playability.py`
- Mirror non-degeneracy + win-feasibility vs Akodo + Q1 identity-engine firing.

### T-D2: `tests/test_shiba_school_strategy.py`
- Unit tests for `ShibaInterruptParryStrategy` decline paths.

## Batch E — Coverage + final gates

### T-E1: Drive `shiba_school.py` to 100%.
### T-E2: Streamlit smoke.
### T-E3: BACKLOG.md update.

## Execution order

A1 → A2 → B1 → B2 → D2 → D1 → C1 → C2 → E1 → E2 → E3
