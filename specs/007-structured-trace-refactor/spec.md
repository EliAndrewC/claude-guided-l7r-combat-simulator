# Feature Specification: Structured Trace Refactor (TraceEntry + BulletedRenderer)

**Feature Branch**: `008-structured-trace-refactor`

**Created**: 2026-05-27

**Status**: Draft (autonomous run)

**Input**: User direction (2026-05-27): "We should pass the data to the frontend in a way which supports many different formattings... bulleted lists which add up the bonuses... structured form that allows us to construct this kind of layout (and possibly structure it differently if viewed in a different view or context)."

**Run Mode**: Autonomous. Decisions logged in `OPEN_QUESTIONS.md` for end-of-run review.

**Why this matters**: After spec 005 added inline source attribution to every multi-source aggregate, the trace lines became too dense for one-line presentation. The user observed a 350+ character line on a single attack with VP+modifier+TN+predicted-damage breakdowns. The UI needs structured access to the components so it can lay them out per view (bulleted summary today; potentially collapsible expanders, JSON export, mobile-friendly compact view, etc., in the future).

## Clarifications

### Session 2026-05-27 (autonomous; pre-answered per project conventions + user input)

- Q: Should `BulletedRenderer` Markdown be wrapped in `st.expander` per round/phase? → A: **No for v1.** Inline bulleted lists. Expanders are a v2 if traces grow too long.
- Q: Bulleted form for single-source aggregates (e.g., a WC where only the ring contributes)? → A: **One line, no bullet sub-list.** The bullet form only fires when there are 2+ components.
- Q: Nested vs. flat for "damage will be" projections on attack lines? → A: **Nested** — the damage projection becomes a sub-bullet of the attack entry.
- Q: Where does the dice array `[18, 9, 9, ...]` go in the bulleted form? → A: **Separate line under the bulleted breakdown.** Hiding loses information; inline gets too wide.
- Q: Should the engine ever import `TraceEntry`? → A: **No.** Per Constitution Principle II, `simulation/` never imports from `web/`. `TraceEntry` is purely a `web/` concept.
- Q: Migration backstop if byte-identical text proves impossible? → A: **Small whitespace/cosmetic differences are acceptable if they're improvements; substantive differences are not** — flag for user review.
- Q: Granularity of `TraceEntry` instances — one per logical user-visible "thing" or one per engine event? → A: **One combined entry per logical operation**, matching the current formatter's composition (e.g., "spends 1 VP on attack → attacks Akodo" is ONE entry that owns both the VP spend and the attack roll).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A playtester reads a bulleted attack-line in the Streamlit UI (Priority: P1)

A simulator user runs a combat and opens the Streamlit UI. The trace renders each attack as a header line + bulleted component breakdown rather than a single 350-character line:

```
Phase 4 | Courtier ⚔️ attacks Akodo (attack) — 9k4 + 5 → 48 vs TN 30 — HIT!
  • Attack roll: 9k4
    - 3k3 Fire ring
    - 5k0 attack skill
    - 1k1 VP on attack
  • Modifier: +5 (Bayushi 2nd Dan free raise)
  • Dice: [18, 9, 9, 7, 6, 6, 4, 3, 2] → 43 kept
  • Damage will be: 10k2
    - 4k2 katana
    - 3k0 Fire ring
    - 3k0 margin (+15 over TN)
```

**Why this priority**: This is the user's reported scenario. The bulleted form is the visible payoff of the refactor.

**Independent Test**: Build a deterministic combat (Bayushi vs Akodo, seed=1234). Invoke `BulletedRenderer().render(entries)` on the resulting trace entries. Assert the Markdown output contains the bullet structure above for the attack event (loose regex match: header line + indented bullet list + sub-bullets per component + dice line).

### User Story 2 — Existing text trace output is byte-identical (Priority: P1)

A developer who runs `env/bin/pytest tests/ -q` sees all ~50+ existing trace-string-assertion tests pass without modification. The text output of `format_history()` is byte-identical to the pre-refactor output.

**Why this priority**: This is the regression guard. The refactor is "wrong by definition" if it changes the text output as a side effect.

**Independent Test**: Run the full pytest suite. Test count must be ≥ baseline (3538) plus the new bulleted-renderer tests. Zero existing trace-assertion test failures. If even one test fails because the text changed cosmetically, document AND flag for user review per pre-resolution (g).

### User Story 3 — The structured form is reusable (Priority: P2)

A developer wants to add a new view of the trace (e.g., a compact mobile view, a JSON export, a CSV log). They build a new renderer that takes `list[TraceEntry]` and produces their output format. They don't touch the formatter, observer, or engine.

**Why this priority**: This is the architectural payoff. Demonstrates that the refactor delivers extensibility, not just one new layout.

