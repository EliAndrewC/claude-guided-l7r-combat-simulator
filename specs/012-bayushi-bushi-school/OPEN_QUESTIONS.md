# Open Questions & Pre-Resolutions — Bayushi Bushi School

**Status**: Autonomous run. Decisions pre-resolved during `/speckit-specify` and the skeleton audit; logged here for end-of-run review. Per the Matsu (specs/011) workflow, deviations encountered during implementation will also be appended below.

The skeleton at `simulation/schools/bayushi_school.py` (263 lines, 9 passing tests) is the **most polished bushi skeleton** remaining. This is primarily an **audit + verification** run rather than a build-from-scratch run.

## Pre-resolutions from skeleton audit + rules-text reading

### Q1: Special Ability — does "all types of attack rolls" include `lunge`?

**Pre-resolution**: **YES**. The rules text says "all types of attack rolls", which is comprehensive. Lunge is an attack roll → Special Ability applies → VP on lunge inflates lunge damage by +1k1 per VP.

**Why**: Rules-text reading is unambiguous: "all types". The Bayushi school knacks are `double attack, feint, iaijutsu` (lunge is not a knack), but the Special Ability mentions ALL attack rolls, not just knacks. A Bayushi who buys lunge as a generic skill DOES get Special Ability damage on lunges.

**Cross-reference**: `BayushiRollParameterProvider.get_damage_roll_params` is called with `skill` as a parameter; the current implementation doesn't filter by skill, so it already implements the broad reading. Verify in `get_breakdown` too.

### Q2: 3rd Dan — "your Special Ability may increase the damage" — confirms VP-on-feint stacks with formula

**Pre-resolution**: **YES, the Special Ability stacks.** Rules text explicitly says "your Special Ability may increase the damage" — the +1k1-per-VP from the Special Ability applies on top of the 3rd Dan feint damage formula (Xk1 where X = attack skill).

**Why**: Rules text is explicit. The skeleton's `BayushiFeintAction.damage_roll_params` returns `(attack_skill + vp, 1 + vp, modifier)` — VP is added to both rolled AND kept. ✅ matches Q2.

**Cross-reference**: `BayushiFeintAction.damage_breakdown` shows components `("attack skill", X, 0), ("base feint kept die", 0, 1), ("VP on feint", vp, vp)`. Per Principle VII the VP component MUST be explicitly labeled — verified present. ✅

### Q3: 4th Dan — "may apply a free raise to any future attack this combat"

**Pre-resolution**: ONE floating bonus per feint event (success OR failure). The bonus is `AnyAttackFloatingBonus(5)` per the standard "raise = +5 to roll" mechanic. Consumable on a single future attack roll (any type — attack, double attack, feint, iaijutsu, lunge). Multiple feints stack (each grants its own bonus).

**Why**: Rules text "may apply a free raise" reads singular per gain — each feint grants ONE raise. Per the standard floating-bonus consumption model, one bonus is consumed per attack roll.

**Cross-reference**: `BayushiAttackSucceededListener` + `BayushiAttackFailedListener` both create `AnyAttackFloatingBonus(5, source="Bayushi 4th Dan")` and yield `GainFloatingBonusEvent`. ✅ Matches.

### Q4: 5th Dan — "calculate your SW as if you had half your number of LW"

**Pre-resolution**: At the moment the WC FAILS, the SW calculation reads `lw // 2` (rounded down). A failed WC always produces ≥ 1 SW (a rules-text floor — the halving cannot zero out a failed WC because failure-with-0-SW would be a contradiction in terms).

**Why**: The skeleton's `BayushiWoundCheckProvider.wound_check(roll, lw)`:
```python
halved_lw = lw // 2
result = DEFAULT_WOUND_CHECK_PROVIDER.wound_check(roll, halved_lw)
if result == 0 and roll < lw:
    return 1
return result
```
This implements: (a) halve LW for SW calc, (b) min-1 SW on a real failure (`roll < lw`). Matches the rules-text reading.

**Edge case**: a successful WC (roll >= lw) yields 0 SW regardless of halving. Verified by `test_successful_wound_check`.

### Q5: Default strategy bindings — to be designed by `school-strategy-designer`

**Status**: Defer to agent during `/speckit-plan`. Bayushi is a **feint-economy** school — `BayushiAttackSucceededListener` + `BayushiAttackFailedListener` reward feints with floating bonuses. The default attack strategy must actually CHOOSE feints (with reasonable frequency) for the 4th Dan engine to fire. Engine default `UniversalAttackStrategy` has a feint branch but it only fires "when VP == 0 and len(actions) > 1" — that may be too restrictive for Bayushi's identity.

**Why**: Constitution Principle VIII (identity drives defaults). Strategy-designer's analysis is the canonical procedure.

## Pre-resolutions from FR-derived ambiguities

### Q6: Trace observability — what entries need Bayushi-specific attribution?

