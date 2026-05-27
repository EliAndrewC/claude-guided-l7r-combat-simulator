# Quickstart: Verifying Action-Level Damage Breakdown

## Prerequisites

- Repository on branch `010-action-damage-breakdown` (or master after squash-merge).
- Baseline tests passing.

## 1. Verify Bayushi feint projection matches actual

Run the calibration combat and inspect Bayushi feint lines:

```bash
PYTHONPATH=/workspace env/bin/python /tmp/probe.py 2>&1 | grep -A 2 "Bayushi.*feint.*HIT"
```

Expected: the `damage will be: XkY` on the attack line matches the `💥 Damage: XkY` on the subsequent damage line. Specifically, **both should read 5k1** (the action's actual params, not the provider's 9k2).

## 2. Verify breakdown attribution is correct

Inspect the breakdown line for a Bayushi feint damage:

```bash
PYTHONPATH=/workspace env/bin/python /tmp/probe.py 2>&1 | grep "Bayushi.*💥 Damage"
```

Expected: contains `"attack skill"` and `"base feint kept die"` (the Bayushi feint's actual components). Does NOT contain `"katana"`, `"Fire ring"`, or `"reconciliation"` (the lie the pre-fix breakdown told).

## 3. Verify Akodo attacks unchanged

```bash
PYTHONPATH=/workspace env/bin/python /tmp/probe.py 2>&1 | grep "Akodo.*💥 Damage"
```

Expected: same as pre-fix (katana + Fire ring + margin breakdown for Akodo's regular attacks).

## 4. Run the test suite

```bash
env/bin/pytest tests/ -q
```

Expected: existing tests pass; ≤ 5 trace-assertion tests updated for the Bayushi feint fix.

## 5. Dispatch trace-reader to re-validate

(orchestrator-driven) Expected: zero "projection-vs-actual mismatch" issues for Bayushi feints.

## When the quickstart fails

- **Projection still 9k2**: the formatter still consults the provider for the projection. Check `_entry_combined_attack` / `_entry_attack_rolled` in `web/adapters/detailed_formatter.py` — should use `action.damage_roll_params()` and `action.damage_breakdown()`.
- **Breakdown still shows "katana + Fire ring + reconciliation"**: same root cause — formatter not consulting the action.
- **Existing tests broken beyond 5 updates**: revisit the default `AttackAction.damage_breakdown` to ensure transparent delegation to the provider.
