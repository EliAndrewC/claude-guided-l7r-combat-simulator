# Feature Specification: Combat Trace Observability Audit

**Feature Branch**: `006-trace-observability-audit`

**Created**: 2026-05-27

**Status**: Draft (autonomous run)

**Input**: User direction (2026-05-27): "sweep all multi-source rolls" after observing a Principle VII violation in a live combat trace where damage `10k10` rendered with no breakdown of its components.

**Rules Source**: Constitution Principle VII at `/simulator/.specify/memory/constitution.md` — Combat Trace Self-Explanation. The constitution mandates: *"Every applied ability, modifier, free raise, extra die, point spend, or rules override that changes a roll's outcome MUST appear in the user-facing combat trace with both its **source** and its **numeric effect**. '+30' is insufficient; '+30 (Mirumoto 5th Dan, +10 per void point × 3)' is correct."*

**Run Mode**: Autonomous. Decisions logged in `OPEN_QUESTIONS.md` for end-of-run user review.

**Why this feature matters**: The trace is the primary artifact a playtester uses to understand a combat outcome. Aggregates rendered without source attribution force the playtester to read engine source code to interpret the trace — defeating the entire point of an observable simulator. This audit is also load-bearing for future schools: every new school's compliance check assumes the current trace formatter renders the components it adds, and if the formatter silently aggregates them away, the verification is meaningless.

## Clarifications

### Session 2026-05-27 (autonomous; pre-answered per project conventions)

- Q: Inline parenthetical breakdown vs. separate sub-lines per component? → A: **Inline parenthetical**, matching the constitution's canonical example `+30 (Mirumoto 5th Dan, +10 per VP × 3)`. Keeps traces compact at the cost of verbose-but-readable single lines. Multi-line breakdowns would fragment the per-event flow and clutter the trace.
- Q: Should the breakdown be shown even when the aggregate appears trivially (e.g., only one source)? → A: **Yes, always show for multi-source aggregates**; when there's exactly one source, the breakdown is the same as the aggregate and is omitted. The principle is "self-explaining"; brevity is secondary.
- Q: How are zero-contribution components rendered (e.g., margin = 0)? → A: **Omit** zero-contribution entries from the breakdown. The reader doesn't need to see `+0k0 from margin`. Document the omission rule in the formatter.
- Q: What does the formatter do when a modifier breakdown's components don't sum to the modifier value? → A: Emit `(unsourced: +K)` as an explicit placeholder. The constitution's "`+30` is insufficient" example maps directly to this case — making the gap visible to users (and tests) is the goal, not hiding it.
- Q: What does "self-explanation" mean across multi-line traces? → A: **Per-line self-explanation**. Attribution in a preceding turn/phase line does NOT count. Each multi-source aggregate must be self-explaining on the line where it appears.
- Q: Should the trace-auditor agent become a mandatory checkpoint in the school-implementation workflow? → A: **Yes**. After this audit lands, the next-school workflow in CLAUDE.md gains `trace-auditor` as a peer of `rules-auditor` and `combat-simulator` after each substantial batch.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A playtester reads an attack-line trace and understands the damage XkY composition (Priority: P1)

A simulator user runs a combat. The attacker's attack hits, deals damage. The trace formatter renders the damage roll's XkY expression with an inline breakdown that lists each contributing source (weapon base, ring contribution, margin extras, VP-on-attack inflation, school-specific extras) with its numeric contribution. The user can read the line and reconstruct the math without consulting source code.

**Why this priority**: This is the user's reported bug. The calibration anchor for the whole audit.

