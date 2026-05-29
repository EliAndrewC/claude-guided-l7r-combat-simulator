# Shosuro Actor School — Open Questions

## Q1 — BLOCKING — 5th Dan applies to damage rolls

**Question**: Does the 5th Dan ability ("After making any non-initiative roll, add your lowest three dice to the result") apply to damage rolls?

**Rules text**: "After making any non-initiative roll, add your lowest three dice to the result. (Some dice may be counted twice.)"

**Skeleton**: `ShosuroActorRollProvider` applies the bonus to `get_skill_roll` and `get_wound_check_roll` only. Damage rolls are NOT modified. The docstring explicitly says "TN or contested rolls are skill rolls and wound checks. Damage rolls and initiative rolls are NOT modified."

**Pre-resolution**: **YES — apply to damage rolls.** The rules text says "any non-initiative roll", with initiative as the SOLE exclusion. Damage rolls are non-initiative rolls (they have dice, they produce a result). The skeleton's interpretation is narrower than the rules-text grants.

**Status**: RESOLVED — will fix in implementation.

## Q2 — INTERPRETIVE — Special Ability "attack" scope

**Question**: When the Special Ability says "roll extra dice equal to your acting on attack, parry, and wound checks", does "attack" mean only the `attack` skill, or all ATTACK_SKILLS (which include feint, double_attack)?

**Skeleton**: Applies to `ATTACK_SKILLS` (the broader set).

**Pre-resolution**: **PASS — ATTACK_SKILLS is defensible.** Other schools (e.g., Courtier "Add your Air to all attack and damage rolls") have interpreted "attack" as the attack-family. Maintains consistency.

**Status**: RESOLVED/PASS — no change.

## Q3 — BLOCKING — 5th Dan applies to damage reduction

**Question**: Damage reduction rolls (from armor) — should they get the lowest-3 bonus?

**Initial pre-resolution**: NO — defer.

**Rules-auditor reversal**: YES — apply. The rules text says "any
non-initiative roll"; damage reduction is a non-initiative roll
(dice rolled/kept, numeric result). The "primary roll" qualifier
in the initial pre-resolution is not in the rules text. Same
logic as Q1: deferring it would narrow the rule.

**Status**: RESOLVED (reversed) — applied to `get_damage_reduction_roll`
alongside Q1's `get_damage_roll`.

## Q4 — MEDIUM — "Some dice may be counted twice"

**Question**: When fewer than 3 dice are rolled, what is the bonus?

**Rules text**: "(Some dice may be counted twice.)" — parenthetical
on the 5th Dan ability.

**Skeleton (pre-fix)**: `_lowest_three_bonus` summed only the dice
present (e.g., 2 dice → sum of both). The parenthetical implies the
lowest die should be re-counted to pad to 3.

**Resolution**: pad `sorted_dice` by appending the lowest die until
length 3. With 1 die, the bonus is 3× that die; with 2 dice, the
lowest die is counted twice.

**Status**: RESOLVED — applied.
