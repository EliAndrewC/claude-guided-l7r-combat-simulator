# Data Model: Action-Level Damage Breakdown

## New method on `AttackAction`

```python
def damage_breakdown(self) -> list[tuple[str, int, int]]:
    """Per-source breakdown of this action's damage params.

    Returns a list of ``(source_label, +rolled, +kept)`` tuples that
    sum to ``self.damage_roll_params()``'s ``(rolled, kept)``.

    The default implementation delegates to the provider:
    ``self.subject().roll_parameter_provider().get_breakdown(
        self.subject(), self.target(), self.skill(), kind="damage",
        attack_extra_rolled=self.calculate_extra_damage_dice(),
        vp=self.vp())``.

    Subclasses that override ``damage_roll_params()`` SHOULD also
    override this method to produce a breakdown that matches their
    override.  When the breakdown doesn't sum to the action's
    ``damage_roll_params()``, ``_normalize_breakdown`` appends a
    ``"reconciliation"`` entry — a Principle VII signal that the
    override is incomplete (per spec 008).
    """
```

## Overrides

### `FeintAction.damage_breakdown()`

```python
def damage_breakdown(self) -> list[tuple[str, int, int]]:
    return []  # Zero damage; nothing to attribute.
```

### `BayushiFeintAction.damage_breakdown()`

```python
def damage_breakdown(self) -> list[tuple[str, int, int]]:
    attack_skill = self.subject().skill("attack")
    vp = self.vp()
    components: list[tuple[str, int, int]] = []
    if attack_skill > 0:
        components.append(("attack skill", attack_skill, 0))
    components.append(("base feint kept die", 0, 1))
    if vp > 0:
        components.append(("VP on feint", vp, vp))
    return components
```

Component labels follow the existing convention (compare `BayushiRollParameterProvider.get_breakdown` which uses `"katana (4k2)"`, `"<Ring> ring"`, `"VP on attack"`).

## Formatter call sites

`web/adapters/detailed_formatter.py` — three sites currently consult the provider's `get_breakdown` directly. After the fix, they consult the action:

| Site | Pre-fix | Post-fix |
|------|---------|----------|
| ~line 878-886 (attack-line damage projection) | `subject.get_damage_roll_params(...)` + `_compute_damage_breakdown(subject, target, action, extra)` | `action.damage_roll_params()` + `action.damage_breakdown()` |
| ~line 1002 (LightWoundsDamageEntry production) | Same | Same |
| ~line 1119 (counterattack projection) | Same | Same |

The XkY rolled/kept comes from `action.damage_roll_params()` (the engine has always used this; the formatter just wasn't). The breakdown components come from `action.damage_breakdown()`.

## Invariants

- **I1**: For every attack action, `sum(c.rolled for c in action.damage_breakdown())` ≤ `action.damage_roll_params()[0]` (rolled total). Equality when the breakdown is complete; `<` triggers a reconciliation entry.
- **I2**: Same for kept.
- **I3**: When `action.damage_breakdown()` is empty (e.g., `FeintAction`), the action's `damage_roll_params()` should be `(0, 0, ?)`. Engine consistency.
- **I4**: The default `AttackAction.damage_breakdown()` produces the same output as the pre-fix provider call. Existing test traces for non-overridden actions are byte-identical.

## Migration risk

The migration is transparent for ~30 attack actions that don't override `damage_roll_params`. The only actions that gain new behavior are:
- `FeintAction` (now returns `[]` — but spec 008's feint suppression means this is rarely rendered anyway).
- `BayushiFeintAction` (the user-visible fix).

The migration risk is small and bounded.
