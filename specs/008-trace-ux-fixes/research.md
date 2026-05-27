# Phase 0 Research: Combat Trace UX Fixes

## trace-reader dry-run findings (cached)

| Issue | Severity | Symptom | Fix area |
|-------|----------|---------|----------|
| 1 | Wrong | Cross-renderer disagreement: TextRenderer says `"+6 from 3 dropped dice in excess of 10k10"`, BulletedRenderer's damage breakdown says `"-3k3 from dice in excess of 10k10"` | Shared `_breakdown_format.py` helper |
| 2 | Misleading | Feint projects `damage will be: 9k2` then actual damage rolls 10k2 / 17 / 0 LW dealt | Feint-damage suppression |
| 3 | Misleading | Attack outcome reads `→ 19 vs TN 30 — HIT!` arithmetically a miss; floating bonus `+15` consumption is on the next line | Inline bonus integration |
| 4 | Noisy | Bulleted damage breakdown shown for a 0-LW-dealt feint | Same fix as #2 |
| 5 | Confusing | Literal `"unsourced"` appears in user-visible modifier label | Identify source + add `explain_modifier` case |
| 6 | Misleading | Damage line says "0 light wounds" with no reason given | Same fix as #2 |

## Per-issue code-location preliminary survey

### Issue 1 — BulletedRenderer uses old form

Likely in `web/adapters/bulleted_renderer.py` — the `_render_attack` builds the damage projection sub-bullets via a path that bypasses the `_format_component_bullet` special-case. Need to find where the damage-projection sub-bullets are generated and route them through the same helper.

### Issues 2/4/6 — Feint damage

`web/adapters/detailed_formatter.py::entries()` walks the engine history and produces `AttackEntry` / `LightWoundsDamageEntry` for each event. The relevant tracking state is `_pending_damage_context` (around line 200 in combat_observer.py). At entry-production time, the formatter MUST detect:
- Is the attack action a feint?
- Did the damage event yield 0 LW dealt?

If both, omit the projection from the AttackEntry AND suppress the LightWoundsDamageEntry entirely. The renderers then have nothing to render.

### Issue 3 — Floating-bonus inline integration

The engine emits the events in order: `AttackRolledEvent` → `AttackSucceededEvent` (or `AttackFailedEvent`) → `SpendFloatingBonusEvent`. The formatter currently produces an AttackEntry from the rolled+succeeded pair, then a separate SpendFloatingBonusEntry from the spend event.

To integrate: at entry-production time, look ahead in the history for a `SpendFloatingBonusEvent` from the same actor immediately following the attack-outcome events. If present, attach the bonus to the AttackEntry's modifier_components (with source) and SKIP producing the standalone SpendFloatingBonusEntry.

### Issue 5 — `unsourced` literal

The `+5 (unsourced)` instance in the dry-run trace is on a wound-check line where the preceding annotation is `"Akodo 4th Dan: spends 1 VP on wound check, +5 per VP = +5"`. The Akodo 4th Dan VP-for-raise modifier IS labeled in the preface text but is also being emitted on the modifier itself — and that modifier's source attribution is missing from `explain_modifier`.

Fix: add an `_is_akodo_bushi` helper case in `web/adapters/modifier_breakdown.py::explain_modifier` for the wound-check VP-raise modifier. The modifier value matches `5 * vp` where vp comes from the AkodoWoundCheckRolledStrategy's spend.

## Existing-test impact estimate

Per the spec's SC-006 (max 10 test updates), the projected impact:
- **Issue 1**: Pure formatter consistency fix. Existing tests asserting on the OLD BulletedRenderer form will need updates. Estimate: 2-4 tests.
- **Issues 2/4/6**: Removing feint damage lines from output. Tests that asserted on `"Damage: XkY"` lines from feints will need updates. Estimate: 2-4 tests.
- **Issue 3**: Inline bonus integration. Tests that asserted on the SEPARATE consumption line will need updates. Estimate: 3-5 tests.
- **Issue 5**: Replacing "unsourced" with the Akodo 4th Dan label. Tests asserting on `"unsourced"` will need updates (if any).

Total estimate: ~8-10 test updates. Within SC-006's threshold.

## Shared helper design

`web/adapters/_breakdown_format.py`:

```python
"""Shared formatting helper for trace-component breakdowns.

Both TextRenderer and BulletedRenderer call format_breakdown_component()
to render per-source contributions in a multi-source aggregate.  This
ensures consistency across renderers and is the single point of change
for any future breakdown-rendering decision.
"""

EXCESS_10K10_SOURCE = "from dice in excess of 10k10"


def format_breakdown_component(rolled: int, kept: int, source: str) -> str:
    """Format a single (rolled, kept, source) component as a string.

    Special-cases the 10k10-overflow synthetic source: emits the
    "+{2N} from {N} dropped die(s) in excess of 10k10" narrative form
    when the delta represents actual overflow (rolled<0 or kept<0).
    All other cases use the standard "{rolled}k{kept} {source}" form.
    """
    if source == EXCESS_10K10_SOURCE and (rolled < 0 or kept < 0):
        dropped = max(0, -rolled) + max(0, -kept)
        bonus = 2 * dropped
        noun = "die" if dropped == 1 else "dice"
        return f"+{bonus} from {dropped} dropped {noun} in excess of 10k10"
    return f"{rolled}k{kept} {source}"
```

Both renderers import + delegate to `format_breakdown_component`. The TWO existing copies of this logic (in `text_renderer.py` and `detailed_formatter.py`) are removed; the third (in `bulleted_renderer.py`) is the one currently rendering the OLD form — also routed through the helper.

## Why batched, not one-shot

Each of the 4 fix areas is independent. Batching them lets a single implementer invocation handle the related changes cleanly:
- Batch A: shared helper + cross-renderer consistency (Issue 1).
- Batch B: feint damage suppression (Issues 2/4/6).
- Batch C: floating-bonus inline (Issue 3) + "unsourced" literal (Issue 5).

Each batch ends with running `trace-reader` to verify the targeted fixes landed without regressing others.
