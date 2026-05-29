# Open Questions & Pre-Resolutions — Otaku Bushi School

**Status**: Autonomous audit run. Decisions pre-resolved during `/speckit-specify`; logged here for end-of-run review.

The skeleton at `simulation/schools/otaku_school.py` (192 lines, 27 passing tests) has several **BLOCKING rules-fidelity defects** identified by careful reading of the rules text:

## Pre-resolutions

### Q1: Special Ability — does the interrupt-lunge actually fire under defaults?

**Pre-resolution**: **Verify via combat-simulator + add an interrupt strategy if not.** Per the Kakita precedent (specs/013 OPEN_QUESTIONS Q3 fix), `add_interrupt_skill("lunge")` is wired but the default interrupt strategy (`CounterattackInterruptStrategy`) doesn't use lunge. If the school's signature mechanic doesn't fire under defaults, that's a Principle VIII identity bug.

**Why**: Same reasoning as Kakita — wired interrupt capability without a strategy that uses it is structurally dead.

**Fix path**: install an `OtakuInterruptLungeStrategy` that fires after an attack resolves (probably on `AttackFailedEvent` / `AttackSucceededEvent` against the Otaku) and yields a lunge interrupt attack.

### Q2: 3rd Dan — "next X action dice" — BLOCKING rules-fidelity defect

**Pre-resolution**: **Fix.** Rules text: "increase that character's **next X action dice this turn** by (6 − that character's Fire) min 1, where X is your attack skill". The skeleton at `OtakuLightWoundsDamageListener.handle` lines 83-86 iterates ALL of `target.actions()`, modifying every die.

**Fix**: limit the loop to the FIRST X dice (where X = `character.skill("attack")`):
```python
attack_skill = character.skill("attack")
# Sort actions so we modify the EARLIEST (chronologically next) X.
actions.sort()
for i in range(min(attack_skill, len(actions))):
    actions[i] = min(10, actions[i] + increase)
actions.sort()
```

**Why**: Rules-text fidelity. The current behavior is strictly more powerful than the rules permit.

### Q3: 5th Dan — "you may" — BLOCKING choice gap

**Pre-resolution**: **Add strategic logic.** Rules text: "you **may** decrease..." — this is a CHOICE. The skeleton always fires when `raw_rolled >= 12`.

**Heuristic**: only fire when `expected_SW_from_rolling < 1`. The trade gives 1 guaranteed SW; if rolling would deliver ≥ 1 SW in expectation anyway, don't trade. With 12+ rolled damage dice the expectation is usually high — but if the target has good WC, the EXPECTATION of forcing a failed WC may be low.

**Simpler heuristic**: only fire when the damage roll's expected LW is below the target's tolerable_LW (i.e., the target's WC would likely succeed without the trade).

**Fix**: in `OtakuFifthDanTakeAttackActionEvent._roll_damage`, compute the expected non-trade damage and the target's expected WC response; trade only when net expected SW from trade ≥ net expected SW from rolling.

**Implementer latitude**: a simpler trigger condition (e.g., "always trade when raw_rolled ≥ 20") is acceptable if a clean expected-value calc is hard to wire from the action event.

### Q4: 5th Dan dice math — BLOCKING

**Pre-resolution**: **Fix.** Rules text: "decrease the number of **rolled** damage dice by 10, to a minimum of 2". The skeleton does `reduced_extra = extra_rolled - 10` — subtracting from MARGIN extras only. For a typical attack with margin=4, this becomes `reduced_extra = -6` → catastrophic negative.

**Fix**: Compute the TOTAL rolled dice (ring + weapon + extras + my_extra_rolled), subtract 10, floor at 2, then propagate back to the damage roll. Possibly via a new `roll_damage_with_dice_override(rolled, kept)` path or by adjusting `extra_rolled` to absorb the entire delta (subject to floor).

**Pragmatic approach**: compute `target_rolled = max(2, total_rolled - 10)`, then `effective_extra = target_rolled - ring - weapon.rolled() - my_extra_rolled` and pass that to `roll_damage` (clamped at 0 if negative, with `kept` reduced if necessary to keep `kept ≤ rolled`).

### Q5: `OTAKU_PRIORITIES` revision

**Pre-resolution**: **Defer like Bayushi/Kakita.** Same anti-identity parry-at-every-rank pattern. Applying the school-progression-designer's revision is likely to cascade into calibration combat / study test failures; defer to a follow-up branch.

### Q6: Trace observability gaps

**Pre-resolution**: Fix the most impactful ones via tagged-action + `modifier_breakdown.py` clauses, per the Kakita precedent. Priority order:
- 3rd Dan action-die manipulation (significant tempo effect, currently silent)
- 5th Dan dice-trade-for-SW (the trade is invisible to the reader; SeriousWoundsDamageEvent appears out of nowhere)
- 4th Dan parry-still-+1 (lunge damage line should explain the +1 when parried)

## To be answered during implementation

### Q7: combat-simulator finding on win-feasibility

**Status**: Run during `/speckit-implement` Batch B.

### Q8: school-strategy-designer's bindings — accepted verbatim?

**Status**: Run during plan dispatch.

### Q9: school-progression-designer's revision — accepted verbatim?

**Status**: Run during plan dispatch (likely deferred per Q5).

## Audit confirmations (post-Phase 2)

All four BLOCKING claims confirmed by `rules-auditor` AND empirically by `combat-simulator`:

- **Q1 IDENTITY GAP**: combat-simulator measured **0 interrupt-lunges across 23 combats** (Scenario A, B×10 seeds, C×5 seeds, D×7 matchups). `add_interrupt_skill("lunge")` is structurally dead under defaults. Strategy-designer proposes new `OtakuInterruptLungeStrategy` (fires on `AttackSucceededEvent`/`AttackFailedEvent`) + `WoundCheckStrategy04`, with mirror-recursion gate (decline against incoming interrupt-lunge) and SW-saturation gate (decline at `sw_remaining() <= 1`).
- **Q2 3rd Dan**: confirmed. trace-reader observed `[2,4,7,8,8]` → `[6,9,10,10]` shift (+2 to every die) silently.
- **Q3 5th Dan "may"**: confirmed unconditional firing.
- **Q4 5th Dan dice math**: confirmed; surfaces as user-visible `-8k-2 reconciliation` label hiding the trade. Worked example: ring=6, weapon=4, margin=2, extras=2 → raw_rolled=14 → skeleton produces `reduced_extra = -8` → negative dice components leak into the trace.

### Q5 — `OTAKU_PRIORITIES`

`school-progression-designer` produced a complete revision (lunge → attack → fire-3 at Dan 3, water-3 at Dan 4, parry capped at 3, anti-identity earth-N removed). **DEFER** per Bayushi/Kakita pattern: applying it shifts seeded calibration combats and cascades into pre-existing trace tests. Document in BACKLOG.

### Q6 — Trace observability

Trace-auditor + trace-reader together identified **3 P0 + 2 P1 gaps**:

- **P0**: 3rd Dan action-die shift is completely silent.
- **P0**: 5th Dan auto-SW renders identically to a counterattack SW (no source label).
- **P0**: 5th Dan dice-trade-down surfaces as `-Nk-M reconciliation` (label hides the rules cause).
- **P1**: 4th Dan parry-still-+1 has no attribution path (not exercised in seed=1 probe; reachable via lunge probe).
- **P1**: Special Ability interrupt-lunge needs a label when wired.

## Deviations log (append during implementation)

(empty — to be populated batch-by-batch)
