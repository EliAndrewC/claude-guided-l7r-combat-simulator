# Phase 0 Research: Akodo Bushi School

## Verbatim rules text (cached from upstream)

Source: `https://github.com/EliAndrewC/l7r/blob/master/rules/04-schools.md` — § "Akodo Bushi School". Fetched 2026-05-27 during the spec phase. Cached here per Constitution Principle III so the spec→plan→tasks→implementation chain has an offline source of truth.

```
## Akodo Bushi School

**School Ring:** Water

**School Knacks:**
* double attack
* feint
* iaijutsu

**Special Ability:**
You get four temporary void points after a successful feint and one
void point after an unsuccessful feint.

**First Dan:**
Rolls one extra die on attack, double attack, and wound checks.

**Second Dan:**
You get a free raise on wound checks.

**Third Dan:**
After you exceed the TN of a wound check, divide the difference
between your wound check and the damage roll by 5, rounding down.
You may add that number multiplied by X to any future attack this
combat, where X is your attack skill.

**Fourth Dan:**
Raise your current and maximum Water by 1. Raising your Water now
costs 5 fewer XP.
You may spend void points after rolling a wound check to receive a
free raise for each void point spent.

**Fifth Dan:**
After you take damage, you may spend void points to deal 10 light
wounds to the attacker for every void point spent, up to the amount
of damage you took.
```

## Skeleton audit findings (defect inventory)

Source file: `simulation/schools/akodo_school.py` (187 lines, last edited prior to spec 003 merge).

### D1 — 4th Dan `range(1, max_spend)` off-by-one [P1 BUG]

**Location**: `AkodoWoundCheckRolledStrategy.recommend`, line 173.

**Symptom**: `for vp in range(1, max_spend)` iterates `vp ∈ {1, 2, ..., max_spend - 1}`, excluding `max_spend` itself. If `max_spend = 5` (the typical late-Dan ceiling), the strategy never considers spending all 5 VP — even when needed to survive.

**Fix**: change to `range(1, max_spend + 1)`.

**Decision**: Apply fix. **Rationale**: Off-by-one excludes the most aggressive spend amount, which is precisely the spend that survives high-damage hits — the rule's core value proposition. **Alternatives considered**: Leave as-is — rejected because the rules text says "you may spend void points" without an exclusive cap, so `max_spend` is reachable.

### D2 — 5th Dan listener duplicates default LW handling [P0 PENDING VERIFICATION]

**Location**: `AkodoLightWoundsDamageListener.handle`, lines 87–95.

**Symptom**: The listener calls `character.take_lw(event.damage)` and dispatches `character.wound_check_strategy().recommend(...)`. This work is normally done by the engine's default `lw_damage` listener. If the Akodo school's `_set_school_listener(character, "lw_damage", ...)` STACKS rather than REPLACES, the character takes 2× damage and runs 2× WC per attack.

**Verification needed**: Inspect `Character._set_school_listener` (per the negation refactor at commit `89dc0bb`, `_set_school_listener` writes to a single slot in `_school_owned_listener_slots`, meaning the slot REPLACES). Confirm via test.

**Decision**: Verify-only, no expected fix. **Rationale**: The negation refactor's slot semantics already guarantee replacement. **Alternatives considered**: Refactor the listener to omit the duplicated default work and rely on the engine's default — rejected because (a) the Akodo listener needs to interleave the 5th Dan strategy between the WC dispatch and the LW take, which the default listener can't do, and (b) doing so would require changing the engine's lw_damage default to support post-WC hooks, expanding the scope significantly.

### D3 — 5th Dan strategy unconditionally spends max VP [P3 FOLLOW-UP]

**Location**: `AkodoFifthDanStrategy.recommend`, line 113.

**Symptom**: Comment in code: `# TODO: implement a little more intelligence`. The strategy always spends max VP regardless of whether the counter-damage threatens the attacker.

**Decision**: Defer per OPEN_QUESTIONS.md Q3. Keep "always spend max" as v1; revisit if Principle IX win-feasibility (SC-004) fails.

**Rationale**: A simple "always spend max" v1 matches the rule's pure interpretation and is the minimum-correctness target. Smarter heuristics (only spend when threatening attacker's WC range) require modeling opponent state and add complexity that isn't load-bearing for the current correctness fix. **Alternatives considered**: Threshold heuristic — deferred to follow-up.

### D4 — Trace observability for Akodo abilities (Principle VII compliance) [P1 NEW WORK]

**Location**: All Akodo listeners + strategies + the user-facing trace formatter in `web/formatters/`.

