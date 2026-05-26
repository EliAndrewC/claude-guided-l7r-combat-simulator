# Open Questions for End-of-Run Review (school-choices)

This document accumulates deferred decisions for the school-choices autonomous run. Run started 2026-05-26 on `003-school-choices`.

## Q1 — Validation policy: warn-and-fallback or hard-error?

**What I decided**: Warn and fall back to default. Specifically:
- Wrong-shape values (e.g., string when list expected) → log warning, use default.
- Invalid values (e.g., `school_ring: void` for Ide) → log warning, use default.
- Unknown keys (school doesn't recognize the choice) → silently ignore.

**Why**: Hard-erroring on misconfiguration breaks downstream tooling that might construct configs programmatically. Warn-and-fallback is more robust and matches Python's "easier to ask forgiveness" idiom; the warning ensures visibility.

**Alternatives**: Raise `ValueError` on invalid values (cleaner failure mode for tooling that wants to catch). Could be added later as an option.

**Where**: `BaseSchool.set_choice` validation hooks.

## Q2 — How do individual schools declare their accepted choice keys?

**What I decided**: No formal registry. Each school overrides the methods it has choices for (e.g., `extra_rolled`, `school_ring`) and reads `self.choice(...)` with a default. The school's docstring documents the keys it accepts.

**Why**: Adding a formal `accepted_choices_schema` registry would be over-engineering for the current 2 schools that use this. If the count grows beyond ~5, revisit and add a registry.

**Alternatives**: Each school exposes a `choices_schema()` method returning dict of (key → type/validator). Could be added without breaking existing code if needed later.

## Q3 — What's the canonical key naming scheme?

**What I decided**: snake_case, descriptive, per-rank prefix where applicable:
- `first_dan_extra_rolled` — list of 2 skill names (precepts is implicitly prepended by the school)
- `second_dan_free_raise` — single skill name
- `school_ring` — single ring name (school-level, no per-rank prefix)

**Why**: Self-documenting; the `first_dan_*` / `second_dan_*` prefix makes it clear at the YAML level which ability the choice affects.

**Alternatives**: Use rules-text-flavored names (e.g., `first_dan_choices`). Both are reasonable; I picked the more descriptive form.

## Q4 — How does Ishi's 1st Dan handle the precepts-is-mandatory rule?

**Rules text**: "Roll one extra die on **precepts** and any two types of rolls of your choice."

**What I decided**: `first_dan_extra_rolled` choice value is just the 2 choice-skills. The school's `extra_rolled()` method prepends `"precepts"` automatically. So:
- YAML `first_dan_extra_rolled: [parry, wound check]` → `extra_rolled() == ["precepts", "parry", "wound check"]`.

**Why**: Precepts is mandatory; making it part of the choice value would be redundant and let users accidentally exclude it.

**Where**: `IsawaIshiSchool.extra_rolled` reads `self.choice("first_dan_extra_rolled", ["wound check", "initiative"])` and returns `["precepts"] + list(choice)`.

## Scope-creep findings

(Populated during the run.)
