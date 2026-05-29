# Open Questions & Pre-Resolutions — Daidoji Yojimbo School

**Status**: Autonomous audit run. Decisions pre-resolved during `/speckit-specify`; logged here for end-of-run review.

The skeleton at `simulation/schools/daidoji_school.py` (237 lines, 34 passing tests) is the most-developed remaining bushi skeleton but has multiple BLOCKING rules-fidelity defects in the 4th and 5th Dan effects.

## Pre-resolutions

### Q1: 3rd Dan ad-hoc attribute tracking — MINOR

**Pre-resolution**: **Refactor.** `apply_rank_three_ability` sets `character._daidoji_third_dan = True` (line 56). Ad-hoc attribute not tracked in `_school_owned_*` slots → school-negation cannot revert. BACKLOG explicitly flagged this.

**Fix**: replace with a tracking mechanism (e.g., use `_set_school_listener` to install a counterattack-succeeded listener that handles the 3rd Dan logic, or use `_set_school_owned_attribute` if available).

### Q2: 4th Dan damage timing — BLOCKING

**Pre-resolution**: **Fix.** Rules text: "before damage has been **rolled**". Skeleton triggers on `LightWoundsDamageEvent` which fires AFTER damage was rolled. Need to intercept earlier — possibly on `AttackSucceededEvent` (after hit but before damage).

**Why**: rules-text fidelity. "Before damage rolled" means the Daidoji acts on the hit confirmation, not on the resulting damage.

**Fix path**: relocate the listener trigger to `AttackSucceededEvent`. Update the listener to intercept the attack action and redirect the damage TARGET so the engine rolls the damage against the Daidoji.

### Q3: 4th Dan "may choose" — strategic gate

**Pre-resolution**: **Add heuristic.** Rules text: "**may choose** to take the damage". Skeleton unconditionally redirects (no strategic logic). Heuristic: redirect when ally's expected SW after the hit exceeds ally's `sw_remaining()` (i.e., ally would likely die without redirect AND Daidoji has more SW headroom).

### Q4: 5th Dan expiry scope — BLOCKING

**Pre-resolution**: **Fix.** Current expiry: `ExpireAfterNextAttackByCharacterListener(daidoji)` — expires after Daidoji attacks. Rules text: "the next time they are attacked" — expire after the next attack AGAINST the attacker (by anyone).

