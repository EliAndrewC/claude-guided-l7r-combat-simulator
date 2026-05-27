# Data Model: Combat Trace UX Fixes

This feature introduces no new engine entities and no new TraceEntry types. Existing entry types may gain optional fields to carry the integration data the renderers need.

## Existing entries with potentially-new fields

### `AttackEntry`

New optional fields the formatter MAY populate during `entries()`:

| Field | Type | Purpose |
|-------|------|---------|
| `consumed_floating_bonuses: list[ModifierDelta]` | optional | When a `SpendFloatingBonusEvent` immediately follows this attack's outcome events, the bonus(es) are recorded here. Renderers use this to produce inline arithmetic on the attack line. |
| `suppress_damage_projection: bool` | optional | When the attack is a feint that deals 0 LW, this flag suppresses the "damage will be: XkY" segment. |

### `LightWoundsDamageEntry`

The existing `LightWoundsDamageEntry` already has all the fields it needs. The change is in the `entries()` method: feint damage events that deal 0 LW are NOT emitted as `LightWoundsDamageEntry` at all. The engine event is still in `engine.history()`; the formatter just doesn't produce an entry for it.

### `SpendFloatingBonusEntry`

The existing `SpendFloatingBonusEntry` is suppressed when its bonus has been integrated into an `AttackEntry.consumed_floating_bonuses`. The formatter tracks "absorbed" `SpendFloatingBonusEvent` instances in walk state and skips emitting entries for them.

## New shared helper

### `web/adapters/_breakdown_format.py::format_breakdown_component(rolled, kept, source) -> str`

The single source of truth for breakdown-component formatting. Both TextRenderer and BulletedRenderer call this; future renderers (JsonRenderer, etc.) call it too.

Replaces the duplicated `_format_one_component` functions currently in `text_renderer.py` and `detailed_formatter.py`, and the special-case in `bulleted_renderer.py::_format_component_bullet`.

## `explain_modifier` extension

`web/adapters/modifier_breakdown.py::explain_modifier` gains a case for the Akodo 4th Dan VP-on-WC modifier:

```python
# When the modifier is on a wound check, the character has Akodo
# Bushi School at Dan >=4, AND the modifier is exactly 5*vp where
# vp is the VP spent on the WC (tracked elsewhere), attribute to
# "Akodo 4th Dan VP raises".
if (
    skill == "wound check"
    and _is_akodo_bushi(character)
    and _school_rank(character) >= 4
    and modifier > 0
    and modifier % 5 == 0
    and (modifier // 5) == character.last_wc_vp_spent  # or equivalent
):
    return [("Akodo 4th Dan VP raises", modifier)]
```

Exact predicate depends on the implementer's investigation (FR-013).

## "unsourced" fallback rendering

When `explain_modifier` returns no source AND the modifier value is non-zero, the renderer emits a non-alarming fallback. Pre-resolution: `"(see preceding line)"` because in most observed cases the modifier value IS attributable from context one line back.

Implementation: in `_format_modifier_breakdown` (both renderers' helpers), replace `f"unsourced: +{N}"` with the fallback string. The `(unsourced: +K)` shape from spec 005 FR-014 is preserved structurally, but the wording changes.

## Workflow change

`CLAUDE.md` "New school implementation workflow" step 6:

```
6. **Implement.** `/speckit-implement` — batches of 3–6 tasks per
   `school-implementer` call. After every substantial batch:
   - `rules-auditor` reviews the diff against the upstream rules clause.
   - `combat-simulator` runs scenarios A (clause exercise), B
     (win-feasibility), B.2, C, D ...
   - `trace-auditor` reviews the trace for Principle VII compliance.
   - `trace-reader` reviews the trace for UX intuitiveness.  [NEW]
```

The two trace agents are peers but check different properties: trace-auditor checks "every value has source attribution"; trace-reader checks "the trace looks coherent and intuitive to a fresh reader". A line can pass one and fail the other.

## Invariants

- **I1**: Cross-renderer consistency — for every TraceEntry that contains breakdown components, TextRenderer and BulletedRenderer use the same string for each component.
- **I2**: Feint suppression — for every feint attack that deals 0 LW, no damage line, no projection, no breakdown appears in either renderer.
- **I3**: Floating-bonus inline integration — when a bonus is consumed on an attack, the attack-line inline arithmetic reflects it and no standalone consumption line appears.
- **I4**: "unsourced" literal absence — `grep -E "\\bunsourced\\b"` returns zero matches on a calibration combat trace from either renderer.
- **I5**: Existing-test impact ≤ 10 — per SC-006, no more than 10 existing trace tests need updates.
