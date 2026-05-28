# Phase 1 Data Model: Hida Bushi School

## New entities

### `HidaRollProvider(DefaultRollProvider)` — `simulation/schools/hida_school.py`

Reuses `DefaultRollProvider` for everything EXCEPT counterattack and attack rolls (where 3rd Dan reroll applies).

**Methods overridden**:
- `roll_skill(self, skill: str, ...)` — after the initial roll, if `skill in {"counterattack", "attack", "double attack", "iaijutsu"}` and character is 3rd-Dan-or-higher Hida:
  - Compute `N = 2 * attack_skill if skill == "counterattack" else attack_skill`
  - If character is `crippled()`: `N = math.ceil(N / 2)`
  - Identify the N lowest dice that are also below 5.5 expected value
  - Reroll each (with 10-explode enabled even when crippled, per Hida 3rd Dan exception)
  - Emit a trace event documenting which dice were rerolled
  - Use new totals in place of old

**Pre-conditions**:
- `character.dan() >= 3` AND `character.school().name() == "Hida Bushi School"`
- skill must be in the eligible-attack set

### `HidaWoundCheckStrategy(WoundCheckStrategy)` — `simulation/schools/hida_school.py`

Extends `WoundCheckStrategy` with the 4th Dan SW-for-LW trade option.

**Decision algorithm**:
1. Compute the base WC decision (call `super().recommend(...)`).
2. Check pre-conditions for trade:
   - `character.lw() > 0`
   - `character.sw() + 2 <= character.max_sw()`
   - NOT `context.in_iaijutsu_phase()` for this character
   - Character is 4th-Dan-or-higher Hida
3. Compute `expected_sw_from_rolling = WoundCheckStrategy.expected_sw_after_spending(...)`.
4. If trade pre-conditions met AND `expected_sw_from_rolling >= 2`: take the trade (yield a `HidaSWForLWTradeEvent`).
5. Else: proceed with base WC strategy.

**Pre-conditions**:
- character is 4th-Dan-or-higher Hida (verified at install time via `apply_rank_four_ability`)

### `HidaSWForLWTradeEvent` — `simulation/schools/hida_school.py` (or `simulation/events.py`)

A new event capturing the 4th Dan trade.

**Fields**:
- `character`: the Hida taking the trade
- `lw_reset_from`: the LW value before the trade (for trace)
- `sw_taken`: always 2 (per rules)

**Effects on play**:
- `character.take_sw(2)` (using existing SW infrastructure)
- `character.set_lw(0)` (using existing LW infrastructure)
- Yields downstream events as if a WC had completed with `sw_inflicted=2, lw_after=0`.

**Trace output** (per Principle VII):
- `"<name> | 🛡️ Hida 4th Dan: take 2 SW to reset LW from N → 0 (alternative wound check)"`

### `HidaCounterattackInterruptStrategy(CounterattackInterruptStrategy)` — `simulation/schools/hida_school.py`

Extends `CounterattackInterruptStrategy` to support the 5th Dan post-damage timing.

