# Spec: Matsu Bushi School

**Branch**: `012-matsu-bushi-school`
**Created**: 2026-05-28
**Status**: Draft (autonomous run)
**Driver**: Run the next entry in `BACKLOG.md` ("Matsu Bushi School") through the same speckit + agent-driven workflow that completed Hida (PR `b52dc08`).

## Rules text (verbatim, from rules/04-schools.md)

> **Matsu Bushi School**
>
> School Ring: Fire
>
> School Knacks: double attack, iaijutsu, lunge
>
> Special Ability: You always roll 10 dice when rolling initiative, keeping the usual number as action dice.
>
> First Dan: Roll one extra die on double attack, iaijutsu, and wound checks.
>
> Second Dan: You get a free raise on iaijutsu rolls.
>
> Third Dan: When you spend a void point, you may add 3X to any future wound check this combat after seeing the roll, where X is your attack skill.
>
> Fourth Dan: Raise your current and maximum Fire by 1. Raising your Fire now costs 5 fewer XP. When you miss the TN on a double attack roll by less than 20, you are still considered to have hit, but you deal no extra damage.
>
> Fifth Dan: After you deal light wounds which result in the defender taking one or more serious wounds, their light wound total is reset to 15 instead of 0.

## Skeleton audit

`simulation/schools/matsu_school.py` (167 lines) is the most complete bushi skeleton remaining — significantly more developed than Hida's was. 16 existing tests in `tests/test_matsu_school.py` all pass at branch creation. The skeleton implements:

| Rules clause | Implementation site | Status |
|---|---|---|
| Special Ability — always 10 initiative dice | `MatsuRollProvider.get_initiative_roll` | **Skeletal** — uses `max(rolled, 10)` (at-least-10). The strict rules reading is "always" = exactly 10. **Ambiguity Q1.** |
| 1st Dan — extra die on double attack / iaijutsu / wound check | `extra_rolled()` returns the three skills | ✅ Correct (verified by test) |
| 2nd Dan — free raise on iaijutsu | `free_raise_skills()` returns `["iaijutsu"]` | ✅ Correct (verified by test) |
| 3rd Dan — +3X WC bonus on VP spend | `MatsuSpendVoidPointsListener` grants `WoundCheckFloatingBonus(3 × attack)` on every `SpendVoidPointsEvent` | **Mostly correct** — but does it apply to ANY future WC or only the NEXT one? **Ambiguity Q2.** And "after seeing the roll" interpretation needs verification — does `WoundCheckFloatingBonus` support post-roll application? **Q2 sub-issue.** |
| 4th Dan — ring raise + discount + near-miss-on-double-attack | `apply_school_ring_raise_and_discount` + `MatsuActionFactory` installing `MatsuDoubleAttackAction` | ✅ Looks correct; near-miss = hit but `calculate_extra_damage_dice → 0` and `direct_damage → None` |
| 5th Dan — defender LW reset to 15 instead of 0 on Matsu-induced SW | `MatsuWoundCheckFailedListener` sets `_lw = 15` on the failed-WC path | **Partial** — only fires on `WoundCheckFailedEvent` (involuntary SW from failed WC). Misses **voluntary SW** from `KeepLightWoundsStrategy` choosing to take SW on a passed WC. **Ambiguity Q3.** |

Other gaps:
- No default attack/parry/WC strategy bindings installed in `apply_special_ability`. Matsu uses the engine default `UniversalAttackStrategy` and `ReluctantParryStrategy`. **Ambiguity Q4** — Matsu's offensive berserker identity may warrant a more aggressive default attack strategy and/or a different parry posture.
- `MATSU_PRIORITIES` in `simulation/templates/strategies.py` exists with reasonable structure but should be reviewed against the school's identity by `school-progression-designer`.

## Goals

1. **Resolve all 4 identified rules-text ambiguities** with documented pre-resolutions in `OPEN_QUESTIONS.md`.
2. **Wire identity-driven defaults** per Constitution Principle VIII — Matsu's berserker identity should drive default attack-strategy choice, ensuring the school's signature mechanics (1st-Dan extra WC die, 3rd-Dan +3X WC bonus, 4th-Dan near-miss double attack, 5th-Dan LW-floor) actually surface under default play.
3. **Verify Principle IX 2(a)+(b)+(c)** — mirror-match non-degeneracy (Matsu is offensive, so expected to terminate naturally) AND win-feasibility ≥ 35% vs Akodo + universal Bushi baseline at 450 XP.
4. **Trace observability per Principle VII** — every Matsu-specific effect surfaces in both `TextRenderer` and `BulletedRenderer` with explicit source attribution.
5. **Constitution gates** — ruff clean, mypy strict on `simulation/` and `web/`, 100% coverage (pragmas with justification per Principle VI v1.3.0), Streamlit smoke OK.

