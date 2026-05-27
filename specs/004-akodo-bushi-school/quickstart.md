# Quickstart: Verifying Akodo Bushi School works end-to-end

This file documents how a developer/playtester can verify the Akodo Bushi School implementation works end-to-end after the speckit run completes.

## Prerequisites

- Repository at branch `005-akodo-bushi-school` (or master after squash-merge).
- Local Python venv with project deps: `env/bin/python --version` returns 3.12+.
- All tests passing on baseline: `env/bin/pytest tests/ -v` exit code 0.

## 1. Smoke test: build an Akodo character

```python
from web.adapters.character_adapter import config_to_character
from web.models import CharacterConfig

config = CharacterConfig(
    name="Test Akodo",
    school="Akodo Bushi School",
    rings={"water": 3, "air": 2, "earth": 2, "fire": 2, "void": 2},
    skills={"attack": 3, "feint": 3, "double attack": 2, "wound check": 2, "parry": 2},
    school_rank=3,  # try 1, 3, and 5
    xp=300,
)
character = config_to_character(config)
assert character.school().name() == "Akodo Bushi School"
assert character.school().school_ring() == "water"
assert character.school_rank() == 3
```

## 2. Trace test: feint TVP gain

Run a deterministic combat where the Akodo successfully feints:

```python
from simulation.providers.calvinist_roll_provider import CalvinistRollProvider
from simulation.combat import Combat

akodo = build_akodo(school_rank=1)  # helper from tests/utilities
opponent = build_baseline_hida(school_rank=1)
roll_provider = CalvinistRollProvider(rolls=[...])  # deterministic seed

combat = Combat([akodo, opponent], roll_provider=roll_provider)
combat.run(max_rounds=10)
trace = combat.trace_lines()

# Verify trace contains Akodo Special Ability attribution
assert any("Akodo Special Ability" in line and "+4 TVP" in line for line in trace)
```

## 3. Bug-fix verification: 4th Dan reaches max_spend

```python
akodo_4th_dan = build_akodo(school_rank=4)
# Set up state so available_vp_for_wc = max_vp_per_roll = 5
# Force a damage event that requires spending all 5 VP to survive.
# Verify the strategy emits SpendVoidPointsEvent(character, "wound check", 5).
```

## 4. Bug-fix verification: 5th Dan no double-damage

```python
akodo_5th_dan = build_akodo(school_rank=5)
# Force an attacker to deal exactly 30 LW.
# After the damage resolves, assert akodo_5th_dan.lw() == 30 (not 60).
```

## 5. Trace observability sweep (Principle VII)

Build a 5th-Dan vs. 5th-Dan Akodo combat (this exercises every Akodo ability):

```bash
env/bin/python -c "
from tests.utilities import build_akodo, run_deterministic_combat
a1 = build_akodo(school_rank=5)
a2 = build_akodo(school_rank=5)
trace = run_deterministic_combat(a1, a2, seed=42)
print('\n'.join(trace))
"
```

Expected trace lines (paraphrased; exact wording is the trace formatter's responsibility):

- "Akodo 1st Dan: +1k0 on attack" (extra die per FR-008)
- "Akodo 2nd Dan: FR on wound check" (free raise per FR-009)
- "Akodo Special Ability: +4 TVP on successful feint" / "Akodo Special Ability: +1 TVP on failed feint" (per FR-006)
- "Akodo 3rd Dan: gained floating bonus +N" (per FR-014 acquisition)
- "Akodo 3rd Dan floating bonus consumed: +N" (per FR-014 consumption)
- "Akodo 4th Dan: spent N VP on wound check, +5N to roll" (per FR-019)
- "Akodo 5th Dan: spent N VP on counter-damage, 10 LW × N = +N0 LW dealt to {attacker}" (per FR-024)

Each line MUST be self-explaining: source attribution AND numeric breakdown. If any line is missing or incomplete, that's a Principle VII gate failure.

## 6. Principle IX validation: win-feasibility vs Hida baseline

```bash
env/bin/python tests/scenarios/akodo_vs_hida_xp300.py --seeds=5
```

Expected output: Akodo wins ≥ 1 of 5 with default strategies. If 0/5, the strategy defaults are not playable per Principle IX — escalate to school-strategy-designer.

## 7. Principle IX mirror check

```bash
env/bin/python tests/scenarios/akodo_mirror_xp300.py --seed=42
```

Expected:
- Combat terminates within 20 rounds (Principle IX 2(a)).
- Trace contains at least one Akodo identity-engine firing per Principle IX 2(b): TVP gain from feint OR a higher-Dan ability fired (3rd Dan floating bonus, 4th Dan VP-WC, 5th Dan counter-damage).

If the combat terminates without ANY identity engine firing, both Akodos won by raw wound-check shootout — that's a Principle IX degeneracy and must be escalated.

## 8. Round-robin validation (Scenario D)

```bash
for opponent in Mirumoto Ishi Hida; do
    env/bin/python tests/scenarios/akodo_vs_${opponent,,}.py
done
```

Each matchup must produce trace lines showing Akodo's identity machinery firing — not just trading plain attacks.

## 9. Constitution quality gates

```bash
env/bin/ruff check .
env/bin/mypy
env/bin/pytest tests/ -v
env/bin/pytest tests/ --cov=simulation/schools/akodo_school --cov-report=term-missing
```

All four MUST pass. Coverage on `simulation/schools/akodo_school.py` must be ≥ 95%.

## 10. Streamlit smoke (Principle VII visual confirmation)

```bash
env/bin/streamlit run web/app.py --server.headless true
# Open the UI, build an Akodo character, run a combat, verify the trace renders.
```

The trace in the UI must show Akodo-attributed lines for each ability that fired. If the UI shows "+30" without attribution, the formatter is missing a hook.

## When the quickstart fails

1. Re-run the failing test in isolation with `-v` to see the trace.
2. Read the rules text (research.md or upstream) and verify the implementation matches.
3. If a Principle VII trace line is missing, find the event in `simulation/events.py` and add a formatter case in `web/formatters/`.
4. If a Principle IX scenario fails, escalate to `school-strategy-designer` (likely a default-binding issue) or `combat-simulator` (likely a numeric-balance issue).
