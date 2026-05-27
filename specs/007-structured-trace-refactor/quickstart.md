# Quickstart: Verifying the Structured Trace Refactor

## Prerequisites

- Repository on branch `008-structured-trace-refactor` (or master after squash-merge).
- Baseline tests passing: `env/bin/pytest tests/ -q`.

## 1. Verify byte-identical text output (the regression guard)

```bash
env/bin/pytest tests/ -q 2>&1 | tail -3
```

Expected: ALL existing tests pass at count ≥ baseline (3538) + new tests. Zero existing trace-string-assertion test regressions.

## 2. Verify structured entries are produced

```python
from web.adapters.detailed_formatter import DetailedEventFormatter
from web.adapters.trace_entries import AttackEntry, RoundHeaderEntry

# ... run a deterministic combat ...
formatter = DetailedEventFormatter()
entries = formatter.entries(engine.history())

# Every entry has a type discriminator
print({type(e).__name__ for e in entries})
# Expected: includes RoundHeaderEntry, PhaseHeaderEntry, AttackEntry, LightWoundsDamageEntry, etc.

# AttackEntry has structured fields
attacks = [e for e in entries if isinstance(e, AttackEntry)]
for a in attacks:
    print(a.actor_name, a.skill, a.rolled, a.kept, len(a.components))
```

## 3. Verify the bulleted renderer

```python
from web.adapters.bulleted_renderer import BulletedRenderer
markdown = BulletedRenderer().render(entries)
print(markdown[:500])
```

Expected: Markdown headers (`## Round N`, `### Phase N`) + bulleted breakdowns for multi-source aggregates + dice lines.

## 4. Verify the round-trip

```python
from web.adapters.text_renderer import TextRenderer

# Old path
old_lines = formatter.format_history(engine.history())

# New path via entries
new_lines = TextRenderer().render_lines(formatter.entries(engine.history()))

assert old_lines == new_lines, "Byte-identical invariant violated!"
```

## 5. Verify the Streamlit UI

```bash
env/bin/streamlit run web/app.py --server.headless true &
# Open the URL, build a combat, verify the bulleted form renders correctly.
```

Expected: each attack/damage roll shows a bulleted layout with source breakdowns instead of a single dense line.

## 6. Verify coverage

```bash
env/bin/pytest tests/ --cov=web/adapters --cov-report=term --no-header
```

Expected:
- `web/adapters/trace_entries.py`: 100%
- `web/adapters/bulleted_renderer.py`: 100%
- `web/adapters/text_renderer.py` (or wherever `TextRenderer` lives): 100%

## 7. Verify trace-auditor PASS (text path unchanged)

Dispatch `trace-auditor` on the calibration combat. Expected: zero new P1 gaps (the text output is byte-identical, so existing Principle VII compliance is preserved).

## When the quickstart fails

- **Byte-identical invariant violated**: Round-trip test in `tests/test_text_renderer_roundtrip.py` will identify the diverging entry type. Fix the TextRenderer's per-entry-type render method.
- **An event isn't producing an entry**: The `entries()` method has an unhandled event type. Add the missing entry type or extend the existing dispatch.
- **BulletedRenderer crashes on an entry type**: The renderer's `render` method has an unhandled entry type. Add the missing per-entry method.
- **Coverage below 100% on new modules**: Add tests or document pragma per Principle VI.
