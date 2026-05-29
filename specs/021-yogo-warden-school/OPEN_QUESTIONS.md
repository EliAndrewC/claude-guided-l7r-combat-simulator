# Open Questions & Pre-Resolutions — Yogo Warden School

**Status**: Autonomous audit run. Decisions pre-resolved during `/speckit-specify`.

The skeleton at `simulation/schools/yogo_school.py` (116 lines, 8 passing tests) is largely correct but has one BLOCKING per-VP scaling defect plus missing identity bindings. **User confirms 5th Dan is intentionally TBD — stub as no-op (must not raise).**

## Pre-resolutions

### Q1: Special Ability per-SW vs per-event TVP — MINOR

**Pre-resolution**: **Keep current.** Rules: "every time you take a serious wound" is ambiguous. Skeleton yields 1 TVP per `SeriousWoundsDamageEvent` regardless of `event.damage`. Per-event is the conservative reading and matches the existing test expectations.

### Q2: 3rd Dan per-VP vs per-event LW reduction — BLOCKING

**Pre-resolution**: **Fix.** Rules: "Whenever you spend a void point, reduce your current light wound total by 2X". Per VP, not per event. Skeleton applies the reduction once per spend_vp event regardless of `event.amount`. A 2-VP spend should reduce LW by `2 * 2X = 4X`, not `2X`.

**Fix**: multiply reduction by `event.amount` → `reduction = 2 * attack_skill * event.amount`.

### Q3: 5th Dan TBD — stub as no-op per user direction

**Pre-resolution**: Per user: "the Yogo Warden does not have a 5th Dan so that will need to be stubbed. But we shouldn't raise NotImplemented anywhere for it, since we want the school to function, just without sa 5th Dan for now." Skeleton already has `pass`. Keep.

### Q4: Identity binding missing — install `WoundCheckStrategy04`

**Pre-resolution**: **Install.** Yogo's identity is "be hit, gain TVP, spend VP aggressively, reduce LW + boost WC". `WoundCheckStrategy04` (0.4 threshold) encourages aggressive VP spending which compounds 3rd Dan's LW reduction + 4th Dan's +5/VP WC modifier. Hida/Shiba/Otaku/Shinjo/Daidoji/Kuni precedent.

### Q5: `YOGO_PRIORITIES` revision

**Pre-resolution**: **Defer** per pattern.

### Q6: Trace observability

**Pre-resolution**: Tag the 3rd Dan LW reduction for future renderer work.

## To be answered during implementation

### Q7: combat-simulator + win-feasibility

**Status**: Will validate during playability tests.

### Q8: school-strategy-designer's bindings — accepted verbatim?

**Status**: Run during plan dispatch.

## Deviations log (append during implementation)

(empty — to be populated batch-by-batch)
