# Spec: Bayushi Bushi School

**Branch**: `013-bayushi-bushi-school`
**Created**: 2026-05-28
**Status**: Draft (autonomous run)
**Driver**: Run the next entry in `BACKLOG.md` ("Bayushi Bushi School") through the same speckit + agent-driven workflow that completed Matsu (commit `69cd640`). Per the user's framing: "the school is already implemented but it would be worth running through our steps to audit the existing implementation."

## Rules text (verbatim, from rules/04-schools.md)

> **Bayushi Bushi School**
>
> School Ring: Fire
>
> School Knacks: double attack, feint, iaijutsu
>
> Special Ability: When spending void points on all types of attack rolls, add 1k1 to the damage rolls of those attacks per void point spent.
>
> First Dan: Roll one extra die on iaijutsu, double attack, and wound checks.
>
> Second Dan: You get a free raise on double attack rolls.
>
> Third Dan: Your feints do Xk1 damage, where X is your attack skill. You don't roll extra damage dice from your Fire or from exceeding the TN, but your Special Ability may increase the damage.
>
> Fourth Dan: Raise your current and maximum Fire by 1. Raising your Fire now costs 5 fewer XP. After a successful or unsuccessful feint, you may apply a free raise to any future attack this combat.
>
> Fifth Dan: When you fail a wound check, calculate your serious wounds as if you had half your number of light wounds (rounded down).

## Skeleton audit

`simulation/schools/bayushi_school.py` (263 lines) is the **most polished skeleton** of any Bushi school remaining — significantly more developed than even Matsu's was. 9 existing tests in `tests/test_bayushi_school.py` all pass at branch creation.

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — VP on attack adds 1k1 to damage | `BayushiRollParameterProvider.get_damage_roll_params` adds `vp` to both `rolled` AND `kept` | ✅ Looks correct, verified by `TestBayushiFeintAction::test_roll_damage`. Also has a thorough `get_breakdown` method for Principle VII attribution. |
| 1st Dan — extra die on iaijutsu/double attack/wound check | `extra_rolled()` returns the three skills | ✅ Correct |
| 2nd Dan — free raise on double attack | `free_raise_skills()` returns `["double attack"]` + `modifier_breakdown.py` surfaces "Bayushi 2nd Dan free raise" attribution | ✅ Correct + trace-attributed |
| 3rd Dan — feint does Xk1 damage (X = attack), no Fire/margin bonus | `BayushiFeintAction.damage_roll_params`: rolled = attack_skill + vp, kept = 1 + vp. `damage_breakdown()` overrides the projection. `BayushiActionFactory` returns it for "feint" skill. | ✅ Looks correct AND has Principle VII per-source breakdown |
| 4th Dan — ring raise + discount + free raise after feint | `apply_school_ring_raise_and_discount` + `BayushiAttackFailedListener` + `BayushiAttackSucceededListener` gain `AnyAttackFloatingBonus(5, source="Bayushi 4th Dan")` with `GainFloatingBonusEvent` for trace | ✅ Looks correct, two listeners cover both success/failure paths |
| 5th Dan — half-LW WC | `BayushiWoundCheckProvider.wound_check(roll, lw)` halves LW + ensures minimum 1 SW on a failed check | ✅ Correct with rules-text fidelity (the "at least 1 SW on failed WC" carve-out is explicit) |

Other observations:
- **No `apply_special_ability` strategy bindings** — `apply_special_ability` only installs the `BayushiRollParameterProvider`. Default `UniversalAttackStrategy` / `ReluctantParryStrategy` / `WoundCheckStrategy` (threshold 0.6) apply.
- **Trace observability appears solid** at the per-source breakdown level — `BayushiRollParameterProvider.get_breakdown` is well-structured. Worth verifying with `trace-auditor` whether all Bayushi-specific effects (Special Ability VP on damage, 3rd Dan feint formula, 4th Dan post-feint floating bonus, 5th Dan half-LW WC) surface with explicit source attribution.
- `BAYUSHI_PRIORITIES` exists with standard structure. Review by `school-progression-designer` recommended — the parry-at-every-rank pattern Matsu's review surfaced as anti-identity may also apply here (Bayushi has no parry-keyed rules text).

## Goals

1. **Audit** all 5 Dan abilities + Special Ability against rules text. Flag any discrepancies as BLOCKING / MINOR / PASSED.
2. **Verify Principle VII trace observability** for each Bayushi-specific effect.
3. **Wire identity-driven defaults** per Constitution Principle VIII — Bayushi's deception/feint identity should drive default attack-strategy choice. Verify mirror non-degeneracy (Bayushi's feint economy might be deadlock-prone like Mirumoto's parry was).
4. **Verify Principle IX 2(a)+(b)+(c)** — mirror termination + win-feasibility ≥ 35% vs Akodo + Bushi baseline.
5. **Constitution gates** — ruff, mypy, 100% coverage, Streamlit smoke OK.

## User Stories

### US1 — Audit + tighten the existing skeleton (Priority: P1) 🎯 MVP

A 5th-Dan Bayushi operates per rules text in a seeded combat. All Dan effects surface with proper attribution.

