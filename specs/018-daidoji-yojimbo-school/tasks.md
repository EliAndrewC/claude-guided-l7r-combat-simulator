# Tasks: Daidoji Yojimbo School

**Branch**: `018-daidoji-yojimbo-school`

All tasks are TDD-first. Quality gates after every batch.

## Batch A — Rules-fidelity BLOCKING fixes

### T-A1: Fix 5th Dan modifier (HIGH-severity NEW BUG)
- **Files**: `simulation/schools/daidoji_school.py::DaidojiFifthDanWoundCheckListener`, `tests/test_daidoji_school.py:577-678` (existing tests codify buggy behavior — REWRITE).
- **Failing test first**: after WC succeeds with excess=15, the ATTACKER's `tn_to_hit()` is reduced by 15 (i.e., `attacker.modifier(None, "tn to hit") == -15`). Existing tests assert `daidoji.modifier(attacker, "attack") == 15` — rewrite to assert against attacker's tn_to_hit instead.
- **Fix**: emit `Modifier(attacker, None, "tn to hit", -excess); yield AddModifierEvent(attacker, modifier)`.

### T-A2: Fix Q4 5th Dan expiry scope
- **Failing test first**: after WC succeeds and modifier is added, the modifier persists until the next attack against the ATTACKER (by anyone), then expires.
- **Fix**: replace `ExpireAfterNextAttackByCharacterListener(daidoji)` with an expiry that triggers on `attack_succeeded` / `attack_failed` events where the target is the attacker — possibly a new `ExpireAfterNextAttackAgainstListener(target)` or use the existing `ExpireAfterNextAttackListener` (verify against modifier_listeners).

### T-A3: Fix Q5 5th Dan ally scope
- **Failing test first**: a Daidoji that has NOT counterattacked for an ally does NOT get 5th Dan benefit when the ally's WC succeeds. A Daidoji that HAS counterattacked for the ally DOES get the benefit.
- **Fix**: maintain a per-combat `_daidoji_counterattacked_for: set[Character]` (tracked in `_school_owned_attributes` so school-negation reverts it); populate in `DaidojiTakeCounterattackActionEvent.play` when the ally is the original attack target; read in the 5th Dan listener instead of adjacency.

### T-A4: Fix Q2 4th Dan timing
- **Failing test first**: ally is hit (AttackSucceededEvent fires); Daidoji intercepts BEFORE damage roll; damage is rolled against the Daidoji's defenses, not the ally's. (Currently damage is rolled against the ally then re-applied to Daidoji.)
- **Fix**: relocate listener trigger to `AttackSucceededEvent`; modify attack action's target before the damage-roll step.
- **Note**: this is the most architecturally involved fix and may require deferral if the engine doesn't expose a hook between AttackSucceededEvent and damage-roll. Investigate first.

### T-A5: Fix Q3 4th Dan strategic choice
- **Failing test first**: redirect fires only when ally is in danger (e.g., ally `expected_sw > sw_remaining`). Healthy ally + healthy Daidoji = no redirect.
- **Fix**: add heuristic gate in `DaidojiFourthDanListener.handle`.

## Batch B — Identity bindings + Q1 refactor

### T-B1: Install `WoundCheckStrategy04` in `apply_special_ability`
- **Failing test first**: after `apply_special_ability(character)`, character's wound_check strategy is `WoundCheckStrategy04`.

### T-B2: Refactor Q1 — 3rd Dan ad-hoc attribute tracking
- Replace `character._daidoji_third_dan = True` with a `_set_school_listener` on `counterattack_succeeded` (or similar slot) so the 3rd Dan logic is tracked in `_school_owned_*` for school-negation. Inline the 3rd Dan logic from `DaidojiTakeCounterattackActionEvent.play` into a listener.

## Batch C — Playability tests

### T-C1: `tests/test_daidoji_school_playability.py`
- Mirror non-degeneracy + identity-engine firing.

## Batch D — Coverage + final gates

### T-D1: Drive `daidoji_school.py` to 100%.
### T-D2: Streamlit smoke.
### T-D3: BACKLOG.md update.

## Execution order

A1 → A2 → A3 → A5 → A4 (or defer) → B1 → B2 → C1 → D1 → D2 → D3
