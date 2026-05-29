# Spec: Isawa Duelist School

**Branch**: `022-isawa-duelist-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Isawa Duelist School"). NOTE: NOT the Isawa Ishi School — this is the Phoenix-clan duelist with water-for-damage Special Ability. BACKLOG flags "water-damage skill_ring mutation flagged by the negation refactor".

## Rules text (verbatim, from rules/04-schools.md)

> **Isawa Duelist School**
>
> **School Ring:** Water
>
> **School Knacks:** double attack, iaijutsu, lunge
>
> **Special Ability:** You add your Water instead of Fire to your
> rolled damage dice.
>
> **First Dan:** Roll one extra die on double attack, lunge, and
> wound checks.
>
> **Second Dan:** You get a free raise on wound checks.
>
> **Third Dan:** After you make any type of attack roll, you may
> lower your TN to be hit by 5 for the next time that you are
> attacked this round to get a bonus of 3X on your attack roll,
> where X is your attack skill. If a successful or unsuccessful
> parry is made against your attack, you do not suffer the TN
> penalty.
>
> **Fourth Dan:** Raise your current and maximum Water by 1.
> Raising your Water now costs 5 fewer XP. Once per round, you may
> lunge as an interrupt action at the cost of 1 action die.
>
> **Fifth Dan:** After a successful wound check, you may add X to
> a future wound check this combat, where X is the amount by which
> the wound check exceeded the light wound total.

## Skeleton audit (pre-audit reading)

`simulation/schools/isawa_school.py` (196 lines), 19 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — Water instead of Fire on damage rolled dice | `character._skill_rings["damage"] = "water"` + `IsawaRollParameterProvider.get_damage_roll_params` uses water ring | ✅ Mostly correct. **Q1 MINOR (BACKLOG-flagged)**: direct mutation of `_skill_rings` not tracked in `_school_owned_*` slots → school-negation can't revert. |
| 1st Dan — +1 die on double attack / lunge / WC | `extra_rolled()` returns the three | ✅ Correct |
| 2nd Dan — free raise on WC | `free_raise_skills()` returns `["wound check"]` | ✅ Correct |
| 3rd Dan — after attack roll, **may** lower own TN by 5 to get +3X on attack. NOT if attack is parried. | `IsawaAttackAction.skill_roll_params` adds `+3 * attack_skill` to modifier unconditionally. `IsawaAttackDeclaredListener` defined but **NEVER INSTALLED**. | **Q4 BLOCKING IDENTITY**: TN penalty entirely missing. +3X bonus has NO downside. Strictly over-powered. **Q3 BLOCKING**: even if the listener WERE installed, it doesn't check for parry. **Q2 MINOR**: "may" gate — bonus is always taken (acceptable). |
| 4th Dan — Water +1 + discount + once-per-round interrupt-lunge | `apply_school_ring_raise_and_discount` + `set_interrupt_cost("lunge", 1)` + `add_interrupt_skill("lunge")` + `IsawaNewRoundListener` resets cost | **Q6 BLOCKING IDENTITY**: no strategy installed for the interrupt-lunge. Same as Kakita/Otaku Q1 — `add_interrupt_skill` wired but no strategy fires it. **Q5 MINOR**: "once per round" not enforced — character could fire interrupt-lunge multiple times per round if it had enough dice. |
| 5th Dan — successful WC → gain `WoundCheckFloatingBonus(roll - damage)` | `IsawaWoundCheckSucceededListener` adds the bonus when positive | ✅ Correct |

## Goals

1. **Fix Q3 + Q4 (3rd Dan TN penalty)** — install the listener, scope to "not parried" attacks.
2. **Fix Q6 (4th Dan interrupt-lunge strategy)** — install a strategy that fires the interrupt-lunge.
3. **Q5 (once-per-round)** — track a per-round flag.
4. **Principle VII trace observability** for 3rd Dan +3X / TN penalty + 5th Dan WC floating bonus.
5. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
6. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — Rules-fidelity BLOCKING fixes (Priority: P1) 🎯 MVP
Q3 (3rd Dan TN penalty + parry exemption), Q4 (install the listener), Q6 (interrupt-lunge strategy).

### US2 — Identity-driven defaults (Priority: P1)
Eager-attack-strategy + WoundCheckStrategy04.

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US4 — Trace observability (Priority: P2)

### US5 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: Damage rolls use Water ring instead of Fire.

### 1st & 2nd Dan
- **FR-002**: `extra_rolled()` returns `["double attack", "lunge", "wound check"]`.
- **FR-003**: `free_raise_skills()` returns `["wound check"]`.

### 3rd Dan (BLOCKING fixes)
- **FR-004**: Attack rolls get +3X modifier where X = attack skill.
- **FR-005**: After an attack, the Isawa's `tn to hit` is reduced by 5 until the next attack against them, UNLESS the attack was parried.
- **FR-006**: Install the listener that applies the TN penalty.

### 4th Dan (BLOCKING fixes)
- **FR-007**: Water ring raise + discount.
- **FR-008**: Once-per-round interrupt-lunge — track a per-round flag.
- **FR-009**: Install a strategy that actually fires the interrupt-lunge.

### 5th Dan
- **FR-010**: After successful WC, gain `WoundCheckFloatingBonus(roll - damage)` if positive.

### Identity-driven defaults
- **FR-011**: `ISAWA_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).
- **FR-012**: `WoundCheckStrategy04` installed (1st Dan WC die + 2nd Dan free raise + 5th Dan floating bonus = deep WC pool).

## Success Criteria

- **SC-001**: 450-XP Isawa wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `isawa_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
