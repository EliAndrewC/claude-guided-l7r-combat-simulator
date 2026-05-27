# Data Model: Akodo Bushi School

## State carried by an Akodo character

An `AkodoBushiSchool` instance, when applied to a `Character`, results in the following character-bound state:

### Listener slot bindings (per-Dan)

| Dan rank | Slot | Listener class | Lifecycle |
|----------|------|----------------|-----------|
| Special | `attack_succeeded` | `AkodoAttackSucceededListener` | Always on once Special Ability applied. |
| Special | `attack_failed` | `AkodoAttackFailedListener` | Always on once Special Ability applied. |
| 3 | `wound_check_succeeded` | `AkodoWoundCheckSucceededListener` | On from 3rd Dan onward. |
| 4 | `wound_check_declared` | `AkodoWoundCheckDeclaredListener` | On from 4th Dan onward. |
| 5 | `lw_damage` | `AkodoLightWoundsDamageListener` | On from 5th Dan onward. Replaces default lw_damage listener. |

These slots are managed via `Character._school_owned_listener_slots` per the negation refactor at commit `89dc0bb`. On 5th-Dan school negation by an Ishi opponent, all of these listeners are removed and the slots restored to pre-school values.

### Strategy bindings

| Strategy | Class | Bound at | Lifecycle |
|----------|-------|----------|-----------|
| Wound-check-rolled handler | `AkodoWoundCheckRolledStrategy` | 4th Dan, internal to `AkodoWoundCheckDeclaredListener` | Inert until 4th Dan applied. |
| 5th Dan VP-counter-damage | `AkodoFifthDanStrategy` | 5th Dan, internal to `AkodoLightWoundsDamageListener` | Inert until 5th Dan applied. |

### Floating bonus collection (3rd Dan)

3rd Dan adds `AnyAttackFloatingBonus(value)` instances to the character's floating-bonus collection (existing engine entity, lives in `simulation/mechanics/floating_bonuses.py`).

**Lifecycle**:
1. **Acquisition**: at `WoundCheckSucceededEvent` for self, compute `value = ((roll - damage) // 5) * skill("attack")` and call `character.gain_floating_bonus(AnyAttackFloatingBonus(value))`. Each successful WC creates a new instance.
2. **Persistence within combat**: bonuses remain in the collection across rounds.
3. **Consumption**: at the next `AttackRolledEvent` for self, one bonus is consumed (FIFO order per OPEN_QUESTIONS.md Q6). The bonus value is added to the attack roll.
4. **Combat boundary**: at `Character.reset()` (or whatever lifecycle hook the combat loop invokes between combats), the floating-bonus collection is cleared. Verify the existing implementation does this; if not, add the reset.

### Static state

These don't change after `apply_*_ability` runs once at character build time:

- School identity: name, ring=water, knacks=[double attack, feint, iaijutsu].
- `extra_rolled` skills: [attack, double attack, wound check]. Read by the engine's roll-parameter providers; never mutated.
- `free_raise_skills`: [wound check]. Read by the engine; never mutated.

## Permanent character mutations from 4th Dan

The 4th Dan calls `apply_school_ring_raise_and_discount(character)`, which:
- Increases current and maximum Water ring by 1.
- Reduces further Water ring purchase cost by 5 XP.

Per the negation refactor convention, these are **permanent stat mods**, NOT buffs — they are NOT reverted on school negation.

## Lifecycle diagram (per-combat)

```text
[Combat start]
    |
    v
Character built; school applied; listeners installed; strategies bound.
    |
    v
[Combat loop begins]
    |
    +---> Round N:
    |       Character takes an attack action.
    |       If skill == "feint":
    |           AttackSucceededEvent or AttackFailedEvent fires.
    |           AkodoAttackSucceededListener / AkodoAttackFailedListener
    |               emits GainTemporaryVoidPointsEvent(character, 4 or 1).
    |           Trace formatter renders "Akodo Special Ability: +N TVP on
    |               (successful/failed) feint".
    |
    +---> Round M (some later round):
    |       Opponent attacks; rolls damage.
    |       LightWoundsDamageEvent fires with target=character.
    |       If character is 5th Dan:
    |           AkodoLightWoundsDamageListener.handle invokes:
    |               1. take_lw(event.damage)
    |               2. wound_check_strategy().recommend(...)
    |                  -> if 4th Dan: AkodoWoundCheckDeclaredListener intercepts
    |                  WC declaration, rolls, then dispatches
    |                  AkodoWoundCheckRolledStrategy for VP-spending decision.
    |                  -> WoundCheckSucceededEvent (if survived):
    |                  AkodoWoundCheckSucceededListener (if 3rd Dan) computes
    |                  floating bonus and gains it.
    |               3. AkodoFifthDanStrategy.recommend - if VP available + damage>=10:
    |                  spend max VP; emit LightWoundsDamageEvent at attacker.
    |                  Trace formatter renders "Akodo 5th Dan: 10 LW × N VP = +N0
    |                  LW dealt to <attacker>".
    |       If attacker is also 5th Dan Akodo:
    |           Recursive lw_damage handler fires on counter-damage.
    |           Terminates naturally on VP exhaustion or damage < 10.
    |
    +---> Round P:
    |       Character makes a follow-up attack.
    |       AttackRolledEvent fires.
    |       Existing engine consumes one AnyAttackFloatingBonus from the
    |           character's collection (FIFO); adds its value to the roll.
    |       Trace formatter renders "+N (Akodo 3rd Dan floating bonus consumed)".
    |
    v
[Combat end]
    |
    v
Character.reset() called.
Floating bonuses cleared.
TVP reset (existing engine behavior).
Permanent stat mods (4th Dan ring +1) preserved.
```

## Invariants

- **I1**: An Akodo character never accumulates floating bonuses while at school rank < 3.
- **I2**: An Akodo character can only spend VP on a WC after rolling it (not before) when school rank ≥ 4.
- **I3**: An Akodo character can only deal counter-damage in response to taking LW when school rank ≥ 5.
- **I4**: TVP gain on feint applies regardless of opponent type or formation (no spatial/relational gating).
- **I5**: Each WC success creates exactly one floating bonus; each attack roll consumes at most one.
- **I6**: 5th Dan counter-damage cannot exceed `min(available_vp, max_vp_per_roll, damage_taken // 10)` VP.
- **I7**: 5th Dan recursion in a self-mirror terminates within `2 × initial_vp + 1` listener-fire iterations (mathematical upper bound).
