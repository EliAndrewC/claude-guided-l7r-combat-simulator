# Phase 1 Data Model: Mirumoto Bushi School

Maps the spec's six Key Entities to concrete Python classes. Each entry notes whether the class **already exists** (in the skeleton), needs **modification**, or is **new**.

## E1. `MirumotoBushiSchool` — the school class

**File**: `simulation/schools/mirumoto_school.py`
**Status**: Exists; needs modification.
**Base**: `BaseSchool` (from `simulation/schools/base.py`).

| Attribute / Method | Type | Source |
|---|---|---|
| `name()` | `str` → `"Mirumoto Bushi School"` | Existing, OK |
| `school_ring()` | `str` → `"void"` | Existing, OK |
| `school_knacks()` | `list[str]` → `["counterattack", "double attack", "iaijutsu"]` | Existing, OK |
| `extra_rolled()` | `list[str]` → `["parry", "double attack", "wound check"]` | **Fix** — currently wrong (`["attack", "double attack", "parry"]`) |
| `free_raise_skills()` | `list[str]` → `["parry"]` | Existing, OK |
| `ap_base_skill()` | `Optional[str]` → `None` | Existing, OK |
| `apply_special_ability(character)` | `None` — installs `MirumotoParryTVPListener` on parry success/failure | Existing, OK |
| `apply_rank_three_ability(character)` | `None` — installs `MirumotoNewRoundListener` and (NEW) wires the two Third Dan strategies | **Modify** — currently only installs the listener |
| `apply_rank_four_ability(character)` | `None` — ring raise + Void discount + (FIX) installs `MIRUMOTO_ACTION_FACTORY` that returns Mirumoto-attack-side subclasses | **Modify** — currently swaps in `MirumotoParryAction` on the wrong side |
| `apply_rank_five_ability(character)` | `None` — installs `MIRUMOTO_ROLL_PARAMETER_PROVIDER` | Existing, OK |

## E2. `MirumotoParryTVPListener` — the Special Ability

**File**: `simulation/schools/mirumoto_school.py`
**Status**: Exists, OK.
**Base**: `Listener` (from `simulation/listeners.py`).

| Method | Behavior |
|---|---|
| `handle(character, event, context)` | If `event` is `ParrySucceededEvent` or `ParryFailedEvent` AND the parrying character is `character`, yields `GainTemporaryVoidPointsEvent(character, 1)`. Engine's existing `GainTemporaryVoidPointsListener` increments `character._tvp`. |

**Lifecycle of granted TVP**:
- Stored on `character._tvp` (above the normal pool cap; engine spends `_tvp` before `_vp`).
- Reset to 0 only at end-of-combat (`Character.reset()` called from `EngineContext.reset()`).
- Cap-free during combat (matches Clarification Q1).

## E3. `_mirumoto_pool` — the Third Dan resource

**Location**: Plain integer attribute on `Character`, set by `MirumotoNewRoundListener`.
**Status**: Listener exists; attribute is created on first `NewRoundEvent`. No state class.

**State machine**:

| Trigger | Effect |
|---|---|
| `NewRoundEvent` for a 3rd-dan-or-higher Mirumoto | `character._mirumoto_pool = 2 * character.skill("attack")` (overwrites previous value, discarding unspent points). |
| Mode-A spend (phase-lower) | `character._mirumoto_pool -= 1` after a successful spend validation. |
| Mode-B spend (+2 after seeing roll) | `character._mirumoto_pool -= 1` after a successful spend validation. |
| `NewRoundEvent` (next round) | Re-overwritten by listener — unspent points discarded. |

**Validation rules**:
- Spend illegal if `_mirumoto_pool == 0`.
- Mode-A spend illegal if target action's phase is already 1 (cannot lower below 1) — FR-008 edge case.
- No upper bound on per-action mode-A spends (FR-009a allows stacking, capped only by phase ≥ 1).
- No upper bound on per-roll mode-B spends (FR-009a allows stacking).

## E4. `MirumotoPhaseLowerStrategy` and `MirumotoPostRollBonusStrategy` — Third Dan decision components

**File**: `simulation/strategies/mirumoto_third_dan.py` (NEW)
**Status**: New.
**Base**: Existing `Strategy` ABC from `simulation/strategies/base.py`.

### `MirumotoPhaseLowerStrategy`

```python
class MirumotoPhaseLowerStrategy(Strategy):
    """Decides how to spend Mirumoto Third Dan points on action phase-lowering.

    Invoked at start of round (and again at each NewPhaseEvent if a re-decision
    is wanted) for a character that has a populated _mirumoto_pool.
    """

    def recommend(self, character, event, context) -> Iterator[events.Event]:
        # Mode A: yield spend events for actions worth phase-lowering.
        ...
```

### `MirumotoPostRollBonusStrategy`

```python
class MirumotoPostRollBonusStrategy(Strategy):
    """Decides whether and how much to spend on +2 bonuses to a roll *after*
    the dice have resolved.

    Invoked immediately after roll resolution, before the roll's total is
    consumed by downstream logic.
    """

    def recommend(self, character, event, context) -> Iterator[events.Event]:
        # Mode B: yield spend events to bump the roll by 2 per point.
        ...
```

**Default implementations**: `EagerPhaseLowerStrategy` and `MarginalBonusStrategy` (per `research.md` R8).

**Pluggability**: Both classes are registered on the character via `character.set_strategy("mirumoto_phase_lower", ...)` and `character.set_strategy("mirumoto_post_roll_bonus", ...)` — matching the existing per-key strategy dispatch pattern.

