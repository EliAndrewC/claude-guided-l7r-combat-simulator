# Feature Specification: Combat Trace UX Fixes

**Feature Branch**: `009-trace-ux-fixes`

**Created**: 2026-05-27

**Status**: Draft (autonomous run)

**Input**: `trace-reader` agent's dry-run report (2026-05-27) on the calibration combat at `random.seed(1234)` (300-XP 5th-Dan Akodo vs 300-XP 5th-Dan Bayushi). Six user-visible UX issues identified, plus two engine concerns deferred to other agents.

**Run Mode**: Autonomous. Decisions logged in `OPEN_QUESTIONS.md` for end-of-run review.

**Why this matters**: The combat trace is the primary artifact a playtester uses to understand a combat outcome. After specs 005, 007 introduced rich attribution and a bulleted layout, multiple UX problems surfaced that make the trace contradict itself OR show information that doesn't help the reader. None of these are engine bugs — the data is correct underneath — but the presentation defeats the principle that the trace should be self-explaining (Constitution VII).

## Clarifications

### Session 2026-05-27 (autonomous; pre-answered per project conventions + dry-run findings)

- Q: Floating-bonus integration into inline summary — format? → A: **inline arithmetic** (`"→ 19, +15 (Akodo 3rd Dan floating bonus) = 34 vs TN 30"`). Reader sees the math reconciled on the line itself.
- Q: Feint damage rendering — suppress entirely vs. minimal annotation? → A: **suppress entirely**. When an action is a feint AND damage dealt is 0, no damage line, no projection. The reader sees: feint attack → school-ability event fires → combat moves on. If a future special-ability feint deals damage, revisit.
- Q: `"unsourced"` literal — replace with what? → A: investigate the actual source and label correctly. Fallback (if unidentifiable): a less attention-grabbing form like `"(see preceding line)"`.
- Q: Cross-renderer consistency fix — patch each renderer vs. extract shared helper? → A: **extract shared helper** (`web/adapters/_breakdown_format.py`). Avoids future regressions when one renderer is modified without the other.
- Q: Should `trace-reader` become a mandatory workflow checkpoint? → A: **Yes** — added to CLAUDE.md alongside `trace-auditor`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A reader sees the same component description across renderers (Priority: P1)

A playtester opens the Streamlit UI (BulletedRenderer output) and also examines the text trace (TextRenderer output). For the same attack's damage breakdown, both surfaces describe the 10k10-overflow component identically — either both say `"+6 from 3 dropped dice in excess of 10k10"` (the new form) or both say `"-3k3 from dice in excess of 10k10"` (the old form). Not one each.

**Why this priority**: This is the Wrong-severity bug. Cross-renderer disagreement is the most damaging kind of UX failure — the reader literally cannot trust either surface.

**Independent Test**: Build the calibration combat. Run both `TextRenderer().render_lines(entries)` and `BulletedRenderer().render(entries)`. For each attack's damage-component breakdown, assert the rendering of the 10k10-overflow component is identical (string-equal up to formatting wrapping).

### User Story 2 — Feint outcomes render coherently (Priority: P1)

A playtester sees a feint attack succeed. The trace shows: (a) the attack line indicating "feint succeeds, TN met", (b) the school-ability event firing (TVP gain for Akodo, floating bonus for Bayushi), (c) no damage line, no projection, no breakdown of a damage-roll that didn't deal damage.

**Why this priority**: Issues 2, 4, 6 of the dry-run report all stem from feint damage handling. Fixing it cleanly eliminates three contradictions in one place.

**Independent Test**: Run the calibration combat. Walk the trace lines. For each feint event:
- Assert NO `"damage will be: XkY"` projection appears on the attack line.
- Assert NO `"💥 Damage:"` line follows the feint attack.
- Assert the school-ability event (TVP / floating bonus) DOES appear cleanly on its own line.
- Assert the feint's outcome is visible — either via the attack-line "HIT!" plus the school-ability event, OR via an explicit "feint succeeded" annotation.

### User Story 3 — Floating-bonus consumption is integrated into the attack outcome (Priority: P1)

A playtester sees an attack hit a TN with a floating bonus consumed. The inline math on the attack line reconciles: `→ kept_sum, +bonus (source) = total vs TN N — HIT!`. The reader doesn't need to scan the next line to figure out why the attack hit despite the raw kept sum being below TN.

