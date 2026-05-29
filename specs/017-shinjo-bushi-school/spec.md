# Spec: Shinjo Bushi School

**Branch**: `017-shinjo-bushi-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Shinjo Bushi School").

## Rules text (verbatim, from rules/04-schools.md)

> **Shinjo Bushi School**
>
> **School Ring:** Air
>
> **School Knacks:** double attack, iaijutsu, lunge
>
> **Special Ability:** Each action you take in combat has a bonus of
> 2X, where X is the number of phases for which the action die was
> held.
>
> **First Dan:** Roll one extra die on initiative, parry, and wound
> checks.
>
> **Second Dan:** You get a free raise on parry rolls.
>
> **Third Dan:** After a successful or unsuccessful parry, all your
> action dice are decreased by X, where X is equal to your attack
> skill.
>
> **Fourth Dan:** Raise your current and maximum Air by 1. Raising
> your Air now costs 5 fewer XP. Your highest action die is set to
> 1 at the beginning of each combat round.
>
> **Fifth Dan:** After you successfully parry, you may add X to a
> future wound check this combat after seeing your roll, where X is
> the amount by which your parry roll exceeded its TN.

## Skeleton audit (pre-audit reading)

`simulation/schools/shinjo_school.py` (152 lines), 13 existing tests.
Multiple rules-fidelity defects identified.

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — +2X bonus per action where X = phases held | `ShinjoSpendActionListener` computes `2 * hold_phases` and stores on `character._shinjo_hold_bonus` | **Q4 BLOCKING IDENTITY**: the bonus is COMPUTED but never CONSUMED. Nothing in the codebase reads `_shinjo_hold_bonus` to apply it to the skill roll. The school's entire identity is structurally dead. |
| Special Ability — hold-phases calculation | `hold_phases = current_phase - initiative_action.phase()` | **Q5 BLOCKING**: `initiative_action.phase()` is the SCHEDULED phase, not the original die value. For a held die (dice=[3], phase=8), this gives `current_phase - 8 = 0` instead of the actual hold of `current_phase - 3`. Should use `min(initiative_action.dice())` for the original die value. |
| 1st Dan — +1 die on **initiative, parry, wound checks** | `extra_rolled()` returns `["double attack", "initiative", "parry"]` | **Q1 BLOCKING**: WRONG skill list. Rules say `initiative, parry, wound checks`. Skeleton returns `double attack, initiative, parry`. |
| 2nd Dan — free raise on parry | `free_raise_skills()` returns `["parry"]` | ✅ Correct |
| 3rd Dan — all action dice decreased by X (X = attack skill) | `ShinjoParryListener` subtracts `attack_skill` from every die in `character.actions()` | ✅ Mostly correct. Note: allows negative results (rules don't explicitly prohibit). |
| 4th Dan — Air +1 + discount + highest action die set to 1 each round | `apply_school_ring_raise_and_discount` + `ShinjoNewRoundListener` which calls `roll_initiative()` THEN sets max die to 1 | **Q2 BLOCKING**: `ShinjoNewRoundListener.handle` calls `character.roll_initiative()` — but the engine's default `NewRoundListener` (`listeners.py`) already does this. Double-rolling initiative breaks combat. Need to NOT call roll_initiative AGAIN; just mutate the (already-rolled) actions list. Order also matters — must fire AFTER the engine's roll_initiative. |
| 5th Dan — successful parry → may add margin to future WC | `ShinjoFifthDanParryListener` adds `WoundCheckFloatingBonus(parry_roll - attack_roll)` if positive | ✅ Mostly correct. Note: rules say "you **may** add X **after seeing your roll**" — a strategic choice. Current is unconditional gain (always granted). Q6 candidate but the bonus is itself a floating-bonus consumed strategically downstream, so "always gain" + "consume strategically" may be the right pattern. |
| 5th Dan listener duplicates 3rd Dan logic | `ShinjoFifthDanParryListener` re-implements the 3rd Dan action-die decrease inline | **Q3 MINOR**: duplication. Replaces the 3rd Dan listener at 5th Dan, so no double-fire — but the duplicated code is fragile. |

## Goals

1. **Fix Q1 (1st Dan extra_rolled skill list)** — wrong skills returned.
2. **Fix Q2 (4th Dan double-roll-initiative bug)** — listener must not re-call roll_initiative.
3. **Fix Q4 (Special Ability bonus consumption)** — wire the hold bonus into the action's skill roll.
4. **Fix Q5 (hold-phases calculation)** — use original die value, not scheduled phase.
5. **Principle VII trace observability** for hold-bonus, 3rd Dan action-die decrease, 4th Dan highest-to-1.
6. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
7. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — Rules-fidelity BLOCKING fixes (Priority: P1) 🎯 MVP
Q1 (extra_rolled list), Q2 (initiative double-roll), Q4 (Special Ability dead), Q5 (hold-phases math).

### US2 — Identity-driven defaults (Priority: P1)
Special Ability hold-bonus actually applied to action skill rolls.

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US4 — Trace observability (Priority: P2)

### US5 — Coverage (Priority: P1)
100% coverage on `simulation/schools/shinjo_school.py` (mechanically enforced).

## Functional Requirements

### Special Ability — hold-bonus
- **FR-001**: Action skill rolls get a +2X modifier where X = (action_die_phase - original_die_value).
- **FR-002**: The hold-phases value uses the ORIGINAL die value (`min(initiative_action.dice())`), not the scheduled phase.
- **FR-003**: The bonus applies to the action skill roll, not to damage or other downstream rolls.
- **FR-004**: The trace MUST surface "Shinjo Special Ability: +2X (held N phases)" attribution.

### 1st Dan (BLOCKING fix)
- **FR-005**: `extra_rolled()` returns `["initiative", "parry", "wound check"]` (NOT `double attack`).

### 2nd Dan
- **FR-006**: `free_raise_skills()` returns `["parry"]`.

### 3rd Dan
- **FR-007**: After parry (success or fail), all remaining action dice are decreased by X = attack skill (in place, allow negatives).
- **FR-008**: The trace MUST surface "Shinjo 3rd Dan: action dice decreased by N (= attack skill)" attribution.

### 4th Dan (BLOCKING fix)
- **FR-009**: `apply_school_ring_raise_and_discount` for Air.
- **FR-010**: At the start of each round, the highest action die is set to 1 — applied AFTER the engine's `roll_initiative`, NOT in addition to it.
- **FR-011**: The trace MUST surface "Shinjo 4th Dan: highest die set to 1" attribution.

### 5th Dan
- **FR-012**: After a successful parry, gain a `WoundCheckFloatingBonus(margin)` where margin = `parry_roll - attack_roll` (only if positive).

### Identity-driven defaults
- **FR-013**: `SHINJO_PRIORITIES` reviewed by `school-progression-designer` (deferred per Bayushi/Kakita/Otaku/Shiba pattern if it breaks tests).
- **FR-014**: Strategy bindings reviewed by `school-strategy-designer`.

## Non-Functional Requirements

- **NFR-001**: 100% coverage (mechanically enforced).
- **NFR-002**: ≤ 5 existing-test updates outside new tests.

## Success Criteria

- **SC-001**: 450-XP Shinjo wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `shinjo_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
