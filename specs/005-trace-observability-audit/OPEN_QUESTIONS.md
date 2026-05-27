# Open Questions for End-of-Run Review (Combat Trace Observability Audit)

This document accumulates deferred decisions for the trace-observability-audit autonomous run. Run started 2026-05-27 on `006-trace-observability-audit`.

## Q1 — Inline breakdown format

**What I decided**: `XkY = N1k(M1) source-1 + N2k(M2) source-2 + ...` (equals-sign + plus-separated terms).

**Why**: Matches the constitution's canonical example `+30 (Mirumoto 5th Dan, +10 per VP × 3)`. The `=` makes the aggregation visually obvious to a casual reader.

**Alternative**: `XkY (source-1: Nk(M), source-2: Nk(M))` — parenthetical-list style. Equally readable; the equals-sign style was chosen for arithmetic clarity.

**Where**: `_format_attack_rolled`, `_format_combined_attack`, `_format_lw_damage` in `web/adapters/detailed_formatter.py`.

## Q2 — Multiple sources contributing the same component type

**What I decided**: List each source separately, even when two sources both contribute the same kind of dice (e.g., both adding extra-rolled dice). E.g., `+1k0 (Akodo 1st Dan) + 1k0 (some-other-school)`.

**Why**: Preserves attribution per source. Merging would lose the "where did each die come from" answer.

**Alternative**: Merge under a single source label like `+2k0 (extra dice: Akodo 1st Dan, other-school)`. More compact but loses per-source granularity.

**Where**: `_detail_components` annotation in observer; formatter renders in order.

## Q3 — Source label naming convention

**What I decided**: Short noun-phrase labels matching the rules text or the established school-attribution pattern:
- "katana" (weapon)
- "Fire ring" / "Water ring" / etc.
- "margin" (extra damage dice from attack-roll margin)
- "VP on attack" (cross-roll inflation)
- "Akodo 1st Dan" / "Akodo Special Ability" / etc. (school attributions, matching the Akodo precedent)

**Why**: Consistent with the existing source labels in events.py + the existing trace formatter. No need to invent new naming.

**Where**: Each contributing source's label, defined where the source-of-truth produces it (RollParameterProvider, school listener, etc.).

## Q4 — `(unsourced: +K)` placeholder lifecycle

**What I decided**: The placeholder is a TEMPORARY signal that a Principle VII gap exists. Tests SHOULD check for its absence in school-implementation runs; its presence is itself a P1 bug that needs follow-up.

**Why**: Surfacing the gap is better than hiding it. Once `explain_modifier` is fully catalogued, the placeholder should never appear in a passing run.

**Follow-up flag**: If the placeholder appears in any school's trace at merge time, log it as a school-spec follow-up (not blocking this audit's merge; the audit only mandates that the placeholder REPLACE silent suppression).

**Where**: `_format_modifier_breakdown` in `web/adapters/detailed_formatter.py`.

## Q5 — Breakdown rendering when aggregate has only one source

**What I decided**: Omit the `= breakdown` parenthetical when the breakdown is trivially the same as the aggregate (one source = full contribution).

**Why**: Avoid clutter. The breakdown adds value only when there's something to disambiguate.

**Where**: All `_format_*_rolled` functions; check `len([c for c in components if c.rolled or c.kept]) > 1` before emitting the breakdown.

## Q6 — Zero-contribution component omission

**What I decided**: Omit components where both `+rolled == 0` AND `+kept == 0`. Components with nonzero rolled OR nonzero kept (e.g., `+0k2` for VP-on-attack contributing kept-only) are RETAINED.

**Why**: A `+0k0` entry would clutter the trace without adding information. A `+0k2` entry is meaningful (kept-only inflation).

**Where**: Formatter's component filter; document in code comment.

## Q7 — Per-school provider breakdown contract

**What I decided**: When a school overrides `get_skill_roll_params` or `get_damage_roll_params`, the override MUST return either (a) the breakdown tuple alongside the totals, OR (b) expose its contribution via a separate accessor (e.g., `school.contribution_to_damage_breakdown(character)`) that the observer can query independently.

**Why**: The breakdown is observer-computed; it needs the data. Without per-school cooperation, school-specific extras would be invisible in the breakdown.

**Where**: Affects each school that overrides roll-params. Audit during implementation. If a school can't easily expose its breakdown, render with `(source: <school> extras, breakdown unknown)` and flag for follow-up.

## Q8 — Existing test churn

**What I decided**: Inline test updates are authorized as part of implementation. The new, more-detailed trace IS the new contract. Tests asserting partial strings (`assertIn(...)`) usually remain valid; tests asserting full-line equality get updated.

**Why**: The more-detailed trace is a Principle VII compliance fix. Tests that locked in the old, gap-ridden trace are codifying the bug.

**Threshold**: If more than 20 tests need updating, flag for user verification mid-run rather than continuing autonomously.

**Where**: Trace-assertion tests in `tests/test_mirumoto_school.py`, `tests/test_ishi_school.py`, `tests/test_akodo_school.py`, plus any general trace tests in `tests/test_detail_dice_integration.py` etc.

## Scope-creep findings

(Populated during the run if substantial out-of-scope work surfaces.)
