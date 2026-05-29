# Spec: Ide Diplomat School

**Branch**: `031-ide-diplomat-school`
**Created**: 2026-05-29
**Status**: Draft (autonomous audit run)
**Driver**: Next entry in `BACKLOG.md`. Previously partial work
(spec 003 added `school_choices` configurability); full audit
never done.

## Rules text (verbatim, from rules/04-schools.md)

> **Ide Diplomat School**
>
> **School Ring:** Any non-Void
>
> **School Knacks:** double attack, feint, worldliness
>
> **Special Ability:** "After a feint which met its TN, lower the
> TN of the target by 10 the next time they are attacked" (even
> if parried).
>
> **First Dan:** Roll one extra die on precepts and any two rolls
> of your choice.
>
> **Second Dan:** You get a free raise on any type of roll of
> your choice.
>
> **Third Dan:** After seeing skill roll results, you may spend
> void points to subtract Xk1 from rolls (where X equals tact
> skill). You know results of all TN and contested rolls except
> sincerity and interrogation.
>
> **Fourth Dan:** Raise current and maximum in any non-Void Ring
> by 1. Raising that Ring now costs 5 fewer XP. You regain an
> extra void point every night.
>
> **Fifth Dan:** Gain a temporary void point whenever you spend
> a void point that was not gained from this technique.

## Skeleton audit (pre-audit reading)

`simulation/schools/ide_school.py` (202 lines), 30+ existing tests.
The 003-school-choices feature added Pattern B (`school_ring`),
Pattern A (`first_dan_extra_rolled`, `second_dan_free_raise`).

| Rules clause | Implementation site | Status |
|---|---|---|
| School Ring "Any non-Void" | `school_ring()` with `school_choices` Pattern B, default water | ✅ Correct |
| Special Ability — feint hits TN → −10 to target's TN on next attack | `IdeFeintSucceededListener` + `IdeFeintFailedListener` (parried branch) install `AnyAttackModifier(... -10)` with `ExpireAfterNextAttackByCharacterListener(character)` | **Q1 INTERPRETIVE**: rules say "the next time they are attacked" — the natural reading is "next attack by anyone". Skeleton restricts to next attack BY THE IDE via `ExpireAfter...ByCharacterListener(character)`. Defensible but narrower. |
| 1st Dan — +1 die on precepts + 2 chosen rolls | `extra_rolled()` with `school_choices` Pattern A | ✅ Correct |
| 2nd Dan — free raise on any chosen roll | `free_raise_skills()` with `school_choices` Pattern A | ✅ Correct |
| 3rd Dan — "spend void points to subtract Xk1" + info-omniscience | `IdeTactSubtractListener` on `attack_rolled`: spends 1 VP, rolls tact-k1, subtracts from attacker's roll | **Q2 INTERPRETIVE**: rules say "from rolls" (plural) and don't fix to 1 VP per use. Skeleton restricts to: (a) attack rolls only, (b) 1 VP per fire. Both defensible scope limits. Info-omniscience clause already-implicit (engine has perfect visibility). |
| 4th Dan — Ring +1 + discount + nightly VP | `apply_school_ring_raise_and_discount` (nightly VP is non-combat) | ✅ Correct |
| 5th Dan — "Gain TVP when spending VP not gained from this technique" | `IdeSpendVPListener` replaces canonical `SpendVoidPointsListener`; spends VP, grants TVP unless `event.skill == "tact"` | **Q3 MEDIUM**: rules exclude TVPs *gained from this technique* (infinite-loop guard). Skeleton's `event.skill != "tact"` check excludes 3rd Dan VP-spends (a different concern). Net effect: spending any non-tact VP — including a 5th-Dan-gained TVP — re-grants another TVP. Defensible simplification; documents trade-off. |

## Goals

1. **Document Q1, Q2, Q3 as defensible deferrals** (rules-auditor
   confirmation required).
2. **Add identity-engine playability test** — feint→SA bonus
   fires at least once vs Akodo.
3. **Mirror non-degeneracy** at 300 XP.
4. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke.

## User Stories

### US1 — Q1/Q2/Q3 rules-auditor verification (Priority: P1)
### US2 — Mirror + identity playability (Priority: P1)
### US3 — Coverage (Priority: P1)

## Functional Requirements

### Special Ability
- **FR-001**: Feint that hits TN installs −10 TN modifier on target;
  modifier expires after the Ide's next attack OR end of round.

### 1st-5th Dan
- **FR-002**: Existing implementations preserved (with Q3 trade-off documented).

### Identity-driven defaults
- **FR-003**: `IDE_PRIORITIES` reviewed by progression-designer.
- **FR-004**: Strategy bindings reviewed by strategy-designer.

## Success Criteria

- **SC-001**: 450-XP Ide wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches at 300 XP either terminate
  within 18 rounds or are honestly skipped per Hida precedent.
- **SC-003**: 100% coverage on `ide_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution gates pass.

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md).
