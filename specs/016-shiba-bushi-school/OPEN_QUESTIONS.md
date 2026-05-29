# Open Questions & Pre-Resolutions — Shiba Bushi School

**Status**: Autonomous audit run. Decisions pre-resolved during `/speckit-specify`; logged here for end-of-run review.

The skeleton at `simulation/schools/shiba_school.py` (139 lines, 6 passing tests) is FUNCTIONALLY complete for the parry-damage + TN-margin mechanics but has the standard identity-strategy gap + a rolled-dice normalization issue.

## Pre-resolutions

### Q1: Special Ability — interrupt-parry never fires under defaults

**Pre-resolution**: **Fix.** `apply_special_ability` calls `set_interrupt_cost("parry", 1)` but does NOT call `add_interrupt_skill("parry")`. The `Character.has_interrupt_action("parry", context)` check (`character.py:340-344`) gates on `skill in self._interrupt_skills`, which is populated by `add_interrupt_skill`. So as wired, the interrupt-parry capability is structurally dead — the same Q1-shape bug as Kakita/Otaku.

**Why**: Identity-mandated mechanic that's structurally unreachable.

**Fix path**: Add `character.add_interrupt_skill("parry")` to `apply_special_ability`, AND install a `ShibaInterruptParryStrategy` that fires on `AttackDeclaredEvent` (when an attack is declared against the Shiba OR against an ally adjacent to the Shiba) and yields a parry-interrupt event.

### Q2: "Spending your lowest 1 action die"

**Pre-resolution**: **Implement explicitly in the new strategy.** Rules text says "spending your **lowest** 1 action die". The standard `BaseAttackStrategy._choose_action` interrupt branch picks the MAXIMUM die. For Shiba's interrupt-parry, the strategy MUST pick `min(actions)` instead.

**Why**: Verbatim rules text requirement; spending the lowest die is strictly less costly than spending the highest, so this is an upside for the Shiba that must be honored.

### Q3: 3rd Dan rolled-dice normalization

**Pre-resolution**: **Fix.** `ShibaTakeParryEvent._roll_damage` does `roll_provider.get_damage_roll(rolled, 1)` directly with `rolled = 2 * attack_skill`. For attack=6, that's a raw 12k1 roll — but the engine convention (`normalize_roll_params`) is that rolled > 10 converts excess to kept (so 12k1 → 10k3). A 5th-Dan Shiba (attack=5) → 10k1 stays unchanged; but combat-simulator may reveal cases where higher attack triggers the normalization mismatch.

**Why**: Rules-fidelity + engine-convention consistency. The rules text says "(2X)k1" but the engine's roll-normalization is a uniform invariant that all damage rolls obey.

**Fix**: Wrap the rolled/kept through `normalize_roll_params` before passing to `roll_provider.get_damage_roll`. Apply the resulting `(rolled, kept, bonus)` consistently (add `bonus` to the resulting roll).

### Q4: `SHIBA_PRIORITIES` revision

**Pre-resolution**: **Defer** like Bayushi/Kakita/Otaku.

Anti-identity observations:
- Counterattack leads at every Dan tier even though Shiba's IDENTITY is parry-damage (3rd Dan) + parry-TN-margin (5th Dan). Counterattack is a knack but not the engine.
- Earth promoted to Dan 3 (no Earth-keyed mechanics — likely template-copied).
- Parry at every Dan tier is correct (identity-aligned).
- School ring (Air) only appears in max-rings phase. Air is the school ring AND the 4th Dan discount target — should appear earlier.

Likely the school-progression-designer will produce a revision (parry-first, attack-second since 3rd Dan scales on attack, air-3 at Dan 3, counterattack capped at 3 or lower, earth removed).

### Q5: Trace observability gaps

