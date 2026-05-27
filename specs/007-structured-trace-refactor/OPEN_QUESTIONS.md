# Open Questions for End-of-Run Review (Structured Trace Refactor)

Run started 2026-05-27 on `008-structured-trace-refactor`.

## Q1 — Where do `TextRenderer` and `BulletedRenderer` live?

**Decision**: New modules `web/adapters/text_renderer.py` and `web/adapters/bulleted_renderer.py`. Both are siblings of `trace_entries.py` + `detailed_formatter.py` + `combat_observer.py`. Lives in `web/adapters/` because they consume entries that came from observer-annotated events — the same architectural layer as the existing formatter.

## Q2 — Should `entries()` be a method on `DetailedEventFormatter` or a free function?

**Decision**: Method on `DetailedEventFormatter`. The walk requires the formatter's state (`_pending_damage_context`, `_pending_iaijutsu_context`, etc.) to correlate composed events. Promoting it to a free function would require carrying the state externally.

## Q3 — `vp_spent` field on `AttackEntry` — single int or list of (source, amount)?

**Decision**: Single `int` plus `vp_skill: str | None` for the rare case where the skill differs (e.g., Akodo 4th Dan spends VP on "wound check" but the action is an attack). For multi-source VP spends (which don't currently occur in the engine), promote later if needed.

## Q4 — Should the round-trip test (FR-030) cover EVERY combat in the test suite, or just per-event-type representative samples?

**Decision**: Per-event-type representative samples. Each entry type gets at least one round-trip test asserting byte-identical text. Existing tests (US2) serve as the comprehensive regression guard across whole combats.

## Q5 — How does `BulletedRenderer` handle composite entries (e.g., AttackEntry with vp_spent + damage_projection)?

**Decision**: Multi-section bulleted format. The VP spend is a sub-bullet under the attack roll (or a prefix on the header line — implementation choice). The damage projection is a nested bullet group under "Damage will be: XkY". TBD final exact format during implementation.

## Q6 — JsonRenderer (SC-004 extensibility demo) — throwaway or kept?

**Decision**: Lives in `tests/test_renderer_extensibility.py` as a unit-test fixture. NOT a shipping module. Demonstrates that a new renderer can be written without touching the formatter / observer / engine. If a future feature ships a real JSON output, it builds on this proof.

## Q7 — `_detail_*` fields stay on events or migrate to `TraceEntry`?

**Decision**: Stay on events. The observer annotates events; the formatter's `entries()` method reads annotations + raw event data to produce structured `TraceEntry` instances. `TraceEntry` is the structured form derived from `_detail_*`, not a replacement for them.

## Q8 — The HTML renderer (`web/adapters/html_renderer.py`)

**Decision**: Out of scope for this feature. Continues to consume text lines (from `format_history()`). A future feature can route HTML through `TraceEntry` if desired.

## Q9 — Mypy strictness on the new modules

**Decision**: Strict mode (per `pyproject.toml`'s `web/` rule). `TraceEntry` subclasses use `@dataclass(frozen=True)` so mutation is prevented at the type level + runtime. Renderers' per-entry-type dispatch uses `isinstance` checks (or `match` statements where elegant).

## Scope-creep findings

(Populated during the run if substantial out-of-scope work surfaces.)
