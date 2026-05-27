# Phase 0 Research: Action-Level Damage Breakdown

## Diagnostic-investigation findings (2026-05-27)

The trace-reader agent's dry-run on the calibration combat flagged "Bayushi feint deals 15 LW vs 0 LW depending on opponent state" as a potential engine bug. Investigation determined the engine behavior is correct (Bayushi has school-specific feint mechanics); the rendering is wrong.

### Engine layer (correct, unchanged)

- `simulation/actions.py:238-247` — `FeintAction.damage_roll_params() → (0, 0, 0)`. Default feint deals zero damage.
- `simulation/schools/bayushi_school.py:162-167` — `BayushiFeintAction(FeintAction)` overrides:
  ```python
  def damage_roll_params(self) -> tuple[int, int, int]:
      rolled = self.subject().skill("attack") + self.vp()
      kept = 1 + self.vp()
      modifier = self.subject().modifier(self.target(), self.skill())
      return (rolled, kept, modifier)
  ```
  Engine deals `attack_skill + vp` rolled, `1 + vp` kept on a Bayushi feint.

### Formatter layer (buggy)

- `web/adapters/detailed_formatter.py:878-880` (attack-line projection):
  ```python
  damage_params = subject.get_damage_roll_params(
      target, action.skill(), extra_dice, action.vp(),
  )
  ```
  Asks the PROVIDER, not the action. For a Bayushi character with feint skill, the provider returns 9k2 (default Bayushi damage with VP-on-attack inflation). The action's actual return is 5k1.

- Same pattern at lines ~1002 (LightWoundsDamage entry) and ~1119 (counterattack projection).

- `_compute_damage_breakdown(subject, target, action, extra)` similarly routes through the provider's `get_breakdown(kind="damage")` to get components. The components claim `4k2 katana + 5k0 Fire ring = 9k2` even though the Bayushi feint doesn't use either.

### Symptoms in trace (calibration combat line 131-133)

```
... — HIT! (+12 over TN, damage will be 9k2 = 4k2 katana + 5k0 Fire ring)  ← PROJECTION LIES
...
💥 Damage: 5k1 = 4k2 katana + 5k0 Fire ring + -4k-1 reconciliation [...]  ← BREAKDOWN LIES
```

The `-4k-1 reconciliation` absorbs the lie (4k1 worth of mis-attribution). spec 008 categorizes this as "non-overflow reconciliation" (raw sum ≤ 10k10), labeling it `"reconciliation"` rather than `"from dice in excess of 10k10"`. The label is correct given the data, but the data is wrong.

## Why action-side accessor (not provider-side patch)

Three alternatives considered:

| Alternative | Pros | Cons |
|-------------|------|------|
| **Action-side `damage_breakdown()`** (chosen) | Single source of truth: the action knows its own params. Symmetric with `damage_roll_params()`. Easy to override per-action. | Adds a method to AttackAction hierarchy. |
| Provider-side `get_breakdown(action=...)` | Centralizes provider knowledge. | Provider would need to inspect action type — leaky abstraction. Tightly couples provider to action class hierarchy. |
| Per-action dict lookup in formatter | Quick fix. | Doesn't scale — every new school-specific action needs a formatter update. |

Chosen: action-side accessor. Symmetric with the existing `damage_roll_params()` (action knows its own behavior).

## Test coverage expectations

- New unit tests for `AttackAction.damage_breakdown()` default behavior.
- New unit tests for `FeintAction.damage_breakdown()` returning `[]`.
- New unit tests for `BayushiFeintAction.damage_breakdown()` returning the expected component list (varies with VP).
- Integration test on the calibration combat: Bayushi feint trace lines no longer show the projection-vs-actual mismatch.
- Regression test: Akodo attack trace lines unchanged.

Estimated test count: 10-15 new tests; 2-5 existing tests updated (those that asserted on the OLD Bayushi feint trace).
