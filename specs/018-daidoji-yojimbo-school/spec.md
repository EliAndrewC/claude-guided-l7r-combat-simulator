# Spec: Daidoji Yojimbo School

**Branch**: `018-daidoji-yojimbo-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md` ("Daidoji Yojimbo School"). BACKLOG notes "interrupt-cost mutation that the 5th Dan negation refactor flagged as not yet tracked".

## Rules text (verbatim, from rules/04-schools.md)

> **Daidoji Yojimbo School**
>
> **School Ring:** Water
>
> **School Knacks:** counterattack, double attack, iaijutsu
>
> **Special Ability:** You may counterattack as an interrupt action by
> spending only 1 action die, but if you do so then your opponent gets
> a free raise on their wound check if you hit.
>
> **First Dan:** Roll one extra die on attack, counterattack, and
> wound checks.
>
> **Second Dan:** You get a free raise on all counterattack rolls.
>
> **Third Dan:** When you counterattack, add X free raises to the
> wound check from the original attack, where X is your attack skill.
>
> **Fourth Dan:** Raise your current and maximum Water by 1. Raising
> your Water now costs 5 fewer XP. You may choose to take the damage
> from a hit dealt to an adjacent character before damage has been
> rolled.
>
> **Fifth Dan:** After you or a character for whom you've
> counterattacked makes a wound check, lower the TN to hit the
> attacker the next time they are attacked by the amount by which the
> wound check exceeded the damage roll. This can lower a TN to below 0.

## Skeleton audit (pre-audit reading)

`simulation/schools/daidoji_school.py` (237 lines), 34 existing tests — the most-developed bushi skeleton remaining in the queue.

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — 1-die counterattack interrupt + opponent +1 raise on WC if hit | `apply_special_ability` sets cost=1 + installs `CounterattackInterruptStrategy` + custom action factory + take-action-event factory; `DaidojiTakeCounterattackActionEvent.play` lowers WC TN by 5 when interrupt-counterattack hits | ✅ Mostly correct. **MINOR**: -5 TN ≡ +5 to WC roll algebraically, so the rules-text "free raise" semantics are equivalent. |
| Counterattack-for-others at no penalty | `DaidojiCounterattackAction.tn` returns `target().tn_to_hit()` (skips the standard `5 * attacker.skill("parry")` penalty) | ⚠️ Not in the rules text I fetched but the skeleton comment treats it as part of the Special Ability. **VERIFY** with rules-auditor. |
| 1st Dan — +1 die on attack/counterattack/WC | `extra_rolled()` returns the three | ✅ Correct |
| 2nd Dan — free raise on counterattack | `free_raise_skills()` returns `["counterattack"]` | ✅ Correct |
| 3rd Dan — counterattack grants X free raises (X = attack skill) to ORIGINAL ATTACK target's WC | Skeleton sets `_daidoji_third_dan = True` flag (ad-hoc attribute); `DaidojiTakeCounterattackActionEvent.play` reads the flag and grants `WoundCheckFloatingBonus(5 * attack_skill)` to `original_target` (the attack's target, NOT the attacker) | **Q1 BLOCKING**: ad-hoc attribute is NOT tracked in `_school_owned_*` slots → school-negation (Ishi 5th Dan) does not revert it. **MINOR**: `5 * attack_skill` matches "X free raises" semantics (each raise = +5). **VERIFY**: rules say "original attack" target — confirm this is the target of the attack the Daidoji is counterattacking. |
| 4th Dan — Water +1 + discount + may take damage from adjacent ally hit | `apply_school_ring_raise_and_discount` + `DaidojiFourthDanListener` on `lw_damage` slot, redirects damage from allies to Daidoji | **Q2 BLOCKING**: rules say "**before damage has been rolled**" — listener fires on `LightWoundsDamageEvent` which is AFTER damage was rolled. Wrong timing. **Q3**: rules say "**may choose**" — listener unconditionally redirects, no strategic logic. |
| 5th Dan — successful WC by Daidoji or counterattack-protected ally → lower attacker's TN to hit by `WC_roll - damage` on NEXT attack against attacker | `DaidojiFifthDanWoundCheckListener` emits `Modifier(daidoji, attacker, ATTACK_SKILLS, excess)` with `ExpireAfterNextAttackByCharacterListener(daidoji)` | **Q4 BLOCKING**: expiry uses `ExpireAfterNextAttackByCharacterListener(daidoji)` which expires after DAIDOJI attacks. Rules say expire after the next attack **against the attacker** (by anyone). Wrong scope. **Q5 BLOCKING**: rules say "for whom you've counterattacked" — needs to track which allies the Daidoji has counterattacked for. Current implementation gates on adjacency, not counterattack history. |

