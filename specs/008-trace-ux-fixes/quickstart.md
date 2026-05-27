# Quickstart: Verifying the Combat Trace UX Fixes

## Prerequisites

- Repository on branch `009-trace-ux-fixes` (or master after squash-merge).
- Baseline tests passing: `env/bin/pytest tests/ -q`.

## 1. Verify cross-renderer consistency (Issue 1)

```bash
PYTHONPATH=/workspace env/bin/python /tmp/probe_dual.py 2>&1 | diff <(grep "in excess of 10k10" /tmp/probe_dual.py.text) <(grep "in excess of 10k10" /tmp/probe_dual.py.bulleted)
```

Expected: zero diff. Both renderers describe the 10k10-overflow component identically.

## 2. Verify feint damage suppression (Issues 2/4/6)

```bash
PYTHONPATH=/workspace env/bin/python /tmp/probe.py 2>&1 | grep -A 1 "(feint)" | head -20
```

Expected: feint attack lines have NO `damage will be:` segment. The line(s) AFTER a feint attack are school-ability events (TVP gain / floating bonus gain), NOT damage events.

```bash
PYTHONPATH=/workspace env/bin/python /tmp/probe.py 2>&1 | grep -B 1 "0 light wounds" | head -10
```

Expected: zero lines matching `0 light wounds` (the damage line is suppressed entirely for 0-LW feints).

## 3. Verify floating-bonus inline integration (Issue 3)

```bash
PYTHONPATH=/workspace env/bin/python /tmp/probe.py 2>&1 | grep "floating bonus" | head -10
```

Expected: lines containing `+N (source floating bonus)` integrated into attack-outcome lines like `→ 19, +15 (Akodo 3rd Dan floating bonus) = 34 vs TN 30 — HIT!`. Standalone `✨ +N (... floating bonus consumed)` lines are minimal or absent on attack-funded bonuses.

## 4. Verify "unsourced" literal absence (Issue 5)

```bash
PYTHONPATH=/workspace env/bin/python /tmp/probe.py 2>&1 | grep -E "\bunsourced\b"
```

Expected: zero matches. Modifiers either show a real source or use the non-alarming fallback `"(see preceding line)"`.

## 5. Verify trace-reader workflow integration

```bash
grep -A 12 "Implement.\\*\\* \`/speckit-implement\`" CLAUDE.md
```

Expected: the per-batch checkpoint list shows `rules-auditor`, `combat-simulator`, `trace-auditor`, AND `trace-reader`.

## 6. Run trace-reader on the calibration combat

(Orchestrator-dispatched, not a CLI tool.) Expected: zero remaining instances of issues 1, 2/4/6, 3, 5 from the dry-run report.

## 7. Constitution quality gates

```bash
env/bin/ruff check .
env/bin/mypy
env/bin/pytest tests/ -q
env/bin/pytest tests/ --cov --cov-report=term --no-header
```

All four must pass. Coverage on `_breakdown_format.py` = 100%.

## When the quickstart fails

- **Issue 1 still present**: BulletedRenderer's damage-component path didn't migrate to the shared helper. Inspect `_render_attack` and the damage-projection sub-bullets in `web/adapters/bulleted_renderer.py`.
- **Issue 2 still present**: feint damage events still generate `LightWoundsDamageEntry`. Inspect `_entry_lw_damage` in `web/adapters/detailed_formatter.py` for the feint+0-LW check.
- **Issue 3 still present**: standalone consumption line still appears. Inspect the `entries()` walk for `SpendFloatingBonusEvent` skip-condition.
- **"unsourced" still appears**: `explain_modifier` case for Akodo 4th Dan VP-on-WC wasn't added OR the fallback wording wasn't changed.