**Why this priority**: Issue 3 of the dry-run report. The inline math currently looks like a contradiction (`→ 19 vs TN 30 — HIT!` makes no sense without the bonus context).

**Independent Test**: Construct a combat where a character consumes a floating bonus on an attack roll. Assert the attack line includes the bonus and source inline in the format `"→ kept_sum, +bonus (source) = total vs TN N"`. Assert no separate "floating bonus consumed" line follows that would have been the previous explanation.

### User Story 4 — The literal word "unsourced" does not appear in user-facing labels (Priority: P1)

A playtester reads the trace and never sees the literal token `"unsourced"`. Modifier breakdowns either show a real source attribution OR (when the source genuinely cannot be identified) show a less attention-grabbing fallback like `"(see preceding line)"` that doesn't read as a bug message.

**Why this priority**: Issue 5 of the dry-run report. The word `"unsourced"` is a Principle VII compliance marker — its presence in user-visible output is an admission of an attribution gap. Per spec 005's FR-014, it was visible-by-design as a development signal; in production traces it's confusing.

**Independent Test**: `grep -E "\\bunsourced\\b" <trace_output>` returns no matches in normal combat traces. If a modifier genuinely lacks attribution (a development-only signal), the rendering is `"(see preceding line)"` or similar non-alarming wording.

### User Story 5 — `trace-reader` becomes a per-batch workflow checkpoint (Priority: P2)

A future developer running the school-implementation workflow gets a `trace-reader` audit after every substantial implementer batch, alongside `rules-auditor`, `combat-simulator`, and `trace-auditor`. The workflow document in CLAUDE.md reflects this.

**Why this priority**: Procedural improvement. Catches future regressions automatically.

**Independent Test**: `grep -A 10 "Implement" CLAUDE.md` shows `trace-reader` listed in the per-batch checkpoint list.

### Edge Cases

