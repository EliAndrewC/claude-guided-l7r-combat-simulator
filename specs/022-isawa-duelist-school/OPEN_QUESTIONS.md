# Open Questions & Pre-Resolutions — Isawa Duelist School

**Status**: Autonomous audit run.

The skeleton at `simulation/schools/isawa_school.py` (196 lines, 19 passing tests) has 3 BLOCKING defects: the 3rd Dan TN penalty is never applied (listener defined but uninstalled), the 4th Dan interrupt-lunge has no strategy, and the 3rd Dan parry-cancels-penalty clause is unimplemented.

## Pre-resolutions

### Q1: Special Ability `_skill_rings["damage"]` direct mutation — MINOR

**Pre-resolution**: **Document but defer.** BACKLOG-flagged. The mutation isn't tracked in `_school_owned_*` slots → school-negation cannot revert. Same pattern as Daidoji's `_daidoji_third_dan`. Cross-school refactor needed; not blocking for this branch.

### Q2: 3rd Dan "may" — MINOR

**Pre-resolution**: **Keep unconditional.** Bonus is +3X (substantial) with a -5 TN penalty (modest). Net positive almost always. Strategic-choice fix would add complexity for marginal gain.

### Q3: 3rd Dan parry-cancels-penalty — BLOCKING

**Pre-resolution**: **Fix.** Rules text: "If a successful or unsuccessful parry is made against your attack, you do not suffer the TN penalty." Listener must NOT apply the TN penalty if the attack was parried.

**Fix path**: trigger on AttackSucceededEvent or AttackFailedEvent (post-resolution); check `event.action.parried()` or `event.action.parry_attempted()`; only apply the modifier if neither.

### Q4: 3rd Dan TN penalty listener not installed — BLOCKING IDENTITY

**Pre-resolution**: **Fix.** `IsawaAttackDeclaredListener` is defined but `apply_rank_three_ability` only installs the action factory. The TN penalty side of the trade is dead. Install via `_set_school_listener`.

### Q5: 4th Dan "once per round" — MINOR

**Pre-resolution**: **Fix.** Track `_isawa_interrupt_lunge_used_this_round` flag; reset on NewRoundEvent. The interrupt-lunge strategy must check this flag before firing.

### Q6: 4th Dan interrupt-lunge strategy missing — BLOCKING IDENTITY

**Pre-resolution**: **Fix.** Install an `IsawaInterruptLungeStrategy` that fires on `AttackRolledEvent` (post-roll trigger so we know whether Isawa or ally is the target). Pattern: Shiba's `ShibaInterruptParryStrategy` + Otaku's `OtakuInterruptLungeStrategy`. Add the once-per-round gate.

### Q7: `ISAWA_PRIORITIES` revision

**Pre-resolution**: **Defer** per pattern.

### Q8: Identity binding — WoundCheckStrategy04

**Pre-resolution**: **Install** in `apply_special_ability`. 1st Dan WC die + 2nd Dan free raise + 5th Dan floating bonus = deep WC pool.

### Q9: Trace observability

**Pre-resolution**: Tag events for future renderer work.

## To be answered during implementation

### Q10: combat-simulator + win-feasibility

**Status**: Will validate during playability tests.

### Q11: school-strategy-designer's bindings — accepted verbatim?

**Status**: Run during plan dispatch.

## Deviations log (append during implementation)

(empty)
