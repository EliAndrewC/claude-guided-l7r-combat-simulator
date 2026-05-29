# Open Questions & Pre-Resolutions — Hiruma Scout School

**Status**: Autonomous audit run. Decisions pre-resolved during `/speckit-specify`; logged here for end-of-run review.

The skeleton at `simulation/schools/hiruma_school.py` (115 lines, 10 passing tests) has the Special Ability completely unimplemented (`pass`) plus rules-fidelity gaps in the 3rd Dan effect.

## Pre-resolutions

### Q1: Special Ability — completely unimplemented (BLOCKING IDENTITY)

**Pre-resolution**: **Fix.** Rules text: "The two allies fighting on your left and right have their TN to be hit raised by 5." Skeleton `apply_special_ability` is `pass`.

**Why**: The entire identity of the school (a formation-anchored Yojimbo-style scout) is structurally dead.

**Fix path**: Per `formation.py:60-64`, the formation exposes `neighbors(character)` which returns same-side left/right neighbors. Options:

1. **Register a listener that maintains modifiers**: e.g., on `NewRoundEvent` or `combat_start`, place a +5 `tn to hit` modifier on each neighbor. Problem: neighbors change as characters fall.
2. **Make `tn_to_hit` formation-aware**: query the formation directly when computing. Cleanest but requires engine-side changes.
3. **Lazy-evaluating modifier**: a special modifier on the Hiruma that, when read by `tn_to_hit` of OTHERS, looks up their neighbor status.

**Pragmatic approach for this audit**: install the modifier at character build (`apply_special_ability` runs once) and on `NewRoundEvent` re-evaluate the neighbor set (remove old modifiers, add new). Use `_set_school_listener("new_round", ...)` — but the 4th Dan ALREADY installs a NewRoundListener. Solution: chain — extend the 4th Dan listener or use a different slot.

Simpler: install a `combat_start` listener (if available) OR install at apply_special_ability + accept that neighbor changes mid-combat are deferred. Investigate the available slots.

### Q2: 3rd Dan bonus scope — BLOCKING

**Pre-resolution**: **Fix.** Rules text: "against the attacker or someone adjacent to them". Skeleton uses `AnyAttackFloatingBonus` which applies on ANY attack (no target gating).

**Fix path**: Need a target-scoped floating bonus, e.g., `AnyAttackVsTargetsFloatingBonus(skills, bonus, targets)`. Add this class or use an inline modifier mechanism.

### Q3: 3rd Dan damage roll — BLOCKING

**Pre-resolution**: **Fix.** Rules text: "your next attack and damage roll". `AnyAttackFloatingBonus` applies to ATTACK_SKILLS (skill rolls), NOT damage. Need a separate bonus for damage roll OR a unified bonus that covers both.

**Fix path**: Grant 2 floating bonuses — one for attack-class skills, one for damage. The combat strategy code will consume the attack one on the attack roll, then the damage one on the damage roll.

### Q4: 5th Dan duplicates 3rd Dan logic — MINOR

**Pre-resolution**: **Refactor.** `HirumaFifthDanParryListener` inline-duplicates the 3rd Dan floating-bonus gain. Subclass `HirumaParryListener` and delegate via `super()` (Shinjo precedent).

### Q5: `HIRUMA_PRIORITIES` revision

**Pre-resolution**: **Defer** per Bayushi/Kakita/Otaku/Shiba/Shinjo pattern. Same knack-at-every-rank + earth-3 (no Hiruma mechanic) + air late + parry-at-every-rank shape.

### Q6: Trace observability

**Pre-resolution**: Tag the events for future renderer work. Priorities:
- Special Ability +5 TN modifier on allies.
- 3rd Dan bonus consumption (already labeled via `source` parameter on `FloatingBonus`).
- 5th Dan damage modifier on attacker.

## To be answered during implementation

### Q7: combat-simulator + win-feasibility

**Status**: Will validate during playability tests.

### Q8: school-strategy-designer's bindings — accepted verbatim?

**Status**: Run during plan dispatch.

### Q9: school-progression-designer's revision — accepted verbatim?

**Status**: Run during plan dispatch (likely deferred per Q5).

## Deviations log (append during implementation)

(empty — to be populated batch-by-batch)