**Pre-resolution**: Fix the most impactful via attribution tags + renderer paths (Kakita/Otaku precedent). Priority:
- **3rd Dan parry damage** (significant per-parry damage, currently silent — LW event emits but no source label).
- **5th Dan TN penalty modifier** (margin-driven TN reduction; currently the modifier emits an `AddModifierEvent` but no labeled cause).
- **Special Ability "parry-other no penalty"** (defensive maneuver vs ally; currently silent).

## To be answered during implementation

### Q6: combat-simulator finding on win-feasibility

**Status**: Run during `/speckit-implement` Batch B.

### Q7: school-strategy-designer's bindings — accepted verbatim?

**Status**: Run during plan dispatch.

### Q8: school-progression-designer's revision — accepted verbatim?

**Status**: Run during plan dispatch (likely deferred per Q4).

## Audit confirmations (post-Phase 2)

### NEW BLOCKING bug (not in original Q-list)

**ShibaParryAction.roll_parry is DEAD CODE.** `rules-auditor` discovered that the engine calls `action.roll_skill()` (`events.py:210`), not `roll_parry()`. The skeleton's override at `shiba_school.py:75-80` was named for the wrong method. Base `ParryAction.roll_skill` (`actions.py:327-336`) ALWAYS applies the `5 * attacker.skill("attack")` parry-other penalty. So the Special Ability "parry attacks directed at other characters with no penalty" is **structurally non-functional in real engine runs**. The existing `test_no_parry_other_penalty` masks the bug because it calls `roll_parry()` directly.

**Fix**: Rename `roll_parry` → `roll_skill` (or override `roll_skill` to suppress the penalty for Shibas).

### Q1 — REFUTED

`Character.__init__` at `character.py:73` initializes `_interrupt_skills = ["counterattack", "parry"]`. `parry` is already in the default list, so `has_interrupt_action("parry", context)` returns True with just `set_interrupt_cost("parry", 1)`. The Q1 fix path proposed in OPEN_QUESTIONS is unnecessary for skill registration. **But**: a custom interrupt STRATEGY is still required (engine default `DefaultInterruptStrategy` only delegates to `parry_strategy` on `AttackRolledEvent` and that delegates to `ReluctantParryStrategy` which gates on damage-estimation — under-firing for a school whose 3rd Dan deals damage on every parry attempt). `add_interrupt_skill("parry")` is harmless idempotent (line 216 dedupes).

### Q2 — CONFIRMED

Standard `BaseAttackStrategy.choose_action` interrupt branch picks `max(unspent)`. Rules-fidelity gap. Custom strategy must select `min(actions())`.

### Q3 — CONFIRMED

`ShibaTakeParryEvent._roll_damage` calls `roll_provider.get_damage_roll(rolled, 1)` directly with `rolled = 2 * skill("attack")`. For `attack >= 6` (rolled >= 12), `normalize_roll_params` is bypassed. Engine convention violated.

### Q4 — `SHIBA_PRIORITIES` revision

`school-progression-designer` produced a complete revision (parry-first / attack-second / counterattack capped at 3 / air-3 at Dan 3 / water-3 at Dan 3 / earth demoted / earth-4 removed). **DEFER** per Bayushi/Kakita/Otaku pattern.

### Q5 — Trace observability gaps

`trace-auditor` + `trace-reader` together identified P0 + P1 gaps:

- **P0**: 5th Dan `AddModifierEvent` is INVISIBLE in both renderers (no handler at all). The 5th Dan ability's effect is entirely silent.
- **P0**: 3rd Dan parry damage rendered as ordinary attack damage with no source attribution. Worse — fires on FAILED parries (rules-correct) without any explanation, leaving readers thinking the rendering is broken.
- **P0**: Subsequent attack TN against parried opponent doesn't surface the 5th Dan penalty in the breakdown.
- **P1**: Parry 2nd Dan free raise labeled `(see preceding line)` where preceding line is the attacker's attack (wrong source).
- **P1**: "reconciliation" leak in parry-damage breakdown (code-internal term, not Shiba-specific).

## Deviations log (append during implementation)

(empty — to be populated batch-by-batch)