**Fix path**: use a different expiry listener that triggers on `attack_succeeded` / `attack_failed` events where the TARGET is the attacker (the modifier's `target`), not where the SUBJECT is the Daidoji.

### Q5: 5th Dan "for whom you've counterattacked" — BLOCKING

**Pre-resolution**: **Fix.** Rules text: "you **or a character for whom you've counterattacked**". Skeleton gates the ally branch on adjacency (line 219), not on counterattack history. Need to track which allies the Daidoji has counterattacked for (per combat) and only apply 5th Dan bonus to their WCs.

**Fix path**: maintain a per-combat set of allies the Daidoji has counterattacked for; populate in `DaidojiTakeCounterattackActionEvent` (when counterattack action runs); read in the 5th Dan WC listener.

### Q6: 4th Dan listener override pattern

**Concern**: `DaidojiFourthDanListener` REPLACES the engine's default `LightWoundsDamageListener` (via `_set_school_listener`). The listener internally instantiates a `LightWoundsDamageListener()` and delegates non-Daidoji cases to it. This is the pattern, but it's fragile — if the engine's default listener changes, the Daidoji's behavior may drift.

**Pre-resolution**: **OK for now.** Pattern is established; the alternative (composing strategies / decorators) is broader infrastructure work.

### Q7: `DAIDOJI_PRIORITIES` revision

**Pre-resolution**: **Defer** per Bayushi/Kakita/Otaku/Shiba/Shinjo pattern. Existing list has knack-at-every-rank + earth-3 (no Daidoji mechanic) — likely to cascade into calibration-combat test failures.

### Q8: Trace observability

**Pre-resolution**: Tag the events for future renderer work; defer broad surfacing per Otaku/Shiba/Shinjo precedent. Priority:
- 3rd Dan: `WoundCheckFloatingBonus` source label.
- 4th Dan: damage redirect notification.
- 5th Dan: `AddModifierEvent` source attribution (similar to Shinjo).

## To be answered during implementation

### Q9: combat-simulator + win-feasibility

**Status**: Will validate during playability tests.

### Q10: school-strategy-designer's bindings — accepted verbatim?

**Status**: Run during plan dispatch.

### Q11: school-progression-designer's revision — accepted verbatim?

**Status**: Run during plan dispatch (likely deferred per Q7).

## Audit confirmations (post-Phase 2)

### NEW HIGH-SEVERITY bug surfaced by rules-auditor

**5th Dan modifier is wrong-skill + wrong-sign + wrong-holder.** Current code:
```python
modifier = Modifier(self._daidoji, attacker, ATTACK_SKILLS, excess)
yield AddModifierEvent(self._daidoji, modifier)
```
- The modifier buffs **Daidoji's own attack-skill rolls** against the attacker by `+excess`.
- The rules say: "lower the TN to hit the attacker the next time they are attacked" — i.e., should reduce the attacker's `tn_to_hit` (which is read from `character.modifier(None, "tn to hit")` per `character.py:897`).
- **Correct**: `Modifier(attacker, None, "tn to hit", -excess); yield AddModifierEvent(attacker, modifier)`.

**The existing tests at `test_daidoji_school.py:577-678` codify the BUGGY behavior** — they assert `daidoji.modifier(attacker, "attack") == 15`. These must be rewritten to assert `attacker.modifier(None, "tn to hit") == -15`.

### REFUTED

- **Special Ability "no penalty for others"**: rules-auditor confirmed this IS in the upstream rules text. The skeleton override is correct.

### CONFIRMED BLOCKING

- **Q2 (4th Dan timing)**: confirmed — listener fires on `LightWoundsDamageEvent` (after damage rolled).
- **Q3 (4th Dan "may choose")**: confirmed — unconditional redirect.
- **Q4 (5th Dan expiry scope)**: confirmed — `ExpireAfterNextAttackByCharacterListener(self._daidoji)` requires Daidoji=target AND Daidoji=subject simultaneously, never triggers. Only end-of-round expiry works currently.
- **Q5 (5th Dan ally scope)**: confirmed — adjacency-gated, not counterattack-history-gated.

### CONFIRMED MINOR

- **Q1 (3rd Dan ad-hoc attribute tracking)**: confirmed. The `5 * attack_skill` magnitude and original-attack-target both correct.

### combat-simulator playability — PASSED

- 10/10 wins vs Akodo 450 (school IS playable even with the broken 5th Dan).
- Mirror non-degeneracy 5/5 PASS.
- Identity engine fires across the 10-seed sweep: 9 interrupt-counterattacks, 24 3rd Dan WC bonuses, 40 5th Dan modifiers (though on the wrong skill).
- Round-robin 15/21 wins (5 opponents crashed on a pre-existing `spend_ap` features limitation — NOT Daidoji-introduced).

### Dead code

- `DaidojiFifthDanWoundCheckListener.__init__` sets `self._default_listener = None` (line 206) but never uses it.

### Strategy bindings

Strategy-designer recommends adding `WoundCheckStrategy04` (1st Dan WC die + 3rd Dan WC bonus = above-average WC pool, threshold 0.4). Other slots leave engine defaults — Daidoji has no Dans tuning attack/parry/action.

### Progression-designer

`DAIDOJI_PRIORITIES` revision proposed (counterattack-first / attack-second / water-3 at Dan 3 / earth removed / parry capped at 2). **DEFER** per pattern.

## Deviations log (append during implementation)

(empty — to be populated batch-by-batch)
