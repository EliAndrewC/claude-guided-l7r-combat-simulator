# Phase 1 Contracts: Python Protocols Consumed and Added

This feature is a pure-engine extension with no external API surface. The "contracts" here are the Python interfaces this feature consumes from the existing codebase and the interfaces it adds.

## Interfaces consumed (existing — no changes)

### `simulation.schools.base.BaseSchool` (ABC)

Already implemented by `MirumotoBushiSchool`. Relevant abstract methods this feature uses:

| Method | Signature | Purpose for Mirumoto |
|---|---|---|
| `name(self) -> str` | — | Factory lookup key |
| `school_ring(self) -> str` | — | Returns `"void"` |
| `school_knacks(self) -> list[str]` | — | Three rank-1 skills |
| `extra_rolled(self) -> list[str]` | — | Rolls that get +1 die (FR-005) |
| `free_raise_skills(self) -> list[str]` | — | Rolls that get a free raise (FR-006) |
| `apply_special_ability(self, character: Any) -> None` | — | Hook for FR-004 (TVP listener) |
| `apply_rank_three_ability(self, character: Any) -> None` | — | Hook for FR-007–FR-009a |
| `apply_rank_four_ability(self, character: Any) -> None` | — | Hook for FR-010–FR-013 |
| `apply_rank_five_ability(self, character: Any) -> None` | — | Hook for FR-014 |

### `simulation.listeners.Listener` (ABC)

Implemented by `MirumotoParryTVPListener` and `MirumotoNewRoundListener`.

```python
class Listener(ABC):
    @abstractmethod
    def handle(self, character: Any, event: Any, context: Any) -> Iterator[Any]: ...
```

### `simulation.strategies.base.Strategy` (ABC)

Implemented by the new Third Dan strategy classes.

```python
class Strategy(ABC):
    @abstractmethod
    def recommend(
        self, character: Any, event: events.Event, context: Any
    ) -> Iterator[events.Event]: ...
```

### `simulation.mechanics.roll_params.RollParameterProvider` (ABC, via `DefaultRollParameterProvider` subclass)

Already implemented by `MirumotoRollParameterProvider`. Methods overridden:

```python
def get_skill_roll_params(
    self, character, target, skill,
    contested_skill=None, ring=None, vp=0
) -> tuple[int, int, int]: ...

def get_wound_check_roll_params(
    self, character, vp=0
) -> tuple[int, int, int]: ...
```

### `simulation.strategies.action_factory.ActionFactory` (ABC, via `DefaultActionFactory`)

Implemented by `MirumotoActionFactory`. Relevant methods:

```python
def get_attack_action(
    self, subject, target, skill, initiative_action, context, vp=0
) -> Any: ...

# Plus the double-attack variant (exact method name to be confirmed in implementation).
def get_parry_action(  # currently overridden; will be REMOVED.
    self, subject, target, attack, skill, initiative_action, context, vp=0
) -> Any: ...
```

The fix is to override the *attack-side* methods (returning `MirumotoAttackAction` and `MirumotoDoubleAttackAction`) and **remove** the parry-side override.

### `simulation.actions.AttackAction` and `DoubleAttackAction`

Subclassed (new) by `MirumotoAttackAction` and `MirumotoDoubleAttackAction`. Relevant methods to override:

```python
class DoubleAttackAction(AttackAction):
    def direct_damage(self) -> Any | None: ...
    def calculate_extra_damage_dice(
        self, skill_roll: int | None = None, tn: int | None = None
    ) -> int: ...
```

`MirumotoDoubleAttackAction.direct_damage` returns `SeriousWoundsDamageEvent` on failed-parry case (FR-012). `MirumotoAttackAction.calculate_extra_damage_dice` halves the per-failed-parry reduction (FR-013).

## Interfaces added by this feature

### Pool accessor helpers (informal — not a separate ABC)

To avoid scattering `character._mirumoto_pool` lookups, expose two small helpers in `simulation/schools/mirumoto_school.py`:

