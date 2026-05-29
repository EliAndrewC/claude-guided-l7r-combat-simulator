# Spec: Hiruma Scout School

**Branch**: `019-hiruma-scout-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Hiruma Scout School").

## Rules text (verbatim, from rules/04-schools.md)

> **Hiruma Scout School**
>
> **School Ring:** Air
>
> **School Knacks:** double attack, feint, iaijutsu
>
> **Special Ability:** The two allies fighting on your left and
> right have their TN to be hit raised by 5.
>
> **First Dan:** Roll an extra die on initiative, parry, and wound
> checks.
>
> **Second Dan:** You get a free raise to all parry rolls.
>
> **Third Dan:** After making a successful or unsuccessful parry,
> add 2X to your next attack and damage roll against the attacker
> or someone adjacent to them, where X is your attack skill.
>
> **Fourth Dan:** Raise your current and maximum Air by 1. Raising
> your Air now costs 5 fewer XP. After rolling initiative, lower
> all of your action dice by 2, to a minimum of 1.
>
> **Fifth Dan:** After making a successful or unsuccessful parry
> roll, the attacker deals 10 fewer light wounds on their next 2
> damage rolls.

## Skeleton audit (pre-audit reading)

`simulation/schools/hiruma_school.py` (115 lines), 10 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — left/right adjacent allies' TN to hit +5 | `apply_special_ability` is `pass` (TODO) | **Q1 BLOCKING IDENTITY**: completely unimplemented. The entire Special Ability is dead. |
| 1st Dan — +1 die on initiative / parry / WC | `extra_rolled()` returns the three | ✅ Correct |
| 2nd Dan — free raise on parry | `free_raise_skills()` returns `["parry"]` | ✅ Correct |
| 3rd Dan — after parry, +2X to next attack AND damage roll vs attacker or adjacent | `HirumaParryListener` grants `AnyAttackFloatingBonus(2 * attack_skill)` | **Q2 BLOCKING**: bonus scope is ANY attack (skills ATTACK_SKILLS), not just vs attacker or adjacent. **Q3 BLOCKING**: rules say "next attack AND damage roll" — bonus applies to BOTH rolls. `AnyAttackFloatingBonus` applies only to attack-class skill rolls (not damage). |
| 4th Dan — Air +1 + discount + after initiative, lower all dice by 2 (min 1) | `apply_school_ring_raise_and_discount` + `HirumaNewRoundListener` which rolls initiative then subtracts 2 (min 1) | ✅ Correct (per Shinjo precedent: `_set_school_listener` replaces engine default new_round listener, so single roll_initiative call is correct). |
| 5th Dan — after parry, attacker deals 10 fewer LW on next 2 damage rolls | `HirumaFifthDanParryListener` adds `Modifier(attacker, None, "damage", -10)` with `ExpireAfterNDamageRollsListener(attacker, 2)` + duplicates 3rd Dan effect inline | ✅ Mostly correct. **Q4 MINOR**: 3rd Dan effect duplicated inline; refactor by subclassing. |

## Goals

1. **Fix Q1 (Special Ability)** — implement +5 tn_to_hit modifier on left/right adjacent allies.
2. **Fix Q2 (3rd Dan scope)** — bonus only applies vs the attacker or characters adjacent to the attacker.
3. **Fix Q3 (3rd Dan damage roll)** — bonus applies to BOTH attack roll AND damage roll.
4. **Fix Q4 (5th Dan refactor)** — subclass `HirumaParryListener` to delegate 3rd Dan effect.
5. **Principle VII trace observability** for Special Ability TN modifier, 3rd Dan bonus, 5th Dan damage modifier.
6. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
7. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — Rules-fidelity BLOCKING fixes (Priority: P1) 🎯 MVP
Q1 (Special Ability), Q2+Q3 (3rd Dan).

### US2 — Identity-driven defaults (Priority: P1)
Defaults match Scout identity (eager parry, WC-tank).

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US4 — Trace observability (Priority: P2)

### US5 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability (BLOCKING — was unimplemented)
- **FR-001**: `apply_special_ability` MUST register a mechanism that grants `+5` to the `tn to hit` of allies that are the Hiruma's left/right neighbors in the formation.
- **FR-002**: The +5 modifier applies only when the Hiruma is alive and present in the formation.

### 1st & 2nd Dan
- **FR-003**: `extra_rolled()` returns `["initiative", "parry", "wound check"]`.
- **FR-004**: `free_raise_skills()` returns `["parry"]`.

### 3rd Dan (BLOCKING fix)
- **FR-005**: After parry (success or fail), the Hiruma gains a bonus equal to `2 * attack_skill` that applies to BOTH the next attack roll AND the next damage roll.
- **FR-006**: The bonus is scoped to attacks against the original attacker OR a character adjacent to the attacker.

### 4th Dan
- **FR-007**: `apply_school_ring_raise_and_discount` for Air.
- **FR-008**: After initiative roll, all action dice reduced by 2 (min 1).

### 5th Dan
- **FR-009**: After parry (success or fail), the original attacker takes -10 damage on their next 2 damage rolls.
- **FR-010**: The 5th Dan listener also produces the 3rd Dan effect (delegation via subclass per Shinjo precedent).

### Identity-driven defaults
- **FR-011**: `HIRUMA_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).
- **FR-012**: Strategy bindings reviewed by `school-strategy-designer`.

## Non-Functional Requirements

- **NFR-001**: 100% coverage (mechanically enforced).
- **NFR-002**: ≤ 5 existing-test updates outside new tests.

## Success Criteria

- **SC-001**: 450-XP Hiruma wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `hiruma_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
