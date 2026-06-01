"""Tests for ``web.adapters.chronicle_renderer.ChronicleRenderer``.

Coverage targets every branch in ``ChronicleRenderer._dispatch`` plus
the helper functions (dice rendering, pill-class selection, the
generic fallback path).  Renders are smoke-checked: each test asserts
the output contains the chronicle CSS classes the theme expects.
"""

from __future__ import annotations

import unittest

from web.adapters.chronicle_renderer import (
    ChronicleRenderer,
    _esc,
    _phase_badge,
    _pill_class_for,
    _render_dice,
    _render_pills,
)
from web.adapters.trace_entries import (
    AttackEntry,
    ComponentDelta,
    CounterattackEntry,
    DamageProjection,
    DeathEntry,
    InitiativeEntry,
    LightWoundsDamageEntry,
    ModifierDelta,
    ParryEntry,
    RoundHeaderEntry,
    SeriousWoundsDamageEntry,
    SpendVpEntry,
    StatusBlockEntry,
    SurrenderEntry,
    UnconsciousEntry,
    WoundCheckEntry,
)


class TestHelpers(unittest.TestCase):
    def test_esc_basic(self) -> None:
        self.assertEqual("a&amp;b", _esc("a&b"))
        self.assertEqual("3", _esc(3))

    def test_phase_badge_strips_prefix(self) -> None:
        self.assertEqual("4", _phase_badge("Phase 4 |"))
        self.assertEqual("0", _phase_badge("Phase 0"))

    def test_pill_class_for(self) -> None:
        self.assertEqual("pill weapon", _pill_class_for("katana"))
        self.assertEqual("pill school", _pill_class_for("Akodo 1st Dan"))
        self.assertEqual("pill school", _pill_class_for("Bayushi Special Ability VP on attack"))
        self.assertEqual("pill school", _pill_class_for("Kuni school formula"))
        self.assertEqual("pill", _pill_class_for("Fire ring"))

    def test_render_dice_marks_kept_dropped_crit(self) -> None:
        # kept=3 of 5; first die is a 10 (crit), last two are dropped
        out = _render_dice([10, 8, 6, 4, 2], 3)
        self.assertIn('class="die crit"', out)  # the 10
        self.assertIn(">10<", out)
        self.assertIn('class="die dropped"', out)
        # 5 tiles total
        self.assertEqual(out.count("<span class="), 5)

    def test_render_dice_empty(self) -> None:
        self.assertEqual("", _render_dice([], 0))

    def test_render_pills_components_and_modifiers(self) -> None:
        comps = [
            ComponentDelta("katana", 4, 2),
            ComponentDelta("Fire ring", 5, 0),
            ComponentDelta("zero source", 0, 0),  # filtered
        ]
        mods = [
            ModifierDelta("Akodo 2nd Dan free raise", 5),
            ModifierDelta("zero mod", 0),  # filtered
            ModifierDelta("Some Debuff", -3),
        ]
        out = _render_pills(comps, mods)
        self.assertIn("pill weapon", out)
        self.assertIn("katana", out)
        self.assertIn("Fire ring", out)
        self.assertIn("pill school", out)
        self.assertIn("+5", out)
        self.assertIn("-3", out)
        self.assertNotIn("zero source", out)
        self.assertNotIn("zero mod", out)

    def test_render_pills_empty_returns_empty_string(self) -> None:
        self.assertEqual("", _render_pills(None, None))
        self.assertEqual("", _render_pills([], []))


