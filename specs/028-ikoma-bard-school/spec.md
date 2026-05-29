# Spec: Ikoma Bard School

**Branch**: `028-ikoma-bard-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Ikoma Bard School").

## Rules text (verbatim, from rules/04-schools.md)

> **Ikoma Bard School**
>
> **School Ring:** Any non-Void
>
> **School Knacks:** discern Honor, oppose knowledge, oppose social
>
> **Special Ability:** Once per round before making an attack roll
> against an opponent, you may force the opponent to spend their
> next available action die to attempt to parry your attack.
>
> **First Dan:** Roll one extra die on attack, bragging, and wound
> checks.
>
> **Second Dan:** You get a free raise on attack rolls.
>
> **Third Dan:** Each adventure you get 2X free raises, where X is
> equal to your bragging skill, which may be applied to the
> following rolls: bragging, culture, heraldry, intimidation,
> attack, and wound checks. You may not spend more than X of these
> free raises on a single roll.
>
> **Fourth Dan:** Raise your current and maximum in any non-Void
> Ring by 1. Raising that Ring now costs 5 fewer XP. When making a
> damage roll for an unparried attack for which you are not keeping
> extra damage dice, you always roll 10 dice.
>
> **Fifth Dan:** Once per conversation or combat round, you can
> apply an oppose knack or your Special ability an additional time.
> You may choose to use your Special Ability after an opponent has
> made an attack roll against you, in which case their attack is
> canceled and their attack roll will be used as their parry roll.
>
> **Note**: the first sentence of the 5th Dan rules text was the
> only fragment returned by the initial spec dispatch's WebFetch.
> Rules-auditor pulled the FULL text directly from upstream which
> includes the second sentence — confirming the skeleton's
> ``IkomaFifthDanAttackRolledListener`` is rules-correct, not
> over-implementation as the spec's initial pre-resolution
> incorrectly claimed.

## Skeleton audit (pre-audit reading)

`simulation/schools/ikoma_bard_school.py` (292 lines), 37 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| School Ring "Any non-Void" | `school_ring()` hardcoded to "water" | **Q1 MEDIUM**: same pattern as Monk/Ide/Priest. Apply school_choices. |
| Special Ability — force parry once per round | `IkomaTakeAttackActionEvent` + `IkomaSpecialTracker` + `IkomaNewRoundListener` | ✅ Mostly correct. **Q2 INTERPRETIVE**: rules say "before making an attack roll"; skeleton triggers AFTER the roll on hits only. Simplification acceptable (the bard's decision-timing automates to "force only when needed"). |
| 1st Dan — +1 die on attack/bragging/WC | `extra_rolled()` ✓ | ✅ Correct |
| 2nd Dan — free raise on attack | `free_raise_skills()` returns `["attack"]` | ✅ Correct |
| 3rd Dan — AP raises on the 6 listed rolls | `ap_base_skill="bragging"` + `ap_skills` returns the 6 | ✅ Correct |
| 4th Dan — Ring +1 (chosen non-Void) + discount + 10-dice damage floor when no raises | `apply_school_ring_raise_and_discount` (uses `school_ring()`) + `IkomaFourthDanRollParameterProvider` sets `rolled = max(rolled, 10)` when `attack_extra_rolled == 0` | ✅ Mostly correct. Ring choice depends on Q1 fix. |
| 5th Dan — "additional time" for SA or oppose knack | `set_max_uses(2)` + `IkomaFifthDanAttackRolledListener` that CANCELS opponent attacks | **Q5 BLOCKING**: `set_max_uses(2)` correctly implements "additional use of Special Ability". But the cancel-opponent-attack listener is NOT in the rules text. The Special Ability is OFFENSIVE (force opponent to parry the Ikoma's attack); canceling an opponent's incoming attack is a different (defensive) ability not granted by 5th Dan. |

## Goals

1. **Fix Q1 (school_ring choice)** — apply Monk/Ide precedent.
2. **Fix Q5 (5th Dan over-implementation)** — REMOVE the cancel-opponent-attack listener; the `set_max_uses(2)` already correctly implements "additional use of Special Ability".
3. **Document Q2 (timing simplification)** as acceptable deferral.
4. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
5. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — 5th Dan over-implementation removal (Priority: P1) 🎯 MVP
Q5 — remove `IkomaFifthDanAttackRolledListener` and its installation.

### US2 — School ring choice (Priority: P1)
Q1 — school_choices.

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US4 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: Once per round, force opponent to spend action die to attempt parry.

### 1st & 2nd Dan
- **FR-002**: `extra_rolled()` returns `["attack", "bragging", "wound check"]`.
- **FR-003**: `free_raise_skills()` returns `["attack"]`.

### 3rd Dan
- **FR-004**: AP system, bragging base, 6 skills, 2X multiplier.

### 4th Dan
- **FR-005**: Ring +1 + discount on chosen non-Void ring via school_choices.
- **FR-006**: 10-dice damage floor when no raises taken on attack.

### 5th Dan (BLOCKING fix)
- **FR-007**: `set_max_uses(2)` — additional use of Special Ability per round.
- **FR-008**: REMOVE the cancel-opponent-attack listener (not in rules).

### Identity-driven defaults
- **FR-009**: `IKOMA_BARD_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).

## Success Criteria

- **SC-001**: 450-XP Ikoma wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `ikoma_bard_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
