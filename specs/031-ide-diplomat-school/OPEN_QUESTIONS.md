# Ide Diplomat School — Open Questions

## Q1 — INTERPRETIVE — SA modifier expiry

**Question**: SA rules-text says "After a feint which met its TN,
lower the TN of the target by 10 the next time they are attacked
(even if parried)." Does "the next time they are attacked" mean
(a) the next attack on the target by anyone, or (b) the next
attack on the target by the Ide?

**Skeleton**: Interpretation (b) — uses
`ExpireAfterNextAttackByCharacterListener(character)` which expires
the modifier only after THIS Ide attacks.

**Pre-resolution**: PASS — interpretation (b) is defensible and
matches the Ide's typical combat pattern (feint then follow-up).
A wider "any attacker" reading would be more powerful but harder
to control narratively. Document as interpretive deferral.

**Status**: RESOLVED — pass (rules-auditor verification requested).

## Q2 — INTERPRETIVE — 3rd Dan scope

**Question**: 3rd Dan says "you may spend void points to subtract
Xk1 from rolls (where X equals tact skill)." Two sub-questions:
(a) does "rolls" mean any rolls or specifically attack rolls?
(b) is the spend exactly 1 VP per use, or variable?

**Skeleton**: Attack rolls only; exactly 1 VP per fire.

**Pre-resolution**: PASS — combat-scope limitation (attack rolls)
matches the simulator's scope; 1 VP per use is the most common
pattern in other schools' interrupts.

**Status**: RESOLVED — pass.

## Q4 — VERIFIED-PASS — 3rd Dan "Xk1" purity

**Question** (raised by rules-auditor): rules say "subtract Xk1
from the roll" — a plain Xk1, not a tact-skill roll. The skeleton
calls `character.roll_provider().get_skill_roll("tact", tact, 1, True)`.
Does `get_skill_roll` apply skill modifiers (emphases, free raises,
floating bonuses) that would exceed a plain Xk1?

**Verification**: Inspected `simulation/mechanics/roll_provider.py`
lines 82-87 (`StandardRollProvider.get_skill_roll`). The method
just constructs a `Roll(rolled, kept, ...)` and rolls — NO skill
modifiers are applied at the roll-provider layer. Skill modifiers
live at the roll-parameter-provider layer
(`DefaultRollParameterProvider.get_skill_roll_params`), which is
NOT called here. The skeleton's `get_skill_roll("tact", tact, 1, True)`
is observationally equivalent to a plain Xk1 roll.

**Status**: RESOLVED — verified PASS. The rules-auditor's concern
was based on a layer-confusion; the engine separates parameter
provision (where modifiers apply) from roll execution (where dice
are rolled). The skeleton's call is correct.

## Q3 — MEDIUM — 5th Dan TVP exclusion

**Question**: Rules say "Gain a temporary void point whenever
you spend a void point that was not gained from this technique."
The exclusion prevents infinite-TVP loops when spending a
previously-5th-Dan-gained TVP. Skeleton's `IdeSpendVPListener`
guards `if event.skill != "tact"` instead — which addresses a
*different* concern (3rd Dan VP-spending feeding 5th Dan) but
does not implement the literal rules exclusion.

**Skeleton**: Excludes `skill == "tact"` (3rd Dan).

**Trade-off**:
- The skeleton's interpretation prevents the 3rd Dan TVP loop
  (a real concern given the spec's combat focus).
- It does NOT prevent the "spending a 5th-Dan-gained TVP grants
  another TVP" loop. The character flows VPs → TVPs → spent →
  more TVPs.
- In practice, the engine consumes TVPs FIRST when spending
  (`character.py:858`), so the loop manifests as sustained TVP
  income while the character keeps spending. Not infinite damage
  because each spend is voluntary.

**Pre-resolution**: PASS — the skeleton's interpretation is a
defensible simplification given:
1. The literal rules exclusion requires tracking VP provenance
   (which TVPs came from 5th Dan vs other sources), which the
   current event/character model does not expose.
2. The "spend → TVP → spend → TVP" loop is self-limiting (each
   spend is a voluntary decision; the character does not spend
   indefinitely).
3. Excluding 3rd Dan tact-spends prevents the only auto-loop
   the simulator can construct.

Document the deviation in OPEN_QUESTIONS for end-of-run review;
do NOT change the implementation in this audit run.

**Status**: RESOLVED — defer the literal-rules implementation
(would need TVP provenance tracking, out of scope).
