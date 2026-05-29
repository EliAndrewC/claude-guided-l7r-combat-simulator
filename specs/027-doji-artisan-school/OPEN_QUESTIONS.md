# Open Questions & Pre-Resolutions — Doji Artisan School

**Status**: Autonomous audit run.

The skeleton at `simulation/schools/doji_artisan_school.py` (302 lines, 33 passing tests) is largely correct and quite developed. Main gap is the school_ring "Air or Water" choice.

## Pre-resolutions

### Q1: School Ring "Air or Water" — MEDIUM

**Pre-resolution**: **Fix.** Rules say player picks Air OR Water (not "Any non-Void"). Apply Monk/Ide/Ise Zumi/Priest school_choices precedent with RESTRICTED validation against `{"air", "water"}` only.

### Q2: SA "while counterattacking" scope — INTERPRETIVE DEFERRED

**Pre-resolution**: **Document, keep current.** Rules text reads:

> You may spend a void point to counterattack as an interrupt action at the cost of one actions die; this void point still gives your counterattack +1k1. While counterattacking, you receive a bonus equal to the attacker's roll divided by 5, rounded down.

"While counterattacking" is ambiguous between:
- (a) Only during the VP-interrupt counterattack described in the first clause.
- (b) On all Doji counterattacks.

Skeleton implements (a). The natural reading of "While counterattacking" as a continuation of the VP-interrupt scenario is defensible — the bonus only applies to the interrupt-style counterattack you just paid VP for.

### Q3: Ad-hoc `_doji_artisan_attack_tracker` — DEFERRED

**Pre-resolution**: **Document, defer.** BACKLOG-flagged. Set directly on character (`character._doji_artisan_attack_tracker = tracker`); not tracked in `_school_owned_*` slots. Same shape as Daidoji `_daidoji_third_dan` (specs/018). Cross-school refactor needed.

### Q4: 5th Dan parry/other-skill coverage — DEFERRED

**Pre-resolution**: **Document, keep current.** Rules say "any TN or contested roll". Skeleton applies the bonus to attack rolls (TN = target's tn_to_hit) and WC rolls (X = current LW). Parry and other skill rolls don't get the bonus. The included paths cover the dominant combat impact; full coverage requires plumbing TN-awareness into each skill-roll path.

### Q5: `DOJI_ARTISAN_PRIORITIES` revision

**Pre-resolution**: **Defer** per pattern.

## To be answered during implementation

### Q6: combat-simulator + win-feasibility

**Status**: Will validate during playability tests.

## Deviations log (append during implementation)

(empty)