**Independent Test**: Run rules-auditor + trace-auditor on the existing code. Address any discrepancies.

### US2 — Mirror non-degeneracy (Priority: P1)

Two 5th-Dan Bayushis mirror-fight; combat terminates within 18 rounds via actual defeat AND identity engine fires (≥ 1 feint per Bayushi per match).

### US3 — Win-feasibility (Priority: P1)

450-XP Bayushi wins ≥ 35% vs 450-XP Akodo. (Wave-Man test deferred per the structural finding from Matsu's branch.)

### US4 — Regression guards (Priority: P1)

- `BAYUSHI_PRIORITIES` references all three knacks (double attack, feint, iaijutsu).
- Parry priority audited per school-progression-designer.

### US5 — trace-reader + trace-auditor approve (Priority: P2)

Final pre-merge agent dispatch reports zero blockers on a seeded combat trace.

## Functional Requirements (audit-derived)

### Special Ability
- **FR-001**: VP spent on attack rolls MUST inflate damage rolls by `+1 rolled, +1 kept` per VP.
- **FR-002**: The VP-on-damage contribution MUST surface in the damage breakdown with explicit "VP on attack" attribution.
- **FR-003**: Applies to ALL attack types — `attack`, `double attack`, `feint`, `iaijutsu`, `lunge` (per rules text "all types of attack rolls").

### 1st & 2nd Dan
- **FR-004**: `extra_rolled()` MUST return `["double attack", "iaijutsu", "wound check"]`.
- **FR-005**: `free_raise_skills()` MUST return `["double attack"]`.
- **FR-006**: The 2nd Dan +5 free raise MUST surface as "Bayushi 2nd Dan free raise" attribution on double-attack modifier breakdowns.

### 3rd Dan
- **FR-007**: `BayushiFeintAction.damage_roll_params` MUST return `(attack_skill + vp, 1 + vp, modifier)`.
- **FR-008**: Feint damage MUST NOT include Fire ring bonus or margin-over-TN dice (per rules text "you don't roll extra damage dice from your Fire or from exceeding the TN").
- **FR-009**: Special Ability VP-on-feint MUST inflate damage per FR-001 (rules text "but your Special Ability may increase the damage").
- **FR-010**: The Bayushi 3rd Dan feint damage formula MUST surface in the trace projection (action.damage_breakdown).

### 4th Dan
- **FR-011**: `apply_rank_four_ability` MUST raise Fire ring + apply 5-XP Fire discount.
- **FR-012**: After a successful OR failed feint, the Bayushi MUST gain `AnyAttackFloatingBonus(5)` with source "Bayushi 4th Dan".
- **FR-013**: The floating bonus MUST be consumable on ANY future attack roll this combat.
- **FR-014**: The bonus gain MUST surface in the trace via `GainFloatingBonusEvent` with source attribution.

### 5th Dan
- **FR-015**: `BayushiWoundCheckProvider.wound_check(roll, lw)` MUST halve `lw` (rounded down) before computing SW count.
- **FR-016**: A failed WC (roll < actual LW) MUST yield at least 1 SW (the 5th Dan halving cannot zero out a failed WC).
- **FR-017**: A successful WC MUST yield 0 SW (the 5th Dan halving has no effect on a passed roll).

### Identity-driven defaults (Principle VIII)
- **FR-018**: `BAYUSHI_PRIORITIES` reviewed by `school-progression-designer`.
- **FR-019**: Strategy bindings reviewed by `school-strategy-designer`.
- **FR-020**: Mirror non-degeneracy verified per Principle IX 2(a)+(b).

## Non-Functional Requirements

- **NFR-001**: 100% coverage on `simulation/schools/bayushi_school.py` per Constitution Principle VI v1.3.0.
- **NFR-002**: ≤ 5 existing-test updates outside new tests.
- **NFR-003**: Both `TextRenderer` and `BulletedRenderer` MUST render all Bayushi effects with explicit source attribution.

## Success Criteria

- **SC-001**: 450-XP Bayushi wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002**: 5/5 seeded mirror matches terminate within 18 rounds via actual defeat.
- **SC-003**: 100% coverage on `simulation/schools/bayushi_school.py`.
- **SC-004**: All ruff + mypy + 8-point Constitution checklist gates pass.
- **SC-005**: Final `rules-auditor` + `trace-auditor` + `trace-reader` + `combat-simulator` dispatches return zero blockers.

## Out of Scope

- Wave-Man 450-XP baseline win-feasibility test (deferred per Matsu's cross-school finding — NO school meets the 35% floor; structural rules-balance question).
- Shugenja-style spell mechanics (not applicable).

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md). Summary:

- **Q1**: Does Special Ability apply to lunge? (Rules say "all types of attack rolls" — broad reading.)
- **Q2**: 3rd Dan "Special Ability may increase damage" — confirms VP inflates feint damage; verify implementation.
- **Q3**: 4th Dan "any future attack" — applies to ALL attack types (single-shot floating bonus per gain).
- **Q4**: 5th Dan "half your LW" — at the moment of the failed WC (not the moment damage was dealt).
- **Q5**: Default strategy bindings — to be designed by `school-strategy-designer`.
