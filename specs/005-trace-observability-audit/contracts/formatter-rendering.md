# Formatter Rendering Contracts (Combat Trace Observability Audit)

This document records the rendering contracts the formatter MUST honor after this audit lands. Tests assert against these specific shapes.

## Attack roll rendering

**Pre-audit**:
```
Phase 2 | Bayushi | ⬛ spends 1 VP on double attack → ⚔️ attacks Akodo (double attack) — 10k10 [9, 9, 8, 7, 6, 6, 4, 3, 2, 2] → 56, +5 = 61 vs TN 50 (base TN 30) — HIT! (+11 over TN, 6 extra damage dice, damage will be 10k10)
```

**Post-audit**:
```
Phase 2 | Bayushi | ⬛ spends 1 VP on double attack → ⚔️ attacks Akodo (double attack) — 10k10 = 6k3 Fire ring + 3k6 attack skill + 1k1 VP on attack [9, 9, 8, 7, 6, 6, 4, 3, 2, 2] → 56, +5 (Bayushi 5th Dan double attack) = 61 vs TN 50 (base TN 30, +20 from 4 raises for double attack) — HIT! (+11 over TN, 6 extra damage dice from margin 11÷5, damage will be 10k10 = 4k2 katana + 6k0 Fire ring + 0k6 margin + 0k2 VP on attack)
```

**Contract**:
- The attack XkY (`10k10`) MUST be followed by `= <breakdown>` showing per-source contributions.
- The bare `+5` modifier MUST be followed by `(source)` attribution.
- The TN expression `vs TN 50 (base TN 30)` MUST be extended with `(base TN 30, +20 from K raises for {action})`.
- The "extra damage dice" parenthetical MUST include the `margin / 5` derivation.
- The "damage will be" projection MUST include the inline breakdown.

## Damage event rendering

**Pre-audit**:
```
Bayushi | 💥 Damage: 10k10 [12, 11, 9, 9, 8, 6, 5, ~~5~~, ~~2~~, ~~2~~] → 60 → Akodo takes 60 light wounds (total: 60)
```

**Post-audit**:
```
Bayushi | 💥 Damage: 10k10 = 4k2 katana + 6k0 Fire ring + 0k6 margin + 0k2 VP on attack [12, 11, 9, 9, 8, 6, 5, ~~5~~, ~~2~~, ~~2~~] → 60 → Akodo takes 60 light wounds (total: 60)
```

**Contract**:
- The damage XkY MUST be followed by `= <breakdown>` showing per-source contributions.
- The breakdown labels match those used in the predictive "damage will be" projection on the attack line.

## Modifier breakdown rendering

**Pre-audit** (silent suppression):
```
... → 56, +5 = 61 vs TN 50 ...
```

**Post-audit** (sourced):
```
... → 56, +5 (Bayushi 5th Dan double attack) = 61 vs TN 50 ...
```

**Post-audit** (unsourced fallback):
```
... → 56, +5 (unsourced: +5) = 61 vs TN 50 ...
```

**Contract**:
- When `explain_modifier` returns a labeled source, render `+N (source)`.
- When `explain_modifier` returns NO source for a nonzero modifier, render `+N (unsourced: +N)`. The placeholder is itself a Principle VII violation visible to tests.
- When `explain_modifier` returns a partial source (e.g., `+3` from a known source out of `+5` total), render `+5 (source: +3, unsourced: +2)`.

## TN rendering

**Pre-audit**:
```
... vs TN 50 (base TN 30) ...
```

**Post-audit (with raises)**:
```
... vs TN 50 (base TN 30, +20 from 4 raises for double attack) ...
```

**Post-audit (no raises)**:
```
... vs TN 30 (base TN 30) ...
```

**Contract**:
- Always show `(base TN M)`.
- When `event.action.raises() > 0`, append `, +X from K raises for {action.skill()}` where X = K × 5.

## Wound check rendering

**Pre-audit** (Akodo 4th Dan example, already partially sourced):
```
⬛ Akodo 4th Dan: spends 1 VP on wound check, +5 per VP = +5 (46→51) → 🖤 Wound Check: 7k5 [...] → 51 vs TN 60 — failed
```

**Post-audit**:
```
⬛ Akodo 4th Dan: spends 1 VP on wound check, +5 per VP = +5 (46→51) → 🖤 Wound Check: 7k5 = 5k5 Water ring + 1k0 Akodo 1st Dan + 1k0 free raise (Akodo 2nd Dan) [...] → 51 vs TN 60 — failed
```

**Contract**:
- The WC XkY MUST be followed by `= <breakdown>` showing per-source contributions.
- Free raise (Akodo 2nd Dan) becomes a labeled source: `("free raise (Akodo 2nd Dan)", +1, +0)` because a free raise on WC adds +1 rolled (per the rule).

## Parry rendering

Similar shape to attack rendering — parry XkY with breakdown of ring + skill + school extras + floating bonuses.

## Iaijutsu duel rendering

Similar shape to attack rendering — iaijutsu XkY with breakdown.

## Floating bonus consumption rendering

**Pre-audit** (Akodo source already shown):
```
✨ +20 (Akodo 3rd Dan floating bonus consumed)
```

**Pre-audit** (untagged source, dry-run gap):
```
✨ +5 (floating bonus consumed)
```

**Post-audit**:
```
✨ +5 (floating bonus consumed, unsourced)
```

**Contract**:
- When the consumed bonus has a source, render with the source label.
- When it doesn't, render `(floating bonus consumed, unsourced)` — visible gap.

## Test contract

Tests assert against:
1. **Presence**: the breakdown parenthetical EXISTS for every aggregate that has multiple sources.
2. **Source labels**: each component's source label matches the rules-text intent (e.g., `"Akodo 1st Dan"` not just `"Akodo"`).
3. **Sum invariant**: `sum(rolled for _, rolled, _ in components) == aggregate_rolled`. Same for kept. (Asserted by parsing the breakdown string OR by directly inspecting `event._detail_components`.)
4. **Absence of bare aggregates**: in scenarios with multi-source contributions, the trace MUST NOT contain `XkY` without a following `= breakdown` (regex assertion).

## Out of contract (explicitly NOT required)

- Color formatting / emoji selection.
- Per-source line breaks (single-line rendering only).
- Localization of source labels.
- The cosmetic placement of the breakdown (e.g., immediately after XkY vs. before the dice list) — implementation may choose whichever fits the existing format best.
