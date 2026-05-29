# Spec: Doji Artisan School

**Branch**: `027-doji-artisan-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Doji Artisan School"). BACKLOG flag: "Has ad-hoc `_doji_artisan_*` attributes flagged by the negation refactor."

## Rules text (verbatim, from rules/04-schools.md)

> **Doji Artisan School**
>
> **School Ring:** Air or Water
>
> **School Knacks:** counterattack, oppose social, worldliness
>
> **Special Ability:** You may spend a void point to counterattack
> as an interrupt action at the cost of one actions die; this void
> point still gives your counterattack +1k1. While counterattacking,
> you receive a bonus equal to the attacker's roll divided by 5,
> rounded down.
>
> **First Dan:** Roll one extra die on counterattack, manipulation,
> and wound checks.
>
> **Second Dan:** You get a free raise on manipulation.
>
> **Third Dan:** Each adventure you get 2X free raises, where X is
> equal to your culture skill, which may be applied to the following
> rolls: bragging, culture, heraldry, manipulation, counterattack,
> and wound checks. You may not spend more than X of these free
> raises on a single roll.
>
> **Fourth Dan:** Raise your current and maximum Air or Water by 1.
> Raising that ring now costs 5 fewer XP. When attacking a target
> who has not attacked you this round, you receive a bonus equal to
> the current phase.
>
> **Fifth Dan:** When making any TN or contested roll, you receive a
> bonus equal to (X-10) / 5 where X is the TN or result of your
> opponent's contested roll.

## Skeleton audit (pre-audit reading)

`simulation/schools/doji_artisan_school.py` (302 lines), 33 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| School Ring "Air or Water" | `school_ring()` hardcoded to "water" | **Q1 MEDIUM**: rules give Air/Water choice. Apply school_choices with restricted validation. |
| Special Ability — VP-interrupt counterattack + attacker-roll/5 bonus | `DojiArtisanCounterattackInterruptStrategy` fires on AttackRolledEvent with VP=1; `DojiArtisanTakeCounterattackActionEvent.play` applies `attacker_roll // 5` post-roll | ✅ Mostly correct. **Q2 INTERPRETIVE**: "while counterattacking" scope — skeleton applies the bonus ONLY through the VP-interrupt path. Alternative reading: applies on ALL Doji counterattacks. Defer. |
| 1st Dan — +1 die on counterattack/manipulation/WC | `extra_rolled()` returns the three | ✅ Correct |
| 2nd Dan — free raise on manipulation | `free_raise_skills()` returns `["manipulation"]` | ✅ Correct |
| 3rd Dan — AP raises on bragging/culture/heraldry/manipulation/counterattack/WC | `apply_ap` + `ap_base_skill="culture"` + `ap_skills` returns all 6 | ✅ Correct (includes non-combat skills for completeness — works because AP system gates by skill membership). |
| 4th Dan — Ring +1 + discount + phase bonus vs non-attackers | `apply_school_ring_raise_and_discount` (uses `school_ring()`) + `DojiArtisanAttackTracker` + 3 listeners | ✅ Mostly correct. **Q3 NOTE**: ad-hoc `character._doji_artisan_attack_tracker` attribute not tracked in `_school_owned_*` slots (BACKLOG flag). Same pattern as Daidoji `_daidoji_third_dan`. Defer per cross-school precedent. |
| 5th Dan — (X-10)/5 bonus on TN/contested rolls | `DojiFifthDanRollParameterProvider`: attacks use `target.tn_to_hit()`; WC uses `character.lw()` | ✅ Mostly correct. **Q4 MINOR**: parry and other skill rolls don't get the bonus. Rules say "any TN or contested roll". Defer (the included paths cover most combat impact). |

## Goals

1. **Fix Q1 (school_ring choice)** — apply Monk/Ide precedent with restricted Air/Water validation.
2. **Document Q2 (SA bonus scope)** as interpretive deferral.
3. **Document Q3 (ad-hoc attribute tracking)** as cross-school refactor deferral.
4. **Document Q4 (5th Dan parry coverage)** as deferral.
5. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
6. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — School ring choice (Priority: P1) 🎯 MVP
Q1 — school_choices with restricted Air/Water validation.

### US2 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US3 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: VP-interrupt counterattack at 1-die cost.
- **FR-002**: VP gives +1k1 to the counterattack roll.
- **FR-003**: Attacker-roll/5 bonus on the VP-interrupt counterattack.

### 1st & 2nd Dan
- **FR-004**: `extra_rolled()` returns `["counterattack", "manipulation", "wound check"]`.
- **FR-005**: `free_raise_skills()` returns `["manipulation"]`.

### 3rd Dan
- **FR-006**: AP system with culture base, ap_skills include counterattack + WC + non-combat skills.

### 4th Dan (Q1 fix)
- **FR-007**: Ring +1 + discount on the chosen Air/Water ring via `school_choices["school_ring"]`.
- **FR-008**: Phase bonus on attacks against targets who haven't attacked the Doji this round.

### 5th Dan
- **FR-009**: (X-10)/5 bonus on attack rolls (X = target's tn_to_hit) and WC rolls (X = current LW).

### Identity-driven defaults
- **FR-010**: `DOJI_ARTISAN_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern).
- **FR-011**: Strategy bindings reviewed by `school-strategy-designer`.

## Success Criteria

- **SC-001**: 450-XP Doji wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds.
- **SC-003**: 100% coverage on `doji_artisan_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
