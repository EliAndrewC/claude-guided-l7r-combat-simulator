# TraceEntry Contracts

This file documents the byte-identical-text contracts each TraceEntry type must honor when rendered by `TextRenderer`. The contracts are the regression specification for FR-009 / FR-011 / US2.

For each entry type, the contract is: **given this entry, `TextRenderer` produces this exact text** (which equals the pre-refactor `_format_*` method's output for the corresponding event).

## RoundHeaderEntry

Input:
- `round_number: 3`

Output (one line):
```
═══ Round 3 ═══
```

## PhaseHeaderEntry

Embedded into the action-line prefix; not its own line in current output. Implementation: the formatter emits `Phase N | <actor> | ...` and `TextRenderer` reproduces this.

## StatusBlockEntry

Multi-line. Example:
```
  ─────
  Akodo:  Light 0 | Serious 0/6 | Void 3/3 | Actions: [1, 2, 2, 8]
  Bayushi:  Light 0 | Serious 0/8 | Void 3/3 | Actions: [1, 2, 2]
  ─────
```

## InitiativeEntry

One line. Example:
```
  Akodo: 5k4 rolled [**1**, **2**, **2**, **8**, ~~10~~] → Actions: [1, 2, 2, 8]
```

## AttackEntry (composite)

The most complex entry. Up to three sub-segments rendered on ONE line:

1. VP-spend prefix (if `vp_spent`): `⬛⬛ spends 2 VP on double attack → `
2. Action declaration: `⚔️ attacks Akodo (double attack)`
3. Roll segment: ` — 10k10 = 5k5 Fire ring + ... [dice] → 57, +5 (source) = 62 vs TN 50 (base TN 30, +20 from 4 raises for double attack) — HIT! (+12 over TN, 2 extra damage dice, damage will be 10k7 = ...)`

Full example (from calibration combat):
```
Phase 2 | Bayushi | ⬛⬛ spends 2 VP on double attack → ⚔️ attacks Akodo (double attack) — 10k10 = 5k5 Fire ring + 5k0 double attack skill + 1k0 Bayushi 1st Dan + 2k2 VP on double attack + -3k3 normalization [...] → 57, +5 (Bayushi 2nd Dan free raise: +5) = 62 vs TN 50 (base TN 30, +20 from 4 raises for double attack) — HIT! (+12 over TN, 2 extra damage dice, damage will be 10k7 = 4k2 katana + 5k0 Fire ring + 2k0 margin (+10 over TN) + 2k2 VP on attack + -3k3 normalization)
```

The contract: TextRenderer's per-AttackEntry output equals this exactly.

## CounterattackEntry, ParryEntry, IaijutsuEntry

Same composite structure as AttackEntry minus the damage-projection segment (counterattack/parry don't have a "damage will be" projection on the same line).

## LightWoundsDamageEntry

```
Bayushi | 💥 Damage: 10k7 = 4k2 katana + ... [dice] → 60 → Akodo takes 60 light wounds (total: 60)
```

## WoundCheckEntry

```
Akodo | ⬛ Akodo 4th Dan: spends 1 VP on wound check, +5 per VP = +5 (46→51) → 🖤 Wound Check: 9k7 = 5k5 Water ring + ... [dice] → 41, +10 (...) = 51 vs TN 60 — FAILED
```

## SpendVpEntry (standalone — when not composed)

```
Bayushi | ⬛⬛ spends 2 VP on double attack
```

## GainTvpEntry

```
Bayushi | ✨ Akodo Special Ability: +4 TVP on successful feint
```

## GainFloatingBonusEntry

```
Akodo | ✨ Akodo 3rd Dan: gained floating bonus +15 (margin 18 ÷ 5 × attack 5)
```

## SpendFloatingBonusEntry

```
Akodo | ✨ +15 (Akodo 3rd Dan floating bonus consumed)
```

## SchoolNegatedEntry

```
Ishi | ❌ Ishi's school is negated (4 VP — Isawa Ishi 5th Dan)
```

## AkodoFifthDanCounterEntry

```
Akodo | ⬛⬛⬛ Akodo 5th Dan: spends 3 VP on counter-damage, 10 LW × 3 = 30 LW dealt to Bayushi
```

## KeepLightWoundsEntry / TakeSeriousWoundEntry

Per the existing `_format_keep_lw` / `_format_take_sw` outputs.

## BulletedRenderer contracts

For the bulleted form, contracts are less rigid (no byte-identical invariant) but per-entry:

- Multi-source aggregates produce a header line + bulleted breakdown + dice line.
- Single-source aggregates produce one line (no bullets).
- TN with raises → `vs TN N (base TN M + K raises × +5 for {action})` on the header line.
- Damage projection (in `AttackEntry.damage_projection`) renders as a nested bulleted group under the attack header.
- Markdown bullets use `- ` (hyphen + space) consistently.

Pseudo-template for an `AttackEntry` with > 1 component:
```markdown
**Phase N | Actor ⚔️ attacks Target (skill)** — `XkY + M` → ROLL vs TN N (...) — OUTCOME

- Attack roll: XkY
  - `+rolled k +kept` source1
  - `+rolled k +kept` source2
  - ...
- Modifier: +M (source1: +X, source2: +Y, ...)
- Dice: [d1, d2, ..., dN]
- TN: N (base M + K raises × +5 for action)
- Damage will be: XkY
  - `+rolled k +kept` source1
  - ...
```

Exact format pins down during implementation.
