# Spec: Togashi Ise Zumi School

**Branch**: `024-ise-zumi-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Togashi Ise Zumi School"). Dragon-clan tattooed monk.

## Rules text (verbatim, from rules/04-schools.md)

> **Togashi Ise Zumi School**
>
> **School Ring:** Void
>
> **School Knacks:** athletics, conviction, dragon tattoo
>
> **Special Ability:** Roll either 1 or 3 extra action dice at the
> beginning of each combat round. If you roll 1 die, it may only be
> spent on athletics actions; if you roll 3 dice, all of your action
> dice may only be spent on athletics actions.
>
> **First Dan:** Roll one extra die on athletics, initiative, and
> wound checks.
>
> **Second Dan:** You get a free raise on athletics rolls.
>
> **Third Dan:** Each day you get 4X free raises which may be applied
> to athletics rolls, where X is your precepts skill. You may not
> spend more than X of these free raises on a single roll.
>
> **Fourth Dan:** Raise the current and maximum rank of any Ring by
> 1. Raising that Ring now costs 5 fewer XP. You may reroll any
> contested roll once after seeing the result, but you must keep the
> new result even if it's lower than the first.
>
> **Fifth Dan:** At any time, you may spend 1 void point to heal 2
> serious wounds.

## Skeleton audit (pre-audit reading)

`simulation/schools/ise_zumi_school.py` (103 lines), 17 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| School Ring — Void | `school_ring()` returns `"void"` | ✅ Correct |
| School Knacks — athletics / conviction / dragon tattoo | `school_knacks()` returns the three | ✅ Correct |
| Special Ability — 1 or 3 extra dice, athletics-only restriction | `IseZumiNewRoundListener` rolls 1 extra die unconditionally; no athletics restriction | **Q1 MEDIUM**: 1-or-3 choice not implemented (always 1). **Q2 MEDIUM**: athletics-only restriction not implemented — extra die is freely usable for attacks/parries, violating the rules. |
| 1st Dan — +1 die on **athletics, initiative, wound checks** | `extra_rolled()` returns `["attack", "parry", "athletics"]` | **Q3 BLOCKING**: skeleton returns WRONG skill list. Rules say `["athletics", "initiative", "wound check"]`. Skeleton list includes attack/parry which aren't in the rules clause. |
| 2nd Dan — free raise on athletics | `free_raise_skills()` returns `["athletics"]` | ✅ Correct |
| 3rd Dan — 4X AP raises on athletics | `apply_ap` + `ap_base_skill = "precepts"` + `ap_skills = ["athletics"]` + `set_ap_multiplier(4)` | ✅ Correct. Note: athletics is non-combat in simulator → 3rd Dan effectively dead in combat. |
| 4th Dan — Raise rank of ANY Ring by 1 + discount + contested-reroll | `apply_school_ring_raise_and_discount` uses `school_ring()` returning "void" | **Q4 MEDIUM**: rules say "any Ring" (player choice). Hardcoded to "void". Apply Ide/Monk school_choices precedent. **Q5 MINOR DEFERRED**: contested-roll reroll not implemented (rarely encountered in combat). |
| 5th Dan — at any time, spend 1 VP to heal 2 SW | `IseZumiWoundCheckFailedListener` fires only on `WoundCheckFailedEvent`; gates on `vp() >= 1 and sw() >= 2` | **Q6 MEDIUM**: rules say "at any time" — restricted to post-WC-failure. **Q7**: SW event flow ordering OK (engine processes yielded events synchronously, so sw() check is post-SW application). |

## Goals

1. **Fix Q3 (1st Dan skill list)** — return rules-text list.
2. **Fix Q4 (4th Dan any-ring choice)** — apply Ide/Monk school_choices pattern.
3. **Document Q1/Q2/Q6 as deferrals** — complex design decisions or rarely-encountered scenarios.
4. **Principle VII trace observability** for 5th Dan VP-spend-to-heal.
5. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
6. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — Rules-fidelity BLOCKING fix (Priority: P1) 🎯 MVP
Q3 (1st Dan extra_rolled).

### US2 — School ring choice (Priority: P1)
Q4 (4th Dan any-ring choice via school_choices).

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US4 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: 1 extra action die per round (Q1/Q2 deferred — current behavior).

### 1st & 2nd Dan
- **FR-002**: `extra_rolled()` returns `["athletics", "initiative", "wound check"]` (Q3 fix — was `["attack", "parry", "athletics"]`).
- **FR-003**: `free_raise_skills()` returns `["athletics"]`.

### 3rd Dan
- **FR-004**: AP system with precepts base, athletics ap_skills, 4x multiplier.

### 4th Dan
- **FR-005**: School ring +1 via `school_choices["school_ring"]` (Q4 fix — was hardcoded "void"). Default "void", validate against {"air", "earth", "fire", "water", "void"} (4th Dan permits Void).
- **FR-006**: Contested-roll reroll DEFERRED.

### 5th Dan
- **FR-007**: After failed WC, spend 1 VP to heal 2 SW (current behavior; Q6 "at any time" deferred).

### Identity-driven defaults
- **FR-008**: `ISE_ZUMI_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).

## Success Criteria

- **SC-001**: 450-XP Ise Zumi wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `ise_zumi_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