**Independent Test**: As an acceptance demonstration, write a minimal `JsonRenderer` (toy implementation; not shipped to UI) that takes `list[TraceEntry]` and emits one JSON object per entry. Assert it covers every entry type without touching `DetailedEventFormatter` or `CombatObserver`. This test serves as the architectural proof; the JsonRenderer itself is throwaway (or kept as a reference).

### User Story 4 — TraceEntry preserves all information (Priority: P1)

For every event the current formatter renders, the corresponding `TraceEntry` captures every datum used in the rendering. No information is lost in the conversion.

**Why this priority**: If information is lost, the TextRenderer can't reproduce byte-identical output (US2 fails) AND BulletedRenderer can't render meaningfully (US1 fails).

**Independent Test**: For each `_format_*` method in the existing formatter, write a test that builds a synthetic event, calls `entries(history)` to get the structured form, calls `TextRenderer().render(entries)` to produce text, and asserts the text matches what `format_history(history)` produced pre-refactor. This is the "round-trip" test.

### User Story 5 — TextRenderer + BulletedRenderer + new modules reach 100% coverage (Priority: P1)

Per Constitution Principle VI v1.3.0, all new code in `trace_entries.py`, `bulleted_renderer.py`, and the `TextRenderer` class must reach 100% line coverage.

**Why this priority**: This is the constitution gate. Without it, the post-change checklist fails.

**Independent Test**: `env/bin/pytest tests/ --cov=web/adapters/trace_entries --cov=web/adapters/bulleted_renderer --cov-report=term` reports 100%. The pragma-audit meta-test passes.

### Edge Cases

- **An event type the new `entries()` method doesn't handle**: the method must not silently drop the event. Falls back to a `RawTextEntry(line: str)` placeholder that the TextRenderer renders verbatim (preserves byte-identical output). If a `RawTextEntry` ever appears in practice, it's a defect (every event MUST have its own entry type). Tests verify zero `RawTextEntry` instances in a representative combat.
- **Backward-compat consumer**: a future test or external script calls `format_history(history)` expecting `list[str]`. The method's signature MUST stay the same. The implementation routes through `entries() + TextRenderer().render()` internally.
- **Composed entries**: "spends 1 VP on attack → attacks Akodo" is currently ONE trace line built from TWO events (SpendVoidPointsEvent + AttackRolledEvent). Per pre-resolution, this becomes ONE `AttackEntry` that owns the VP spend AND the attack roll. The entry's `vp_spent: int | None` field captures the prefix.
- **Empty / no-event combats**: `entries([])` returns `[]`. Both renderers handle the empty list (produce `[]` / empty string).
- **A renderer being called with a `TraceEntry` type it doesn't know**: should fail loudly (`raise NotImplementedError` or equivalent), NOT silently drop. Defensive guards have `# pragma: no cover` per Principle VI.

## Requirements *(mandatory)*

### Functional Requirements

**TraceEntry definition (`web/adapters/trace_entries.py`, NEW)**

- **FR-001**: A new module `web/adapters/trace_entries.py` MUST define a tagged-union of dataclass-based `TraceEntry` types — one per logical event category in the current formatter. The exact list is finalized during `/speckit-plan`; minimum coverage: round header, phase header, status block, take-action/attack composite, attack-rolled, counterattack-rolled, parry-rolled, iaijutsu-rolled, LW damage, SW damage, wound-check declared, wound-check rolled, keep-LW, take-SW, gain-TVP, spend-VP, gain-floating-bonus, spend-floating-bonus, school-negated, akodo-5th-dan-counter, initiative.
- **FR-002**: Component types: `ComponentDelta(source: str, rolled: int, kept: int)` and `ModifierDelta(source: str, amount: int)`. Both are immutable (`frozen=True`) dataclasses.
- **FR-003**: Each `TraceEntry` subclass MUST carry every datum the current formatter uses to render it. The set of fields is verified by US4 round-trip tests.
- **FR-004**: `TraceEntry` types use `Literal["..."]` discriminator fields (e.g., `kind: Literal["attack"]`) so renderers can dispatch via a single `match` / `dict` lookup.
- **FR-005**: `trace_entries.py` MUST NOT import from `simulation/`. Imports go in the opposite direction only (the formatter, which lives in `web/`, imports both `simulation` events AND `trace_entries`).

**Entry production (`DetailedEventFormatter.entries()`, refactor)**