### BACKLOG-flagged tracking concerns

- `set_interrupt_cost("counterattack", 1)` — mutates `_interrupt_costs`; not tracked in `_school_owned_*` slots.
- `_daidoji_third_dan = True` — ad-hoc attribute on character; not tracked.

## Goals

1. **Fix Q1 (3rd Dan ad-hoc attribute tracking)** — refactor to use proper slot or listener-based approach.
2. **Fix Q2 (4th Dan timing)** — intercept BEFORE damage is rolled, not after.
3. **Fix Q3 (4th Dan "may choose")** — add strategic logic for ally-damage redirect.
4. **Fix Q4 (5th Dan expiry scope)** — expire after attack against the attacker (by anyone), not after Daidoji attacks.
5. **Fix Q5 (5th Dan "for whom you've counterattacked")** — track counterattack history; only apply 5th Dan bonus to those allies' WC.
6. **Principle VII trace observability** for 3rd Dan WC raises, 4th Dan damage redirect, 5th Dan TN modifier.
7. **Principle IX 2(a)+(b)** — mirror non-degeneracy + win-feasibility vs Akodo at 450 XP.
8. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — Rules-fidelity BLOCKING fixes (Priority: P1) 🎯 MVP
Q2 (4th Dan timing), Q4 + Q5 (5th Dan scope), Q1 (3rd Dan tracking).

### US2 — Identity-driven defaults (Priority: P1)
Defaults match Yojimbo (defender) identity.

### US3 — Mirror non-degeneracy + win-feasibility (Priority: P1)

### US4 — Trace observability (Priority: P2)

### US5 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability + interrupt strategy
- **FR-001**: 1-die counterattack interrupt with WC TN reduction (or equivalent free-raise-to-opponent) when interrupt-counterattack hits.
- **FR-002**: Counterattack-for-others has no TN penalty (skip the `5 * attacker.skill("parry")` term).

### 1st & 2nd Dan
- **FR-003**: `extra_rolled()` returns `["attack", "counterattack", "wound check"]`.
- **FR-004**: `free_raise_skills()` returns `["counterattack"]`.

### 3rd Dan
- **FR-005**: After counterattack, grant `5 * attack_skill` to the original attack's TARGET via `WoundCheckFloatingBonus`.
- **FR-006**: The 3rd Dan flag MUST be tracked in `_school_owned_*` for school-negation (Ishi 5th Dan).

### 4th Dan
- **FR-007**: Water ring raise + discount via `apply_school_ring_raise_and_discount`.
- **FR-008**: Damage redirect intercepts BEFORE damage is rolled (rules text: "before damage has been rolled") — gate on `AttackSucceededEvent` (after hit but before damage), not on `LightWoundsDamageEvent`.
- **FR-009**: Strategic gate: only redirect when ally is at risk (e.g., low SW remaining); not unconditionally.

### 5th Dan
- **FR-010**: After WC succeeds for Daidoji or for an ally Daidoji counterattacked for, emit a `Modifier(_, attacker, ATTACK_SKILLS, +excess)` that lowers the attacker's TN to hit on the NEXT attack against them (by anyone).
- **FR-011**: Expiry scoped to "next attack against the attacker", NOT "next attack by Daidoji".

### Identity-driven defaults
- **FR-012**: `DAIDOJI_PRIORITIES` reviewed by `school-progression-designer` (deferred per pattern if it breaks tests).
- **FR-013**: Strategy bindings reviewed by `school-strategy-designer`.

## Success Criteria

- **SC-001**: 450-XP Daidoji wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds via actual defeat.
- **SC-003**: 100% coverage on `daidoji_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
