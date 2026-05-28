# Quickstart: Verifying Hida Bushi School Implementation

## Prerequisites

- Repository on branch `011-hida-bushi-school`.
- Baseline tests passing (master at spec-009 squash-merge).

## 1. Verify knack list fix

```bash
PYTHONPATH=/workspace env/bin/python -c "
from simulation.schools.factory import school_factory
s = school_factory('Hida Bushi School')
print(s.school_knacks())
assert s.school_knacks() == ['counterattack', 'double attack', 'iaijutsu'], s.school_knacks()
print('PASS')
"
```

Expected: `['counterattack', 'double attack', 'iaijutsu']` then `PASS`.

```bash
grep -rn '"lunge"' simulation/templates/strategies.py simulation/templates/generator.py simulation/schools/hida_school.py
```

Expected: zero matches in any of these three files (the lunge knack belongs to Otaku, Shinjo, Kakita, Isawa Duelist, Matsu — those are fine and untouched).

## 2. Verify 3rd Dan reroll on counterattack

Build a 3rd-Dan Hida with attack skill = 4; have them counterattack against a known attack with predestined dice (one die comes up at 3, others at 8-10):

```bash
PYTHONPATH=/workspace env/bin/python -c "
# Stripped down combat with deterministic provider
# (orchestrator to provide a probe script)
"
```

Expected in trace: `"Hida 3rd Dan: reroll up to 8 dice (counterattack, X=4) → rerolled [3, 4, 4] (low dice)"`. Trace should show old totals and new totals.

## 3. Verify 4th Dan SW-for-LW trade

Build a 4th-Dan Hida at LW=30, SW=0, max_SW=3. Have them take damage. The Hida should elect to take 2 SW instead of rolling WC.

Expected trace event: `"Hida 4th Dan: take 2 SW to reset LW from 30 → 0 (alternative wound check)"`.

## 4. Verify 4th Dan iaijutsu-phase guard

Build a 4th-Dan Hida and start an iaijutsu duel. The Hida is the duelist. The trade should NOT fire during the duel's focus/strike phase.

Expected: SW-for-LW trade does not fire; falls back to normal WC.

## 5. Verify 5th Dan WC bonus from counterattack excess

5th-Dan Hida successfully counterattacks an attack. Counterattack roll exceeds TN by 7. Hida then takes damage from the attack and rolls WC.

Expected trace: WC roll line includes `"+7 (Hida 5th Dan: counterattack excess +7)"`.

## 6. Verify 5th Dan post-damage counterattack timing

5th-Dan Hida is attacked. Hida defers the counterattack decision until after the damage roll. Trace shows:

1. Attack roll: HIT
2. Damage roll: XkY → N LW
3. WC fires → SW inflicted (if applicable)
4. Hida decides: counterattack NOW
5. Counterattack roll: succeeds
6. Original attacker takes damage from counterattack, potentially impaired/killed

The defender's damage (step 2-3) MUST resolve fully even if the attacker is killed in step 6.

## 7. Run the full test suite

```bash
env/bin/ruff check .
env/bin/mypy
env/bin/pytest tests/ -v
env/bin/pytest tests/ --cov --cov-report=term | grep -E "(simulation/schools/hida|TOTAL)"
```

Expected:
- ruff: zero errors
- mypy: zero errors
- pytest: zero failures
- coverage on `simulation/schools/hida_school.py`: 100%
- overall coverage: 100%

## 8. Dispatch verification agents

- `rules-auditor`: verify the implementation diff against the verbatim Hida rules text (no rules-fidelity discrepancies).
- `combat-simulator`: run Scenarios A (clause exercise), B (win-feasibility vs Akodo + Hida baselines at matched XP), B.2 (action-disadvantage), C (mirror non-degeneracy), D (round-robin).
- `trace-auditor`: verify Principle VII attribution on all new Hida effects in a calibration combat trace.
- `trace-reader`: verify UX intuitiveness across the 8 categories on the calibration trace.

## When the quickstart fails

- **Knack list still shows "lunge"**: check all 3 sites (school file, generator template, HIDA_PRIORITIES). The fix must be coherent.
- **3rd Dan reroll doesn't fire**: check that `HidaRollProvider` is installed at `apply_rank_three_ability` and that the skill is in the eligible-attack set.
- **3rd Dan reroll fires on parry/wound check**: bug — the eligibility check must restrict to attack-class skills.
- **4th Dan SW-for-LW fires during iaijutsu**: bug — the `context.in_iaijutsu_phase()` accessor isn't being consulted, or isn't being set by the duel engine.
- **5th Dan WC bonus not appearing in trace**: bug — `_counterattack_excess_margin` isn't being stored on the action, OR the WC roll isn't consulting it, OR the formatter isn't sourcing it (Principle VII violation).
- **5th Dan post-damage counterattack fires PRE-damage**: bug — the strategy is using the base class's decision path instead of the deferred path.
- **Mirror match deadlocks**: Principle IX violation. Re-dispatch school-strategy-designer for a fix.

## Edge case probe checklist

For SC verification, the implementer should have probe scripts demonstrating each of:

- [ ] 3rd Dan with N=0 dice (no eligible low dice) → trace records "reroll considered (no dice eligible)"
- [ ] 3rd Dan with crippled Hida → N halved + 10s still reroll
- [ ] 4th Dan SW-for-LW at LW=0 → trade short-circuits
- [ ] 4th Dan SW-for-LW with SW+2 > max_SW → trade NOT taken (would kill); fall back to WC
- [ ] 5th Dan WC bonus stacking (Hida counterattacks Hida counterattack) → only outermost margin counts
- [ ] 5th Dan post-damage counterattack: defender DIES from damage → counterattack does not fire
- [ ] 5th Dan post-damage counterattack: kills attacker → defender's damage still applies
