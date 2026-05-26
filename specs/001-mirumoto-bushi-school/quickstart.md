# Phase 1 Quickstart: Verifying the Mirumoto Bushi School

This is the recipe a developer (or reviewer) follows to verify that the Mirumoto Bushi implementation works end-to-end after `/speckit-implement` lands.

## Prerequisites

- Working tree on branch `001-mirumoto-bushi-school`
- Python venv active (or the project's `env/` symlink in place — `env/bin/pytest` etc. work)

## 1. Unit-test verification

Run the school's test file in isolation:

```bash
env/bin/pytest tests/test_mirumoto_school.py -v
```

Expected: all tests pass (matches SC-005). The test classes correspond 1:1 to the data-model's anticipated test classes (see `data-model.md` § Test data model).

Then run the full suite:

```bash
env/bin/pytest tests/ -v
```

Expected: all tests pass, no other school's tests regressed.

## 2. Lint + type check

```bash
env/bin/ruff check .
env/bin/mypy
```

Both must report zero errors (Constitution Quality Gates 1–2).

## 3. Coverage check

```bash
env/bin/pytest tests/ --cov=simulation --cov-report=term-missing
```

Expected: total coverage ≥ 90% (Constitution Principle VI). New code paths in `simulation/schools/mirumoto_school.py` and `simulation/strategies/mirumoto_third_dan.py` should each be at or near 100% — any uncovered branch is a review blocker.

## 4. Inspect the school's static metadata

```python
from simulation.schools.factory import get_school

school = get_school("Mirumoto Bushi School")

assert school.school_ring() == "void"
assert set(school.school_knacks()) == {"counterattack", "double attack", "iaijutsu"}
# First Dan: extra die on parry, double attack, wound check
assert set(school.extra_rolled()) == {"parry", "double attack", "wound check"}
# Second Dan: free raise on parry
assert school.free_raise_skills() == ["parry"]
```

Maps to acceptance scenarios US1.1, US1.2, US1.4. This exercises FR-001–FR-003 and FR-005–FR-006 at the schema level.

## 5. Construct a 1st-dan Mirumoto Bushi end-to-end

```python
from simulation.character import Character
from simulation.schools.factory import get_school

mirumoto = Character("Mirumoto")
school = get_school("Mirumoto Bushi School")
mirumoto.set_school(school)                  # set_school takes the school instance only
school.apply_special_ability(mirumoto)       # installs TVP-on-parry listener
school.apply_rank_one_ability(mirumoto)      # installs +1 die on parry/double-attack/wound-check
school.apply_rank_two_ability(mirumoto)      # installs free raise on parry

# Now mirumoto.extra_rolled("parry") == 1, FreeRaise on parry is in mirumoto._modifiers, etc.
# For higher dans, also call apply_rank_three_ability / four / five in sequence (after rank 1/2).
```

For convenience, the test file uses helpers like `_make_third_dan_mirumoto`, `_make_fourth_dan_mirumoto`, and `_make_fifth_dan_mirumoto` in `tests/test_mirumoto_school.py`. Use those as a reference if you want a fully-wired character at any rank.

## 6. Run a scripted combat with deterministic dice

The cleanest reference patterns are in `tests/test_mirumoto_school.py` — specifically `TestMirumotoUS1Integration::test_scripted_parry_grants_tvp_and_rolls_extra_die` (parry + TVP), `TestMirumotoUS2Integration::test_mode_a_multi_spend_enables_parry_scenario_1` (Third Dan reactive phase-lowering), `TestMirumotoUS3Integration::test_failed_parry_against_double_attack_lands_auto_sw` (Fourth Dan auto-SW), and `TestMirumotoUS3Integration::test_failed_parry_against_regular_attack_increases_damage_vs_baseline` (Fourth Dan halving). Each constructs a `Character`, school-applies the appropriate ranks, sets a `CalvinistRollProvider` to pre-queue dice, builds an `EngineContext` with two `Group`s, and drives the relevant `TakeAttackActionEvent` / `TakeParryActionEvent` through `CombatEngine.event(...)`.

Note: `CombatEngine.run_round()` requires pre-queueing the initiative roll plus every dice roll the round consumes — for ad-hoc REPL exploration, driving discrete `Take*ActionEvent`s through `engine.event(...)` (as the integration tests do) is more practical than full-round scripting.

Maps to acceptance scenarios US1.6, US2.2, US3.3, US3.4.

## 7. Streamlit UI smoke test (optional)

The feature does not require UI changes, but if you have time:

```bash
env/bin/streamlit run web/app.py --server.headless true
```

Open the dashboard and select "Mirumoto Bushi School" in any character builder. Confirm the school appears, the ring is Void, and the knacks are correct. (This exercises the factory wiring end-to-end.)

## 8. Sanity-check the trace against the rules

For any combat you run with a Mirumoto Bushi, open `rules/04-schools.md` § "Mirumoto Bushi School" alongside the trace output. Set the logger to `DEBUG` (`tests/test_mirumoto_school.py` does this in its header) to see the Mirumoto-specific log lines T018 added. Every dan-rank effect that fires should be matchable to a rules clause without consulting the source code (SC-006). Specifically:

| Log marker / trace event | Rules clause |
|---|---|
| `GainTemporaryVoidPointsEvent` after `ParryFailedEvent` or `ParrySucceededEvent` | Special Ability |
| (Implicit) +1 rolled die on parry/double-attack/wound-check roll-params | 1st Dan |
| (Implicit) `FreeRaise` modifier on parry rolls | 2nd Dan |
| `[Mirumoto 3rd Dan]` pool reset on `NewRoundEvent` | 3rd Dan (pool grant) |
| `[Mirumoto 3rd Dan mode A]` lowered action phase X→Y, pool A→B | 3rd Dan (phase-lower spend) |
| `[Mirumoto 3rd Dan mode B]` +N bonus on `<skill>` roll, pool A→B | 3rd Dan (post-roll bonus spend) |
| (Static) Ring "void" raised, `_discounts["void"] == 5` | 4th Dan (Void +1 / -5 XP) |
| `[Mirumoto 4th Dan]` auto-serious-wound lands on failed parry | 4th Dan (auto-SW clause / FR-012) |
| `[Mirumoto 4th Dan]` failed-parry damage-die reduction halved | 4th Dan (halving clause / FR-013) |
| `[Mirumoto 5th Dan]` +N VP bonus on `<skill>` | 5th Dan |

If any of these are missing or unclear in the trace, file as a follow-up — the trace is the primary auditing surface for SC-002 and SC-006.

## Done criteria

The feature is done when:

1. All steps 1–6 pass without errors.
2. Step 8's table maps cleanly to your trace output.
3. The Quality Gates checklist in `spec.md` § Success Criteria (SC-001 through SC-006) is satisfied.
4. PR is opened on `001-mirumoto-bushi-school` against `master`. (Push is the user's action, not the agent's — per memory `feedback-git-pushes`.)