- **Feint that DOES deal damage** (e.g., a hypothetical future special-ability feint): the spec assumes feints always deal 0 LW. If an exception arises, the damage-line suppression rule must be revisited. Pre-resolution: defer until such a feint exists in the engine.
- **Multiple floating bonuses consumed on one attack** (e.g., Akodo with both a 3rd Dan floating bonus AND a banked attack bonus from elsewhere): the inline form should list each source separately (`"→ 19, +15 (Akodo 3rd Dan), +5 (other source) = 39 vs TN 30 — HIT!"`).
- **Floating bonus consumed on attack but attack still misses** (the bonus wasn't enough): `"→ 19, +5 (source) = 24 vs TN 30 — MISS"`. The reader sees the bonus was used and the attack still failed.
- **Modifier source identified as "Akodo 4th Dan VP raises"** (the suspected `"unsourced"` origin): once the source is identified, the modifier shows the correct attribution; the literal `"unsourced"` disappears for this case. Future genuine `unsourced` cases (if any) use the non-alarming fallback.
- **The new shared `_breakdown_format` helper is imported by tests** — verify both renderers' tests still pass when the helper is the canonical source of truth.
- **A future renderer (e.g., JsonRenderer) wants to format dropped-dice components**: it imports the shared helper too. The helper is the single source of truth for this formatting decision.

## Requirements *(mandatory)*

### Functional Requirements

**Issue 1 — Cross-renderer dropped-dice consistency**

- **FR-001**: A new shared helper module `web/adapters/_breakdown_format.py` MUST host the `"+X from N dropped dice/die in excess of 10k10"` formatting logic for the 10k10-overflow synthetic-component case. The helper exposes one function (e.g., `format_breakdown_component(rolled, kept, source) -> str`) callable by both TextRenderer and BulletedRenderer.
- **FR-002**: TextRenderer's `_format_one_component` (currently in `web/adapters/text_renderer.py`) and detailed_formatter's `_format_one_component` (currently in `web/adapters/detailed_formatter.py`) MUST delegate to the shared helper rather than duplicating the special-case logic.
- **FR-003**: BulletedRenderer's `_format_component_bullet` (currently in `web/adapters/bulleted_renderer.py`) MUST delegate to the shared helper. The bulleted form (`- {content}`) wraps the helper's output but does not re-implement the special-case detection.
- **FR-004**: An automated test MUST verify cross-renderer consistency: for every multi-source aggregate in a calibration combat trace, the TextRenderer and BulletedRenderer descriptions of the same component must agree (string-equal up to whitespace/markdown wrapping). When they disagree, the test surfaces the specific component as a Wrong-severity regression.

**Issues 2, 4, 6 — Feint damage rendering**

- **FR-005**: When an attack action is a feint AND the resulting damage dealt is 0, NO `"damage will be: XkY"` projection MUST appear on the attack line. The reader sees `"⚔️ attacks <target> (feint) — XkY [...] vs TN N — HIT!"` followed by the school-ability event(s), no damage projection.
- **FR-006**: When the engine emits a `LightWoundsDamageEvent` whose action is a feint AND damage dealt is 0, NO damage rendering MUST occur. The event is silently absorbed by the formatter (it's still in `engine.history()` for downstream consumers like tests, but neither TextRenderer nor BulletedRenderer emits a line for it).
- **FR-007**: The trace-reader regression test MUST verify the feint-damage suppression: for every feint attack in a sample combat, no `"💥 Damage:"` line follows, no `"damage will be:"` projection precedes, and no bulleted damage breakdown appears.

**Issue 3 — Floating-bonus inline integration**

- **FR-008**: When an attack-rolled event is followed by a `SpendFloatingBonusEvent` from the same actor on the same skill, the floating bonus's value and source MUST be integrated into the attack line's inline arithmetic. Format: `"→ kept_sum, +bonus (source) = total vs TN N — outcome"`. The `total` is `kept_sum + modifier_components + floating_bonus_value`. The outcome (HIT / MISS) is computed from `total` (not from the raw `kept_sum`).
- **FR-009**: When multiple floating bonuses are consumed on the same attack, they MUST each appear in the inline arithmetic with their own source attribution: `"→ kept_sum, +bonus1 (source1), +bonus2 (source2) = total vs TN N — outcome"`.
- **FR-010**: The standalone `"✨ +N (source floating bonus consumed)"` line that previously appeared after the attack-outcome line MUST be suppressed when its bonus is already integrated into the attack-line inline arithmetic. The reader sees one consolidated line, not two contradictory lines.
- **FR-011**: When a floating bonus is consumed but the attack STILL misses, the inline arithmetic still reflects the consumption: `"→ kept_sum, +bonus (source) = total vs TN N — MISS"`. The reader sees the bonus was used.

**Issue 5 — "unsourced" literal**

- **FR-012**: The literal word `"unsourced"` MUST NOT appear in user-visible trace output under normal combat conditions. A `grep -E "\\bunsourced\\b"` check on a calibration combat trace MUST return zero matches.
- **FR-013**: Investigate the specific `+5 (unsourced)` instance in the dry-run report (Round 1 line 228 of the calibration combat). Identify whether the source is the Akodo 4th Dan VP-on-WC modifier (most likely) OR another source. Add the corresponding case to `explain_modifier` in `web/adapters/modifier_breakdown.py`.
- **FR-014**: When `explain_modifier` genuinely cannot identify a modifier's source (i.e., a development-only edge case), the formatter MUST render a non-alarming fallback (e.g., `"(see preceding line)"`) rather than the bare `"unsourced"` token. The previous Principle VII signal that `(unsourced: +K)` provided is still satisfied (the gap is visible) but the wording is non-alarming.

**Issue: `trace-reader` workflow integration**

- **FR-015**: CLAUDE.md's "New school implementation workflow" step 6 (per-batch checkpoint list) MUST include `trace-reader` alongside `rules-auditor`, `combat-simulator`, and `trace-auditor`. The list grows from 3 agents to 4.
- **FR-016**: The workflow description MUST note that `trace-reader` complements `trace-auditor` — they review the same output but check different properties (Principle VII compliance vs. UX intuitiveness).

**Cross-cutting**

- **FR-017**: Every change in this spec is formatter-only. NO engine ordering changes, NO new events, NO new annotations. The `_detail_*` annotation fields on events remain unchanged.
- **FR-018**: Coverage on the new `_breakdown_format.py` module MUST be 100% per Constitution Principle VI v1.3.0.
- **FR-019**: Existing trace-assertion tests (~3000+ in current suite) MUST continue to pass. If a test fails because of a deliberate text change (e.g., the feint damage line disappearing), the test is updated to reflect the new expected behavior; flag the diff for user verification if more than 10 existing tests need updating.

### Key Entities

- **`_breakdown_format.py`** (NEW): shared helper module for breakdown-component formatting. Single source of truth for the "+X from N dropped dice" rendering decision.
- **`detailed_formatter.py::_entry_attack`** + **`_entry_lw_damage`** + similar entry-production methods: extended to detect (a) floating-bonus consumption on the same roll, (b) feint actions with 0 LW dealt. These detections produce different TraceEntry shapes (or fields) that the renderers consume.
- **TextRenderer** and **BulletedRenderer**: consume the updated TraceEntry shapes. Renderers don't re-detect feint/floating-bonus; they read the entry fields.
- **`explain_modifier`** in `web/adapters/modifier_breakdown.py`: gains a case for Akodo 4th Dan VP-on-WC (and possibly other previously-unsourced cases discovered during investigation).
- **`trace-reader` agent**: becomes part of the per-batch workflow checkpoint after this spec lands.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cross-renderer test passes — for every multi-source aggregate in the calibration combat, TextRenderer and BulletedRenderer descriptions match (string-equal up to formatting wrapping).
- **SC-002**: Feint regression test passes — for every feint attack in a sample combat, no damage line, no damage projection, no damage breakdown.
- **SC-003**: Floating-bonus inline test passes — every attack that consumes a floating bonus shows the bonus in the inline arithmetic on the attack line, AND the standalone consumption line does not appear.
- **SC-004**: `grep -E "\\bunsourced\\b" <calibration_trace>` returns zero matches.
- **SC-005**: CLAUDE.md's "New school implementation workflow" step 6 lists `trace-reader` as a per-batch checkpoint.
- **SC-006**: All existing tests (3739+ in current suite) continue to pass after the refactor. Any test updates that ARE made reflect intentional text changes (no cosmetic drift); flag for review if more than 10 tests need updating.
- **SC-007**: `env/bin/ruff check .` PASS; `env/bin/mypy` PASS strict mode; coverage on new `_breakdown_format.py` = 100%.
- **SC-008**: Re-running `trace-reader` on the calibration combat after the fixes reports: Issue 1 PASS (cross-renderer consistency), Issues 2/4/6 PASS (feint damage), Issue 3 PASS (floating-bonus inline), Issue 5 PASS (no "unsourced").

## Assumptions

- The four primary issues (1, 2/4/6, 3, 5) are independent — each fix can land in its own batch without conflicting with the others.
- The `+5 (unsourced)` instance in the dry-run trace is the Akodo 4th Dan VP-on-WC modifier (highest-probability source given the surrounding context). If investigation reveals a different source, the fix scope extends but the spec's structure is unchanged.
- Feint engine semantics are correct (feints don't deal LW); the issue is purely presentation. If the engine actually deals damage on some feints, that's a `rules-auditor` follow-up, not part of this spec.
- The floating-bonus integration is a formatter-only change. The engine's event sequence (attack → outcome → bonus-consumption) stays the same; the formatter notices the consumption when producing the attack-line text.
- The shared `_breakdown_format` helper is the right abstraction; both renderers' tests pass after the migration without restructuring.
- Existing trace tests will need < 10 updates total (most are partial-string asserts via `assertIn`, which still match the new traces).

## Out of scope

- Engine-side ordering changes (e.g., emitting bonus-consumption events before attack-outcome events).
- Rules-correctness investigations flagged by the dry-run agent (feint dealing 15 LW vs. 0 LW variability; double-consumption math). Those go to `rules-auditor` and `combat-simulator` separately.
- New event types, new observer annotations, new engine state.
- HTML renderer refactoring (still consumes text lines via TextRenderer).
- Streamlit UI restructuring beyond what naturally follows from the fixed BulletedRenderer output.
- Performance optimization.
- Mobile-friendly compact layouts.
- Iaijutsu-specific or void-negation-specific rendering improvements (not surfaced by the dry-run on this calibration combat; would be a separate spec).
