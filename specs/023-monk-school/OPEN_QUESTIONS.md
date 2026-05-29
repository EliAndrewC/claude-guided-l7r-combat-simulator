# Open Questions & Pre-Resolutions — Brotherhood of Shinsei Monk School

**Status**: Autonomous audit run.

The skeleton at `simulation/schools/monk_school.py` (262 lines, 35 passing tests) is largely correct. Main gap is the school_ring hardcoding ("Any non-Void" → player choice).

## Pre-resolutions

### Q1: school_ring "Any non-Void" — MEDIUM

**Pre-resolution**: **Fix.** Rules: "School Ring: Any non-Void". Skeleton hardcodes `"water"`. Apply Ide Diplomat precedent at `ide_school.py:107-125` — read `school_choices["school_ring"]`, default to "water", validate against {"air", "earth", "fire", "water"}, warn + fallback on invalid.

### Q2: 3rd Dan AP-spend timing — MINOR

**Pre-resolution**: **Keep eager.** Rules: "may be applied to action dice at any time". Skeleton lowers eagerly at start-of-round. Strategic-choice optimization (e.g., only lower dice if attacker has earlier-phase dice) is a follow-up.

### Q3: 5th Dan damage check skips hit-vs-TN — MINOR

**Pre-resolution**: **Document, don't fix.** Rules: "your attack continues and you hit/miss and roll damage as normal". Skeleton always rolls damage when counter cancels the attack. In practice the attacker's attack roll usually exceeds their own `tn_to_hit`, so the monk meeting/exceeding that threshold also exceeds tn_to_hit. Gap is theoretical; fix can come with broader 5th Dan refactor.

### Q4: Identity binding — WoundCheckStrategy04

**Pre-resolution**: **Consider.** 1st Dan +1 WC die + 3rd Dan AP raises on WC = decent WC pool. Strategy-designer will recommend during dispatch.

### Q5: `MONK_PRIORITIES` revision

**Pre-resolution**: **Defer** per pattern.

### Q6: Trace observability

**Pre-resolution**: Tag the 3rd Dan AP-spend-on-action-dice and 5th Dan counter-attack events for future renderer work.

## To be answered during implementation

### Q7: combat-simulator + win-feasibility

**Status**: Will validate during playability tests.

## Deviations log (append during implementation)

(empty)