**Independent Test**: Build a deterministic combat where a Bayushi 5th-Dan attacker double-attacks an Akodo (similar to the user's reported trace). Force a hit with a specific margin (e.g., +12 over TN). The damage line MUST render the breakdown inline: `damage will be 10k7 = 4k2 katana + 6k0 Fire ring + 0k2 margin (+12÷5) + 0k2 VP on attack` (or equivalent). Assert via trace string match. The `_format_attack_rolled` projection AND the final `_format_lw_damage` rendering both must show the breakdown.

### User Story 2 — A playtester reads an attack-line trace and understands the attack XkY composition (Priority: P1)

Same combat as US1. The attack roll's `10k10` expression also has multiple sources (base ring + skill + Akodo 1st Dan extra die + VP-on-attack effect + floating bonuses). The trace renders the breakdown inline at the moment the XkY appears.

**Why this priority**: Same shape as US1 but for the attack roll. The two together cover the vast majority of multi-source aggregates a playtester encounters.

**Independent Test**: Same combat as US1. Assert the attack line renders the breakdown: `10k10 = 6k3 Fire+skill + 1k0 Akodo 1st Dan + 1k1 VP on attack + 2k6 ...` (exact terms depend on the character build). The aggregate (rolled, kept) totals must equal the sum of breakdown contributions.

### User Story 3 — A bare numeric modifier always shows a source (Priority: P1)

When the trace shows a `+N` modifier on a roll (e.g., `+5` after a kept-sum), the rendering MUST include a source label. If the formatter's `explain_modifier` can't account for the full `+N`, the rendering shows `(unsourced: +K)` for the unaccounted portion — making the gap visible rather than hiding it.

**Why this priority**: This is the constitution's prototypical "+30 is insufficient" violation. The most-likely-to-confuse case.

**Independent Test**: Construct a scenario where an attack rolls and a bare `+5` appears (e.g., a free raise from a knack, or a Bayushi double-attack bonus). Assert the trace string includes the source for every numeric modifier. Construct a deliberately-broken scenario where `explain_modifier` doesn't have a case for the source; assert the trace shows `(unsourced: +5)` rather than rendering `+5` with no parenthetical.

### User Story 4 — TN computation shows its raise-count attribution (Priority: P1)

When an action inflates TN (e.g., double attack costs 4 raises, +20 TN), the trace renders the TN line with the raise breakdown: `vs TN 50 (base TN 30, +20 from 4 raises for double attack)`.

**Why this priority**: TN is a numeric aggregate every attack line touches. The current trace shows the delta from base but not its derivation, which is exactly the same shape as the damage-XkY bug.

**Independent Test**: Force a double-attack at base TN 30 (so TN = 50). Assert the trace contains `(base TN 30, +20 from 4 raises for double attack)` or equivalent attribution. Same shape applies to other raise-costing actions (feint, double attack, etc.).

### User Story 5 — VP-on-attack's inflation of damage dice is visible (Priority: P1)

When a character spends VP on an attack roll, the L7R rules grant `+1k1` to the subsequent damage roll per VP spent. The trace currently shows the spend (`⬛⬛ spends 2 VP on double attack`) but the downstream damage line does NOT show that VP inflated its dice. After this audit, the damage breakdown must include `(VP on attack: +Nk(N))` as an explicit source-list entry.

**Why this priority**: Cross-roll effects (where a spend on one roll inflates a later roll) are a P0 user-confusion vector — the playtester sees the spend on round 1 and the inflated damage on round 1, but with no causal arrow between them. Currently invisible.

**Independent Test**: Construct a combat with deterministic VP spending. Assert the damage breakdown for the attack that the VP funded contains a `(VP on attack: +2k2)` entry (or equivalent for the spent amount). The breakdown's contributions must sum to the rendered XkY.

### Edge Cases

- **Aggregate with only ONE source**: render without breakdown parenthetical (the breakdown would be the same as the aggregate). E.g., if a base attack has no modifiers, `7k3` doesn't need `7k3 = 7k3 base`.
- **Zero-contribution sources**: omit from breakdown. `4k2 katana + 0k0 margin + 6k0 Fire` is rendered as `4k2 katana + 6k0 Fire`.
- **Components that sum incorrectly**: the formatter's safety clause must explicitly render `(unsourced: +K)` instead of silently suppressing. The unsourced placeholder is itself a Principle VII violation but a visible one — surface it so tests can flag it.
- **Floating bonus consumed without source**: when a floating bonus has no source attribution (e.g., emitted by an older path), the consumption line falls back to "+N (floating bonus consumed, unsourced)" — surfaces the gap.
- **Iaijutsu duels**: most multi-source-roll mechanics also fire in iaijutsu duels. The same rendering rules apply.
- **Wound checks with multiple raises (VP + AP + conviction + floating bonus stacking)**: the WC line must show each resource's contribution distinctly, not lump them into a single `+N`.
- **Cross-character-school interactions**: when a school ability is silently disabled (e.g., post-negation), the relevant component still appears in the breakdown but with a `(disabled)` suffix on its source label — OR is omitted entirely if it contributed `+0`. Pre-resolution: omit if zero contribution; otherwise label with `(disabled)`.
- **Per-line self-explanation across phase boundaries**: a turn-phase header is NOT a substitute for inline source attribution. E.g., a damage line in Phase 5 still needs its full breakdown even if Phase 4 spent the relevant VP.

## Requirements *(mandatory)*

### Functional Requirements

**Annotation infrastructure (observer layer)**

- **FR-001**: `CombatObserver._annotate_attack` MUST attach a `_detail_components: list[tuple[str, int, int]]` annotation to attack-rolled events. Each tuple is `(source_label, +rolled, +kept)`. The sum of `+rolled` across the list equals the total rolled dice; same for `+kept`.
- **FR-002**: `CombatObserver._annotate_damage` MUST attach the same shape annotation to damage events (both the predictive "damage will be" projection on the attack line AND the final `LightWoundsDamageEvent` rendering).
- **FR-003**: The observer MUST compute the breakdown by tapping the same source-of-truth methods that produce the rolled/kept totals: `DefaultRollParameterProvider.get_skill_roll_params` for attack rolls, `DefaultRollParameterProvider.get_damage_roll_params` for damage. Per-school overrides (Bayushi, Akodo, etc.) MUST be reflected in the breakdown by either (a) the per-school provider returning a breakdown alongside the totals, OR (b) the observer reconstructing the breakdown by querying the contributing sources independently.
- **FR-004**: Cross-roll effects MUST appear in the downstream roll's breakdown. Specifically, when a character spends VP on an attack and the damage roll is inflated, the damage breakdown's source list MUST include `("VP on attack", +N rolled, +N kept)` where N = spent VP.
- **FR-005**: Annotations MUST be observer-attached (not new fields on the engine event classes). This preserves backward compatibility for tests and other formatters that consume the raw events.

**Trace formatter (rendering layer)**

- **FR-006**: `_format_attack_rolled` MUST render the attack roll's XkY with an inline parenthetical breakdown when `_detail_components` exists AND has more than one nonzero entry. Format: `XkY = N1k(M1) source-1 + N2k(M2) source-2 + ...`. Zero-contribution entries are omitted.
- **FR-007**: `_format_attack_rolled`'s "damage will be" projection MUST render the damage XkY with the same inline breakdown format.
- **FR-008**: `_format_combined_attack` (the combined-line variant for short attacks) MUST render the same breakdown as `_format_attack_rolled`.
- **FR-009**: `_format_lw_damage` (the final damage event) MUST render the damage XkY with the same inline breakdown.
- **FR-010**: `_format_modifier_breakdown` MUST NOT silently suppress when its components don't sum to the modifier value. Instead, render the partial breakdown and append `(unsourced: +K)` for the unaccounted portion.
- **FR-011**: `_format_tn` MUST render TN with raise-count attribution. Format: `vs TN N (base TN M)` becomes `vs TN N (base TN M, +X from K raises for {action})`. When the action has no raises (X = 0), the inline parenthetical reduces to just `(base TN M)`.
- **FR-012**: When the attack line shows both an attack-roll XkY and a "damage will be" XkY, both MUST have breakdowns; the renderings MUST be syntactically distinct so a reader doesn't confuse the two.

**`explain_modifier` audit (source attribution catalog)**

- **FR-013**: `explain_modifier` in `web/adapters/modifier_breakdown.py` MUST be audited for every modifier source currently produced by any in-scope school's mechanics. At minimum, the bare-`+5` case the dry-run surfaced (Bayushi double-attack bonus or whichever source produced it) MUST resolve to a labeled entry. Other school-attribution gaps MUST be enumerated and fixed.
- **FR-014**: Where `explain_modifier` cannot identify a modifier's source (legitimate gap in the catalog), the formatter MUST emit `(unsourced: +K)` rather than silently rendering a bare modifier.

**Cross-cutting consistency**

- **FR-015**: Existing tests on Mirumoto (`tests/test_mirumoto_school.py`), Ishi (`tests/test_ishi_school.py`), and Akodo (`tests/test_akodo_school.py`) that assert specific trace strings MUST be reviewed. Tests asserting partial trace strings (e.g., `assertIn("Akodo Special Ability", trace)`) usually remain valid. Tests asserting full-line equality MUST be updated to reflect the new breakdowns. The more-detailed trace IS the new contract.
- **FR-016**: The trace-auditor agent MUST re-run on at least one scenario per implemented school (Mirumoto, Ishi, Akodo) AFTER this audit lands. Each re-audit must report PASS on all 5 P1 gaps from the original dry-run.
- **FR-017**: Per-line self-explanation: each multi-source aggregate line MUST be self-explaining without reference to a preceding line. Tests must assert against per-line strings, not against concatenated multi-line strings.

**Workflow integration**

- **FR-018**: CLAUDE.md "New school implementation workflow" MUST be updated to add `trace-auditor` as a parallel checkpoint alongside `rules-auditor` after every substantial implementer batch. The workflow's per-step list grows to include the trace-auditor in step 6.

### Key Entities

- **`CombatObserver`** (`web/adapters/combat_observer.py`): annotates events with detail data the formatter renders. Gains new `_annotate_attack` and `_annotate_damage` behaviors that compute `_detail_components`.
- **`DetailedEventFormatter`** (`web/adapters/detailed_formatter.py`): renders user-visible trace lines. Methods affected: `_format_attack_rolled` (line ~417), `_format_combined_attack` (line ~1055), `_format_lw_damage` (line ~576), `_format_modifier_breakdown` (line ~649), `_format_tn` (line ~1015). All ~line numbers are pre-audit; new line numbers post-edit will differ.
- **`DefaultRollParameterProvider`** (`simulation/mechanics/roll_params.py`): source-of-truth for rolled/kept totals on each roll type. `get_skill_roll_params` (line ~132) and `get_damage_roll_params` (line ~115) need to expose the contributing pieces (ring, skill, school extras, weapon, VP-on-attack effect) so the observer can reconstruct the breakdown.
- **`explain_modifier`** (`web/adapters/modifier_breakdown.py`): catalog of modifier-source attributions. Each case maps a modifier value to a `(source_label, +N)` tuple. Needs an audit for missing cases.
- **`AttackRolledEvent`** / **`LightWoundsDamageEvent`** (`simulation/events.py`): NOT modified at the engine level. Their schemas remain unchanged. The observer wraps them with annotation fields.
- **`trace-auditor` agent** (`.claude/agents/trace-auditor.md`): a read-only Principle VII reviewer. Used during this audit's regression checkpoints AND going forward in school-implementation workflows.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 5 P1 gaps from the trace-auditor dry-run (2026-05-27) are closed. Re-running trace-auditor on the same 5th-Dan-Akodo-vs-5th-Dan-Bayushi scenario at `random.seed(1234)` returns zero P1 findings.
- **SC-002**: Existing 2962 tests continue to pass (no regressions). Test count grows by the number of new trace-string-assertion tests added (estimate: 15–25 new tests across attack/damage/WC/parry/TN breakdowns + cross-roll effects + unsourced-modifier rendering).
- **SC-003**: Coverage on `web/adapters/detailed_formatter.py` and `web/adapters/combat_observer.py` remains ≥ 90% globally per Constitution Principle VI.
- **SC-004**: `env/bin/ruff check .` PASS; `env/bin/mypy` PASS with zero strict-mode errors.
- **SC-005**: trace-auditor agent re-validates each currently-implemented school (Mirumoto, Ishi, Akodo) with a one-scenario re-audit. Each returns zero P1 findings.
- **SC-006**: A manual sweep of a 5th-Dan-vs-5th-Dan combat trace identifies, for every aggregate value (XkY rolls, +N modifiers, TN expressions), source attribution AND numeric breakdown. A rules-literate playtester unfamiliar with the codebase can read each trace line and reconstruct the math.
- **SC-007**: CLAUDE.md "New school implementation workflow" includes `trace-auditor` as a per-batch checkpoint, alongside `rules-auditor` and `combat-simulator`.
- **SC-008**: After implementation, the user's original bug case (`damage will be 10k10` with no breakdown) renders the full composition: `damage will be 10k10 = 4k2 katana + 6k0 Fire + 0k4 margin + 0k0 VP on attack` (or equivalent for whichever VP/raises actually fired). The user, re-running the combat, can read the line and trace every contribution to its source.

## Assumptions

- The breakdown data CAN be computed from the existing engine state without engine refactoring. If a per-school provider doesn't expose its component pieces, we can either query the school's contribution methods directly (e.g., `school.extra_rolled("attack")`) OR have the per-school provider return a breakdown tuple alongside the totals. If neither works for some specific source, that source is rendered as `(source: +N, unknown breakdown)` and flagged for follow-up.
- The "5 P1 gaps" enumerated in the spec are the COMPREHENSIVE set per the trace-auditor dry-run. A follow-up audit during implementation may surface more (e.g., parry-roll undecomposed, iaijutsu-roll undecomposed). These get added as additional FRs during implementation if uncovered.
- Existing tests that assert specific trace strings will need updates. The autonomous run authorizes inline test updates as part of the implementation work; if more than 20 tests need updating, flag for end-of-run user review.
- The trace formatter is the SOLE user-visible rendering path. Other adapters (e.g., debug logs in `simulation/log.py`) are NOT subject to Principle VII. This audit's scope ends at `web/adapters/detailed_formatter.py`.
- Adding the trace-auditor checkpoint to CLAUDE.md will lengthen each future school workflow by one parallel-agent invocation per batch (negligible cost given the existing agent budget).
- The "unsourced placeholder" convention (`(unsourced: +K)`) is a temporary signal — a Principle VII violation that's visible rather than hidden. Once all sources are catalogued in `explain_modifier`, the placeholder should never appear in a passing run. Tests SHOULD specifically check for its absence in school-implementation runs.
- Cross-roll effects beyond VP-on-attack → damage are out of scope for this audit. If AP-on-X → Y or conviction-on-X → Y effects exist with similar invisibility, they get their own follow-up.

## Out of scope

- Refactoring how the engine computes raises, VP-spend effects, or any other rule mechanics. This audit surfaces existing data; it does not change semantics.
- Adding NEW source attributions for school abilities that don't exist yet (each school's source attribution is the school's own spec's responsibility, not this audit's).
- UI/Streamlit changes beyond surfacing the trace as-formatted by `detailed_formatter`. The Streamlit page reads `format_history()`; if that produces better-attributed lines, the UI inherits the improvement for free.
- Internationalization / localization of source labels. Labels are English; that's fixed.
- Performance optimization. The breakdown computation runs once per event and is dominated by the engine's existing dice rolling.
- A redesign of the trace's visual style (e.g., colored output, font choices, emoji selection). Style remains as-is; only content changes.
- Adding source attribution to non-roll trace lines (e.g., conversation events, state-change notifications). Principle VII's scope is roll outcomes per its text; this audit honors that scope.
