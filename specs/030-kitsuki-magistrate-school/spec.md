# Spec: Kitsuki Magistrate School

**Branch**: `030-kitsuki-magistrate-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md`.

## Rules text (verbatim, from rules/04-schools.md)

> **Kitsuki Magistrate School**
>
> **School Ring:** Water
>
> **School Knacks:** discern Honor, iaijutsu, presence
>
> **Special Ability:** You use Water for interrogation rolls,
> and you add twice your Water to all attack rolls.
>
> **First Dan:** Roll one extra die on investigation,
> interrogation, and wound checks.
>
> **Second Dan:** You get a free raise on interrogation rolls.
>
> **Third Dan:** Each adventure you get 2X free raises, where X
> is equal to your investigation skill, which may be applied to
> the following rolls: interrogation, intimidation, law,
> underworld, attack, and wound checks. You may not spend more
> than X of these free raises on a single roll.
>
> **Fourth Dan:** Raise your current and maximum Water by 1.
> Raising your Water now costs 5 fewer XP. You automatically
> know the Void, parry, and phase of the next action of each
> character during combat, and you know the result of contested
> rolls made against you out of combat.
>
> **Fifth Dan:** Your presence is so overwhelming that the Air,
> Fire and Water rings of chosen characters are reduced by one.
> You may do this to any one character, or you may do it to
> multiple characters so long as the sum of their experience
> does not exceed your experience. This does not work during the
> iaijutsu phase of a duel, and it does not stack with other
> Kitsuki Magistrates targeting the same character.

## Skeleton audit (pre-audit reading)

`simulation/schools/kitsuki_school.py` (115 lines), 23 existing tests.

| Rules clause | Implementation site | Status |
|---|---|---|
| School Ring "Water" | `school_ring()` returns "water" | ✅ |
| Special Ability — 2×Water on attack | `KitsukiRollParameterProvider` adds `2*water` to ATTACK_SKILLS modifier | ✅ Correct (uses ATTACK_SKILLS broader interpretation, defensible) |
| Special Ability — "Water for interrogation rolls" | NOT IMPLEMENTED | **Q1 PASS-DEFER**: interrogation is a non-combat social skill; combat-irrelevant. Document deferral. |
| 1st Dan — +1 die on investigation/interrogation/WC | `extra_rolled()` ✓ | ✅ |
| 2nd Dan — free raise on interrogation | `free_raise_skills()` returns `["interrogation"]` | ✅ |
| 3rd Dan — AP raises on 6 listed rolls | `ap_skills=["attack", "wound check"]` | ✅ Mostly correct; non-combat skills (interrogation, intimidation, law, underworld) omitted per combat-scope precedent. |
| 4th Dan — Water +1, discount, info-omniscience | `apply_school_ring_raise_and_discount` + TODO comment | ✅ Mostly correct. **Q2 PASS-DEFER**: "automatically know Void/parry/phase of next action" — the combat AI already has effective access to all opponent state; the "knowledge" granted by the rules text is already implicit. Document deferral. |
| 5th Dan — reduce A/F/W of CHOSEN characters | `KitsukiFifthDanNewRoundListener` reduces ALL opponents unconditionally on round 1 | **Q3 BLOCKING**: rules say "chosen characters" with XP budget constraint; skeleton applies to every opponent regardless of XP. **Q4 MEDIUM**: rules say "does not stack with other Kitsuki Magistrates targeting the same character" — skeleton has no stacking guard. **Q5 PASS-DEFER**: rules say "not during iaijutsu phase of a duel" — duel iaijutsu phase is not modeled separately in the engine; combat-only context makes this vacuous. |

## Goals

1. **Fix Q3 (5th Dan targeting)** — restrict ring-reduction to a
   single target chosen per the XP budget rule. Simplest correct
   interpretation: target the single opponent with the highest
   XP (most threatening, and the rules permit one target without
   needing budget tracking).
2. **Fix Q4 (Kitsuki stacking)** — install a per-target guard
   that prevents two Kitsuki Magistrates from reducing the same
   opponent's rings.
3. **Document Q1, Q2, Q5** as deferrals.
4. **Principle IX 2(a)+(b)** — mirror non-degeneracy +
   win-feasibility vs Akodo at 450 XP.
5. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — 5th Dan target restriction (Priority: P1) 🎯 MVP
Q3 — reduce a single chosen opponent's rings; pick the one with
highest XP (deterministic, identity-aligned).

### US2 — 5th Dan stacking guard (Priority: P1)
Q4 — prevent multiple Kitsuki Magistrates from stacking.

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US4 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: Add 2×Water to attack-skill rolls.

### 1st & 2nd Dan
- **FR-002**: `extra_rolled()` = `["interrogation", "investigation", "wound check"]`.
- **FR-003**: `free_raise_skills()` = `["interrogation"]`.

### 3rd Dan
- **FR-004**: AP system; investigation base; combat skills attack+WC.

### 4th Dan
- **FR-005**: Water +1 + discount.

### 5th Dan (Q3/Q4 fixes)
- **FR-006**: Reduce A/F/W by 1 on a single chosen target
  (highest-XP opponent), once per combat.
- **FR-007**: Stacking guard — track per-target whether a
  Kitsuki Magistrate has already reduced rings; skip if so.

### Identity-driven defaults
- **FR-008**: `KITSUKI_PRIORITIES` reviewed by progression-designer.
- **FR-009**: Strategy bindings reviewed by strategy-designer.

## Success Criteria

- **SC-001**: 450-XP Kitsuki wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches at 300 XP either
  terminate within 18 rounds or are honestly skipped per Hida precedent.
- **SC-003**: 100% coverage on `kitsuki_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
