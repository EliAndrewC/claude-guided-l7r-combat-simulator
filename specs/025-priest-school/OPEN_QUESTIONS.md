# Open Questions & Pre-Resolutions — Priest School

**Status**: Autonomous audit run. Per user direction: "this will involve a lot of bonuses to other people on the same side, and therefore will be a big deal to implement but take a shot at it and see what you can do with our usual process."

Most of the Priest School's identity centers on BUFFING ALLIES. The simulator's combat is typically 1v1, so a substantial portion of the rules text is moot in scope. Focus on the rules-fidelity fixes that have combat impact.

## Pre-resolutions

### Q1: School Ring "Any non-Void" — MEDIUM

**Pre-resolution**: **Fix.** Apply Monk/Ide/Ise Zumi `school_choices` precedent. Default "water"; validate against {"air", "earth", "fire", "water"}.

### Q2: 1st Dan "any one skill / any one combat roll" — MEDIUM

**Pre-resolution**: **Fix.** Rules grant player two free choices on top of fixed precepts. Apply `school_choices` for `first_dan_extra_skill` and `first_dan_extra_combat`. Defaults: `"initiative"` and `"wound check"` (matches skeleton's current hardcoded values).

### Q3: 2nd Dan self+allies free raise — DEFERRED

**Pre-resolution**: **Defer.** Bragging/precepts/sincerity are non-combat skills; ally version is moot in 1v1 simulator. Current self-only implementation is consistent.

### Q4: 3rd Dan beginning-of-combat vs per-round — BLOCKING

**Pre-resolution**: **Fix.** Rules: "Roll X dice at the **beginning of combat**". Skeleton fires per round → priest accumulates X pool dice EVERY round, strictly over-powered. Track an `_priest_pool_initialized` flag; roll once on the first NewRoundEvent of the combat.

### Q5: 3rd Dan swap vs add semantics — DEFERRED

**Pre-resolution**: **Defer.** Rules: "**swap** any of these dice for any rolled die" — the priest's pool die REPLACES one of the actual rolled dice. The engine doesn't model this; `FloatingBonus` ADDS to the roll. The add-instead-of-swap approximation is over-powered when the pool die exceeds a rolled die's value, equivalent when it's between min and max of the rolled dice, and weaker when the pool die is lower than the rolled die being replaced. Full swap semantics would require engine-level changes.

### Q6: 3rd Dan ally swap — DEFERRED

**Pre-resolution**: **Defer.** Same as Q3 — moot in 1v1.

### Q7: 4th Dan contested-roll Honor free raise — DEFERRED

**Pre-resolution**: **Defer.** Contested rolls in combat are typically iaijutsu duels (rare).

### Q8: 5th Dan Conviction-on-allies + action-die lowering — BIG DEFERRED

**Pre-resolution**: **Defer.** Entirely unimplemented in skeleton. The mechanics:
- "Spend Conviction points on allies' rolls" — requires ally targeting + a Conviction-points spending system.
- "Conviction points refresh after each conversation and combat round" — per-round resource refresh.
- "Spend points to lower action dice for counterattack/parry" — action-die manipulation tied to a non-VP resource pool.

This is a major implementation effort that's mostly moot in 1v1 simulator. Document and skip.

### Q9: `PRIEST_PRIORITIES` revision

**Pre-resolution**: **Defer** per pattern.

## To be answered during implementation

### Q10: combat-simulator + win-feasibility

**Status**: Will validate during playability tests. NOTE: priest is identity-aligned as a non-combatant; win-rate against Akodo may be very low.

## Deviations log (append during implementation)

(empty)