- **FR-006**: `DetailedEventFormatter` MUST grow an `entries(history: list[Event]) -> list[TraceEntry]` method. Walks the event history with the same logic the current `format_history` uses, but emits `TraceEntry` instances instead of strings.
- **FR-007**: Every event the current formatter handles MUST be converted to a `TraceEntry` of the appropriate type. No silent drops, no `RawTextEntry` fallbacks in correct operation.
- **FR-008**: The `entries()` method preserves the current formatter's event-composition logic. E.g., when the current formatter combines a `SpendVoidPointsEvent` immediately followed by a `TakeAttackActionEvent` into one trace line, the new `entries()` method emits ONE `AttackEntry` with `vp_spent` populated.

**TextRenderer (`TextRenderer` class, replaces existing `_format_*` methods)**

- **FR-009**: A new `TextRenderer` class MUST consume `list[TraceEntry]` and produce `list[str]` matching the pre-refactor output of `format_history()` byte-for-byte. The renderer method name is `render_lines(entries: list[TraceEntry]) -> list[str]` (alias `render` accepts both list and single entry for convenience).
- **FR-010**: `DetailedEventFormatter.format_history(history)` MUST become a thin wrapper: `return TextRenderer().render_lines(self.entries(history))`. Same public signature; same output; no caller changes.
- **FR-011**: The existing 50+ trace-string-assertion tests MUST pass unchanged after the refactor. If even one fails, the refactor is wrong by definition.

**BulletedRenderer (`web/adapters/bulleted_renderer.py`, NEW)**

- **FR-012**: A new module `web/adapters/bulleted_renderer.py` MUST define a `BulletedRenderer` class with a `render(entries: list[TraceEntry]) -> str` method that produces Markdown.
- **FR-013**: Multi-source aggregates (attack/parry/counterattack/iaijutsu/WC rolls and damage rolls with > 1 component) MUST render as a bulleted breakdown. Format:
  ```
  <header line summarizing roll + outcome>
    - <component_1.rolled>k<component_1.kept> <component_1.source>
    - <component_2.rolled>k<component_2.kept> <component_2.source>
    - ...
  ```
- **FR-014**: Single-source aggregates (and aggregates with 0 components) MUST render as a single line (no bullet list). The bullet form only fires when `len([c for c in components if c.rolled or c.kept]) >= 2`.
- **FR-015**: Modifiers (`+N (source)`) get their own bullet underneath the component breakdown when present.
- **FR-016**: The dice array (`[18, 9, ...]`) gets its own line under the bullets, formatted as `Dice: [...]` or equivalent.
- **FR-017**: TN with raises renders as `vs TN N (base TN M + K raises × +5 for {action})` on the header line.
- **FR-018**: Damage projection (predictive "damage will be") nests under the attack entry as a sub-bullet group. The actual `DamageEntry` later in the trace gets its own top-level entry.
- **FR-019**: Floating-bonus gain/consume entries render as one line with source attribution (e.g., `✨ Akodo 3rd Dan: gained floating bonus +20 (margin 18 ÷ 5 × attack skill 5)`).
- **FR-020**: VP-spend entries render as one line (no bullets) since they're single-source.
- **FR-021**: Round headers and phase headers render as Markdown headings (`## Round N`, `### Phase N`).
- **FR-022**: Status blocks render with each character's status on its own line.

**Streamlit UI wiring (`web/views/3_Run_Simulation.py`, edit)**