```python
def _pool_remaining(character: Any) -> int:
    """Return the character's current Third Dan pool size (0 if not set)."""

def _try_spend_pool_point(character: Any) -> bool:
    """Atomically decrement the pool. Return True on success, False if empty."""
```

These are intentionally module-private (`_` prefix). The two strategy classes consume them. No abstract base class — single-call-site simplicity.

### `MirumotoPhaseLowerStrategy(Strategy)`

```python
class MirumotoPhaseLowerStrategy(Strategy):
    """Decides Third Dan mode-A (phase-lowering) spends.

    Invoked by the combat loop's existing strategy-dispatch on phase-related
    events. Decision interface mirrors the spec's FR-008 + FR-009a:

    - May choose to lower one or more actions' phases by one or more steps.
    - Must never spend more points than `_pool_remaining(character)`.
    - Must never lower an action below phase 1.
    """

    def recommend(self, character, event, context) -> Iterator[events.Event]:
        ...
```

Default implementation: `EagerPhaseLowerStrategy` (subclass) — spends a point on the soonest scheduled non-phase-1 action whenever the pool has ≥ 1 point AND any enemy in the same group has a pending attack this round.

### `MirumotoPostRollBonusStrategy(Strategy)`

```python
class MirumotoPostRollBonusStrategy(Strategy):
    """Decides Third Dan mode-B (+2 after-roll) spends.

    Invoked immediately after the character's attack or parry roll resolves,
    before the roll's total is consumed by downstream logic. Decision interface
    mirrors FR-009 + FR-009a:

    - May spend zero or more points on the roll.
    - +2 per point, additive.
    - Must never spend more points than `_pool_remaining(character)`.
    """

    def recommend(self, character, event, context) -> Iterator[events.Event]:
        ...
```

Default implementation: `MarginalBonusStrategy` (subclass) — spends just enough points to push a failing roll over the TN or to gain one additional raise.

## Event types

### Consumed

| Event | Source | Use |
|---|---|---|
| `NewRoundEvent` | `simulation/events.py` | Trigger for pool reset (MirumotoNewRoundListener) |
| `NewPhaseEvent` | `simulation/events.py` | Trigger for mode-A spend decisions (MirumotoPhaseLowerStrategy) |
| `ParrySucceededEvent`, `ParryFailedEvent` | `simulation/events.py` | Trigger for TVP grant (MirumotoParryTVPListener) |
| `GainTemporaryVoidPointsEvent` | `simulation/events.py` | Yielded by the TVP listener; consumed by the engine's existing `GainTemporaryVoidPointsListener` |

### Yielded

- `GainTemporaryVoidPointsEvent` (already yielded by skeleton).
- *(NEW)* Spend events for the Third Dan strategies. The exact event names depend on the existing engine pattern — likely just direct attribute mutation + a logging event, or a new `ThirdDanPointSpentEvent` for trace clarity. To be determined during `/speckit-implement` after a quick check of how Akodo's TVP-on-failed-feint is traced.

## Trace contract (for SC-006)

For combat traces to be reviewable against the rules file (SC-006), every Mirumoto-specific effect must emit a distinctive log event. Specifically:

- Special Ability TVP grant — already logged via `GainTemporaryVoidPointsEvent`.
- 3rd Dan pool creation — log on `NewRoundEvent` with the pool size.
- 3rd Dan mode-A spend — log target action, pre-spend phase, post-spend phase.
- 3rd Dan mode-B spend — log target roll, points spent, resulting bonus.
- 4th Dan auto-SW landing on failed parry — log the override path so reviewers can distinguish it from a no-parry-attempted auto-SW.
- 4th Dan halved damage-die-reduction — log the original reduction value alongside the halved one.
- 5th Dan +10 bonus — log per-roll, separately from the standard VP bonus.

These are documentation guidance, not API contracts; the implementation tasks should make sure each surfaces in the trace.
