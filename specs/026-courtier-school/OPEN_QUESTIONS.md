# Open Questions & Pre-Resolutions — Courtier School

**Status**: Autonomous audit run.

The skeleton at `simulation/schools/courtier_school.py` (115 lines, 15 passing tests) is largely correct. Per user direction: "the courtier does have several combat-relevant abilities" — SA, 3rd Dan AP, 4th Dan TVP, 5th Dan all-roll Air all have combat impact.

## Pre-resolutions

### Q1: 4th Dan "manipulation roll" — DEFERRED

**Pre-resolution**: **Defer.** Manipulation is non-combat; ally version of the TVP trigger is moot.

### Q2: 4th Dan `_targets_triggered` persists across combats — MINOR

**Pre-resolution**: **Fix.** Rules text "once per target per **conversation or fight**" — the set should reset between fights. Current skeleton tracks per-listener-instance, which persists for the character's lifetime. In the simulator's single-combat usage this is harmless, but a proper implementation should reset on combat start. Add a `NewRoundEvent` listener that resets the set on round 1.

### Q3: 5th Dan if/else simplification — MINOR

**Pre-resolution**: **Refactor.** `CourtierFifthDanRollParameterProvider.get_skill_roll_params` has an if/else that both branches do `modifier += character.ring("air")`. Collapse to a single unconditional add.

### Q4: 5th Dan "Add your Air to all TN and contested rolls" interpretation — DEFERRED

**Pre-resolution**: **Document, keep current.** Rules text is ambiguous:
- (a) "TN" could mean TN-to-be-hit (defensive stat) — courtier's defensive TN gets +Air.
- (b) "TN [rolls]" — all rolls that have a TN (= most rolls).
- (c) "[your] TN [stat] and [your] contested rolls".

Skeleton implements (b): adds Air to all skill rolls. The "stacks with Special Ability for attack rolls" clause supports interpretation (b)/(c). TN-to-be-hit defensive interpretation (a) is not implemented; deferring as an alternate interpretation rather than a bug.

### Q5: 3rd Dan AP skill scope — PASSED

Rules text lists "heraldry, manipulation, sincerity, tact, attack, and wound checks". Skeleton's `ap_skills=["attack", "wound check"]` keeps the combat-relevant subset. Non-combat skills omitted per simulator scope.

### Q6: `COURTIER_PRIORITIES` revision

**Pre-resolution**: **Defer** per pattern.

## To be answered during implementation

### Q7: combat-simulator + win-feasibility

**Status**: Will validate during playability tests. NOTE: courtier with high Air should be a competent fighter despite social identity.

## Deviations log (append during implementation)

(empty)
