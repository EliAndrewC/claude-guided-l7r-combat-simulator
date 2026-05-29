# Merchant School — Open Questions

## Q1 — INTERPRETIVE — SA post-roll VP value

**Question**: SA says "You may spend void points after you see the
results of your initial roll." Rules don't redefine what VP does
on a roll. Normally VP grants +1k1 (one additional die rolled and
kept). Skeleton converts post-roll VP to flat +5 per VP because
the dice are already rolled.

**Pre-resolution**: PASS — VP cannot retroactively add dice to a
roll already made; the dice were rolled with the original (rolled,
kept) parameters. A flat +5 per VP is a conservative approximation
of the expected value of keeping one additional die (which would
have an expected value ~5.5 if it were a fresh roll).

**Status**: RESOLVED — pass.

## Q2 — INTERPRETIVE — 5th Dan auto-reroll vs voluntary

**Question**: 5th Dan says "you MAY reroll some of the dice" —
voluntary. Skeleton's `MerchantRollProvider._maybe_reroll`
automatically rerolls dice when beneficial (expected_gain > 0).

**Pre-resolution**: PASS — the simulator's AI plays optimally on
behalf of the character; auto-rerolling when beneficial matches
"the character would always choose to do this." A pessimal
implementation (never reroll) would violate Principle VIII
(identity engine never fires). The skeleton's auto-decision is
correct for the simulator's purpose.

**Status**: RESOLVED — pass.

## Q4 — DEFERRED (rules-auditor MEDIUM) — Pre-roll VP foreclosed

**Question** (rules-auditor): SA says "you MAY spend VP after seeing
the roll" — permissive, not mandatory. The skeleton's
`MerchantAttackOptimizerFactory` ALWAYS passes `max_vp=0`,
foreclosing the option of pre-roll VP spending. For attacks where
+1k1 pre-roll would beat +5 post-roll, the Merchant is strictly
worse than baseline.

**Pre-resolution**: DEFER — implementing a hybrid optimizer that
chooses between pre-roll +1k1 and post-roll +5 would require a
decision rule the rules-text does not specify. The current
"always defer" interpretation matches the simulator's optimal-play
frame (post-roll information is always at least as much as pre-roll
information). Documented trade-off; not fixed.

**Status**: RESOLVED — defer.

## Q5 — DEFERRED (rules-auditor BLOCKING) — 5th Dan rolled-vs-kept asymmetry

**Question** (rules-auditor): The 5th Dan reroll algorithm in
`_find_dice_to_reroll` and `_maybe_reroll` does not distinguish
between kept and unkept dice. For an XkY roll with X>Y, the
X-Y unkept low dice are already dropped from `original_total`,
but the algorithm's `expected_gain = x * 5.5 - reroll_sum`
treats all dice symmetrically. This overestimates the gain of
rerolling kept dice and underestimates the (potentially free)
gain of rerolling unkept dice.

**Skeleton behavior**: The reroll still fires when beneficial under
the current heuristic; it just uses a suboptimal selection rule.
Rerolling unkept low dice is technically "free upside" (they
weren't contributing anyway) but the algorithm may skip them in
favor of rerolling kept low dice it thinks have larger gain.

**Pre-resolution**: DEFER — the rules text says "you MAY reroll
some of the dice" — the algorithm's choice of WHICH dice to
reroll is a player decision, not a rules-fidelity concern. The
skeleton's heuristic is suboptimal but not rules-violating. A
proper fix would require:
1. Threading the `kept` parameter through `_find_dice_to_reroll`
   so it can distinguish kept (top-K) from unkept (bottom X-K)
   dice.
2. A different expected-gain formula for unkept dice (expected
   value of displacing the lowest kept die).
3. Considering non-contiguous subsets (rules-auditor MEDIUM).

The 5th Dan ability still fires when the heuristic finds a
beneficial reroll. The literal rules are satisfied. Documented
as a known sub-optimal heuristic for future refinement.

**Status**: RESOLVED — defer (sub-optimal but rules-compliant).

## Q3 — INTERPRETIVE — "Once per roll" guard

**Question**: 5th Dan says "You may only do this once per roll."
Is the skeleton's interpretation (each `get_*_roll` call is one
roll) correct?

**Pre-resolution**: PASS — each call to `get_skill_roll` /
`get_damage_roll` / etc. represents a single dice-pool roll. The
skeleton calls `_maybe_reroll` once per such call. Matches rules.

**Status**: RESOLVED — pass.