## User Stories

### US1 — Full Dan ladder fires end-to-end (Priority: P1) 🎯 MVP

A 5th-Dan Matsu operates per rules text in a seeded combat. Every Dan effect surfaces in the trace with proper attribution.

**Independent Test**: Seeded 5th-Dan Matsu combat. Assert:
- `Roll: N` reflects always-10 initiative dice
- 1st-Dan +1 die on double attack / iaijutsu / wound check is visible in rolled count
- 2nd-Dan free raise on iaijutsu appears in modifier breakdown
- 3rd-Dan VP-spend grants a floating bonus that's later consumed on a WC, both events traced
- 4th-Dan near-miss double attack renders as a hit with no extra damage
- 5th-Dan: when a Matsu attack causes SW, defender's LW is set to 15 (not 0) and the trace surfaces "Matsu 5th Dan: LW reset to 15" or equivalent

### US2 — Mirror non-degeneracy (Priority: P1)

Two 5th-Dan Matsus mirror-fight; combat terminates within 18 rounds AND each takes at least one attack action AND identity engine fires (double attacks or iaijutsu attacks > 0 total).

**Independent Test**: 5 seeded mirror matches, all terminate < 18 rounds with actual defeat (not cap-saturation per Hida-lessons).

### US3 — Win-feasibility (Priority: P1)

450-XP Matsu wins ≥ 35% vs 450-XP Akodo and ≥ 35% vs 450-XP universal Bushi baseline across 20 seeds.