**Two decision points (vs base's one)**:
1. **Pre-damage** (existing): Should the Hida counterattack BEFORE seeing damage?
2. **Post-damage** (new for 5th Dan): If the Hida deferred the pre-damage decision, should they counterattack NOW after seeing damage?

**Decision algorithm**:
- If `character.dan() >= 5`:
  - On pre-damage interrupt query: defer (return None / "wait").
  - On post-damage interrupt query (new event slot): decide based on damage taken + attacker state.
- Else (4th Dan or below): fall through to `super().recommend(...)`.

**Pre-conditions**:
- character is 5th-Dan Hida (verified at install time via `apply_rank_five_ability`)

### `PostDamageInterruptCheckEvent` — `simulation/events.py`

A new event slot fired AFTER `LightWoundsDamageEvent` resolves but BEFORE the attack flow concludes.

**Purpose**: gives 5th-Dan Hidas (or any future school with deferred-counterattack mechanics) a chance to act with full information about the damage taken.

**Effects on play**:
- Yields no effect on its own; just a hook for installed listeners (`HidaCounterattackInterruptStrategy`).

### `_counterattack_excess_margin` attribute on attack actions — `simulation/actions.py`

A new optional attribute on attack actions storing the margin (`roll - TN`) by which a counterattack against this attack succeeded.

**Set by**: the counterattack-resolution flow on a successful Hida 5th Dan counterattack.

**Read by**: the WC roll resolution on the damage from the counterattacked attack — added to the WC roll.

**Trace attribution**: when nonzero, the WC trace line MUST include `+X (Hida 5th Dan: counterattack excess +X)`.

### `context.in_iaijutsu_phase()` accessor — `simulation/engine.py` (or context module)

A boolean accessor on the combat context: returns True while THIS character is in the iaijutsu duel's first-strike phase.

**Set/cleared by**: the iaijutsu duel engine at `DuelInitiativeRolledEvent` (set) and `DuelEndedEvent` (clear) boundaries.

**Read by**: `HidaWoundCheckStrategy.recommend()` to gate the SW-for-LW trade.

## Modified entities

### `HidaBushiSchool` — `simulation/schools/hida_school.py`

- **`school_knacks()`**: change return value to `["counterattack", "double attack", "iaijutsu"]` (was: `["counterattack", "iaijutsu", "lunge"]`).
- **`apply_special_ability(self, character)`**: existing wiring is correct; possibly add a trace-attribution hook so the +5 free raise is sourced in the trace (Principle VII).
- **`apply_rank_three_ability(self, character)`**: REPLACE the TODO with installation of the `HidaRollProvider`.
- **`apply_rank_four_ability(self, character)`**: keep existing `apply_school_ring_raise_and_discount(character)` call AND add installation of `HidaWoundCheckStrategy`.
- **`apply_rank_five_ability(self, character)`**: REPLACE the TODO with installation of `HidaCounterattackInterruptStrategy` (replacing the default `CounterattackInterruptStrategy`) AND register a listener for `PostDamageInterruptCheckEvent`.

### `HIDA_PRIORITIES` — `simulation/templates/strategies.py:209-251`

- Replace all 5 occurrences of `("skill", "lunge", N)` with `("skill", "double attack", N)`.
- Revise ordering per the school-progression-designer agent's proposal (see Phase 1 output).

### `simulation/templates/generator.py:35`

- Change `"Hida Bushi School": ["counterattack", "iaijutsu", "lunge"]` to `"Hida Bushi School": ["counterattack", "double attack", "iaijutsu"]`.

### `web/adapters/detailed_formatter.py` and / or `web/adapters/trace_entries.py`

- Add trace entry types and renderings for:
  - The +5 free raise from Hida special ability (re-attributed in the attack-roll line).
  - The 3rd Dan reroll event (showing dice before → after).
  - The 4th Dan SW-for-LW trade event.
  - The 5th Dan counterattack-excess bonus on WC rolls (sourced).
  - The 5th Dan post-damage counterattack timing (event ordering).

Per Principle VII: each must be self-explaining without consulting source code.

## Relationships

```
HidaBushiSchool
├── apply_rank_three → installs HidaRollProvider
├── apply_rank_four  → installs HidaWoundCheckStrategy + ring raise/discount
└── apply_rank_five  → installs HidaCounterattackInterruptStrategy + post-damage listener

HidaRollProvider
└── intercepts roll_skill for {counterattack, attack, double attack, iaijutsu}
    → calls _find_dice_to_reroll → emits trace event

HidaWoundCheckStrategy
├── consumes context.in_iaijutsu_phase()
└── on trade-decision → yields HidaSWForLWTradeEvent

HidaCounterattackInterruptStrategy
├── pre-damage: defers (5th Dan)
└── post-damage (PostDamageInterruptCheckEvent listener): decides + stores
    _counterattack_excess_margin on the originating attack action

WC resolution on damage from counterattacked attack
└── reads _counterattack_excess_margin → adds to WC roll → sources in trace
```