- **FR-023**: The Streamlit page MUST consume the bulleted form via `BulletedRenderer().render(entries)`. The existing `render_play_by_play_html` call continues to work (it consumes text lines; new code doesn't break it), but the new path is the primary UI surface.
- **FR-024**: The Streamlit page uses `st.markdown(bulleted_text)` (without `unsafe_allow_html=True` — pure Markdown). If the bulleted form requires special formatting that pure Markdown can't express, fall back to HTML with documented `unsafe_allow_html=True`.

**Coverage (per Constitution Principle VI v1.3.0)**

- **FR-025**: `web/adapters/trace_entries.py` MUST reach 100% coverage. The pragma-audit meta-test (`tests/test_coverage_pragma_audit.py`) verifies no unjustified pragmas.
- **FR-026**: `web/adapters/bulleted_renderer.py` MUST reach 100% coverage.
- **FR-027**: The `TextRenderer` class (wherever it lives — `web/adapters/text_renderer.py` is one option) MUST reach 100% coverage. The existing trace-string tests are the primary coverage source.
- **FR-028**: New tests at `tests/test_bulleted_renderer.py` cover the bulleted form per-entry-type. Estimate: 30-50 tests.
- **FR-029**: New tests at `tests/test_trace_entries.py` cover the `TraceEntry` dataclass behavior (construction, immutability, discriminator). Estimate: 10-20 tests.
- **FR-030**: New round-trip tests at `tests/test_text_renderer_roundtrip.py` verify that `format_history(h) == TextRenderer().render_lines(entries(h))` for every event type. Estimate: 25-35 tests (one per `_format_*` method).

**Architectural compliance**

- **FR-031**: `simulation/` MUST NOT import from `trace_entries` or any of the renderers. Engine purity per Constitution Principle II.
- **FR-032**: The `entries()` method MUST NOT throw on any event in the existing test suite's combats. Verified by running all existing combat-producing tests through `entries()` and asserting no exceptions.

### Key Entities

- **`TraceEntry`**: discriminated union of dataclasses, one per logical user-visible trace element. Lives in `web/adapters/trace_entries.py`.
- **`ComponentDelta`** / **`ModifierDelta`**: shared fields used in multiple entry types (e.g., attack-roll components vs. modifier breakdown).
- **`DetailedEventFormatter`** (existing): grows `entries()` method; refactored to make `format_history()` a thin wrapper.
- **`TextRenderer`** (new): produces text lines from entries. Replaces the `_format_*` methods of the existing formatter.
- **`BulletedRenderer`** (new): produces Markdown for the Streamlit UI.
- **Streamlit page** (`web/views/3_Run_Simulation.py`): consumes the bulleted form.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every existing trace-assertion test (~50+) passes after the refactor with zero modification. Verified by running `env/bin/pytest tests/` and assert all PASS at count ≥ baseline + new tests.
- **SC-002**: `BulletedRenderer().render(entries(history))` on a 300-XP 5th-Dan-Akodo-vs-5th-Dan-Bayushi combat (seed=1234) produces Markdown that includes a bullet structure for every attack and damage roll with > 1 source component.
- **SC-003**: `web/adapters/trace_entries.py` reports 100% coverage. `web/adapters/bulleted_renderer.py` reports 100%. The renderer module that hosts `TextRenderer` reports 100%.
- **SC-004**: A new (throwaway) `JsonRenderer` written in the test file `tests/test_renderer_extensibility.py` consumes `list[TraceEntry]` and produces JSON for every entry type, demonstrating the architectural extensibility — without touching the formatter, observer, or engine.
- **SC-005**: `env/bin/ruff check .` PASS; `env/bin/mypy` PASS with zero strict-mode errors.
- **SC-006**: `trace-auditor` re-validation on the calibration combat reports zero new P1 gaps (text output's Principle VII compliance preserved).
- **SC-007**: Streamlit page `web/views/3_Run_Simulation.py` correctly renders the bulleted form via `st.markdown` (verified via the Streamlit smoke check at Quality Gate 5, NOT unit tests since the page itself is excluded from coverage).
- **SC-008**: `simulation/` files contain zero new imports from `trace_entries` or any renderer. Verified by `grep -r "trace_entries\|text_renderer\|bulleted_renderer" simulation/` returning no matches.

## Assumptions

- The current `_detail_*` annotation fields on events are sufficient for the structured form. If a piece of information is currently rendered but not annotated (e.g., computed inline by the formatter), it gets either (a) added as an annotation OR (b) computed during entry production. No engine-level changes.
- The `DetailedEventFormatter`'s state (e.g., `_pending_damage_context`) used to correlate events across the history is preserved. The `entries()` method walks the same state, just emits structured objects instead of strings.
- The byte-identical-text invariant holds for all current trace lines. If a specific line is provably impossible to reproduce without invasive refactor (e.g., a numeric format quirk), document and flag for user review.
- `BulletedRenderer` produces pure Markdown; Streamlit's `st.markdown(text)` (without `unsafe_allow_html`) renders it correctly.
- All ~25 existing `_format_*` methods map to a finite set of `TraceEntry` types. The exact mapping is enumerated in `/speckit-plan`'s `data-model.md`.
- The test suite produces a representative sample of every event type. Round-trip tests cover the per-entry-type space.
- No performance concerns. Both renderers are sub-second on typical combats.

## Out of scope

- New engine event types or annotation kinds (the engine emits the same events; the observer attaches the same annotations).
- Refactoring the existing HTML renderer (`web/adapters/html_renderer.py`) to consume `TraceEntry`. It continues to consume text lines for now; that's a future feature.
- Per-school formatter customizations.
- Internationalization of source labels.
- A configuration system for switching renderers dynamically.
- A JSON / API output format as a shipping feature. (A throwaway JsonRenderer demonstrates the extensibility; not deployed.)
- Performance optimization.
- `st.expander` per round/phase (deferred to v2; current bulleted form is good enough).
- Mobile-friendly compact view (a future renderer would consume the same `TraceEntry` types).
- Refactoring tests that USE `format_history()` to use the structured form instead (text output is byte-identical; tests stay).
- Updates to the `trace-auditor` agent (it reads text output, which is unchanged).
- Coverage on Streamlit page modules (`web/views/`) — these remain excluded per Principle VI's UI-entry-point category.
