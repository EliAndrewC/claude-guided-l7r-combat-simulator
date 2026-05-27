# Engine Event Contracts (Akodo Bushi School)

This document records the engine-event contract Akodo's listeners depend on. These contracts are NOT being refactored — they are LOCKED-IN behavior assumed by the implementation. Tests must verify that the engine continues to honor these contracts after the Akodo refactor.

## AttackSucceededEvent / AttackFailedEvent

**Producer**: combat loop after an attack roll resolves.

**Fields used by Akodo**:
- `event.action.subject()` → `Character` who declared the attack.
- `event.action.skill()` → string skill name (e.g., `"feint"`, `"attack"`, `"double attack"`).

**Akodo listener contract**: `AkodoAttackSucceededListener` and `AkodoAttackFailedListener` filter on `subject == character AND skill == "feint"`. Other skills are ignored.

**Invariant**: Both events fire for every feint roll. A failed feint emits `AttackFailedEvent`, not nothing.

## GainTemporaryVoidPointsEvent

**Producer**: emitted by Akodo's feint listeners; consumed by the engine to increment `character.temporary_vp`.

**Fields**:
- `character` → recipient.
- `n` → integer count to add (1 or 4 for Akodo).

**Akodo emission contract**:
- On successful feint: `yield GainTemporaryVoidPointsEvent(character, 4)`.
- On failed feint: `yield GainTemporaryVoidPointsEvent(character, 1)`.

**Trace contract** (Principle VII): the formatter MUST render this event with attribution. Acceptable strings include "Akodo Special Ability: +N TVP on (successful|failed) feint" or equivalent. The numeric value AND the source MUST appear.

## WoundCheckSucceededEvent

**Producer**: combat loop after a successful wound check (roll ≥ damage).

**Fields used by Akodo**:
- `event.subject` → character whose WC just succeeded.
- `event.roll` → the WC roll total.
- `event.damage` → the damage that triggered the WC.

**Akodo 3rd Dan emission contract**:
```python
bonus = ((event.roll - event.damage) // 5) * character.skill("attack")
character.gain_floating_bonus(AnyAttackFloatingBonus(bonus))
```

**Trace contract**: at acquisition, formatter MUST render "Akodo 3rd Dan: gained floating bonus +N (margin {roll - damage} ÷ 5 × attack skill {skill('attack')})" or equivalent.

## WoundCheckDeclaredEvent / WoundCheckRolledEvent

**Producer**: WoundCheckDeclaredEvent fires from the engine when a character is about to roll a wound check. WoundCheckRolledEvent fires after the roll.

**Akodo 4th Dan interception**: `AkodoWoundCheckDeclaredListener` intercepts the declaration, manually rolls the WC, wraps in `WoundCheckRolledEvent`, and dispatches `AkodoWoundCheckRolledStrategy` for the VP-spending decision.

**Contract for the strategy**: must consider `vp ∈ {1, ..., max_spend}` (inclusive of max_spend per FR-017). Must select smallest spend per FR-018.

**Trace contract**: at the spend, formatter MUST render "Akodo 4th Dan: spent N VP on wound check, +5 per VP = +5N to roll ({orig_roll}→{new_roll})" or equivalent.

## LightWoundsDamageEvent

**Producer**: combat loop after a successful attack rolls damage. **Also emitted by Akodo's 5th Dan strategy** as counter-damage.

**Fields**:
- `event.subject` → attacker (who is dealing the damage).
- `event.target` → defender (who is taking it).
- `event.damage` → LW count.

**Akodo 5th Dan listener contract**: filters on `target == character`. The listener:
1. Applies LW: `character.take_lw(event.damage)`.
2. Dispatches WC: yields from `character.wound_check_strategy().recommend(...)`.
3. Dispatches 5th Dan VP-decision: yields from `AkodoFifthDanStrategy.recommend(...)`.

**5th Dan strategy emission contract**:
```python
max_vp = min(
    character.void_point_manager().vp("damage"),
    character.max_vp_per_roll(),
    event.damage // 10
)
if max_vp > 0:
    yield SpendVoidPointsEvent(character, "damage", max_vp)
    yield LightWoundsDamageEvent(character, event.subject, 10 * max_vp)
```

**Trace contract**: counter-damage rendering MUST include "Akodo 5th Dan: spent N VP on counter-damage, 10 LW × N = +{10N} LW dealt to {attacker}" or equivalent.

**Recursion contract**: if `event.subject` is also a 5th-Dan Akodo, that character's `lw_damage` listener will fire on the counter-damage event. Termination is guaranteed by VP exhaustion and the `damage < 10` cutoff.

## AnyAttackFloatingBonus

**Producer**: Akodo 3rd Dan listener gains via `character.gain_floating_bonus()`.

**Consumer**: engine's attack-roll pipeline consumes one floating bonus per `AttackRolledEvent` (per OPEN_QUESTIONS.md Q4 / Q6).

**Contract invariants**:
- Single-use: each bonus is consumed by exactly one attack roll.
- Combat-scoped: cleared at `Character.reset()` per Principle IX combat-boundary requirement.
- Order: FIFO per OPEN_QUESTIONS.md Q6 (or whatever order the existing engine implements — tests align with engine, not over-specify).

**Trace contract**: at consumption, formatter MUST render "+N (Akodo 3rd Dan floating bonus consumed)" or equivalent.

## Side-channel: character.knowledge().observe_damage_roll

**Producer**: Akodo 5th Dan listener calls when `event.subject != character` (i.e., observing damage to another character).

**Purpose**: feeds the character-knowledge subsystem used by other strategies. NOT Akodo-specific in scope but resides in the 5th Dan listener as a co-located optimization.

**Decision** (per research.md D5): keep in 5th Dan listener; do not refactor. Document via a code comment but no behavioral change.
