# Phase 1 Quickstart: Verifying the Isawa Ishi School

Recipe to verify the Isawa Ishi implementation works end-to-end after `/speckit-implement` lands.

## Prerequisites

- Branch `002-isawa-ishi-school`
- Python venv: `env/bin/pytest`, `env/bin/ruff`, `env/bin/mypy` available

## 1. Unit-test verification

```bash
env/bin/pytest tests/test_ishi_school.py -v
env/bin/pytest tests/ -v  # full suite, no regressions in other schools
```

Expected: all tests pass.

## 2. Lint + type check

```bash
env/bin/ruff check .
env/bin/mypy
```

Both zero-error.

## 3. Coverage check

```bash
env/bin/pytest tests/ --cov=simulation --cov-report=term-missing
```

Expected: project-wide ≥ 90%; `simulation/schools/ishi_school.py` and `simulation/strategies/ishi_dan_abilities.py` each ≥ 90%.

## 4. Construct an Isawa Ishi and inspect Special Ability machinery

```python
from simulation.character import Character
from simulation.schools.factory import get_school

c = Character("Ishi")
school = get_school("Isawa Ishi School")
c.set_school(school)
school.apply_special_ability(c)
school.apply_rank_one_ability(c)
school.apply_rank_two_ability(c)
school.apply_rank_three_ability(c)

# Set explicit rings to verify VP math
c.set_ring("void", 4)
c.set_ring("fire", 3)
c.set_ring("water", 2)
c.set_ring("air", 3)
c.set_ring("earth", 3)

# Special Ability: max_vp = highest_ring + school_rank = 4 + 3 = 7
assert c.max_vp() == 7

# Special Ability: max_vp_per_roll = lowest_ring - 1 = 2 - 1 = 1
assert c.max_vp_per_roll() == 1
```

Maps to US1 acceptance scenarios.

## 5. 1st Dan / 2nd Dan inspection

```python
# 1st Dan: extra die on precepts, wound check, initiative
assert set(school.extra_rolled()) == {"precepts", "wound check", "initiative"}

# 2nd Dan: free raise on precepts (Q2 default; OPEN_QUESTIONS.md)
assert school.free_raise_skills() == ["precepts"]
```

## 6. 3rd Dan ally-boost scripted scenario

```python
from simulation.context import EngineContext
from simulation.engine import CombatEngine
from simulation.groups import Group
from simulation.mechanics.roll_provider import CalvinistRollProvider

# Build a 3rd-dan Ishi + an ally + an enemy.
# Run a scripted combat where the ally's attack roll lands just below TN.
# Verify the Ishi spends 1 VP and the precepts.k1 result is added to the ally's roll.
# Verify the Ishi's _ishi_negation_done flag is unchanged (3rd Dan is not 5th Dan).
```

Maps to US3 acceptance scenarios. The test file `tests/test_ishi_school.py::TestIshiUS3Integration` is the canonical version.

## 7. 5th Dan negation scripted scenario

```python
# Build a 5th-dan Ishi with enough VP for negation.
# Build a 4th-dan Mirumoto Bushi as opponent (school rank 4 → cost = 2 * 4 = 8 VP).
# Trigger the Ishi's first YourMoveEvent.
# Verify (a) Ishi's VP decreased by 8, (b) Mirumoto._school_negated_by == Ishi,
# (c) Mirumoto's MirumotoParryTVPListener no longer fires on subsequent parries.
```

Maps to US5 acceptance scenarios.

## 8. Principle IX playability validation (run by `combat-simulator`)

- **Scenario A**: 300-XP Ishi vs Akodo at 3rd / 5th dan. Combat terminates; Ishi wins ≥ 20% (3rd) / ≥ 40% (5th).
- **Scenario B.1 (1v1 mirror)**: Special Ability + 5th Dan negation fire. 3rd Dan inert in 1v1 mirror — acceptable per Layer-3 analysis.
- **Scenario B.2 (2v2 mirror)**: 3rd Dan ally-boost fires when allies exist.
- **Scenario C (action-disadvantage)**: Ishi takes ≥ 1 attack action per fight.
- **Scenario D (behavioral round-robin)**: 0 counterattacks, 0 double attacks; VP-cap respected; (at 5th dan) 1 negation per fight.

## 9. Sanity-check the trace against the rules

For any Isawa Ishi combat, set `logger.setLevel(logging.DEBUG)` and look for these trace markers:

| Trace marker | Rules clause |
|---|---|
| Custom VP cap rendered in roll annotations | Special Ability |
| `[Ishi 1st Dan]` extra die on precepts/wound check/initiative | 1st Dan |
| `Isawa Ishi 2nd Dan free raise: +5` on precepts roll trace | 2nd Dan |
| `Isawa Ishi 3rd Dan ally boost from <Ishi name>: +X` on ally roll trace | 3rd Dan |
| Void+1 stat + 5-XP discount visible | 4th Dan |
| `⛔ {negator} negates {target}'s {school_name} ({cost} VP — Isawa Ishi 5th Dan)` | 5th Dan |

## Done criteria

1. Steps 1–7 pass without errors.
2. Step 8 playability scenarios PASS per combat-simulator audit.
3. Quality Gates per spec § Success Criteria (SC-001 through SC-007) satisfied.
4. PR opened on `002-isawa-ishi-school` against `master`. Push is user's action (per `feedback-git-pushes` memory).