**Pre-resolution**:
- **Special Ability VP on damage** — `BayushiRollParameterProvider.get_breakdown` already attaches `"VP on attack"` component to damage breakdowns. Verify renderer surfaces this.
- **3rd Dan feint damage** — `BayushiFeintAction.damage_breakdown` shows `attack skill / base feint kept die / VP on feint`. Verify renderer surfaces these without falsely attributing Fire ring or margin dice.
- **4th Dan post-feint floating bonus** — `GainFloatingBonusEvent` is yielded with `source="Bayushi 4th Dan"` + breakdown explaining which feint outcome triggered it. Verify renderer surfaces source.
- **5th Dan half-LW WC** — currently NO explicit trace attribution; the wound_check returns half the normal SW count but the trace doesn't say "Bayushi 5th Dan: LW halved for SW calc". May need a trace attribution. Decide during implementation.

### Q7: Mirror non-degeneracy

**Pre-resolution**: Bayushi's identity is feint-economy with floating bonuses. Both Bayushis feint, both gain floating bonuses, both attack. Mirror should terminate naturally (offensive). But verify via combat-simulator Scenario C.

**Why**: Unlike Hida's defensive stack (which absorbed damage indefinitely), Bayushi's feints DEAL damage (via 3rd Dan Xk1 formula). Mirror should not deadlock.

## To be answered during implementation

### Q8: `school-progression-designer`'s `BAYUSHI_PRIORITIES` revision — accepted verbatim?

**Status**: To be dispatched during `/speckit-plan`. Current `BAYUSHI_PRIORITIES` buys parry at every Dan tier — same anti-identity pattern Matsu's review surfaced. Should parry be capped lower?

### Q9: `school-strategy-designer`'s default bindings — accepted verbatim?

**Status**: To be dispatched during `/speckit-plan`. See Q5.

### Q10: Existing skeleton trace gaps?

**Status**: To be discovered during `trace-auditor` dispatch. The skeleton looks polished but should be verified end-to-end.

## Deviations log (append during implementation)

### Batch A: designer proposals applied + reverted — 2026-05-28

The school-progression-designer (Q8) and school-strategy-designer (Q9) both returned strong proposals. Both were applied; both produced **cascading test failures** in the existing trace-calibration combat (Bayushi-vs-Akodo seed=1234) that drives ~10 tests across `tests/test_trace_observability.py`, `tests/test_unsourced_literal_absence.py`, `tests/test_floating_bonus_inline.py`, and `tests/test_bulleted_renderer.py`. **Both proposals were reverted** to keep this branch focused on audit-and-document; the fixes are deferred to a follow-up branch.

**Designer findings (logged for the follow-up branch):**

1. **P0 — `BayushiAttackStrategy` not installed under defaults** (strategy-designer): the engine default `UniversalAttackStrategy`'s feint branch is gated on `character.vp() == 0 AND len(character.actions()) > 1` (simulation/strategies/base.py:208). A Bayushi whose VP economy is continuously replenished routinely has `vp() > 0`, so the feint branch never fires. Net effect: the school's 3rd Dan Xk1 feint damage formula AND 4th Dan post-feint floating bonus engines are **functionally unreachable under defaults** — a clear Constitution Principle VIII violation. The implementation of `BayushiAttackStrategy` (feint-first ladder + saturation drain + identity-correct branches) is provided as a class in `simulation/schools/bayushi_school.py` but NOT installed in `apply_special_ability`. The follow-up branch needs to (a) install the strategy and (b) re-calibrate the trace-observability tests to a new seed or a non-Bayushi fixture.

2. **MINOR — `BAYUSHI_PRIORITIES` is anti-identity** (progression-designer): same parry-at-every-rank pattern Matsu's review flagged. Bayushi has no parry-keyed rules text. Proposed revision: feint first, attack ahead of DA/iaijutsu (attack is the literal X multiplier in 3rd Dan's Xk1 formula), parry capped at 3, fire promoted to Dan 3, void promoted to Dan 4, earth/air demoted. NOT applied — applying it shifts the 300-XP build composition, which shifts the calibration combat.

**Why both reverted**: the user's framing was "audit the existing implementation" — the audit's value is identifying issues, not necessarily fixing them. Applying both fixes would require re-calibrating ~10 trace tests, which is a separate scope. The `BayushiAttackStrategy` class is preserved in source as the proposed fix; the OPEN_QUESTIONS deferral references it.

**Recommendation for the follow-up branch**:
1. Apply both designer proposals.
2. Replace the seed=1234 Bayushi-Akodo calibration with either (a) a non-Bayushi fixture for the trace tests OR (b) a new seed that exhibits the same trace features under the new Bayushi behavior.
3. Run combat-simulator Scenario C (mirror) to verify the saturation drain works.

**Quality gates this batch**: 3925 tests pass + 5 skipped (4 Hida + 1 Matsu Wave-Man); ruff + mypy clean; coverage maintained.