**Independent Test**: 20 seeds Hida ... err, Matsu vs each. (Matsu is offensive; expect this to be more achievable than Hida's was.)

### US4 — Regression guards (Priority: P1)

- `MATSU_PRIORITIES` references all three knacks (`double attack`, `iaijutsu`, `lunge`).
- No future regression that removes the `MatsuDoubleAttackAction` near-miss carve-out.

### US5 — trace-reader + trace-auditor approve (Priority: P2)

After implementation, both agents report zero blockers on a seeded 5th-Dan Matsu combat trace.

## Functional Requirements

### FR-001 to FR-005 — Special Ability (always-10 initiative)
- **FR-001**: Matsu's `roll_initiative()` MUST always roll exactly 10 dice (the strict reading of "always 10"; see Q1).
- **FR-002**: The `kept` count MUST remain unchanged (the rules text explicitly says "keeping the usual number as action dice").
- **FR-003**: The trace MUST surface the always-10 dice count (e.g., visible in the initiative trace line). Pre-existing initiative tracing is sufficient if it already shows the dice count.
- **FR-004**: A non-Matsu character's initiative MUST be unaffected.
- **FR-005**: A 5th-Dan-negated Matsu (via Isawa Ishi 5th Dan) MUST revert to standard initiative dice count.

### FR-006 to FR-009 — 1st & 2nd Dan
- **FR-006**: 1st Dan: `extra_rolled()` MUST return `["double attack", "iaijutsu", "wound check"]`.
- **FR-007**: 2nd Dan: `free_raise_skills()` MUST return `["iaijutsu"]`.
- **FR-008**: The 2nd Dan +5 free raise MUST surface in the iaijutsu-roll modifier breakdown with explicit "Matsu 2nd Dan free raise" attribution.
- **FR-009**: The 1st Dan +1 die MUST be observable as the rolled count being one higher than the base would suggest, visible in the trace.

### FR-010 to FR-014 — 3rd Dan (+3X WC bonus on VP spend)
- **FR-010**: On `SpendVoidPointsEvent` where subject is the Matsu, a `WoundCheckFloatingBonus(3 × attack_skill)` MUST be gained.
- **FR-011**: The floating bonus MUST be consumable on a future WC roll, per the standard `WoundCheckFloatingBonus` mechanism — applies "after seeing the roll" (post-roll application) per the rules text.
- **FR-012**: The bonus MUST stack with itself on multiple VP spends (a Matsu who spends 2 VP in the same combat has two pending bonuses).
- **FR-013**: The trace MUST show the floating-bonus gain (with source "Matsu 3rd Dan") AND its consumption on a WC roll.
- **FR-014**: A Matsu with 0 attack skill MUST gain a +0 bonus (i.e., the listener doesn't crash but the effect is null).

### FR-015 to FR-021 — 4th Dan (ring raise + discount + near-miss double attack)
- **FR-015**: `apply_rank_four_ability` MUST raise current Fire by 1 and apply the 5-XP discount on subsequent Fire purchases.
- **FR-016**: A 5th-Dan Matsu's `MatsuActionFactory` MUST return `MatsuDoubleAttackAction` for `double attack` skill.
- **FR-017**: `MatsuDoubleAttackAction.is_hit()` MUST return True when `skill_roll >= tn() - 20` (near-miss carve-out) AND not parried.
- **FR-018**: For a near-miss (`skill_roll < tn`), `calculate_extra_damage_dice` MUST return 0.
- **FR-019**: For a near-miss, `direct_damage()` MUST return `None` (no direct SW damage from the double attack).
- **FR-020**: For a clear hit (`skill_roll >= tn`), `MatsuDoubleAttackAction` MUST behave identically to the parent `DoubleAttackAction`.
- **FR-021**: The trace MUST clearly indicate a near-miss with explicit "Matsu 4th Dan: near-miss" attribution.

### FR-022 to FR-026 — 5th Dan (LW-floor of 15)
- **FR-022**: When a Matsu's attack causes the defender to take SW (involuntary, via failed WC), the defender's LW MUST be set to 15 instead of 0.
- **FR-023**: The trace MUST surface "Matsu 5th Dan: LW reset to 15" attribution on the LW transition.
- **FR-024**: If the defender's LW total was ALREADY ≤ 15 before the attack, the LW MUST still be set to exactly 15 (an INCREASE, per strict rules reading; Q5).
- **FR-025**: The Matsu's OWN failed WC behaves normally (LW resets to 0, no special treatment).
- **FR-026**: A 5th-Dan-negated Matsu (via Isawa Ishi 5th Dan) MUST revert to standard behavior (LW resets to 0).

### FR-027 to FR-030 — Identity-driven defaults (Principle VIII)
- **FR-027**: `MATSU_PRIORITIES` MUST be reviewed by `school-progression-designer`. Lunge / double attack / iaijutsu MUST be prioritized over plain attack (the school knacks).
- **FR-028**: The school MUST install identity-driven default attack/parry/WC strategies via `school-strategy-designer`'s proposal.
- **FR-029**: `apply_special_ability` MUST set up the strategy slot bindings AT LEAST for the attack slot (offensive identity), even if reserve / kill-shot tiers are minimal.
- **FR-030**: Mirror non-degeneracy MUST hold per Principle IX 2(a)+(b)+(c) — combat-simulator verifies 5/5 mirror seeds terminate within 18 rounds via actual defeat (not cap-saturation).

## Non-Functional Requirements

- **NFR-001**: All Matsu-specific code lives in `simulation/schools/matsu_school.py` (plus tests in `tests/test_matsu_school*.py`).
- **NFR-002**: 100% coverage on `simulation/schools/matsu_school.py` per Constitution Principle VI v1.3.0 (pragma skips allowed with one-line justification).
- **NFR-003**: ≤ 5 existing-test updates outside the new tests (per the Mirumoto / Ishi / Akodo / Hida cap convention).
- **NFR-004**: Both `TextRenderer` and `BulletedRenderer` MUST render all new Matsu effects with explicit source attribution per Principle VII.

## Success Criteria

- **SC-001 / FR-029**: 450-XP Matsu wins ≥ 35% vs 450-XP Akodo across 20 seeds.
- **SC-002 / FR-029**: 450-XP Matsu wins ≥ 35% vs 450-XP universal Bushi baseline across 20 seeds.
- **SC-003 / FR-030**: 5/5 seeded mirror matches terminate within 18 rounds via actual defeat.
- **SC-004**: Test count increases by 35-60 (existing 16 + new tests for new behaviors + coverage tests).
- **SC-005**: Coverage = 100% on the school module.
- **SC-006**: All ruff + mypy + 8-point Constitution checklist gates pass.

## Out of Scope

- Shugenja-style spell-list mechanics (not applicable; Matsu has none).
- Action-disadvantage scenario (Scenario B.2) — optional; if combat-simulator surfaces it as relevant during US3 verification we'll address, but it's not a P1 requirement.
- Re-tuning Akodo or Hida templates to balance against Matsu — out of scope for this branch (those are separate, larger questions documented in their respective `OPEN_QUESTIONS.md`).

## Clarifications

See [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) for the full list of ambiguities with pre-resolutions. Summary:

- **Q1**: Special Ability "always 10" → strict (exactly 10, not "at least 10").
- **Q2**: 3rd Dan floating bonus applies to ANY future WC (the standard `WoundCheckFloatingBonus` mechanism, which is per-WC-roll consumable).
- **Q3**: 5th Dan triggers on involuntary SW (failed WC) only, not on voluntary SW from `KeepLightWoundsStrategy`.
- **Q4**: Identity-driven default attack strategy proposed by `school-strategy-designer` during `/speckit-plan`.
- **Q5**: 5th Dan "LW reset to 15" means exactly 15, even if defender previously had < 15 LW (rules-text reading is "set to 15", not "increase to at least 15" or "decrease to at most 15").
