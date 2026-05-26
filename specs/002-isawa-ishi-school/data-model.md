# Phase 1 Data Model: Isawa Ishi School

Maps the spec's seven Key Entities to concrete Python classes. Each entry notes status: **exists & OK**, **exists & needs fixes**, or **NEW**.

## E1. `IsawaIshiSchool`

**File**: `simulation/schools/ishi_school.py`
**Status**: Exists with bugs.

| Method | Type | Status |
|---|---|---|
| `name()` → `"Isawa Ishi School"` | `str` | OK |
| `school_ring()` → `"void"` | `str` | OK |
| `school_knacks()` → `["absorb void", "kharmic spin", "otherworldliness"]` | `list[str]` | OK |
| `extra_rolled()` → `["precepts", "wound check", "initiative"]` | `list[str]` | OK per Q1 |
| `free_raise_skills()` → `["attack"]` → **CHANGE to** `["precepts"]` | `list[str]` | FIX per Q2 |
| `ap_base_skill()` → `None` | `Optional[str]` | OK |
| `apply_special_ability(character)` | install VP provider + `PlainAttackStrategy` (NEW per R3) | EXTEND |
| `apply_rank_three_ability(character)` | install rewritten `IshiAllyBoostListener` + new `IshiAllyBoostStrategy` on `"ishi_ally_boost"` slot | REWRITE |
| `apply_rank_four_ability(character)` | ring raise + discount | OK |
| `apply_rank_five_ability(character)` | install `IshiYourMoveListener` + `EagerNegationStrategy` on `"ishi_negate_school"` slot | IMPLEMENT |
| `vp_provider()` | accessor | OK |

## E2. `IshiMaxVPProvider`

**File**: `simulation/schools/ishi_school.py`
**Status**: Exists & OK.

