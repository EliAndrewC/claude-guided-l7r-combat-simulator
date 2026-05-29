# Spec: Shiba Bushi School

**Branch**: `016-shiba-bushi-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Shiba Bushi School").

## Rules text (verbatim, from rules/04-schools.md)

> **Shiba Bushi School**
>
> **School Ring:** Air
>
> **School Knacks:** counterattack, double attack, iaijutsu
>
> **Special Ability:** You may parry as an interrupt action by
> spending your lowest 1 action die, and you may parry attacks
> directed at other characters with no penalty.
>
> **First Dan:** Roll an extra die on double attack, parry, and wound
> checks.
>
> **Second Dan:** You get a free raise on parry rolls.
>
> **Third Dan:** Your successful or unsuccessful parry rolls deal
> (2X)k1 damage, where X is equal to your attack skill. You don't
> roll extra damage dice from your Fire or from exceeding the TN.
>
> **Fourth Dan:** Raise your current and maximum Air by 1. Raising
> your Air now costs 5 fewer XP. You roll an extra 3k1 on wound
> checks.
>
> **Fifth Dan:** After you successfully parry, the TN to hit the
> parried opponent on the next attack directed at them this combat
> is lowered by the amount by which your parry roll exceeded its TN.
> This can lower the TN to a negative number.

## Skeleton audit (pre-audit reading)

`simulation/schools/shiba_school.py` (139 lines), 6 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — parry as interrupt for 1 (lowest) die | `apply_special_ability`: `set_interrupt_cost("parry", 1)` + custom `ShibaParryAction` | **Q1 IDENTITY GAP**: `add_interrupt_skill("parry")` NOT wired → `has_interrupt_action("parry", context)` returns False → interrupt-parry can NEVER fire. Same shape as Kakita/Otaku Q1 bug. |
| Special Ability — "spending your **lowest** 1 action die" | n/a (no strategy) | **Q2**: standard interrupt logic spends HIGHEST. Even if Q1 is fixed, must enforce lowest-die semantics. |
| Special Ability — parry-other no penalty | `ShibaParryAction.roll_parry` skips the -10 | ✅ Correct (verified by `test_no_parry_other_penalty`) |
| 1st Dan — +1 die on double attack / parry / wound check | `extra_rolled()` returns the three | ✅ Correct |
| 2nd Dan — free raise on parry | `free_raise_skills()` returns `["parry"]` | ✅ Correct |
| 3rd Dan — parry deals (2X)k1, X = attack skill, no Fire/TN extras | `ShibaTakeParryEvent._roll_damage`: `rolled = 2 * skill("attack")`, `kept = 1`, direct `roll_provider.get_damage_roll(rolled, 1)` | ⚠️ Mostly correct but **Q3**: bypasses `normalize_roll_params` (rolled > 10 not converted to kept). Concrete defect: a 5th-Dan Shiba with attack=6 → rolled=12 should roll 10k3 (normalize), but skeleton rolls 12k1 raw. |
| 3rd Dan — damage on FAILED parry too | `ShibaTakeParryEvent.play` yields damage after both `succeeded` and `failed` branches | ✅ Correct |
| 4th Dan — Air +1 with discount + extra 3k1 on wound check | `apply_school_ring_raise_and_discount` + `_set_school_extra_rolled("wound check", 3)` + `_set_school_extra_kept("wound check", 1)` | ✅ Correct |
| 5th Dan — TN penalty equal to margin on NEXT attack against parried opponent | `ShibaParrySucceededListener`: penalty on `event.action.target()` (the original attacker) as `tn to hit` modifier with `ExpireAfterNextAttackListener` | ✅ Correct |

## Goals

1. **Fix Q1 (interrupt-parry identity bug)** — install `ShibaInterruptParryStrategy` so the Special Ability fires under defaults.
2. **Q2 lowest-die semantics** — verify or fix the action-die selection for interrupt-parry.
3. **Fix Q3 (3rd Dan rolled-dice normalization)** — route parry damage through `normalize_roll_params` for the rolled > 10 case.
4. **Principle VII trace observability** for the 3rd Dan parry damage + 5th Dan TN modifier.
5. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
6. **Constitution gates** — ruff, mypy, 100% coverage (mechanically enforced), Streamlit smoke.

## User Stories

### US1 — Identity-driven defaults (Priority: P1) 🎯 MVP
Special Ability interrupt-parry actually produces behavior under defaults. The school's parry-centric identity drives the default attack strategy.

### US2 — Rules-fidelity fixes (Priority: P1)
Q3 (3rd Dan rolled-dice normalization) fixed.

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)
5 mirror seeds terminate; Shiba ≥ 35% vs 450-XP Akodo (Constitution Principle IX).

### US4 — Trace observability (Priority: P2)
3rd Dan parry damage and 5th Dan TN penalty modifier surface in trace with attribution.

### US5 — Coverage (Priority: P1)
100% coverage on `simulation/schools/shiba_school.py` (mechanically enforced).

## Functional Requirements

### Special Ability + interrupt strategy
- **FR-001**: `apply_special_ability` MUST wire `set_interrupt_cost("parry", 1)` and `add_interrupt_skill("parry")` (existing — verify add).
- **FR-002**: The school MUST install an interrupt strategy that fires the parry-interrupt when an attack is declared against the Shiba (or a defended ally).
- **FR-003**: The interrupt action MUST spend the character's LOWEST eligible action die (rules text — "spending your lowest 1 action die").

### 1st & 2nd Dan
- **FR-004**: `extra_rolled()` returns `["double attack", "parry", "wound check"]`.
- **FR-005**: `free_raise_skills()` returns `["parry"]`.

### 3rd Dan (rules-fidelity)
- **FR-006**: After a successful or unsuccessful parry, Shiba deals `(2 × attack skill)k1` damage to the attacker (target).
- **FR-007**: The rolled-dice count MUST go through `normalize_roll_params` so rolled > 10 converts to kept.
- **FR-008**: NO Fire ring or TN-overshoot extras are added to the parry damage roll.
- **FR-009**: The trace MUST surface "Shiba 3rd Dan: parry deals (2 × X)k1 = N damage" attribution.

### 4th Dan
- **FR-010**: `apply_school_ring_raise_and_discount` for Air.
- **FR-011**: Wound check rolls get +3 rolled / +1 kept.

### 5th Dan
- **FR-012**: After a successful parry, the parried opponent's `tn to hit` is reduced by `(parry_roll - parry_tn)` for the NEXT attack against them.
- **FR-013**: The modifier expires after that next attack.
- **FR-014**: The trace MUST surface "Shiba 5th Dan: TN-to-hit -N (parry margin)" attribution.

### Identity-driven defaults
- **FR-015**: `SHIBA_PRIORITIES` reviewed by `school-progression-designer` (deferred per Bayushi/Kakita/Otaku pattern if it breaks tests).
- **FR-016**: Strategy bindings reviewed by `school-strategy-designer`.

## Non-Functional Requirements

- **NFR-001**: 100% coverage (mechanically enforced).
- **NFR-002**: ≤ 5 existing-test updates outside new tests.
- **NFR-003**: Both renderers surface all Shiba effects with explicit source attribution.

## Success Criteria

- **SC-001**: 450-XP Shiba wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds via actual defeat.
- **SC-003**: 100% coverage on `shiba_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.
- **SC-005**: Final review-agent dispatches return zero blockers.

## Out of Scope

- Wave-Man 450-XP win-feasibility (structural deferral established with Hida).

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). Summary:

- **Q1**: Special Ability interrupt-parry — `add_interrupt_skill` missing.
- **Q2**: "Lowest 1 action die" semantics.
- **Q3**: 3rd Dan rolled-dice normalization.
- **Q4**: `SHIBA_PRIORITIES` revision (likely deferred).
- **Q5**: Trace observability gaps to address.
