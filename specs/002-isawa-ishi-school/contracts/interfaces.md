# Phase 1 Contracts: Isawa Ishi Python Interfaces

The Ishi feature is pure-engine + UI annotation work. The "contracts" are the Python interfaces consumed (existing) and added (new).

## Interfaces consumed (existing — no changes)

### `simulation.schools.base.BaseSchool` (ABC)
Implemented by `IsawaIshiSchool`. Abstract methods used: `name`, `school_ring`, `school_knacks`, `extra_rolled`, `free_raise_skills`, `ap_base_skill`, `apply_special_ability`, `apply_rank_one_ability` through `apply_rank_five_ability`. **NEW** for this feature: a class-level decorator or instance check that short-circuits each `apply_*_ability` when `character._school_negated_by is not None`. Implementation choice OAD-1.

### `simulation.listeners.Listener` (ABC)
Implemented by `IshiAllyBoostListener` and `IshiYourMoveListener`.

### `simulation.strategies.base.Strategy` (ABC)
Implemented by `IshiAllyBoostStrategy` and `IshiNegateSchoolStrategy` ABCs and their default concrete subclasses.

### `MaxVPProvider` protocol
`IshiMaxVPProvider` satisfies `max_vp(character) -> int` and `max_vp_per_roll(character) -> int`. Already implemented and correct.

### `Character` API surface
- `character.vp()` — read available VP.
- `character.spend_vp(n)` — spend VP.
- `character.skill(name)` — read skill rank.
- `character.school()` and `character.school_rank()` — read school info (for 5th Dan cost calculation).
- `character.experience()` (or equivalent) — for the schoolless 5th-Dan cost path. **Verify during implementation that this accessor exists on `Character`**; if not, the implementer adds it.
- **NEW**: `character._school_negated_by: Optional[Character]` — new attribute.

### `Event` types consumed
- `*RolledEvent` family — attack/parry/double-attack/counterattack/iaijutsu/feint/lunge/wound-check. 3rd Dan listener subscribes to each.
- `YourMoveEvent` — 5th Dan trigger.
- `SpendVoidPointsEvent` — 3rd Dan and 5th Dan VP spends.
- `GainTemporaryVoidPointsEvent` — not used by Ishi.

## Interfaces added by this feature

### `IshiAllyBoostStrategy(Strategy)` ABC and default

```python
class IshiAllyBoostStrategy(Strategy):
    """3rd Dan decision strategy: spend VP to boost an ally's roll."""

    def recommend(
        self, character: Any, event: events.Event, context: Any,
    ) -> Iterator[events.Event]:
        raise NotImplementedError()


class EagerAllyBoostStrategy(IshiAllyBoostStrategy):
    """Default: spend if margin < 0 and pool > 0 and precepts > 0."""
```

Slot key: `"ishi_ally_boost"` on `character._strategies`.

### `IshiNegateSchoolStrategy(Strategy)` ABC and default

```python
class IshiNegateSchoolStrategy(Strategy):
    """5th Dan decision strategy: negate target school."""

    def recommend(
        self, character: Any, event: events.Event, context: Any,
    ) -> Iterator[events.Event]: ...


class EagerNegationStrategy(IshiNegateSchoolStrategy):
    """Default: on first YourMoveEvent, negate highest-rank schooled opponent."""
```

Slot key: `"ishi_negate_school"` on `character._strategies`.

### `SchoolNegatedEvent` event class

```python
class SchoolNegatedEvent(Event):
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

### `Character._school_negated_by` attribute contract

```python
# Set by a 5th-dan Ishi's negation. Cleared by Character.reset().
self._school_negated_by: Optional[Character] = None
```

### `IshiAllyBoostListener` and `IshiYourMoveListener`

Standard `Listener` subclasses; live in `simulation/schools/ishi_school.py`. Multi-event-type subscription for `IshiAllyBoostListener`: the implementer decides whether to install it on multiple per-event slots or whether to add a generic "post-roll" hook to the engine. Default: install on each of the eight `*_rolled` slots (less engine surface change).

## Trace contract (Principle VII)

`web/adapters/modifier_breakdown.py::explain_modifier` extended:

- For a roll where `skill == "precepts"` and the character has Ishi at rank ≥ 2: append `("Isawa Ishi 2nd Dan free raise", 5)` to the breakdown.
- For a roll where the action has `_ishi_boosted_by` set (a 3rd Dan boost has fired): append `("Isawa Ishi 3rd Dan ally boost from {boost_source.name()}", boost_value)`.

`web/adapters/detailed_formatter.py` adds a `_format_school_negated_event` method rendering `SchoolNegatedEvent` like:

```
Phase X | {negator} | ⛔ negates {target}'s {school_name} ({vp_cost} VP — Isawa Ishi 5th Dan)
```
