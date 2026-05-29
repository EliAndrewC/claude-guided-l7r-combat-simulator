# Spec: Courtier School

**Branch**: `026-courtier-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Courtier School"). User direction: "the courtier does have several combat-relevant abilities."

## Rules text (verbatim, from rules/04-schools.md)

> **Courtier School**
>
> **School Ring:** Air
>
> **School Knacks:** discern Honor, oppose social, worldliness
>
> **Special Ability:** Add your Air to all attack and damage rolls.
>
> **First Dan:** Roll one extra die on tact, manipulation, and wound
> checks.
>
> **Second Dan:** You get a free raise on manipulation rolls.
>
> **Third Dan:** Each adventure you get 2X free raises, where X is
> equal to your tact skill, which may be applied to the following
> rolls: heraldry, manipulation, sincerity, tact, attack, and wound
> checks. You may not spend more than X of these free raises on a
> single roll.
>
> **Fourth Dan:** Raise your current and maximum Air by 1. Raising
> your Air now costs 5 fewer XP. Once per target per conversation
> or fight, you get a temporary void point after a successful attack
> or manipulation roll.
>
> **Fifth Dan:** Add your Air to all TN and contested rolls. This
> stacks with your Special Ability for attack rolls.

## Skeleton audit (pre-audit reading)

`simulation/schools/courtier_school.py` (115 lines), 15 existing tests. Combat-relevant identity:
- SA +Air on attack/damage
- 3rd Dan AP raises on attack/WC
- 4th Dan TVP-on-attack-success (once per target per fight)
- 5th Dan +Air on all skill rolls (stacks with SA)

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — Air on attack/damage | `CourtierRollParameterProvider` adds Air to ATTACK_SKILLS skill modifier + damage modifier | ✅ Correct |
| 1st Dan — +1 die on tact/manipulation/WC | `extra_rolled()` returns `["manipulation", "tact", "wound check"]` | ✅ Correct |
| 2nd Dan — free raise on manipulation | `free_raise_skills()` returns `["manipulation"]` | ✅ Correct |
| 3rd Dan — AP system, 2X raises on listed rolls, max X per roll | `apply_ap` + `ap_base_skill="tact"` + `ap_skills=["attack", "wound check"]` | ✅ Mostly correct. Non-combat skills (heraldry, manipulation, sincerity) omitted — OK for combat scope. |
| 4th Dan — Air +1 + discount + once-per-target-per-fight TVP on successful attack | `apply_school_ring_raise_and_discount` + `CourtierAttackSucceededListener` tracks `_targets_triggered` set | ✅ Mostly correct. **Q2 MINOR**: `_targets_triggered` persists across combats — per rules "once per fight" the set should reset between combats. Edge case in single-combat simulator. |
| 5th Dan — Air on all TN/contested rolls (stacks with SA) | `CourtierFifthDanRollParameterProvider` adds Air to ALL skill rolls + WC | ✅ Mostly correct. **Q3 MINOR**: if/else branches both do the same thing (`modifier += character.ring("air")`) — can simplify. **Q4 INTERPRETIVE**: "all TN" might also include TN-to-be-hit (defensive). Skeleton interprets as "all skill rolls". Defensible. |

## Goals

1. **Refactor Q3 (5th Dan simplification)** — collapse the if/else.
2. **Fix Q2 (TVP reset between combats)** — install a NewRoundEvent listener at start of combat (or reset on combat-start).
3. **Document Q4 (TN-to-be-hit interpretation)** as deferral — current "all skill rolls" interpretation is defensible.
4. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
5. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — 5th Dan refactor + TVP reset (Priority: P1) 🎯 MVP
Q3 simplification + Q2 reset-between-combats.

### US2 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US3 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: Add Air to attack-skill rolls and damage rolls.

### 1st & 2nd Dan
- **FR-002**: `extra_rolled()` returns `["manipulation", "tact", "wound check"]`.
- **FR-003**: `free_raise_skills()` returns `["manipulation"]`.

### 3rd Dan
- **FR-004**: AP system with tact base, attack+WC ap_skills, 2x multiplier.

### 4th Dan
- **FR-005**: Air ring raise + discount.
- **FR-006**: TVP gain on successful attack, once per target per fight. (Q2 fix — reset between fights.)

### 5th Dan (refactor)
- **FR-007**: Add Air to all skill rolls (stacks with SA on attack rolls). WC also gets +Air.
- **FR-008**: Simplify the if/else (Q3).

### Identity-driven defaults
- **FR-009**: `COURTIER_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).
- **FR-010**: Strategy bindings reviewed by `school-strategy-designer`.

## Success Criteria

- **SC-001**: 450-XP Courtier wins ≥ 35% vs 450-XP Akodo across 20 seeds (subject to inherent courtier combat strength — combat-simulator will measure).
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `courtier_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