## E5. `MirumotoActionFactory` and attack-side subclasses — Fourth Dan modifiers

**File**: `simulation/schools/mirumoto_school.py`
**Status**: Factory exists but wrong side; subclasses partly exist but wrong target.

### Replaced/added subclasses

| Subclass | Base | Override | Behavior |
|---|---|---|---|
| `MirumotoDoubleAttackAction` (NEW) | `DoubleAttackAction` | `direct_damage()` | Returns `SeriousWoundsDamageEvent` *even* when `parry_attempted()` is `True`, **if** the parry failed. (FR-012 — auto-SW lands on failed parries against this Mirumoto's double attacks.) |
| `MirumotoAttackAction` (NEW) | `AttackAction` | `calculate_extra_damage_dice(skill_roll, tn)` | When called in the "parry failed" path, halves the damage-die-count reduction (FR-013). |
| `MirumotoActionFactory` (MODIFIED) | `DefaultActionFactory` | `get_attack_action` and the double-attack equivalent | Returns the Mirumoto subclasses above for 4th-dan-or-higher Mirumoto characters. |
| `MirumotoParryAction` (REMOVE) | — | — | The skeleton's existing class modifies the wrong side. Delete or repurpose. |

**Hook diagram** (for FR-012):

```
DoubleAttackAction.direct_damage(self):
    if not self.parry_attempted():
        return SeriousWoundsDamageEvent(...)     # baseline
    return None                                  # baseline: parry attempted, no auto-SW

MirumotoDoubleAttackAction.direct_damage(self):
    if not self.parry_attempted():
        return SeriousWoundsDamageEvent(...)     # baseline
    # NEW: failed parries do not prevent the auto-SW
    if self.parries_declared() and not any(p.is_success() for p in self.parries_declared()):
        return SeriousWoundsDamageEvent(...)
    return None                                  # successful parry: as baseline (auto-SW prevented)
```

(Implementation will use the engine's actual API for "did any declared parry succeed" — to be verified during implementation.)

## E6. `MirumotoRollParameterProvider` — Fifth Dan modifier

**File**: `simulation/schools/mirumoto_school.py`
**Status**: Exists, OK.
**Base**: `DefaultRollParameterProvider` (from `simulation/mechanics/roll_params.py`).

| Override | Behavior |
|---|---|
| `get_skill_roll_params(character, target, skill, contested_skill, ring, vp)` | Calls super, then if `vp > 0` adds `5 * vp` to the modifier (yielding +10 per VP total). Returns `normalize_roll_params(...)`. |
| `get_wound_check_roll_params(character, vp)` | Calls super, then if `vp > 0` adds `5 * vp` to the modifier. |

**Provenance neutrality**: The provider operates on the `vp` integer that the engine passes in. The engine sources that `vp` from the character's total available VP (`_vp + _tvp`), so temp and normal voids are indistinguishable here. This satisfies FR-004a's "no provenance tracking" requirement.

## Entity dependency graph

```
MirumotoBushiSchool
├── installs → MirumotoParryTVPListener        (Special Ability, all dans)
├── installs → MirumotoNewRoundListener         (3rd Dan)
│       └── mutates → character._mirumoto_pool
├── wires up → MirumotoPhaseLowerStrategy       (3rd Dan, Mode A)
│       └── consumes → character._mirumoto_pool
├── wires up → MirumotoPostRollBonusStrategy    (3rd Dan, Mode B)
│       └── consumes → character._mirumoto_pool
├── installs → MIRUMOTO_ACTION_FACTORY          (4th Dan)
│       ├── returns → MirumotoAttackAction       (FR-013)
│       └── returns → MirumotoDoubleAttackAction (FR-012)
└── installs → MIRUMOTO_ROLL_PARAMETER_PROVIDER (5th Dan, FR-014)
```

## Test data model

**File**: `tests/test_mirumoto_school.py`
**Status**: Exists with several tests; will be extended (per `tests/test_akodo_school.py` as the reference pattern).

Test classes anticipated (one class per acceptance scenario cluster):

1. `TestMirumotoBushiSchoolBasics` (existing — fix `test_extra_rolled`).
2. `TestMirumotoParryTVPListener` (existing — verify success and failure paths, cap-bypass).
3. `TestMirumotoFirstDanExtraDie` (NEW — assert wound checks and double attacks roll +1 die).
4. `TestMirumotoSecondDanFreeRaise` (NEW — assert parry rolls get a free raise).
5. `TestMirumotoThirdDanPool` (NEW — pool size on round start, attack-skill-0 case, reset on next round).
6. `TestMirumotoPhaseLowerStrategy` (NEW — mode-A spends; phase-1 floor; stacking on same action).
7. `TestMirumotoPostRollBonusStrategy` (NEW — mode-B spends; stacking on same roll; declaration after roll resolution).
8. `TestMirumotoFourthDanVoidRaiseAndDiscount` (NEW — current/max +1; XP cost −5 with 0 floor).
9. `TestMirumotoFourthDanDoubleAttackAutoSW` (NEW — failed parry vs Mirumoto's double attack → auto-SW lands).
10. `TestMirumotoFourthDanRegularAttackHalving` (NEW — failed parry vs Mirumoto's regular attack → damage-die reduction halved).
11. `TestMirumotoFifthDanPlusTen` (NEW — +10 per VP on attack, parry, wound check; +10 does NOT apply to non-combat rolls; per-VP stacking via Edge Cases).
12. `TestMirumotoFifthDanWithTempVP` (NEW — +10 applies when spending a temporary VP — FR-004a interaction).
