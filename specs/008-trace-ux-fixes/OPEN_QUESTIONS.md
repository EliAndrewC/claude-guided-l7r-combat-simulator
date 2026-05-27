# Open Questions for End-of-Run Review (Combat Trace UX Fixes)

Run started 2026-05-27 on `009-trace-ux-fixes`.

## Q1 — Floating-bonus integration format

**Decision**: inline arithmetic — `"→ kept_sum, +bonus (source) = total vs TN N — outcome"`.

**Where**: TextRenderer and BulletedRenderer attack-line rendering.

## Q2 — Feint damage rendering

**Decision**: completely suppress for feints. No damage line, no projection, no breakdown.

**Alternative considered**: render a minimal `"feint succeeded — no LW dealt"` line. Rejected because the attack-outcome line already says HIT and the school-ability event makes the consequence visible. Adding a third line is redundant.

## Q3 — `"unsourced"` literal fallback

**Decision**: replace with `"(see preceding line)"` for the genuinely-unattributable case. For the specific `+5 (unsourced)` instance flagged by the dry-run, the source is the Akodo 4th Dan VP-on-WC modifier — add the case to `explain_modifier`.

## Q4 — Shared helper module location

**Decision**: `web/adapters/_breakdown_format.py`. Private (leading-underscore) to signal "internal to web/adapters/".

## Q5 — Engine ordering — should bonus-consumption events fire BEFORE attack-outcome events?

**Decision**: NO. Formatter-only change. Engine ordering changes are out of scope for this spec.

## Q6 — How does the formatter know an action is a feint AND deals 0 LW?

**Decision**: `event.action.skill() == "feint"` for the action check; for the 0-LW check, the `LightWoundsDamageEvent` carries the damage amount. The formatter inspects both at entry-production time.

## Q7 — Cross-renderer consistency test enforcement

**Decision**: a new test `tests/test_cross_renderer_consistency.py` runs the calibration combat through both renderers, parses each multi-source aggregate's component breakdown, and asserts the same component strings appear in both. The test runs as part of the normal pytest suite.

## Scope-creep findings

(Populated during the run if substantial out-of-scope work surfaces.)