class TestChronicleRender(unittest.TestCase):
    def setUp(self) -> None:
        self.r = ChronicleRenderer()

    def test_render_round_header(self) -> None:
        out = self.r.render([RoundHeaderEntry(round_number=2)])
        self.assertIn("chronicle-round-divider", out)
        self.assertIn("弐", out)  # 2 → 弐
        self.assertIn("Round 2", out)

    def test_round_header_falls_back_to_arabic_for_unmapped(self) -> None:
        out = self.r.render([RoundHeaderEntry(round_number=99)])
        self.assertIn("Round 99", out)
        self.assertIn(">99<", out)

    def test_render_status_block(self) -> None:
        entry = StatusBlockEntry(
            statuses={
                "Akodo": {"lw": 10, "sw": 1, "sw_threshold": 8,
                          "vp": 3, "vp_max": 4, "actions": [1, 2],
                          "crippled": False},
                "Kakita": {"lw": 0, "sw": 0, "sw_threshold": 10,
                           "vp": 4, "vp_max": 4, "actions": [],
                           "crippled": True},
            },
        )
        out = self.r.render([entry])
        self.assertIn("chronicle-evt-status", out)
        self.assertIn("Akodo", out)
        self.assertIn("Kakita", out)
        self.assertIn("crippled", out)  # CSS class on the crippled status

    def test_render_initiative(self) -> None:
        entry = InitiativeEntry(entries=[
            {"name": "Akodo", "rolled": 6, "kept": 5,
             "dice": [10, 8, 4, 4, 2, 1], "actions": [1, 2, 2, 4]},
        ])
        out = self.r.render([entry])
        self.assertIn("chronicle-evt-initiative", out)
        self.assertIn("Akodo", out)
        self.assertIn("6k5", out)
        self.assertIn("Actions", out)

    def _attack(self, **overrides: object) -> AttackEntry:
        base: dict[str, object] = {
            "phase_prefix": "Phase 1 |",
            "actor_name": "Akodo",
            "target_name": "Kakita",
            "skill": "attack",
            "vp_spent": 1,
            "vp_skill": "attack",
            "rolled": 10,
            "kept": 5,
            "modifier": 5,
            "components": [
                ComponentDelta("Fire ring", 4, 4),
                ComponentDelta("attack skill", 5, 0),
                ComponentDelta("Akodo 1st Dan", 1, 0),
            ],
            "modifier_components": [
                ModifierDelta("Akodo 2nd Dan free raise", 5),
            ],
            "dice": [10, 9, 8, 6, 5, 5, 3, 2, 1, 1],
            "sum_of_kept": 38,
            "total": 43,
            "tn": 30,
            "base_tn": 30,
            "outcome": "hit",
            "damage_projection": DamageProjection(
                rolled=10, kept=5, components=[
                    ComponentDelta("katana", 4, 2),
                    ComponentDelta("Fire ring", 4, 0),
                ],
                extra_damage_dice=5,
                margin_over_tn=13,
            ),
        }
        base.update(overrides)
        return AttackEntry(**base)  # type: ignore[arg-type]

    def test_render_attack_hit_marks_crit_when_high_extra_dice(self) -> None:
        out = self.r.render([self._attack()])
        self.assertIn("chronicle-evt crit", out)
        self.assertIn("HIT", out)
        self.assertIn("Akodo", out)
        self.assertIn("attacks", out)
        self.assertIn("⬛", out)  # vp square
        self.assertIn("pill school", out)  # Akodo 1st Dan etc.

    def test_render_attack_miss(self) -> None:
        out = self.r.render([self._attack(outcome="miss",
                                         damage_projection=None,
                                         vp_spent=None)])
        self.assertIn("MISS", out)
        self.assertNotIn("⬛", out)  # no vp clause

    def test_render_attack_low_extras_not_crit(self) -> None:
        out = self.r.render([self._attack(
            damage_projection=DamageProjection(
                rolled=4, kept=2, components=[
                    ComponentDelta("katana", 4, 2),
                ],
                extra_damage_dice=0,
                margin_over_tn=0,
            ),
        )])
        self.assertIn("chronicle-evt", out)
        # crit class is only applied for extras >= 4
        self.assertNotIn("chronicle-evt crit", out)

    def test_render_attack_suppresses_damage_projection(self) -> None:
        out = self.r.render([self._attack(suppress_damage_projection=True)])
        self.assertNotIn("damage will be", out)

    def test_render_counterattack(self) -> None:
        entry = CounterattackEntry(
            phase_prefix="Phase 3 |",
            actor_name="Hiruma",
            target_name="Akodo",
            vp_spent=None,
            vp_skill=None,
            rolled=9,
            kept=4,
            modifier=10,
            components=[ComponentDelta("Fire ring", 4, 4), ComponentDelta("counterattack skill", 5, 0)],
            modifier_components=[ModifierDelta("Hiruma 3rd Dan: post-parry bonus", 10)],
            dice=[9, 8, 6, 5, 5, 4, 3, 2, 1],
            sum_of_kept=28,
            total=38,
            tn=30,
            outcome="hit",
            damage_projection=None,
        )
        out = self.r.render([entry])
        self.assertIn("counter-attacks", out)
        self.assertIn("HIT", out)
        self.assertIn("Hiruma 3rd Dan: post-parry bonus", out)

    def test_render_parry(self) -> None:
        entry = ParryEntry(
            phase_prefix="Phase 2 |",
            actor_name="Shiba",
            target_name="Akodo",
            rolled=10, kept=8, modifier=5,
            components=[ComponentDelta("Air ring", 5, 5), ComponentDelta("parry skill", 5, 0)],
            modifier_components=[ModifierDelta("Shinjo 2nd Dan free raise", 5)],
            dice=[10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
            sum_of_kept=52, total=57, tn=50,
            outcome="succeeded",
        )
        out = self.r.render([entry])
        self.assertIn("SUCCEEDED", out)
        self.assertIn("parries", out)
        self.assertIn("Shiba", out)

    def test_render_parry_failed(self) -> None:
        entry = ParryEntry(
            phase_prefix="Phase 2 |",
            actor_name="Shiba",
            target_name="Akodo",
            rolled=10, kept=8, modifier=0,
            components=[], modifier_components=[],
            dice=[5, 4, 3, 2, 1, 1, 1, 1, 1, 1],
            sum_of_kept=23, total=23, tn=50,
            outcome="failed",
        )
        out = self.r.render([entry])
        self.assertIn("FAILED", out)

    def test_render_lw_damage(self) -> None:
        entry = LightWoundsDamageEntry(
            phase_prefix="Phase 1 |",
            attacker_name="Akodo",
            target_name="Kakita",
            rolled=10, kept=5,
            components=[ComponentDelta("katana", 4, 2), ComponentDelta("Fire ring", 4, 0)],
            dice=[12, 9, 8, 7, 5, 4, 3, 2, 1, 1],
            sum_of_kept=41,
            damage=41,
            lw_after=41,
        )
        out = self.r.render([entry])
        self.assertIn("💥 damage", out)
        self.assertIn("Kakita", out)
        self.assertIn("takes", out)
        self.assertIn("41 LW", out)
        self.assertIn("(total 41)", out)

    def test_render_lw_damage_without_lw_after(self) -> None:
        entry = LightWoundsDamageEntry(
            phase_prefix="Phase 1 |",
            attacker_name="Akodo",
            target_name="Kakita",
            rolled=0, kept=0,
            components=[],
            dice=[],
            sum_of_kept=0,
            damage=0,
            lw_after=None,
        )
        out = self.r.render([entry])
        self.assertNotIn("(total", out)

    def test_render_sw_damage(self) -> None:
        entry = SeriousWoundsDamageEntry(
            phase_prefix="Phase 1 |",
            target_name="Kakita",
            damage=2,
            from_double_attack=True,
        )
        out = self.r.render([entry])
        self.assertIn("2 serious wounds", out)
        self.assertIn("from double attack", out)

    def test_render_sw_damage_singular_no_da(self) -> None:
        entry = SeriousWoundsDamageEntry(
            phase_prefix="Phase 1 |",
            target_name="Kakita",
            damage=1,
            from_double_attack=False,
        )
        out = self.r.render([entry])
        self.assertIn("1 serious wound", out)
        self.assertNotIn("serious wounds", out)
        self.assertNotIn("from double attack", out)

    def _wc(self, **overrides: object) -> WoundCheckEntry:
        base: dict[str, object] = {
            "phase_prefix": "Phase 1 |",
            "character_name": "Akodo",
            "vp_spent": None,
            "vp_source": None,
            "vp_skill": None,
            "vp_breakdown": None,
            "rolled": 8, "kept": 6, "modifier": 5,
            "components": [],
            "modifier_components": [ModifierDelta("Akodo 2nd Dan free raise", 5)],
            "dice": [9, 8, 7, 6, 5, 4, 3, 2],
            "sum_of_kept": 39, "total": 44, "tn": 20,
            "outcome": "passed",
        }
        base.update(overrides)
        return WoundCheckEntry(**base)  # type: ignore[arg-type]

    def test_render_wound_check_passed(self) -> None:
        out = self.r.render([self._wc()])
        self.assertIn("PASSED", out)
        self.assertIn("wound check", out)
        self.assertIn("Akodo 2nd Dan free raise", out)

    def test_render_wound_check_failed_no_dice(self) -> None:
        out = self.r.render([self._wc(
            rolled=0, kept=0, modifier=0,
            modifier_components=[],
            dice=[], sum_of_kept=0, total=0,
            outcome="failed",
        )])
        self.assertIn("FAILED", out)

    def test_render_terminal_death(self) -> None:
        out = self.r.render([
            DeathEntry(phase_prefix="Phase 5 |", character_name="Akodo"),
        ])
        self.assertIn("Akodo", out)
        self.assertIn("chronicle-evt death", out)
        self.assertIn("falls", out)

    def test_render_terminal_unconscious(self) -> None:
        out = self.r.render([
            UnconsciousEntry(phase_prefix="Phase 5 |", character_name="Akodo"),
        ])
        self.assertIn("Akodo", out)
        self.assertIn("chronicle-evt fall", out)

    def test_render_terminal_surrender(self) -> None:
        out = self.r.render([
            SurrenderEntry(phase_prefix="Phase 5 |", character_name="Akodo"),
        ])
        self.assertIn("Akodo", out)
        self.assertIn("chronicle-evt fall", out)
        self.assertIn("surrenders", out)

    def test_render_generic_delegates_to_bulleted(self) -> None:
        # SpendVpEntry doesn't have a bespoke chronicle renderer →
        # delegates to BulletedRenderer and wraps each line in a
        # low-weight generic event row.  The exact text comes from
        # BulletedRenderer; here we just verify the wrapping and the
        # presence of the underlying spend signal.
        entry = SpendVpEntry(
            phase_prefix="Phase 1 |",
            character_name="Akodo",
            amount=2,
            skill="attack",
        )
        out = self.r.render([entry])
        self.assertIn("chronicle-evt-generic", out)
        self.assertIn("VP", out)
        self.assertIn("attack", out)

    def test_render_empty_list(self) -> None:
        self.assertEqual("", self.r.render([]))


if __name__ == "__main__":  # pragma: no cover  # test entry
    unittest.main()
