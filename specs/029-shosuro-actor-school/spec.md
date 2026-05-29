# Spec: Shosuro Actor School

**Branch**: `029-shosuro-actor-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Shosuro Actor School").

## Rules text (verbatim, from rules/04-schools.md)

> **Shosuro Actor School**
>
> **School Ring:** Air
>
> **School Knacks:** athletics, discern Honor, pontificate
>
> **Special Ability:** Roll extra dice equal to your acting on
> attack, parry, and wound checks.
>
> **First Dan:** Roll one extra die on attack, sincerity, and
> wound checks.
>
> **Second Dan:** You get a free raise on sincerity rolls.
>
> **Third Dan:** Each adventure you get 2X free raises, where X
> is equal to your sincerity skill, which may be applied to the
> following rolls: acting, heraldry, sincerity, sneaking, attack,
> and wound checks. You may not spend more than X of these free
> raises on a single roll.
>
> **Fourth Dan:** Raise your current and maximum Air by 1.
> Raising your Air now costs 5 fewer XP. Your Rank is considered
> 5.0 higher for the purpose of calculating your stipend.
>
> **Fifth Dan:** After making any non-initiative roll, add your
> lowest three dice to the result. (Some dice may be counted
> twice.)

## Skeleton audit (pre-audit reading)

`simulation/schools/shosuro_actor_school.py` (143 lines), 25
existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| School Ring "Air" | `school_ring()` returns "air" | ✅ Correct (no choice) |
| Special Ability — extra dice equal to acting on attack/parry/WC | `ShosuroRollParameterProvider` adds `character.skill("acting")` to ATTACK_SKILLS + parry + wound check | ✅ Mostly correct. **Q2 INTERPRETIVE**: ATTACK_SKILLS includes feint/double-attack, broader than rules-text "attack". Defensible per other schools' "attack means attack-family" precedent. |
| 1st Dan — +1 die on attack/sincerity/WC | `extra_rolled()` returns those three | ✅ Correct |
| 2nd Dan — free raise on sincerity | `free_raise_skills()` returns `["sincerity"]` | ✅ Correct |
| 3rd Dan — AP system, 2X raises, 6 listed rolls | `ap_base_skill="sincerity"` + `ap_skills` returns the 6 | ✅ Correct |
| 4th Dan — Air +1, discount, stipend | `apply_school_ring_raise_and_discount` (stipend = no-op in combat) | ✅ Correct |
| 5th Dan — "any non-initiative roll" | `ShosuroActorRollProvider` wraps `get_skill_roll` + `get_wound_check_roll` only. **Damage rolls excluded.** | **Q1 BLOCKING**: rules say "any non-initiative roll"; skeleton restricts to skill + wound check. Damage rolls (which are non-initiative) should also get the lowest-3-dice bonus per rules. |

### Q1 BLOCKING context

Skeleton's docstring states: "TN/contested rolls are skill rolls
and wound checks. Damage rolls and initiative rolls are NOT
modified." This is a NARROWER interpretation than the rules text
"any non-initiative roll" — which would include damage rolls.

The rules-text scope is broad: "After making any non-initiative
roll, add your lowest three dice to the result." Initiative is
explicitly excluded by name; nothing else is excluded.

Decision: **extend the 5th Dan bonus to damage rolls** to match
rules text. Damage reduction rolls remain deferred (interpretive
edge case — "damage reduction" is arguably a defensive adjustment
rather than a primary roll).

## Goals

1. **Fix Q1 (5th Dan damage roll)** — extend lowest-3-dice
   bonus to damage rolls per rules-text "any non-initiative".
2. **Document Q2 (Special Ability scope)** as deferral — ATTACK_SKILLS
   broader interpretation is defensible.
3. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility
   vs Akodo at 450 XP.
4. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — 5th Dan damage roll (Priority: P1) 🎯 MVP
Q1 — extend `ShosuroActorRollProvider.get_damage_roll` to add
lowest-3-dice bonus from damage dice info.

### US2 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US3 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: Acting skill rank added to attack-family + parry +
  wound check rolled dice.

### 1st & 2nd Dan
- **FR-002**: `extra_rolled()` = `["attack", "sincerity", "wound check"]`.
- **FR-003**: `free_raise_skills()` = `["sincerity"]`.

### 3rd Dan
- **FR-004**: AP system, sincerity base, 6 skills, 2X multiplier.

### 4th Dan
- **FR-005**: Air +1 + discount.

### 5th Dan (Q1 BLOCKING fix)
- **FR-006**: After ANY non-initiative roll (skill, wound check,
  AND damage), add lowest 3 dice to result.

### Identity-driven defaults
- **FR-007**: `SHOSURO_ACTOR_PRIORITIES` reviewed by
  `school-progression-designer` (deferred per pattern).
- **FR-008**: Strategy bindings reviewed by
  `school-strategy-designer` (deferred per pattern).

## Success Criteria

- **SC-001**: 450-XP Shosuro wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds
  (or skip with Hida-style honest documentation).
- **SC-003**: 100% coverage on `shosuro_actor_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
