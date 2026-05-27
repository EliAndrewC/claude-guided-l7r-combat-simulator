# Quickstart: Verifying the Trace Observability Audit landed

This file documents how to verify the audit landed end-to-end.

## Prerequisites

- Repository at branch `006-trace-observability-audit` (or master after squash-merge).
- Baseline tests passing: `env/bin/pytest tests/ -v` exit code 0.

## 1. Re-run the trace-auditor calibration scenario

Run a 300-XP 5th-Dan Akodo vs 300-XP 5th-Dan Bayushi combat at `random.seed(1234)` (the dry-run scenario):

```bash
PYTHONPATH=/workspace env/bin/python /tmp/probe.py  # uses the recipe in the trace-auditor agent doc
```

Inspect the trace. The five P1 gaps from the dry-run MUST all be closed:

1. **Damage XkY breakdown present**: every `damage will be XkY` and `Damage: XkY` line MUST include `= <breakdown>`.
2. **Attack XkY breakdown present**: every attack line's `XkY` MUST include `= <breakdown>`.
3. **All `+N` modifiers labeled**: no bare `+N` without `(source)` or `(unsourced: +K)`.
4. **TN with raises broken down**: `vs TN N (base TN M, +X from K raises for {action})`.
5. **VP-on-attack visible in damage**: damage breakdown for attacks funded by VP includes `(VP on attack: +Nk(N))`.

## 2. Run the trace-observability test suite

```bash
env/bin/pytest tests/test_trace_observability.py -v
```

All tests MUST pass. New test count: 15–25 new tests across the audit's FRs.

## 3. Re-run school-specific test suites

```bash
env/bin/pytest tests/test_mirumoto_school.py -v
env/bin/pytest tests/test_ishi_school.py -v
env/bin/pytest tests/test_akodo_school.py -v
```

All school tests MUST still pass. Tests asserting `assertIn(...)` on partial trace strings remain valid. Tests that locked in full-line equality of the old (gap-ridden) trace MAY have been updated as part of the audit — the new, more-detailed trace is the new contract.

## 4. Dispatch the trace-auditor on each implemented school

```bash
# (via the orchestrator's Agent tool — not a CLI invocation)
```

For each of Mirumoto, Ishi, Akodo:
- Trace-auditor runs a scripted combat.
- Reports zero P1 gaps.
- May surface P2/P3 recommendations (acceptable; not blocking).

## 5. Constitution quality gates

```bash
env/bin/ruff check .
env/bin/mypy
env/bin/pytest tests/ -v
env/bin/pytest tests/ --cov=web --cov=simulation/mechanics --cov-report=term
```

All four MUST pass. Coverage on the affected modules ≥ 90%.

## 6. CLAUDE.md workflow check

Open `CLAUDE.md` and verify the "New school implementation workflow" section step 6 includes `trace-auditor` as a per-batch checkpoint alongside `rules-auditor` and `combat-simulator`.

## 7. Streamlit smoke (manual UI verification)

```bash
env/bin/streamlit run web/app.py --server.headless true
```

Open the UI, build any character, run a combat. The trace in the UI MUST show the new inline breakdowns for attack rolls, damage rolls, WC rolls, TN expressions, and modifiers. If any aggregate appears bare, that's a Principle VII gap and a follow-up.

## 8. Pick a school and replay the user's original bug

Build a 300-XP Bayushi vs Akodo combat. Trigger a double-attack hit. Verify the damage line renders:

```
⚔️ attacks Akodo (double attack) — XkY = <attack breakdown> [...] → N, +M (source) = total vs TN T (base TN B, +R from K raises for double attack) — HIT! (+P over TN, Q extra damage dice from margin P÷5, damage will be DkE = <damage breakdown>)
```

The user, re-running this combat, can read the damage line and trace every contribution back to its source — closing the bug they reported.

## When the quickstart fails

1. Re-run trace-auditor: which P1 gaps are still open? The gap report identifies fix locations.
2. If a school's test broke: was the trace string assertion locking in the old gap? Update it to the new, more-detailed string.
3. If `(unsourced: +K)` appears in a passing trace: `explain_modifier` is missing a case for that modifier source. Add it to the catalog in `web/adapters/modifier_breakdown.py`.
4. If the breakdown sum doesn't equal the aggregate: the observer's `get_breakdown` is missing a contributing source. Trace from the source-of-truth in `simulation/mechanics/roll_params.py` to figure out what was skipped.
