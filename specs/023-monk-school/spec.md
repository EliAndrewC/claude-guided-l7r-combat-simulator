# Spec: Brotherhood of Shinsei Monk School

**Branch**: `023-monk-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Brotherhood of Shinsei Monk School"). Unarmed monk.

## Rules text (verbatim, from rules/04-schools.md)

> **Brotherhood of Shinsei Monk School**
>
> **School Ring:** Any non-Void
>
> **School Knacks:** conviction, otherworldliness, worldliness
>
> **Special Ability:** You roll and keep one extra die for damage
> rolls from unarmed attacks.
>
> **First Dan:** Roll one extra die on attack, damage, and wound
> checks.
>
> **Second Dan:** You get a free raise on all attack rolls.
>
> **Third Dan:** Each adventure you get 2X free raises, where X is
> equal to your precepts skill, which may be applied to the following
> rolls: history, law, precepts, wound checks, and attack. You may
> not spend more than X of these free raises on a single roll.
> These free raises may also be applied to action dice at any time,
> lowering a single die by 5 phases.
>
> **Fourth Dan:** Raise your current and maximum rank in a non-Void
> ring of your choice by 1. Raising this Ring now costs 5 fewer XP.
> Failed parry attempts do not lower your rolled damage dice.
>
> **Fifth Dan:** Once per round after you have been attacked but
> before damage is rolled, you may spend an action die from any
> phase to attack your attacker. If your attack roll is at least as
> high as your attacker's then the attack against you is canceled;
> your attack continues and you hit/miss and roll damage as normal.

## Skeleton audit (pre-audit reading)

`simulation/schools/monk_school.py` (262 lines), 35 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| School Ring — "Any non-Void" (player choice) | `school_ring()` hardcoded to `"water"` | **Q1 MEDIUM**: rules say player chooses ring at character build; should use `school_choices` (Ide Diplomat precedent at `ide_school.py:107-125`). |
| School Knacks — conviction / otherworldliness / worldliness | `school_knacks()` returns the three | ✅ Correct |
| Special Ability — +1k1 on damage rolls (unarmed) | `_set_school_extra_rolled("damage", 1)` + `_set_school_extra_kept("damage", 1)` | ✅ Correct |
| 1st Dan — +1 die on attack / damage / WC | `extra_rolled()` returns the three | ✅ Correct |
| 2nd Dan — free raise on attack | `free_raise_skills()` returns `["attack"]` | ✅ Correct |
| 3rd Dan — AP system + 2X raises + lower action dice by 5 phases per AP | `apply_ap` + `MonkNewRoundListener._lower_action_dice` (spends AP eagerly each round to lower highest die above 5) | ✅ Mostly correct. **Q2 MINOR**: rules say "at any time" — strategic-choice optimization deferred; eager-spend is acceptable. |
| 4th Dan — Ring +1 (chosen non-Void) + discount + failed parry doesn't lower damage dice | `apply_school_ring_raise_and_discount` (uses `school_ring()` which is currently hardcoded "water") + `MonkActionFactory` returns `MonkAttackAction` whose `calculate_extra_damage_dice` ignores `parry_attempted` | ✅ Mostly correct. The "chosen non-Void" depends on Q1's school_choices fix to redirect the +1 to the chosen ring. |
| 5th Dan — once-per-round counter-attack (any phase die) | `MonkFifthDanListener` fires on `AttackSucceededEvent` (target=monk); spends HIGHEST die; rolls attack vs attacker; if counter_roll >= attacker_roll, cancels original attack AND rolls damage on attacker | ✅ Mostly correct. **Q3 MINOR**: skeleton always rolls damage when canceled. Rules say "your attack continues and you hit/miss and roll damage as normal" — implying the hit-vs-tn_to_hit check should also gate the damage. In practice attacker's attack roll usually exceeds their own tn_to_hit so the gap is theoretical. |

## Goals

1. **Fix Q1 (school_ring choice)** — use `school_choices["school_ring"]` per Ide Diplomat precedent.
2. **Principle VII trace observability** for 3rd Dan AP-spend-on-action-dice + 5th Dan counter-attack.
3. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
4. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — School ring choice fix (Priority: P1) 🎯 MVP
Q1 — implement `school_choices["school_ring"]` with "water" default + valid non-Void validation.

### US2 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US3 — Trace observability (Priority: P2)

### US4 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: Damage rolls get +1 rolled AND +1 kept (unarmed).

### 1st & 2nd Dan
- **FR-002**: `extra_rolled()` returns `["attack", "damage", "wound check"]`.
- **FR-003**: `free_raise_skills()` returns `["attack"]`.

### 3rd Dan
- **FR-004**: AP system with `precepts` base skill + ap_skills include attack and WC.
- **FR-005**: `MonkNewRoundListener` lowers action dice by 5 phases per AP available (after initiative roll).

### 4th Dan
- **FR-006**: Ring +1 + discount on the chosen ring (per Q1 fix).
- **FR-007**: Failed parry attempts don't lower the monk's rolled damage dice.

### 5th Dan
- **FR-008**: After `AttackSucceededEvent` (target=monk), once per round, spend highest action die, roll attack, compare to attacker's roll. If counter_roll >= attacker_roll, cancel original + roll damage on attacker.

### School ring choice (Q1 fix)
- **FR-009**: `school_ring()` reads `school_choices["school_ring"]`; defaults to "water"; validates non-Void; warns + fallback on invalid.

### Identity-driven defaults
- **FR-010**: `MONK_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).
- **FR-011**: Strategy bindings reviewed by `school-strategy-designer`.

## Non-Functional Requirements

- **NFR-001**: 100% coverage (mechanically enforced).

## Success Criteria

- **SC-001**: 450-XP Monk wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `monk_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
