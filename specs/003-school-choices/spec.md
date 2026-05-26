# Feature Specification: Configurable School Choices

**Feature Branch**: `003-school-choices`

**Created**: 2026-05-26

**Status**: Draft (autonomous run)

**Input**: User direction (2026-05-26): "Make 1st/2nd/3rd Dan choices and similar build-time school decisions overrideable in YAML, with hardcoded defaults preserved. Implement generically so any school can opt in."

**Rules Source**: `rules/04-schools.md` — multiple schools have rules-text clauses like "any two rolls of your choice", "any skill of your choice", "any non-Void Ring", etc. These are *build-time* player choices that the engine must honor per Constitution Principle III.

**Run Mode**: Autonomous. Decisions in `OPEN_QUESTIONS.md`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A character YAML can override 1st-Dan skill choices for an Isawa Ishi (Priority: P1)

A simulator user authoring a custom Isawa Ishi YAML can specify which two skills the character's 1st Dan extra die applies to (alongside the mandatory precepts), instead of the school's default `wound check` + `initiative`.

**Independent Test**: Load a YAML with `school_choices: {first_dan_extra_rolled: [parry, wound check]}` for an Isawa Ishi character. Assert `school.extra_rolled() == ["precepts", "parry", "wound check"]` (precepts is mandatory per rules text; the other two come from the choice).

### User Story 2 — A character YAML can override 2nd-Dan free-raise skill choice (Priority: P1)

The same YAML can specify `second_dan_free_raise: parry` to change which skill receives the 2nd Dan free raise. Defaults to `precepts` (Ishi) or `attack` (Ide) when absent.

**Independent Test**: Load a YAML with `school_choices: {second_dan_free_raise: parry}` for an Isawa Ishi. Assert `school.free_raise_skills() == ["parry"]`.

### User Story 3 — An Ide Diplomat YAML can override the school ring (Priority: P2)

Rules text says "School Ring: Any non-Void" for Ide. The YAML can specify `school_choices: {school_ring: fire}` to make this particular Ide a fire-based diplomat. Defaults to `water` when absent.

**Independent Test**: Load a YAML with `school_choices: {school_ring: air}` for an Ide. Assert `school.school_ring() == "air"`. Verify the Special Ability ring-raise (4th Dan) targets `air`, not `water`.

### Edge Cases

- YAML provides a choice for a school that doesn't recognize the key (e.g., `school_choices: {first_dan_extra_rolled: [...]}` for a Mirumoto). The choice is silently ignored — Mirumoto's `extra_rolled()` is hardcoded.
- YAML provides an invalid choice value (e.g., `school_ring: void` for Ide whose rules text forbids Void). The school's `set_choice` validation rejects with a clear error, OR the choice is silently coerced to default. **My decision (autonomous run)**: log a warning and use the default. Document in OPEN_QUESTIONS.md.
- YAML provides a choice with wrong-shape value (e.g., `first_dan_extra_rolled: "parry"` — a string instead of a list of 2). **My decision**: log a warning, fall back to default.
- Empty `school_choices: {}` → all defaults apply.
- Missing `school_choices` entirely → backward compatible, all defaults apply.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `CharacterConfig` MUST gain a new field `school_choices: dict[str, Any]` (default empty dict). The YAML loader MUST round-trip this field.
- **FR-002**: `BaseSchool` MUST expose `set_choice(key: str, value: Any) -> None` and `choice(key: str, default: Any = None) -> Any` methods. Choices are stored per-school-instance.
- **FR-003**: `web/adapters/character_adapter.py::config_to_character` MUST apply choices to the school instance via `school.set_choice(k, v)` BEFORE the school's `apply_*_ability` methods are called.
- **FR-004**: Schools with rules-text player choices MUST consult `self.choice(...)` in the appropriate methods (e.g., `extra_rolled`, `free_raise_skills`, `school_ring`) and fall back to the school's hardcoded default when the choice is absent.
- **FR-005**: The Isawa Ishi School MUST honor `first_dan_extra_rolled` (list of 2 skill names) and `second_dan_free_raise` (single skill name). Defaults: `["wound check", "initiative"]` and `"precepts"` respectively.
- **FR-006**: The Ide Diplomat School MUST honor `first_dan_extra_rolled` (list of 2), `second_dan_free_raise` (single skill), and `school_ring` (any non-Void: air, earth, fire, water). Defaults: `["wound check", "initiative"]`, `"attack"`, `"water"` respectively.
- **FR-007**: Invalid choices (wrong shape, void-as-school-ring-for-Ide, unknown skill names) MUST log a warning and use the default; they MUST NOT crash the build.
- **FR-008**: Schools that have NO player choices (e.g., Mirumoto, Akodo) MUST behave unchanged — backward compatible.
- **FR-009**: Documentation: the YAML schema must be documented in `CLAUDE.md` or equivalent so future school implementations know to use the mechanism.

## Assumptions

- The `school_choices` schema is per-school. Each school defines its own keys; there is no central registry.
- The "Any non-Void" constraint for Ide's school ring is enforced at choice-validation time, not at YAML-schema time.
- Defaults match the existing hardcoded values (no behavioral change for unspecified choices).
- Pattern B (school-ring/element choice) is mostly relevant for Ide (per the survey); Priest and Shugenja have similar patterns but are stub schools — defer to when they're properly implemented.

## Success Criteria

- **SC-001**: A YAML round-trips `school_choices` through `CharacterConfig` without losing data.
- **SC-002**: Existing 2864 tests continue to pass (backward compat).
- **SC-003**: New tests verify Pattern A (Ishi 1st/2nd Dan choices) and Pattern B (Ide school-ring choice) honor YAML overrides.
- **SC-004**: ruff PASS, mypy PASS, full pytest PASS.

## Out of scope

- Priest school's chosen ring (Priest is a stub — defer).
- Shugenja school's chosen element (Shugenja is a stub — defer).
- UI for editing `school_choices` in the Streamlit interface (engine-side feature only).
- Validation of skill names against a canonical skill registry (basic shape validation only).
