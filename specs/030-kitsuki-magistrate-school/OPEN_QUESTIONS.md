# Kitsuki Magistrate School — Open Questions

## Q1 — DEFERRED — Special Ability "Water for interrogation"

**Question**: SA rules-text first clause says "You use Water for
interrogation rolls." Should this be implemented?

**Pre-resolution**: DEFER — interrogation is a non-combat social
skill. The engine simulates combat only; this clause has no
combat effect. Document as a deferred non-combat refinement.

**Status**: RESOLVED — deferred.

## Q2 — DEFERRED — 4th Dan info-omniscience

**Question**: 4th Dan says "You automatically know the Void,
parry, and phase of the next action of each character during
combat." Should the engine model this?

**Pre-resolution**: PASS — the combat AI already has effective
access to all opponent state (`character.vp()`, `character.parry_skill()`,
`character.actions()`); the "knowledge" granted is already implicit.
The rules-text intent is to help human players make informed
decisions; the simulator's AI has perfect visibility regardless.

**Status**: RESOLVED — already-implicit pass.

## Q3 — BLOCKING — 5th Dan targeting

**Question**: Rules say "Air, Fire and Water rings of CHOSEN
characters are reduced by one." Skeleton applies to ALL
opponents unconditionally.

**Rules constraint**: "You may do this to any one character, or
you may do it to multiple characters so long as the sum of their
experience does not exceed your experience."

**Pre-resolution**: FIX — reduce a single chosen target's rings.
Pick the highest-XP opponent (most threatening; rules permit a
single target without budget arithmetic). The multi-target XP
budget rule is harder to implement and the single-target case
already satisfies the rules. Multi-target with XP budget is
deferred as a possible refinement.

**Status**: RESOLVED — single-target highest-XP fix.

## Q4 — MEDIUM — 5th Dan stacking guard

**Question**: Rules say "it does not stack with other Kitsuki
Magistrates targeting the same character." Skeleton has no
stacking guard.

**Pre-resolution**: FIX — track an `_kitsuki_5th_dan_applied`
flag on the target so a second Kitsuki sees the flag and skips.

**Status**: RESOLVED — guard fix.

## Q5 — DEFERRED — "Not during iaijutsu phase of a duel"

**Question**: Rules say "This does not work during the iaijutsu
phase of a duel." Should the engine model this?

**Pre-resolution**: DEFER — the engine does not model duel
iaijutsu as a separate combat phase. The clause is vacuously
satisfied; document as a deferred refinement.

**Status**: RESOLVED — deferred.
