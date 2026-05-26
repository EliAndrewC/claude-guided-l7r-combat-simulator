# Phase 0 Research: Isawa Ishi School

This document consolidates the three research streams that drive the Isawa Ishi implementation: deferred-question resolutions, the school-progression-designer's recommendation, and the school-strategy-designer's recommendation.

## R1. Deferred-question resolutions (from spec Assumptions + OPEN_QUESTIONS.md)

Eight questions deferred by the autonomous-run pattern. Best-guess answers locked in for this implementation; user overrides on review.

| # | Question | Answer | Rationale | Severity if wrong |
|---|---|---|---|---|
| Q1 | 1st Dan: which 2 skills get +1 die? | wound check + initiative | Matches skeleton; defensive Void-mystic identity | MEDIUM |
| Q1b | Per-roll VP cap applies to 3rd Dan ally boost? | NO | Cap constrains own-roll spends, not buffs on others' rolls; rules-text natural reading | LOW |
| Q2 | 2nd Dan: free raise on which skill? | precepts | Synergy with 3rd Dan (X=precepts); skeleton's `attack` is identity-misfit | MEDIUM |
| Q3 | 3rd Dan target scope? | Ally-only (in-group), no adjacency requirement | Buffing opponents mechanically wrong; adjacency not in rules text | HIGH |
| Q4 | Strategy defaults? | Per strategy-designer (R3 below) | Identity-driven choices per Principle VIII | HIGH |
| Q5 | 5th Dan implementation? | Per-character `_school_negated_by` flag + base-class short-circuit helper | Minimal engine surface; reuses existing reset machinery; allows mutual negation | HIGH |
| Q5b | 5th Dan trigger timing? | On first `YourMoveEvent` where Ishi has enough VP | Rules-text "instantaneous, no action consumed" maps to earliest reactive event | MEDIUM |
| Q6 | Where does the negation short-circuit check live? | `BaseSchool.apply_*_ability` wrapper OR `Character` dispatch — decision deferred to implementer; default = base-class helper | Both are viable; base-class is cleaner architecturally | MEDIUM |

Each entry has full rationale + alternatives in [OPEN_QUESTIONS.md](./OPEN_QUESTIONS.md).

## R2. School-progression-designer recommendation

The designer proposed a revised `ISHI_PRIORITIES` list driven by **Special Ability dynamics** (max_vp = highest_ring + school_rank means bumping the highest ring gives *double* dividend: +1 ring AND +1 max VP).

**Five divergences from the existing generic priorities**:

