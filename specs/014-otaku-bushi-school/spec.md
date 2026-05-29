# Spec: Otaku Bushi School

**Branch**: `015-otaku-bushi-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Otaku Bushi School"). Per user clarification: there are no mount mechanics for Otaku; the BACKLOG caveat does not apply.

## Rules text (verbatim, from rules/04-schools.md)

> **Otaku Bushi School**
>
> School Ring: Fire
>
> School Knacks: double attack, iaijutsu, lunge
>
> Special Ability: After an attack against you is completely resolved, you may make a lunge attack at your attacker as an interrupt action at the cost of one action die.
>
> First Dan: Roll one extra die on iaijutsu, lunge, and wound checks.
>
> Second Dan: You get a free raise on wound checks.
>
> Third Dan: After you roll damage against an opponent, increase that character's next X action dice this turn by (6 - that character's Fire) min 1, where X is your attack skill, to a maximum of phase 10.
>
> Fourth Dan: Raise your current and maximum Fire by 1. Raising your Fire now costs 5 fewer XP. When you lunge, you always roll the extra damage die from using lunge even if your attack is unsuccessfully parried.
>
> Fifth Dan: After a successful attack or lunge roll, you may decrease the number of rolled damage dice by 10, to a minimum of 2, to automatically deal 1 serious wound to your opponent. You may only do this once per damage roll.

## Skeleton audit (pre-audit reading)

`simulation/schools/otaku_school.py` (192 lines), 27 existing tests. Several rules-fidelity gaps surface from a careful reading of the rules text against the implementation:

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — 1-die-interrupt lunge after attack resolved | `apply_special_ability`: `set_interrupt_cost("lunge", 1)` + `add_interrupt_skill("lunge")` | **Q1 IDENTITY GAP**: no strategy is installed that ACTUALLY uses the interrupt lunge. Same pattern as the Kakita HIGH-severity bug — the wired interrupt capability may never produce behavior under defaults. |
| 1st Dan — +1 die on iaijutsu / lunge / wound check | `extra_rolled()` returns the three | ✅ Correct |
| 2nd Dan — free raise on wound checks | `free_raise_skills()` returns `["wound check"]` | ✅ Correct |
| 3rd Dan — **next X action dice** increased by (6 − target Fire), where X = attack skill | `OtakuLightWoundsDamageListener.handle` iterates ALL of `target.actions()` | **Q2 BLOCKING**: skeleton modifies ALL the target's action dice; rules say only the NEXT X (X = Otaku's attack skill). Direct rules-fidelity defect. |
| 3rd Dan — `increase = max(1, 6 - target.fire)` | `increase = max(1, 6 - target.ring("fire"))` | ✅ Correct formula |
| 3rd Dan — max phase 10 cap | `actions[i] = min(10, actions[i] + increase)` | ✅ Correct |
| 4th Dan — Fire +1 with 5-XP discount + lunge always-extra-die even on parry | `apply_school_ring_raise_and_discount` + `OtakuLungeAction.calculate_extra_damage_dice` returns 1 when parried | ✅ Mostly correct. The +1 vs base LungeAction's `super() + 1` semantics need verification (does it stack or replace?). |
| 5th Dan — "you may" decrease rolled damage dice by 10 (min 2) → auto 1 SW | `OtakuFifthDanTakeAttackActionEvent._roll_damage`: when `raw_rolled >= 12`, ALWAYS trades 10 dice for SW | **Q3 BLOCKING + Q4 BLOCKING**: (i) "you may" → choice; skeleton always fires (no strategic logic). (ii) Skeleton does `reduced_extra = extra_rolled - 10` — subtracting from MARGIN extras only, not from TOTAL rolled. With margin = 4, this becomes -6 extra rolled → catastrophic miscalc. Rules-text says decrease TOTAL rolled by 10 with floor of 2. |
| 5th Dan — "only once per damage roll" | Implicit (one event per attack) | Looks correct via event structure |

Other observations:

- **`OTAKU_PRIORITIES`** has the same anti-identity parry-at-every-rank pattern (Bayushi / Matsu / Kakita all flagged this).
- **No attack strategy installed** in `apply_special_ability`. Default `UniversalAttackStrategy` may not prioritize lunge (which is the school's signature skill for the Special Ability + 4th Dan).
- **No interrupt strategy installed** for the Special Ability lunge interrupt — same as Q1 above.
- **3rd Dan trace observability**: the action-die manipulation is a significant tempo effect (e.g., target's actions [1,3,5] → [4,6,8] is a major shift). Need explicit "Otaku 3rd Dan: shifted target's action dice +N (6 − Fire min 1)" attribution.
- **4th Dan parry-still-gets-die observability**: when lunge is parried but Otaku still gets +1 damage die, the trace should explain why.
- **5th Dan dice-trade observability**: when 10 rolled dice → 1 SW, the trace should show this trade explicitly.

## Goals

1. **Fix Q2 (3rd Dan "next X dice")** — primary BLOCKING rules-fidelity bug.
2. **Fix Q3 + Q4 (5th Dan "may" choice + dice math)** — BLOCKING rules-fidelity bugs.
3. **Resolve Q1 (Special Ability strategy)** — verify whether the interrupt-lunge capability fires under defaults; install a strategy if not.
4. **Principle VII trace observability** for each Otaku-specific effect.
5. **Principle IX 2(a)+(b)+(c)** — mirror non-degeneracy + win-feasibility ≥ 35% vs Akodo at 450 XP.
6. **Constitution gates** — ruff, mypy, 100% coverage (mechanically enforced), Streamlit smoke.

## User Stories

### US1 — Rules-fidelity fixes (Priority: P1) 🎯 MVP
Q2 (3rd Dan X dice) + Q3 (5th Dan may-choice) + Q4 (5th Dan dice math) all fixed and regression-guarded.

### US2 — Identity-driven defaults (Priority: P1)
Special Ability interrupt-lunge actually produces behavior under defaults. The school's lunge-centric identity drives the default attack strategy.

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)
5 mirror seeds terminate; Otaku ≥ 35% vs 450-XP Akodo.

### US4 — Trace observability (Priority: P2)
3rd Dan tempo penalty, 4th Dan parry-still-+1, 5th Dan dice-trade all surface in trace with attribution.

### US5 — Coverage (Priority: P1)
100% coverage on `simulation/schools/otaku_school.py` (now mechanically enforced).

## Functional Requirements

### Special Ability + interrupt strategy
- **FR-001**: `apply_special_ability` MUST wire `set_interrupt_cost("lunge", 1)` + `add_interrupt_skill("lunge")` (existing — verify).
- **FR-002**: The school MUST install an attack strategy that fires the interrupt-lunge when an attack against the Otaku has resolved AND the Otaku has future action dice.

### 1st & 2nd Dan
- **FR-003**: `extra_rolled()` returns `["iaijutsu", "lunge", "wound check"]`.
- **FR-004**: `free_raise_skills()` returns `["wound check"]`.

### 3rd Dan (BLOCKING fix)
- **FR-005**: After Otaku rolls damage against an opponent, the listener modifies the target's **next X action dice** where X = Otaku's attack skill (NOT all action dice).
- **FR-006**: The increase is `max(1, 6 - target.ring("fire"))` per die.
- **FR-007**: Each modified die is capped at phase 10.
- **FR-008**: The trace MUST surface "Otaku 3rd Dan: shifted N action dice by +M (6 − Fire min 1)" attribution.

### 4th Dan
- **FR-009**: `apply_school_ring_raise_and_discount` for Fire.
- **FR-010**: `OtakuLungeAction.calculate_extra_damage_dice` returns +1 even when parried.
- **FR-011**: When parried but +1-die fires, the trace MUST surface "Otaku 4th Dan: +1 extra damage die (parried lunge carve-out)" attribution.

### 5th Dan (BLOCKING fixes)
- **FR-012**: `OtakuFifthDanTakeAttackActionEvent` reduces the **total rolled damage dice** by 10, with floor of 2 (NOT `extra_rolled - 10`).
- **FR-013**: The dice-trade is a strategic CHOICE: only fires when it improves expected outcome (e.g., when expected SW from rolling < 1).
- **FR-014**: Fires at most once per damage roll.
- **FR-015**: The trace MUST surface "Otaku 5th Dan: traded 10 rolled damage dice for 1 SW (Nk... → (N−10)k...)" attribution.

### Identity-driven defaults
- **FR-016**: `OTAKU_PRIORITIES` reviewed by `school-progression-designer` (deferred per Bayushi/Kakita pattern if it breaks tests).
- **FR-017**: Strategy bindings reviewed by `school-strategy-designer`.

## Non-Functional Requirements

- **NFR-001**: 100% coverage (mechanically enforced).
- **NFR-002**: ≤ 5 existing-test updates outside new tests.
- **NFR-003**: Both renderers surface all Otaku effects with explicit source attribution.

## Success Criteria

- **SC-001**: 450-XP Otaku wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds via actual defeat.
- **SC-003**: 100% coverage on `otaku_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.
- **SC-005**: Final review-agent dispatches return zero blockers.

## Out of Scope

- Wave-Man 450-XP win-feasibility (structural deferral).
- Mount mechanics (per user clarification: not part of Otaku rules).

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). Summary:

- **Q1**: Special Ability interrupt-lunge — strategy install needed?
- **Q2**: 3rd Dan "next X action dice" — BLOCKING fix needed.
- **Q3**: 5th Dan "may" choice — needs strategic logic.
- **Q4**: 5th Dan dice math — BLOCKING fix needed.
- **Q5**: `OTAKU_PRIORITIES` revision (likely deferred).
- **Q6**: Trace observability gaps to address.