**Symptom**: The skeleton does not explicitly emit user-facing trace lines with source attribution for Akodo abilities. The `GainTemporaryVoidPointsEvent`, `SpendVoidPointsEvent`, `LightWoundsDamageEvent`, etc. are engine events; whether the user-visible trace surfaces "Akodo Special Ability: +4 TVP" or just "+4 TVP" depends on the formatter.

**Verification needed**: Read `web/formatters/*` and check how each Akodo-relevant event is rendered. If attribution is missing, add it.

**Decision**: Audit the formatter; add attribution for any missing events. **Rationale**: Principle VII requires the trace to be self-explaining without consulting source code. **Alternatives considered**: Source-only logging via `logger.debug` — rejected per Principle VII (debug logs are not sufficient).

### D5 — 5th Dan listener knowledge-tracking branch [LOW]

**Location**: `AkodoLightWoundsDamageListener.handle`, lines 88–91.

**Symptom**: The listener has an additional branch that fires when `event.subject != character` — recording `character.knowledge().observe_damage_roll(event.subject, event.damage)`. This is unrelated to the 5th Dan rule but happens to live in the same listener.

**Decision**: Keep as-is. **Rationale**: Knowledge tracking is part of the engine's character-knowledge subsystem (used by other strategies like the wound-check optimizer) and is not Akodo-specific. Moving it would expand scope. **Alternatives considered**: Move to a separate listener slot — rejected as a scope expansion.

## Engine entities reference

Existing entities Akodo's listeners and strategies depend on:

| Entity | File | Purpose |
|--------|------|---------|
| `GainTemporaryVoidPointsEvent` | `simulation/events.py` | Emitted by Special Ability on feint outcome. |
| `SpendVoidPointsEvent` | `simulation/events.py` | Emitted by 4th Dan / 5th Dan strategies. |
| `LightWoundsDamageEvent` | `simulation/events.py` | Source of 5th Dan trigger AND emitted as counter-damage. |
| `AttackSucceededEvent` / `AttackFailedEvent` | `simulation/events.py` | Special Ability trigger (filtered by `skill() == "feint"`). |
| `WoundCheckDeclaredEvent` / `WoundCheckRolledEvent` / `WoundCheckSucceededEvent` | `simulation/events.py` | 3rd Dan + 4th Dan triggers. |
| `AnyAttackFloatingBonus` | `simulation/mechanics/floating_bonuses.py` | 3rd Dan floating-bonus container. |
| `apply_school_ring_raise_and_discount` | `simulation/schools/base.py` | 4th Dan ring raise + XP discount. |
| `_set_school_listener` | `simulation/schools/base.py` | Slot-replacing listener install (post-negation-refactor semantics). |

## Pattern precedent from specs 001 and 002

What worked in Mirumoto (spec 001):
- Per-batch `rules-auditor` review caught 8 rules-correctness bugs the implementer missed.
- `school-strategy-designer` flagged identity-default mismatches (AlwaysParryStrategy installation came from this).
- Mirror-match playability check (Scenario C) caught a TVP-engine-never-firing degenerate case.

What worked in Ishi (spec 002):
- Autonomous-run with OPEN_QUESTIONS.md let the run complete without interactive stops, while preserving user judgment on non-trivial choices.
- school-progression-designer's ring priorities matched the school's identity (void-first).
- Test count: ~25 new tests, comprehensive coverage of all 5 Dan ranks.

What changed mid-run that we're applying preemptively here:
- Principle VII (trace observability) — applied from the start of this spec via FRs 006/008/009/014/019/024/031/032.
- Principle IX 2(b) (mirror identity-engine-firing) — applied from the start via FR-029, SC-005.
- Principle VIII (identity-driven defaults) — applied from the start via FR-026/027 and dedicated agent reviews.

## Existing `simulation/templates/strategies.py` priority schema reference

The strategies module exposes per-school priority lists (e.g., `MIRUMOTO_PRIORITIES`, `ISHI_PRIORITIES`) that drive XP allocation during character generation. The `school-progression-designer` agent will propose an `AKODO_PRIORITIES` list. Expected shape:

```python
AKODO_PRIORITIES: list[tuple[str, str]] = [
    ("ring", "water"),     # WC survivability (school ring)
    ("skill", "attack"),    # Multiplier in 3rd Dan formula
    ("skill", "feint"),     # Drives the TVP economy
    ("skill", "double attack"),
    # ... etc., as proposed by the designer
]
```

Exact ordering deferred to the designer agent during Phase 1.5 (post-plan).
