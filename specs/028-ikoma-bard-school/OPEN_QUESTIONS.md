# Open Questions & Pre-Resolutions — Ikoma Bard School

**Status**: Autonomous audit run.

The skeleton at `simulation/schools/ikoma_bard_school.py` (292 lines, 37 passing tests) is largely correct but has one BLOCKING over-implementation in the 5th Dan listener.

## Pre-resolutions

### Q1: School Ring "Any non-Void" — MEDIUM

**Pre-resolution**: **Fix.** Apply Monk/Ide/Priest school_choices precedent. Default "water"; validate against `{"air", "earth", "fire", "water"}`.

### Q2: SA "before attack roll" vs "after roll on hit" timing — INTERPRETIVE DEFERRED

**Pre-resolution**: **Document, keep current.** Rules text "before making an attack roll" implies the bard declares the SA use before rolling. Skeleton automates by deferring the decision to after the roll: only force parry when the attack actually hits (otherwise no point). This is a defensible decision-automation simplification.

### Q5: 5th Dan — RESOLVED (initial pre-resolution was based on truncated rules text)

**Pre-resolution**: **NO FIX. SKELETON IS RULES-CORRECT.**

Initial Q5 BLOCKING claim was based on the WebFetch returning only the first sentence of the 5th Dan rules text:

> Once per conversation or combat round, you can apply an oppose knack or your Special ability an additional time.

Based on that, the cancel-opponent-attack listener appeared to be over-implementation. **Rules-auditor pulled the FULL text directly from upstream:**

> Once per conversation or combat round, you can apply an oppose knack or your Special ability an additional time. **You may choose to use your Special Ability after an opponent has made an attack roll against you, in which case their attack is canceled and their attack roll will be used as their parry roll.**

The second sentence EXPLICITLY grants the cancel-attack ability. The skeleton's `IkomaFifthDanAttackRolledListener` is rules-correct. The original plan to REMOVE it would have introduced a rules discrepancy.

**MINOR refinement deferred**: rules say "their attack roll will be used as their parry roll" — meaning the canceled attack roll should become the opponent's parry roll against the Ikoma's NEXT attack. The skeleton sets `set_parried()` to cancel the attack but doesn't carry forward the attack roll as a parry roll. This is a partial implementation that's beyond the scope of this audit.

### Q3: Identity bindings

**Pre-resolution**: No combat strategy bindings needed; school has no defensive 5th Dan (after Q5 fix), no special wound-check strategy mandate.

### Q4: `IKOMA_BARD_PRIORITIES` revision

**Pre-resolution**: **Defer** per pattern.

## To be answered during implementation

### Q6: combat-simulator + win-feasibility

**Status**: Will validate during playability tests. NOTE: removing the over-powered 5th Dan cancel-attack listener will reduce Ikoma's defensive power. Expect win-rate to drop from pre-fix baseline.

## Deviations log (append during implementation)

(empty)
