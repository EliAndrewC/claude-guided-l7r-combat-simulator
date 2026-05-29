# Spec: Kakita Duelist School

**Branch**: `014-kakita-duelist-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Run the next entry in `BACKLOG.md` ("Kakita Duelist School") through the audit-driven speckit workflow. Per the user's framing: "It's already been implemented, but I think we can proceed with auditing it using the usual process."

## Rules text (verbatim, from rules/04-schools.md)

> **Kakita Duelist School**
>
> School Ring: Fire
>
> School Knacks: double attack, iaijutsu, lunge
>
> Special Ability: Your 10s on initiative rolls are considered to be in a special Phase 0. You may use interrupt actions to attack using iaijutsu, and any Phase 0 attacks use iaijutsu.
>
> First Dan: Roll one extra die on double attack, iaijutsu, and initiative rolls.
>
> Second Dan: You get a free raise on all iaijutsu rolls.
>
> Third Dan: Your attacks get a bonus of X for each phase before the defender's next action they occur, where X is equal to your attack skill. If a defender does not have an action remaining in this round, they are considered to act in phase 11. This applies to all types of attacks, and you know the next action of everyone within striking range.
>
> Fourth Dan: Raise your current and maximum Fire by 1. Raising your Fire now costs 5 fewer XP. You get a free raise to all damage rolls from attacks using iaijutsu.
>
> Fifth Dan: At the beginning of phase 0 in each combat round, make a contested iaijutsu roll against an opponent. If the opponent doesn't have iaijutsu, they may roll attack instead, and you get an extra free raise. Make a damage roll against this opponent; if you won the contested roll then roll 1 extra damage die for every 5 by which your roll exceeded your opponent's, and if you lost then roll 1 fewer damage die for every 5 by which their roll exceeded yours.

## Skeleton audit

`simulation/schools/kakita_school.py` (610 lines) is the **largest skeleton of any remaining bushi school** — significantly more complex than Bayushi's. 16 existing tests in `tests/test_kakita_school.py`; all pass at branch creation. The skeleton implements 24 classes/functions including:

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — 10s → Phase 0 on initiative | `KakitaRollProvider.get_initiative_roll` + `KakitaInitiativeDieProvider` (rolls 0-9, no explode) | **Subtle**: implementation uses 0-9 dice where 0 represents "was-a-10". Mechanically equivalent to the rules-text reading IF L7R initiative phases line up with `die_value`. See Q5. |
| Special Ability — iaijutsu as interrupt | `apply_special_ability` calls `character.add_interrupt_skill("iaijutsu")` | ✅ Looks correct |
| Special Ability — Phase 0 attacks use iaijutsu | `KakitaAttackStrategy.recommend` forces iaijutsu at `phase() == 0` | ✅ Looks correct |
| 1st Dan — +1 die on double attack / iaijutsu / initiative | `extra_rolled()` returns the three | ✅ Correct |
| 2nd Dan — free raise on iaijutsu | `free_raise_skills()` returns `["iaijutsu"]` | ✅ Correct (verify modifier_breakdown attribution) |
| 3rd Dan — tempo bonus X-per-phase-of-defender's-next-action | `KakitaAttackAction.skill_roll_params` (and DoubleAttack + Lunge variants) | ✅ Looks correct |
| 3rd Dan — defender-with-no-actions → phase 11 | `KakitaAttackAction` defaults `target_tempo = 11` | ✅ Correct |
| 3rd Dan — applies to ALL attack types | `KakitaActionFactory` routes `attack`, `iaijutsu`, `double attack`, `lunge` through Kakita-specific classes | ✅ Correct |
| 3rd Dan — "know next action of everyone within striking range" | Implicit in code's access to `target.actions()` | **Q4 question**: is this a knowledge-tracking concern or a no-op given the engine's full-information model? |
| 4th Dan — Fire +1 + 5-XP discount | `apply_school_ring_raise_and_discount` | ✅ Correct |
| 4th Dan — free raise on iaijutsu damage rolls | `KakitaRollParameterProvider.get_damage_roll_params` adds `+5` mod when `skill == "iaijutsu"` | ✅ Correct |
| 5th Dan — contested iaijutsu at phase 0 | `KakitaNewPhaseListener` + `ContestedIaijutsuAttackAction` + `TakeContestedIaijutsuAttackAction` | ✅ Substantial implementation; verify rules-fidelity end-to-end |
| 5th Dan — opponent w/o iaijutsu rolls attack + extra free raise | `KakitaNewPhaseListener.handle` checks `target.skill("iaijutsu") == 0` and switches to "attack" skill | **Q2**: is the extra free raise actually applied somewhere? (skeleton selects "attack" but does it ADD the bonus?) |
| 5th Dan — won: +1 damage die per 5 over | `ContestedIaijutsuAttackAction.calculate_extra_damage_dice` | ✅ Looks correct |
| 5th Dan — lost: -1 damage die per 5 under | Same method — `(skill_roll - opponent_skill_roll) // 5` is negative when lost | ✅ Correct via integer arithmetic |

