# Spec: Priest School

**Branch**: `025-priest-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Priest School"). BACKLOG flag: "Has 5 TODO markers — likely a near-empty skeleton." User direction: "this will involve a lot of bonuses to other people on the same side, and therefore will be a big deal to implement but take a shot at it and see what you can do with our usual process".

## Rules text (verbatim, from rules/04-schools.md)

> **Priest School**
>
> **School Ring:** Any non-Void
>
> **School Knacks:** conviction, otherworldliness, pontificate
>
> **Special Ability:** You have all 10 rituals listed under the
> Priest profession.
>
> **First Dan:** Roll one extra die on precepts, any one skill, and
> any one type of combat roll.
>
> **Second Dan:** You and your allies get a free raise on all rolls
> for which you receive an Honor bonus (bragging, precepts, and open
> sincerity).
>
> **Third Dan:** Roll X dice at the beginning of combat, where X is
> equal to your precepts skill. You may swap any of these dice for
> any rolled die on any attack, parry, wound check, or damage roll.
> You may swap any of these dice for any lower die on any of those
> types of rolls made by any ally.
>
> **Fourth Dan:** Raise your current and maximum of your School's
> chosen Ring by 1. Raising that Ring now costs 5 fewer XP. You and
> your allies get a free raise on all contested rolls for which your
> opponent has an equal or higher skill rank.
>
> **Fifth Dan:** You may spend the points from your Conviction knack
> on your allies' rolls, and your Conviction points refresh after
> each conversation and combat round. You may also spend these
> points to lower action dice in order for you or an ally to
> counterattack or parry.

## Skeleton audit (pre-audit reading)

`simulation/schools/priest_school.py` (84 lines), 11 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| School Ring — "Any non-Void" (player choice) | `school_ring()` hardcoded to "water" | **Q1 MEDIUM**: same pattern as Monk/Ide/Ise Zumi — needs `school_choices`. |
| Special Ability — all 10 rituals (no combat effect) | `apply_special_ability` is `pass` | ✅ Correct — rituals have no combat applicability. |
| 1st Dan — extra die on "precepts, any one skill, any one type of combat roll" | `extra_rolled()` hardcoded to `["precepts", "initiative", "wound check"]` | **Q2 MEDIUM**: rules grant player choice of "any one skill" + "any one combat roll". Hardcoded choices don't match rules. Apply school_choices pattern. |
| 2nd Dan — free raise on Honor-bonus rolls (self + allies) | `free_raise_skills()` returns `["bragging", "precepts", "sincerity"]` (self only) | **Q3 DEFERRED**: skills are non-combat; ally-buff version moot in 1v1 simulator. |
| 3rd Dan — Roll X dice at **beginning of combat**, swap (not add) for any rolled die on attack/parry/WC/damage; swap for lower die on ally rolls | `PriestNewRoundListener` fires on EVERY new round (not start-of-combat) + uses `FloatingBonus` which ADDS rather than SWAPS | **Q4 BLOCKING**: rolls X dice per ROUND instead of per COMBAT — strictly over-powered (priest accumulates pool every round). **Q5 DEFERRED**: swap semantics not modeled in engine (FloatingBonus adds, doesn't replace). **Q6 DEFERRED**: ally-target swap. |
| 4th Dan — Ring +1 + discount + Honor free-raise on contested rolls (self + allies) | `apply_school_ring_raise_and_discount` ✓ + TODO for contested raises | ✅ Ring raise correct (will need school_choices Q1 for the chosen ring). **Q7 DEFERRED**: contested-roll bonus (rare in combat). |
| 5th Dan — Conviction on allies' rolls + refresh + action-die lower for counterattack/parry | `apply_rank_five_ability` is `pass` | **Q8 BIG DEFERRED**: unimplemented. Conviction-on-allies + action-die lowering are complex ally-buff mechanics; majority moot in 1v1 simulator. |

## Goals

1. **Fix Q1 (school_ring choice)** — apply Monk/Ide precedent.
2. **Fix Q4 (3rd Dan beginning-of-combat)** — fire ONCE per combat, not per round.
3. **Fix Q2 (1st Dan choices)** — apply school_choices for the two "any one" slots.
4. **Document Q3/Q5/Q6/Q7/Q8 as deferrals** — ally-buff mechanics that are moot in 1v1 simulator or require engine-level "swap" mechanics.
5. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
6. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — 3rd Dan BLOCKING fix (Priority: P1) 🎯 MVP
Q4 (fire pool roll ONCE per combat, not every round).

### US2 — School ring choice + 1st Dan choices (Priority: P1)
Q1 + Q2 (school_choices pattern).

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US4 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: No combat effect (`pass`).

### 1st Dan (Q2 fix)
- **FR-002**: `extra_rolled()` returns `["precepts", chosen_skill, chosen_combat]` from `school_choices`, defaulting to `["precepts", "initiative", "wound check"]`. Validate choices.

### 2nd Dan
- **FR-003**: `free_raise_skills()` returns `["bragging", "precepts", "sincerity"]`.

### 3rd Dan (Q4 BLOCKING fix)
- **FR-004**: Roll X dice ONCE at the FIRST `NewRoundEvent` (combat start), where X = precepts. Subsequent rounds do NOT re-roll. Pool persists for the duration of combat.
- **FR-005**: Each pool die becomes a FloatingBonus applicable to attack/parry/WC/damage (swap-vs-add semantics deferred).

### 4th Dan (Q1 fix)
- **FR-006**: School ring +1 via `school_choices["school_ring"]`; default "water"; validate against {"air", "earth", "fire", "water"} (rules: "Any non-Void").
- **FR-007**: Contested-roll Honor free raise — DEFERRED.

### 5th Dan
- **FR-008**: DEFERRED (entirely unimplemented). `apply_rank_five_ability` is no-op.

### Identity-driven defaults
- **FR-009**: `PRIEST_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).

## Success Criteria

- **SC-001**: 450-XP Priest wins ≥ 35% vs 450-XP Akodo across 20 seeds (subject to inherent priest combat weakness — informational).
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `priest_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