1. **Precepts maxes first** (it's the X in the 3rd Dan Xk1 boost; basic-skill cheap).
2. **Void leads ring buys** (Dan-3 block: void → 3 BEFORE earth → 3, because void becomes the unique highest ring and pumps max_vp by +1 in addition to the ring bump).
3. **Void → 5 moves into Dan-4 block** (discounted to 20 XP via 4th Dan; same Mirumoto-style pattern).
4. **Water ahead of fire/earth/air in max-rings** (water is the only non-void ring with a rules-text Ishi clause — 1st Dan extra die on wound check).
5. **Fire last** at every tier (no Ishi clause cites fire; refuses to elevate it on stylistic grounds per Principle VIII).

**Proposed list** (verbatim from designer report; full per-block rationale and cost-machinery sanity check in `research.md` § "School-progression-designer full report" below):

```python
ISHI_PRIORITIES: list[tuple[str, str, int]] = [
    ("skill", "precepts", 2),
    ("skill", "precepts", 3),
    # Dan 2
    ("skill", "absorb void", 2),
    ("skill", "kharmic spin", 2),
    ("skill", "otherworldliness", 2),
    ("skill", "attack", 2),
    ("skill", "parry", 2),
    ("skill", "precepts", 4),
    # Dan 3
    ("skill", "absorb void", 3),
    ("skill", "kharmic spin", 3),
    ("skill", "otherworldliness", 3),
    ("skill", "attack", 3),
    ("skill", "parry", 3),
    ("ring", "void", 3),
    ("ring", "water", 3),
    ("ring", "earth", 3),
    ("skill", "precepts", 5),
    # Dan 4
    ("skill", "absorb void", 4),
    ("skill", "kharmic spin", 4),
    ("skill", "otherworldliness", 4),
    ("skill", "attack", 4),
    ("skill", "parry", 4),
    ("ring", "void", 5),
    ("ring", "air", 3),
    ("ring", "fire", 3),
    ("ring", "water", 4),
    ("ring", "earth", 4),
    # Dan 5
    ("skill", "absorb void", 5),
    ("skill", "kharmic spin", 5),
    ("skill", "otherworldliness", 5),
    ("skill", "attack", 5),
    ("skill", "parry", 5),
    # Max rings -- cheapest first per file convention
    ("ring", "air", 4),
    ("ring", "fire", 4),
    ("ring", "void", 6),
    ("ring", "water", 5),
    ("ring", "earth", 5),
    ("ring", "air", 5),
    ("ring", "fire", 5),
]
```

**Template projections** (per designer's walk-through):

- **150 XP**: rings void=3, water=2, earth=2, air=2, fire=2; precepts=4, knacks=2; max_vp = 3 + 2 = 5
- **250 XP**: rings void=3, water=3, earth=3, air=2, fire=2; precepts=5, knacks=3; max_vp = 3 + 3 = 6
- **350 XP**: rings void=5, water=3, earth=3, air=3, fire=3; precepts=5, knacks=4; max_vp = 5 + 4 = 9
- **450 XP**: rings void=5, water=4, earth=4, air=4, fire=3+; max_vp = 5 + 5 = 10

The Ishi reaches max_vp = 9 at 350 XP (vs ~7 with the existing generic list), dramatically increasing the 3rd Dan ally-boost firing rate.

## R3. School-strategy-designer recommendation

The designer's audit produced the following bindings (Layer 1 + Layer 2):

| Strategy slot | Class | Status |
|---|---|---|
| `"parry"` | `ReluctantParryStrategy` | Keep engine default (no parry-reward in Ishi) |
| `"interrupt"` | `DefaultInterruptStrategy` | Keep engine default (no counterattack knack) |
| `"attack"` | `PlainAttackStrategy` | **CHANGE from `UniversalAttackStrategy`** — Ishi has no double-attack/feint knack; default wastes branches |
| `"action"` | `HoldOneActionStrategy` | Keep engine default |
| `"wound_check"` | `WoundCheckStrategy` | Keep engine default (with per-roll cap caveat) |
| `"light_wounds"` | `KeepLightWoundsStrategy` | Keep engine default |
| `"ishi_ally_boost"` (NEW slot) | `EagerAllyBoostStrategy` (NEW class) | Default policy for 3rd Dan spend |
| `"ishi_negate_school"` (NEW slot) | `EagerNegationStrategy` (NEW class) | Default policy for 5th Dan negation |

**Listener changes**:
- DO NOT override `attack_rolled` listener (current skeleton bug). Chain the boost listener as an additional `*_rolled` event subscriber.
- ADD a `IshiYourMoveListener` or wrap the action strategy to consult `ishi_negate_school` BEFORE the normal action strategy fires.
- BROADEN the boost listener to subscribe to all `*RolledEvent` types (attack, parry, double attack, counterattack, iaijutsu, feint, lunge, wound check).

**Eight bugs identified in existing skeleton** (severity-ranked):
1. (HIGH) `IshiAllyBoostListener` overrides `attack_rolled` listener wholesale → breaks interrupt cascade.
2. (HIGH) 3rd Dan listener only handles `AttackRolledEvent` → misses 7 other roll types.
3. (HIGH) No once-per-roll guard for 3rd Dan.
4. (HIGH) 5th Dan unimplemented.
5. (MEDIUM) `formation().is_adjacent` requirement has no rules basis.
6. (MEDIUM) Default `UniversalAttackStrategy` wastes branches on double-attack/feint.
7. (MEDIUM) 3rd Dan decision hardcoded in Listener (violates Principle V).
8. (LOW) No trace annotation when listener fires/abstains.

**Layer 3 (playability) verdict**:
- Scenario A (Ishi vs Akodo): ✓ winnable — `HoldOneActionStrategy` phase-10 trigger + `PlainAttackStrategy` desperate-fallback guarantees offense each round. 5th Dan negation is decisive at 5th dan.
- Scenario B (mirror): ✓ terminates + ✓ identity engine fires via Special Ability + 5th Dan negation. **Explicit caveat**: 3rd Dan is structurally inert in 1v1 mirror (no allies). Combat-simulator should run a 2v2 mirror as augmenting scenario for 3rd Dan verification.
- Scenario C (action-disadvantage): ✓ handles via same phase-10 trigger + desperate-fallback.

**Layer 4 — Recommended validation scenarios**:
1. Win-feasibility vs Akodo at 300 XP (100 trials).
2. Win-feasibility vs Hida at 300 XP (100 trials).
3. 1v1 mirror non-degeneracy (Special Ability + 5th Dan trace markers present).
4. 2v2 mirror with 3rd Dan ally-boost firing (verify ≥1 `[Ishi 3rd Dan]` annotation per fight).
5. Action-disadvantage (Ishi attacks ≥1 time per fight).
6. Behavioral round-robin vs every fully-implemented school (fingerprint check).
7. Per-roll VP cap correctness (lowest_ring=1 → max_vp_per_roll=0 → no VP spent on own rolls).
8. 3rd Dan once-per-roll guard.
9. 5th Dan negation actually disables opponent school (Mirumoto's TVP listener should NOT fire).

## R4. Skeleton audit

The existing `simulation/schools/ishi_school.py` (108 lines) has:

| Component | Status | Action |
|---|---|---|
| School metadata (name, ring, knacks) | ✅ OK | None |
| `IshiMaxVPProvider` (Special Ability VP calc) | ✅ OK | Keep |
| `extra_rolled = ["precepts", "wound check", "initiative"]` | ✅ OK per Q1 | Keep |
| `free_raise_skills = ["attack"]` | ❌ Should be `["precepts"]` per Q2 | Fix |
| `apply_special_ability` installs VP provider only | ⚠️ MISSING `set_attack_strategy(PlainAttackStrategy())` per R3 | Extend |
| `apply_rank_three_ability` installs `IshiAllyBoostListener` on `"attack_rolled"` | ❌ 4 bugs (R3 bugs 1, 2, 3, 5) | Refactor |
| `IshiAllyBoostListener` | ❌ 4 bugs (override scope, event scope, no guard, adjacency) | Rewrite |
| `apply_rank_four_ability` does ring raise + discount | ✅ OK | Keep |
| `apply_rank_five_ability` is TODO | ❌ Unimplemented | Implement per Q5 |

## R5. New engine surface required

Three small additions to engine code:

1. **`Character._school_negated_by: Optional[Character]`** attribute on `simulation/character.py`. Default `None`. Reset in `Character.reset()` (already called by `EngineContext.reset()` at combat boundaries).

2. **`BaseSchool` helper or per-`apply_*_ability` short-circuit** in `simulation/schools/base.py`. When `character._school_negated_by is not None`, the per-rank ability dispatch returns early (yields nothing). Implementation choice (OAD-1) deferred to implementer; default = decorate `apply_*_ability` methods with a guard.

3. **`SchoolNegatedEvent`** in `simulation/events.py` — new event class for trace observability per Principle VII. Carries (negator, target, vp_cost, target_school_name).

## R6. New strategy module surface

`simulation/strategies/ishi_dan_abilities.py` (NEW), modeled on `mirumoto_third_dan.py`:

- `IshiAllyBoostStrategy(Strategy)` ABC — pluggable interface for 3rd Dan decisions.
- `EagerAllyBoostStrategy(IshiAllyBoostStrategy)` — default. Spend if ally roll < TN and Ishi has ≥1 VP and precepts > 0 and the once-per-roll guard isn't set.
- `IshiNegateSchoolStrategy(Strategy)` ABC.
- `EagerNegationStrategy(IshiNegateSchoolStrategy)` — default. On first `YourMoveEvent`, negate highest-rank opposing school if VP cost is affordable.
- Module-private helpers: `_already_boosted(action)` for the per-roll guard, `_negation_cost(target)` for the cost calculation.

## R7. Trace annotation extensions (Principle VII)

`web/adapters/modifier_breakdown.py::explain_modifier` extended to recognize:

- **Ishi 2nd Dan free raise on precepts**: when character has Ishi at rank ≥ 2 AND skill == "precepts", attribute the +5 modifier as "Isawa Ishi 2nd Dan free raise".
- **Ishi 3rd Dan ally boost**: when an ally's roll has been boosted by a 3rd-dan-or-higher Ishi in the same group, attribute the bonus value as "Isawa Ishi 3rd Dan ally boost from {ishi_name}".
- **Ishi 5th Dan negation**: render the `SchoolNegatedEvent` in the trace with explicit "{ishi_name} negates {target_name}'s {school_name}; cost {vp} VP".

`web/adapters/detailed_formatter.py` extended to format `SchoolNegatedEvent` in the trace stream.

## Open architectural decisions surfaced during plan

- **OAD-1** — Negation short-circuit location: `BaseSchool` per-ability decorator (cleaner architecturally) vs. `Character` dispatch site (single check point). **Default for the run**: BaseSchool per-ability decorator. Will be implemented in the task that adds the 5th Dan.

- **OAD-2** — `EagerAllyBoostStrategy` location: separate `simulation/strategies/ishi_dan_abilities.py` (per Mirumoto precedent — Principle V) vs. inline in `ishi_school.py`. **Default**: separate module.

- **OAD-3** — 5th Dan negation trigger event: `YourMoveEvent` (rules-text "instantaneous") vs. `AttackDeclaredEvent` (reactive when threatened). **Default**: `YourMoveEvent` (matches "instantaneous, no action consumed"). Sibling class `ReactiveNegationStrategy` documented as possible alternative.