| Method | Behavior |
|---|---|
| `max_vp(character)` | `highest_ring + school_rank` (Special Ability) |
| `max_vp_per_roll(character)` | `max(0, lowest_ring - 1)` |
| `set_school_rank(rank)` | rank-tracking setter (called by school's per-rank methods) |

## E3. `IshiAllyBoostListener` (rewritten)

**File**: `simulation/schools/ishi_school.py`
**Status**: Exists but buggy — rewrite.

| Aspect | Old (buggy) | New |
|---|---|---|
| Installed on slot | `"attack_rolled"` (overrides default) | Multiple slots: `"attack_rolled"`, `"parry_rolled"`, `"counterattack_rolled"`, `"wound_check_rolled"`, ... — OR a single generic post-roll subscriber if the engine supports it (TBD by implementer). Chain WITH the default; don't override. |
| Event scope | `AttackRolledEvent` only | All combat-relevant `*RolledEvent` types |
| Target scope | In-group + adjacent ally | In-group ally (no adjacency check) per Q3 |
| Once-per-roll guard | None | Yes — attach `_ishi_boosted_by` to the action object |
| Spend decision | Hardcoded in listener | Delegated to `IshiAllyBoostStrategy` via `character.strategies["ishi_ally_boost"]` |
| Fallback branch | Erroneously calls `interrupt_strategy().recommend()` for non-ally case | Remove — that's not this listener's job |
| Trace annotation | None | `[Ishi 3rd Dan]` log + `SpendVoidPointsEvent` annotation |

## E4. `IshiAllyBoostStrategy` (NEW) + `EagerAllyBoostStrategy` (NEW default)

**File**: `simulation/strategies/ishi_dan_abilities.py` (NEW)
**Status**: NEW.

```python
class IshiAllyBoostStrategy(Strategy):
    """ABC for 3rd Dan ally-boost decisions. Pluggable per Principle V."""

    def recommend(
        self, character: Any, event: events.Event, context: Any
    ) -> Iterator[events.Event]:
        raise NotImplementedError()


class EagerAllyBoostStrategy(IshiAllyBoostStrategy):
    """Default: spend 1 VP whenever an ally's roll is below TN and we have
    VP + precepts > 0 + the once-per-roll guard isn't set.
    """
```

| Method | Behavior |
|---|---|
| `recommend(character, event, context)` | Inspect `event.action` to determine TN and ally roll value. If ally is in-group, roll < TN by ≥1, `character.vp() >= 1`, `character.skill("precepts") > 0`, and `event.action` not already boosted: yield `SpendVoidPointsEvent(character, "ishi_3rd_dan_boost", 1)` then mutate the ally's roll by `+precepts_k1_kept`. Set `event.action._ishi_boosted_by = character`. |

## E5. `IshiNegateSchoolStrategy` (NEW) + `EagerNegationStrategy` (NEW default)

**File**: `simulation/strategies/ishi_dan_abilities.py`
**Status**: NEW.

```python
class IshiNegateSchoolStrategy(Strategy):
    """ABC for 5th Dan school-negation decisions. Pluggable per Principle V."""

    def recommend(
        self, character: Any, event: events.Event, context: Any
    ) -> Iterator[events.Event]: ...


class EagerNegationStrategy(IshiNegateSchoolStrategy):
    """Default: on first YourMoveEvent for an Ishi at 5th dan, identify the
    highest-rank opposing school and negate if VP cost is affordable.
    Fires at most once per combat.
    """
```

| Method | Behavior |
|---|---|
| `recommend(character, event, context)` | Only fire on `YourMoveEvent` and only if `_negation_done` flag is unset on the character. Iterate enemy groups; pick highest-rank schooled enemy (or schoolless if none); compute `cost = 2 * opponent.school_rank()` (or `floor(opponent_xp / 50)` for schoolless). If `character.vp() >= cost`: yield `SpendVoidPointsEvent(character, "ishi_negate_school", cost)`, set `opponent._school_negated_by = character`, yield new `SchoolNegatedEvent(character, opponent, cost, opponent.school().name())`, set `character._ishi_negation_done = True`. |

## E6. `IshiYourMoveListener` (NEW)

**File**: `simulation/schools/ishi_school.py`
**Status**: NEW.

| Aspect | Behavior |
|---|---|
| Installed on slot | `"your_move"` (chained — see implementation note) |
| Event | `YourMoveEvent` |
| Logic | Before the standard `action_strategy()` runs, consult `character.strategies["ishi_negate_school"]`. If it yields events, those events fire first (the negation completes). Then the normal action strategy proceeds (the Ishi still takes its action that round; negation is "instantaneous, no action consumed" per rules text). |

## E7. Engine surface additions

### `Character._school_negated_by` attribute

**File**: `simulation/character.py`
**Status**: NEW.

```python
self._school_negated_by: Optional["Character"] = None
```

Reset in `Character.reset()` (combat-boundary reset).

### `BaseSchool` per-ability decorator OR check helper

**File**: `simulation/schools/base.py`
**Status**: NEW per OAD-1.

Implementation default: decorator `@_check_negated_short_circuit` applied to each `apply_special_ability`, `apply_rank_one_ability`, ..., `apply_rank_five_ability` in `BaseSchool`. When `character._school_negated_by is not None`, the method returns immediately (yields nothing / no side effects).

**Alternative** (OAD-1 fallback): a single check in `Character` or in the engine's school-ability dispatch site. Implementer chooses based on testability.

### `SchoolNegatedEvent`

**File**: `simulation/events.py`
**Status**: NEW.

```python
class SchoolNegatedEvent(Event):
    """5th Dan Isawa Ishi negation. Trace observability per Principle VII."""

    def __init__(
        self,
        negator: Any,
        target: Any,
        vp_cost: int,
        target_school_name: str,
    ) -> None:
        super().__init__("school_negated", negator)
        self.target = target
        self.vp_cost = vp_cost
        self.target_school_name = target_school_name
```

## Entity dependency graph

```
IsawaIshiSchool
├── installs → IshiMaxVPProvider                  (Special Ability)
├── installs → PlainAttackStrategy                (FIX: attack slot)
├── installs → IshiAllyBoostListener              (3rd Dan)
│       └── delegates → IshiAllyBoostStrategy (default: EagerAllyBoostStrategy)
│               └── reads ← character.skill("precepts")
│               └── reads ← character.vp()
│               └── checks ← event.action._ishi_boosted_by (per-roll guard)
│               └── mutates → event.action.skill_roll() or event.roll (wound check)
├── installs → IshiYourMoveListener               (5th Dan trigger)
│       └── delegates → IshiNegateSchoolStrategy (default: EagerNegationStrategy)
│               └── reads ← opponent.school_rank() or opponent_xp
│               └── checks ← character.vp() >= cost
│               └── mutates → opponent._school_negated_by = character
│               └── yields → SchoolNegatedEvent (for trace)
└── (4th Dan): apply_school_ring_raise_and_discount (Void +1, -5 XP)

Character._school_negated_by (new attribute)
└── checked by → BaseSchool per-ability decorator (negation short-circuit)
```

## Test data model

**File**: `tests/test_ishi_school.py` (NEW)

Anticipated test classes:

1. `TestIsawaIshiSchoolBasics` — school metadata (ring, knacks, extra_rolled, free_raise_skills).
2. `TestIshiMaxVPProvider` — max_vp + max_vp_per_roll arithmetic + edge cases.
3. `TestIshiSpecialAbilityIntegration` — character.max_vp() == highest_ring + school_rank end-to-end.
4. `TestIshiFirstDanExtraDice` — extra die on precepts / wound check / initiative.
5. `TestIshiSecondDanPrecepts FreeRaise` — free raise on precepts only.
6. `TestIshiAllyBoostListener` — fires on all combat roll events; ally-restricted; once-per-roll guard.
7. `TestEagerAllyBoostStrategy` — spend conditions; precepts.k1 mutation.
8. `TestIshiFourthDanVoidRaiseAndDiscount` — Void+1 + -5 XP.
9. `TestIshiFifthDanNegation` — VP cost; flag set; reset; mutual negation.
10. `TestSchoolNegationShortCircuit` — `BaseSchool.apply_*_ability` returns early when flag set.
11. `TestEagerNegationStrategy` — first-move trigger; cost calculation; schoolless opponents.
12. `TestIshiTraceClarity` — Principle VII annotations for all Ishi events.
13. `TestIshiUS1Integration` (US1 from spec) — Special Ability end-to-end.
14. `TestIshiUS3Integration` (US3) — 3rd Dan ally boost in scripted combat.
15. `TestIshiUS5Integration` (US5) — 5th Dan negation in scripted combat.