Other observations:

- **Name discrepancy**: `name()` returns `"Kakita Bushi School"`, but the upstream rules-text title is `"Kakita Duelist School"`. `BACKLOG.md` explicitly flagged this: *"factory registration name is 'Kakita Bushi School' but upstream rules-text title is 'Kakita Duelist School' — verify which is authoritative before audit."* → **Q1**.
- **4 unused strategy variants**: `KakitaAttackStrategy05`, `KakitaInterruptAttackStrategy05`, `KakitaNoVPAttackStrategy`, `KakitaNoVPInterruptAttackStrategy` — defined but never installed. Likely intended for player-choice configuration (low-VP-spending builds, etc.). **Q3**: keep or remove?
- `KAKITA_PRIORITIES` exists with the same anti-identity parry-at-every-rank pattern Bayushi / Matsu's reviews flagged. **Q6**: should the progression-designer revise this?
- `KakitaInitiativeDieProvider` calls `random.randint(0, 9)` directly. Consistent with the established `DefaultDieProvider` precedent (also calls `random.randint`) — providers are the canonical boundary where randomness enters the engine. **No issue.**

## Goals

1. **Audit** all 5 Dan abilities + Special Ability against the verbatim rules text. Flag any discrepancies as BLOCKING / MINOR / PASSED.
2. **Resolve the name discrepancy** (Q1).
3. **Verify Principle VII trace observability** for each Kakita-specific effect — especially the 3rd Dan tempo bonus, the 4th Dan iaijutsu damage free raise, and the 5th Dan contested damage swing.
4. **Verify Principle IX 2(a)+(b)+(c)** — mirror non-degeneracy + win-feasibility ≥ 35% vs Akodo at 450 XP.
5. **Constitution gates** — ruff, mypy, 100% coverage (now mechanically enforced by `fail_under = 100`), Streamlit smoke.

## User Stories

### US1 — Audit + tighten the existing skeleton (Priority: P1) 🎯 MVP
Rules-auditor + trace-auditor + trace-reader return zero blocking findings on the existing implementation. Any discovered discrepancies are addressed.

### US2 — Mirror non-degeneracy (Priority: P1)
Two 5th-Dan Kakitas mirror-fight; combat terminates within 18 rounds via actual defeat. Identity engine (iaijutsu attacks + tempo bonus) fires.

