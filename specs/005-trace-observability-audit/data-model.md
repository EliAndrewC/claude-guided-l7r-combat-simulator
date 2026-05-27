# Data Model: Combat Trace Observability Audit

## New annotation field

### `_detail_components` (attached by `CombatObserver`)

**Type**: `list[tuple[str, int, int]]`

**Semantics**: each tuple is `(source_label, +rolled, +kept)`. The list represents the per-source contributions to a multi-source aggregate. The sum of `+rolled` across the list equals the aggregate's rolled count; same for `+kept`.

**Attached to**:
- Attack-rolled events (`AttackRolledEvent` and its action-class subtypes)
- Light-wounds-damage events (`LightWoundsDamageEvent`) for both the predictive "damage will be" projection on the attack line AND the final damage event rendering

**Invariants**:
- `sum(rolled for _, rolled, _ in components) == aggregate_rolled`
- `sum(kept for _, _, kept in components) == aggregate_kept`
- Components with `(0, 0)` contributions are PRESENT in the list (the observer doesn't filter — the formatter does, per FR-006).
- Source labels are non-empty strings.

**Lifecycle**:
1. **Compute**: at observer-annotation time (per event), `CombatObserver` queries `character.roll_parameter_provider().get_breakdown(...)` to obtain the contribution list AND attaches it to the event.
2. **Render**: at formatter-rendering time, the formatter reads the annotation and emits the inline parenthetical breakdown.
3. **Reset**: the annotation lives on the event for the lifetime of the event in the history. The event itself is garbage-collected after the trace is rendered (no per-character state).

## Source labels

A finite catalog of source labels used across the breakdown:

| Label | Domain | Where it appears |
|-------|--------|------------------|
| `"<ring> ring"` (e.g., `"Fire ring"`) | All multi-source rolls | The character's ring contribution |
| `"<skill> skill"` (e.g., `"attack skill"`) | Attack / parry rolls | The character's skill contribution |
| `"<weapon> (XkY)"` (e.g., `"katana (4k2)"`) | Damage rolls | The weapon's base damage dice |
| `"margin (+X over TN)"` | Damage rolls | Extra damage dice from attack-roll margin (`floor(margin/5)` extras) |
| `"VP on attack"` | Damage rolls | Cross-roll inflation from VP spent on the attack |
| `"<school> <ability>"` (e.g., `"Akodo 1st Dan"`) | All multi-source rolls | School-conferred extra dice |
| `"<source> floating bonus"` (e.g., `"Akodo 3rd Dan floating bonus"`) | Subsequent attack rolls | Consumed floating bonus |
| `"free raise"` | Wound check / parry / etc. | Free raise contribution |
| `"unsourced"` | Any | Placeholder when `explain_modifier` can't catalog the source — itself a Principle VII violation, but a visible one |

## Lifecycle diagram (per-event)

```text
[Engine emits AttackRolledEvent / LightWoundsDamageEvent]
    |
    v
[DetailedCombatEngine forwards to CombatObserver]
    |
    v
[CombatObserver._annotate_attack(event) or _annotate_damage(event)]
    |
    +--> calls character.roll_parameter_provider().get_breakdown(...) which:
    |       enumerates contributing sources (ring, skill, school extras,
    |       weapon, margin, VP-on-attack effect, floating bonuses, ...) and
    |       returns a list of (source_label, +rolled, +kept) tuples.
    |
    v
[event._detail_components = breakdown]
    |
    v
[event stored in engine.history()]
    |
    v
[DetailedEventFormatter.format_history()]
    |
    v
[per-event formatter case reads event._detail_components and emits inline parenthetical]
    |
    v
[user-visible trace line with breakdown]
```

## Invariants (per FR)

- **I1** (FR-001/002): `_detail_components` is attached to every attack-rolled and damage event by the observer. If the observer can't compute the breakdown (e.g., due to a missing per-school accessor), the annotation is `[("unknown", aggregate_rolled, aggregate_kept)]` — a single "unknown" source covering the whole aggregate. This is a P1 gap visible to the trace-auditor.
- **I2** (FR-006/007/009): the formatter renders the inline breakdown when `len([c for c in components if c[1] > 0 or c[2] > 0]) > 1`. When exactly one component contributes, the breakdown is omitted (it's trivially the same as the aggregate).
- **I3** (FR-010): `_format_modifier_breakdown` rendering: if `sum(component_values) < modifier_value`, append `(unsourced: +K)` where K is the unaccounted portion. If sum exceeds the modifier value, that's a logic bug — render the breakdown anyway with `(check: +M actual, +K reported)` to surface it.
- **I4** (FR-011): `_format_tn` rendering when raises are present: `vs TN N (base TN M, +X from K raises for {action})`. When `raises == 0`, the parenthetical reduces to `(base TN M)`.
- **I5** (FR-017): per-line self-explanation. The breakdown is rendered on the line where the aggregate appears, not deferred to a different turn/phase.

## Per-school breakdown contribution

A school may contribute to a roll's breakdown in two ways:

1. **Via `extra_rolled(skill)`**: the default provider already incorporates this. The breakdown computation labels these contributions with the school's name + the Dan rank that conferred them. E.g., Akodo's 1st Dan extra die on attack rolls becomes `("Akodo 1st Dan", +1, 0)`. Schools don't need to do anything new.

2. **Via per-school `RollParameterProvider` overrides**: rare. Only if a school doesn't fit the `extra_rolled` model. If a school overrides `get_skill_roll_params` or `get_damage_roll_params` directly, the override MUST also implement `get_breakdown(...)` returning the per-source contribution list. This is documented in a new `BaseSchool` docstring section.

## Cross-roll effects (e.g., VP-on-attack → damage)

When the engine resolves an attack, the VP spent on the attack inflates the subsequent damage roll. The observer must propagate this contribution:

- The `AttackDeclaredEvent` (or the relevant attack event) carries the VP spend.
- The downstream `LightWoundsDamageEvent`'s breakdown computation queries the attack's VP spend and labels the contribution `("VP on attack", +vp, +vp)` (each VP adds +1 rolled + +1 kept to damage per L7R rules).

The observer is the natural integration point: at damage-annotation time, the observer has access to both the damage event AND the recent attack event (via `engine.history()` reverse lookup or via context state).

## Snapshot of affected files (for the implementer)

| File | Change kind | Estimated LOC delta |
|------|-------------|---------------------|
| `web/adapters/combat_observer.py` | EDIT: `_annotate_attack`, `_annotate_damage` extended to compute and attach `_detail_components` | +50–100 |
| `web/adapters/detailed_formatter.py` | EDIT: `_format_attack_rolled`, `_format_combined_attack`, `_format_lw_damage`, `_format_modifier_breakdown`, `_format_tn` extended to render breakdowns | +80–150 |
| `web/adapters/modifier_breakdown.py` | EDIT: `explain_modifier` audited for missing source cases | +20–50 |
| `simulation/mechanics/roll_params.py` | EDIT: `DefaultRollParameterProvider.get_breakdown` new method | +60–100 |
| `simulation/schools/bayushi_school.py` | EDIT (if needed): add `get_breakdown` override OR ensure `extra_rolled` covers Bayushi's contributions | +0–30 |
| `tests/test_trace_observability.py` | NEW: trace-assertion test suite | +400–500 |
| `tests/test_*_school.py` | MAYBE EDIT: update assertions that lock in old trace strings | ±20 each |
| `CLAUDE.md` | EDIT: add trace-auditor to per-batch checkpoint | +5 |

Total estimated net: ~600–800 LOC delta across the audit.
