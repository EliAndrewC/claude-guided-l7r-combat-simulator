# Phase 0 Research: Hida Bushi School

## Codebase audit findings (2026-05-28)

### Counterattack-roll-bonus mechanism (Hida Special Ability, already correct)

`simulation/events.py:152` already applies pending counterattack roll bonuses:

```python
def _roll_attack(self, context: Any) -> Iterator["Event"]:
    attack_roll = self.action.roll_skill()
    # Apply any pending counterattack roll bonus (e.g. Hida school +5)
    bonus = getattr(self.action, '_counterattack_roll_bonus', 0)
    if bonus:
        attack_roll += bonus
        self.action.set_skill_roll(attack_roll)
    ...
```

This is the mechanism `HidaTakeCounterattackActionEvent` (in `hida_school.py:63`) writes to. The +5 free raise to the attacker is wired correctly already. **The Hida special ability is fully implemented at the engine level.**

The trace-attribution side may still need updating per FR-002 (Principle VII: source the +5 as "Hida special ability: free raise (+5) for 1-die interrupt counterattack" in the user-visible trace).

### Wound condition: `crippled()`, not `impaired()`

`simulation/character.py:267`:

```python
def crippled(self) -> bool:
    return self.sw() >= self.ring("earth")
```

The engine has **one** wound-condition predicate: `crippled()` (SW ≥ earth ring). The L7R rules text for Hida 3rd Dan uses the term "impaired". These should be treated as synonymous in this simulator (the project doesn't model a separate "Impaired" condition between healthy and crippled).

**Decision**: For Hida 3rd Dan, "impaired" = `character.crippled()`. If future rules text requires a finer-grained wound condition, that's an engine extension separate from Hida.

**Rationale**: L7R's "impaired" and "crippled" are typically used interchangeably for "SW threshold reached"; this simulator's `crippled()` matches the threshold.

### Roll provider architecture

`simulation/mechanics/roll_provider.py:16` defines `RollProvider` (ABC), `:46` defines `DefaultRollProvider`, `:129` defines `CalvinistRollProvider` (deterministic test provider). School-specific providers exist (KakitaRollProvider, MerchantRollProvider, MatsuRollProvider, etc.).

The existing provider methods support: parameter normalization, modifier addition, breakdown attribution. For 3rd Dan reroll, the right hook is likely in the roll resolution itself — after the initial dice are rolled, before kept dice are selected, intercept and selectively reroll up to N lowest dice.

**Decision**: Implement 3rd Dan reroll as either:
- (a) a `HidaRollProvider(DefaultRollProvider)` subclass that overrides roll resolution to apply the reroll-N-lowest logic when the skill is "counterattack" or "attack" / "double attack" / "iaijutsu" (i.e., not feint, parry, or wound check).
- (b) A roll-extension hook in `simulation/mechanics/` consumed by all providers when the character has 3rd-Dan-Hida-tagged extra dice.

**Pre-resolution**: Start with (a) for simplicity — Hida-specific provider. Refactor to (b) only if the codebase has comparable patterns for other schools (Merchant uses (a)-style; that's the precedent).

### iaijutsu duel engine

`simulation/duel.py` has the iaijutsu duel implementation. Key events:
- `IaijutsuFocusEvent` (line 78)
- `IaijutsuStrikeEvent` (line 88)
- `DuelStrikeRolledEvent` (line 98)
- `DuelStrikeAction` (line 126)
- `DuelState` (line 205)

The "iaijutsu phase" the Hida 4th Dan rule mentions corresponds to the focus + strike phase of the duel. There is no `context.in_iaijutsu_phase()` accessor as of the audit; the context's `phase()` returns the combat phase (1-10), not the duel phase.

**Decision**: Add a `context.in_iaijutsu_phase() -> bool` method on the context object that returns True between `DuelInitiativeRolledEvent` and `DuelEndedEvent` for THIS character. The duel engine sets/clears this flag at the duel boundary events.

**Pre-resolution**: Implementer may choose between (a) extending the existing context object with a duel-tracking field, (b) introducing a separate `DuelContext` subclass that the duel engine installs while a duel is active.

### Wound check strategy hierarchy

`simulation/strategies/base.py:673` defines `WoundCheckStrategy`. Subclasses:
- `WoundCheckStrategy02` (line 695)
- `WoundCheckStrategy04` (line 707)
- `WoundCheckStrategy05` (line 701)
- `WoundCheckStrategy08` (line 713)
- `StingyWoundCheckStrategy` (line 719)

These subclasses tune the "tolerable SW" threshold for spending floating bonuses/AP/VP/conviction. For Hida 4th Dan, the right extension is a subclass that ALSO considers the 2-SW-for-LW-reset trade as an alternative outcome BEFORE deciding to roll.

**Decision**: Subclass `WoundCheckStrategy` to add the trade decision. The trade requires (i) LW > 0, (ii) SW + 2 ≤ max_SW, (iii) NOT in iaijutsu phase. If all conditions met AND `tolerable_sw < 2` (rolling is risky), take the trade.

### CounterattackInterruptStrategy and post-damage timing

`simulation/strategies/base.py:743` defines `CounterattackInterruptStrategy`. Current behavior: decides at interrupt-decision time (BEFORE the attack roll resolves, so well before damage).

For Hida 5th Dan post-damage timing, the existing strategy must be replaced by a `HidaCounterattackInterruptStrategy` that:
1. Skips the immediate pre-damage interrupt decision (defers).
2. Reserves an action die (or pre-spends, depending on engine constraint).
3. After the damage roll resolves and damage is applied, decides whether to fire the counterattack.

**Decision**: The cleanest implementation is to add a new event slot in the attack flow — after `LightWoundsDamageEvent` resolves (LW added + WC fires + SW potentially inflicted), before the next phase event, the engine asks the defender "do you wish to fire a deferred counterattack now?". This event is consulted only by `HidaCounterattackInterruptStrategy`-bound characters with available action dice.

**Pre-resolution**: Implementer may choose between (a) modifying the engine's attack-flow to include this slot for all characters (no-op for non-Hida), or (b) installing a listener on the Hida character that handles the post-damage event. (b) is more in line with the existing listener architecture but requires more event-routing setup.

### Counterattack-excess margin storage

The Hida 5th Dan's "add X to wound check" mechanism mirrors the existing `_counterattack_roll_bonus` pattern. Decision: store the counterattack excess margin on the originating attack action as `_counterattack_excess_margin`. The WC roll consults this attribute when resolving on damage from THAT attack.

**Decision**: Use `getattr(action, '_counterattack_excess_margin', 0)` pattern, symmetric with the existing roll-bonus pattern at events.py:152.

### Roll-extension precedent

`simulation/professions.py:472` has the WaveMan reroll pattern (reroll 10s when crippled, up to a cap). The Merchant 5th Dan `_find_dice_to_reroll` algorithm is at `simulation/schools/merchant_school.py:188`. Both are precedents for the Hida 3rd Dan reroll implementation.

**Decision**: Reuse the Merchant `_find_dice_to_reroll` algorithm as a starting point for the dice-selection logic. The Hida-specific difference is the N cap (2X or X) and the "reroll 10s even when impaired" override.

## Outstanding questions for clarification (none — all pre-resolved per spec)

The spec's Clarifications section pre-resolves all 7 ambiguities surfaced during specification. No further questions need to be raised in this Phase 0.

## Decision summary

| Decision | Approach |
|----------|----------|
| 3rd Dan reroll provider | New `HidaRollProvider(DefaultRollProvider)` subclass |
| 3rd Dan dice selector | Reuse Merchant `_find_dice_to_reroll` algorithm with N cap |
| 3rd Dan impaired = crippled | YES — engine has no separate impaired condition |
| 4th Dan WC strategy | New `HidaWoundCheckStrategy(WoundCheckStrategy)` subclass |
| 4th Dan SW-for-LW event | New `HidaSWForLWTradeEvent` (NOT a wound-check event) |
| 4th Dan iaijutsu guard | New `context.in_iaijutsu_phase()` accessor; duel engine sets/clears |
| 5th Dan post-damage interrupt | New event slot AFTER LightWoundsDamageEvent; new `HidaCounterattackInterruptStrategy` subclass |
| 5th Dan WC bonus storage | `_counterattack_excess_margin` attribute on attack action, mirroring existing roll-bonus pattern |
| 5th Dan stacking limit | Outermost-only (pre-resolution Q11) |
| Knack list fix | Apply to all 3 sites: hida_school.py, generator.py:35, HIDA_PRIORITIES |
| Strategy bindings | school-strategy-designer agent proposal |
| XP progression | school-progression-designer agent proposal |