### US3 — Win-feasibility (Priority: P1)
450-XP Kakita wins ≥ 35% vs 450-XP Akodo. (Wave-Man test deferred per the structural finding from Matsu's branch.)

### US4 — Regression guards (Priority: P1)
- `KAKITA_PRIORITIES` references all three knacks.
- 3rd Dan tempo bonus formula `attack_skill * tempo_diff` does not regress.

### US5 — trace-reader + trace-auditor approve (Priority: P2)
Final pre-merge dispatch returns zero blockers.

## Functional Requirements (audit-derived)

### Special Ability
- **FR-001**: Kakita's initiative roll produces dice values in `[0, 9]` (no native 10 face).
- **FR-002**: A 0 in the roll's results corresponds to a "Phase 0" action die (acts before standard phase 1-10).
- **FR-003**: Kakita MAY use interrupt actions for iaijutsu (via `character.add_interrupt_skill("iaijutsu")`).
- **FR-004**: Phase 0 attacks MUST use iaijutsu (enforced by `KakitaAttackStrategy.recommend` at `phase() == 0`).

### 1st & 2nd Dan
- **FR-005**: `extra_rolled()` returns `["double attack", "iaijutsu", "initiative"]`.
- **FR-006**: `free_raise_skills()` returns `["iaijutsu"]`.
- **FR-007**: The 2nd Dan +5 free raise surfaces in the iaijutsu modifier breakdown with explicit "Kakita 2nd Dan" attribution.

### 3rd Dan (tempo bonus)
- **FR-008**: `KakitaAttackAction.skill_roll_params` adds `attack_skill * max(0, target_tempo - subject_tempo)` to the modifier.
- **FR-009**: `target_tempo` defaults to 11 when the target has no remaining actions.
- **FR-010**: `target_tempo = min(target.actions())` when the target has remaining actions.
- **FR-011**: All three attack-class skills (attack, double attack, lunge) AND iaijutsu apply the tempo bonus (via the three Kakita action subclasses).
- **FR-012**: The trace MUST surface the tempo bonus with explicit "Kakita 3rd Dan: tempo bonus +X" attribution per Principle VII.

### 4th Dan
- **FR-013**: `apply_rank_four_ability` raises Fire + applies 5-XP Fire discount.
- **FR-014**: `KakitaRollParameterProvider.get_damage_roll_params` adds `+5` to the modifier when `skill == "iaijutsu"`.
- **FR-015**: The +5 free raise MUST surface in the iaijutsu damage breakdown with explicit "Kakita 4th Dan" attribution per Principle VII.

### 5th Dan (contested iaijutsu)
- **FR-016**: At every `NewPhaseEvent` where `phase == 0`, `KakitaNewPhaseListener` fires a contested iaijutsu against the easiest target.
- **FR-017**: If the target has 0 iaijutsu skill, the listener switches their roll to "attack" AND grants the Kakita an extra free raise.
- **FR-018**: `ContestedIaijutsuAttackAction.calculate_extra_damage_dice` returns `(skill_roll - opponent_skill_roll) // 5` — positive when won, negative when lost.
- **FR-019**: The contested-iaijutsu damage event MUST surface "Kakita 5th Dan: contested iaijutsu" attribution in the trace per Principle VII.

### Identity-driven defaults (Principle VIII)
- **FR-020**: `KAKITA_PRIORITIES` reviewed by `school-progression-designer` (Q6).
- **FR-021**: Default strategy bindings reviewed against the rules-text identity (Q3 — keep or remove the 4 unused variants).
- **FR-022**: Mirror non-degeneracy verified per Principle IX 2(a)+(b)+(c).

## Non-Functional Requirements

- **NFR-001**: 100% coverage on `simulation/schools/kakita_school.py` (mechanically enforced by `fail_under = 100`).
- **NFR-002**: ≤ 5 existing-test updates outside new tests.
- **NFR-003**: Both `TextRenderer` and `BulletedRenderer` MUST render all Kakita effects with explicit source attribution.

## Success Criteria

- **SC-001**: 450-XP Kakita wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds via actual defeat.
- **SC-003**: 100% coverage on `simulation/schools/kakita_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution checklist gates pass.
- **SC-005**: Final review-agent dispatches return zero blockers.

## Out of Scope

- Wave-Man 450-XP baseline win-feasibility (structural deferral per Matsu's cross-school finding).
- Rewriting the iaijutsu-duel engine (already exists, see CLAUDE.md commit `5d67a78`).

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). Summary:

- **Q1**: Name — keep "Kakita Bushi School" (backwards-compat) OR change to "Kakita Duelist School" (rules-fidelity)?
- **Q2**: 5th Dan "extra free raise" when opponent rolls attack — is it implemented?
- **Q3**: 4 unused strategy variants — keep, document, or remove?
- **Q4**: 3rd Dan "know next action" — knowledge tracking or no-op given full-info engine?
- **Q5**: Initiative dice 0-9 vs rules-text "10s → phase 0" equivalence.
- **Q6**: `KAKITA_PRIORITIES` parry-at-every-rank — same anti-identity pattern as Bayushi/Matsu.
- **Q7**: Trace observability gaps to investigate.
