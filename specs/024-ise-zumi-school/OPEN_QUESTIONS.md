# Open Questions & Pre-Resolutions — Togashi Ise Zumi School

**Status**: Autonomous audit run.

The skeleton at `simulation/schools/ise_zumi_school.py` (103 lines, 17 passing tests) has one BLOCKING rules-fidelity bug (1st Dan skill list) plus the standard "any Ring" / `school_choices` gap.

## Pre-resolutions

### Q1: Special Ability 1-or-3 choice — MEDIUM DEFERRED

**Pre-resolution**: **Document and defer.** Rules: "Roll either 1 or 3 extra action dice". Skeleton always rolls 1. The choice depends on whether the Ise Zumi commits ALL dice to athletics (3-mode) or just some (1-mode). Without combat athletics actions, the choice is meaningless. Defer with current always-1 behavior.

### Q2: Athletics-only restriction on extra dice — MEDIUM DEFERRED

**Pre-resolution**: **Document and defer.** Rules: extra dice "may only be spent on athletics actions". Skeleton doesn't restrict — extra die can be used for attacks. In a simulator with no combat athletics actions, restricting would create dead dice. Defer with current unrestricted behavior. Note: this makes the Ise Zumi slightly over-powered vs rules.

### Q3: 1st Dan WRONG extra_rolled list — BLOCKING

**Pre-resolution**: **Fix.** Rules: "Roll one extra die on **athletics, initiative, and wound checks**". Skeleton returns `["attack", "parry", "athletics"]` — neither attack nor parry are in the rules clause; initiative and wound check are missing. Substantive rules-fidelity bug.

### Q4: 4th Dan "any Ring" choice — MEDIUM

**Pre-resolution**: **Fix.** Rules: "Raise the current and maximum rank of **any Ring** by 1". Skeleton hardcoded to "void". Apply Monk/Ide school_choices precedent — read `school_choices["school_ring"]`, default to "void", validate against any ring including Void (4th Dan permits Void per rules text "any Ring").

### Q5: 4th Dan contested-roll reroll — MINOR DEFERRED

**Pre-resolution**: **Defer.** Skeleton comment says "social ability, not applicable in combat simulation". True for most cases; contested iaijutsu duels exist but rarely.

### Q6: 5th Dan "at any time" — MEDIUM DEFERRED

**Pre-resolution**: **Document and defer.** Rules: "At any time, you may spend 1 void point to heal 2 serious wounds." Skeleton restricts to post-WC-failure. Proactive heal-strategy is a follow-up.

### Q7: `ISE_ZUMI_PRIORITIES` revision

**Pre-resolution**: **Defer** per pattern.

## To be answered during implementation

### Q8: combat-simulator + win-feasibility

**Status**: Will validate during playability tests.

## Deviations log (append during implementation)

(empty)
