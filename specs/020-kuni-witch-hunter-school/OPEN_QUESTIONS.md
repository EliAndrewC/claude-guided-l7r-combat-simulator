# Open Questions & Pre-Resolutions — Kuni Witch Hunter School

**Status**: Autonomous audit run. Decisions pre-resolved during `/speckit-specify`; logged here for end-of-run review.

The skeleton at `simulation/schools/kuni_school.py` (84 lines, 10 passing tests) has 3 BLOCKING rules-fidelity defects plus a known engine gap (`features.py:586` `NotImplementedError`).

## Pre-resolutions

### Q1: Special Ability missing +1 rolled — BLOCKING

**Pre-resolution**: **Fix.** Rules text: "Roll an extra (X+1)k(X+1) on wound checks". With Taint=0 (simulator baseline), X=0 → 1k1 = +1 rolled AND +1 kept. Skeleton only adds +1 kept (`_set_school_extra_kept`); missing `_set_school_extra_rolled("wound check", 1)`.

### Q2: 1st Dan missing interrogation — BLOCKING

**Pre-resolution**: **Fix.** Rules: "Roll one extra die on damage, **interrogation**, and wound checks." Skeleton omits interrogation. Non-combat skill so the simulator never reads it, but rules-fidelity gap.

### Q3: 4th Dan extra action die — DEFERRED

**Pre-resolution**: **Defer.** Rules text: "Roll an extra action die in combat, which may not be used to attack targets without the Shadowlands Taint." In a simulator without Taint, the extra die can ONLY be used for non-attack actions (parry, WC, etc.). Implementation requires per-die usage restrictions (not currently modeled). Defer to a follow-up branch with broader action-die infrastructure.

### Q4: 5th Dan missing "take half" backlash — BLOCKING

**Pre-resolution**: **Fix.** Rules text: "you may choose to inflict that number of light wounds on the opponent who dealt them **and take half that amount yourself**." Skeleton reflects all damage to the attacker but the Kuni takes no additional damage themselves — over-powered.

**Fix path**: when reflecting `N` LW on the attacker, also emit a `LightWoundsDamageEvent(attacker, kuni, N // 2)` so the Kuni takes half.

### Q5: 5th Dan "may choose" — strategic gate

**Pre-resolution**: **Document but DON'T add gate.** Rules say "may choose" but combat-simulator validation of unconditional behavior takes precedence (and the reflection IS the school's signature mechanic; gating it suppresses identity). Defer strategic-choice fix to a follow-up branch.

### Q6: Engine gap — `features.py:586` `NotImplementedError`

**Pre-resolution**: **Fix.** The features collector raises on `SpendAdventurePointsEvent`. With the Kuni's 3rd Dan AP-spend system active, every AP spend in combat crashes the collector — confirmed empirically by Daidoji round-robin (Kuni was 1 of 5 opponents that crashed with this error).

**Fix**: replace the raise with a no-op (skip observation). AP spends are not currently a tracked feature; the engine just needs to not blow up.

### Q7: `KUNI_PRIORITIES` revision

**Pre-resolution**: **Defer** per pattern.

### Q8: Trace observability

**Pre-resolution**: Tag the 5th Dan damage events for future renderer work.

## To be answered during implementation

### Q9: combat-simulator + win-feasibility

**Status**: Will validate during playability tests.

### Q10-11: school-strategy-designer + school-progression-designer bindings.

**Status**: Run during plan dispatch.

## Deviations log (append during implementation)

(empty — to be populated batch-by-batch)
