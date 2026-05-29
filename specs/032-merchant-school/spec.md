# Spec: Merchant School

**Branch**: `032-merchant-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Final entry in `BACKLOG.md`.

## Rules text (verbatim, from rules/04-schools.md)

> **Merchant School**
>
> **School Ring:** Water
>
> **School Knacks:** discern Honor, oppose knowledge, worldliness
>
> **Special Ability:** "You may spend void points after you see the
> results of your initial roll."
>
> **First Dan:** "Roll one extra die on interrogation, sincerity,
> and wound checks."
>
> **Second Dan:** "You get a free raise on interrogation rolls."
>
> **Third Dan:** "Each adventure you get 2X free raises, where X
> is equal to your sincerity skill, which may be applied to the
> following rolls: commerce, heraldry, interrogation, sincerity,
> attack, and wound checks. You may not spend more than X of these
> free raises on a single roll."
>
> **Fourth Dan:** "Raise your current and maximum Water by 1.
> Raising your Water now costs 5 fewer XP. Your Rank is considered
> 5.0 higher for the purpose of calculating your stipend."
>
> **Fifth Dan:** "After making any non-initiative roll, you may
> reroll some of the dice so long as the dice being rerolled add
> up to at least 5*(X-1) where X is the number of dice being
> rerolled. You may only do this once per roll. As per your
> Special Ability, you may spend Void Points before and/or after
> you make this reroll."

## Skeleton audit (pre-audit reading)

`simulation/schools/merchant_school.py` (394 lines), 35+ tests.
This is the LARGEST skeleton in the audit queue.

| Rules clause | Implementation site | Status |
|---|---|---|
| School Ring "Water" | `school_ring()` returns "water" | ✅ |
| Special Ability — VP after seeing roll | `MerchantAttackOptimizerFactory` (max_vp=0) + `MerchantAttackRolledStrategy` (post-roll spend) + `MerchantWoundCheckStrategy`/`MerchantWoundCheckRolledStrategy` | ✅ Largely correct. **Q1 INTERPRETIVE**: VP gives +5 per VP (flat) since the dice are already rolled; rules don't redefine VP. Defensible simplification — VP cannot retroactively add dice to a roll already made. |
| 1st Dan — +1 die on interrogation/sincerity/WC | `extra_rolled()` returns the three skills | ✅ Correct |
| 2nd Dan — free raise on interrogation | `free_raise_skills()` returns `["interrogation"]` | ✅ Correct |
| 3rd Dan — AP raises on 6 listed rolls | `ap_skills` returns all 6 (commerce, heraldry, interrogation, sincerity, attack, wound check); `ap_base_skill="sincerity"` | ✅ Correct — includes non-combat skills (commerce, heraldry, interrogation, sincerity) per rules |
| 4th Dan — Water +1, discount, stipend | `apply_school_ring_raise_and_discount` (stipend non-combat) | ✅ Correct |
| 5th Dan — reroll dice meeting sum-≥-5(X-1) constraint, once per roll, VP before/after | `MerchantRollProvider` wraps inner provider; `_find_dice_to_reroll` picks beneficial low dice; "once per roll" satisfied because each get_*_roll call is one roll | ✅ Largely correct. **Q2 INTERPRETIVE**: rules say "you may reroll some of the dice" — voluntary. Skeleton automatically rerolls when beneficial. Defensible per "optimal play simulator" interpretation. |

## Goals

1. **Document Q1, Q2 as defensible deferrals** (rules-auditor verification).
2. **Add identity-engine playability test** — Merchant rerolls dice + post-roll VP spending fires at least once.
3. **Mirror non-degeneracy** at 300 XP.
4. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — rules-auditor verification (Priority: P1)
### US2 — Mirror + identity playability (Priority: P1)
### US3 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: VP can be spent post-roll on attack and wound check; gives +5 per VP.

### 1st-5th Dan
- **FR-002**: Existing implementations preserved (with Q1/Q2 trade-offs documented).

### Identity-driven defaults
- **FR-003**: `MERCHANT_PRIORITIES` reviewed by progression-designer.
- **FR-004**: Strategy bindings reviewed by strategy-designer.

## Success Criteria

- **SC-001**: 450-XP Merchant wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches at 300 XP either terminate
  within 18 rounds or are honestly skipped per Hida precedent.
- **SC-003**: 100% coverage on `merchant_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
