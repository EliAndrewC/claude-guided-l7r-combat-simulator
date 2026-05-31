"""Tests for the explain_modifier attribution branches added in the
2026-05-30 trace-reader cat#10 sweep — Kitsuki SA, Shinjo 2nd Dan
free raise, and the Hiruma 3rd Dan post-parry walk-through.

Constitution Principle VII coverage: each new attribution branch must
have a focused unit test so the labels remain pinned to the rules
text they're meant to surface (not silently regressed by future
refactors).
"""

from __future__ import annotations

import unittest
from typing import Any

from simulation.character import Character
from simulation.mechanics.modifiers import Modifier
from simulation.schools.hiruma_school import HirumaScoutSchool
from simulation.schools.kitsuki_school import KitsukiMagistrateSchool
from simulation.schools.shinjo_school import ShinjoBushiSchool
from web.adapters.modifier_breakdown import explain_modifier


def _fake_action(target: Any) -> Any:
    class _A:
        def target(self) -> Any:
            return target
    return _A()


class TestKitsukiSpecialAbilityAttribution(unittest.TestCase):
    def test_kitsuki_sa_attributed_on_attack(self) -> None:
        k = Character("Kitsuki")
        k.set_ring("water", 5)
        school = KitsukiMagistrateSchool()
        k.set_school(school)
        school.apply_special_ability(k)
        contribs = explain_modifier(k, "attack", 10)
        labels = [c[0] for c in contribs]
        self.assertTrue(
            any("Kitsuki Special Ability" in label for label in labels),
            f"expected Kitsuki SA attribution, got {labels}",
        )
        # Value should be 2 × water = 10.
        self.assertEqual(10, next(c[1] for c in contribs if "Kitsuki" in c[0]))

    def test_kitsuki_sa_not_attributed_on_non_attack(self) -> None:
        k = Character("Kitsuki")
        k.set_ring("water", 5)
        school = KitsukiMagistrateSchool()
        k.set_school(school)
        school.apply_special_ability(k)
        # Parry isn't in ATTACK_SKILLS for this attribution rule.
        contribs = explain_modifier(k, "parry", 10)
        self.assertEqual(
            [], [c for c in contribs if "Kitsuki" in c[0]],
        )

    def test_kitsuki_sa_zero_water_no_attribution(self) -> None:
        k = Character("Kitsuki")
        # water defaults to 2 (Character default), set explicitly to 0
        k.set_ring("water", 0)
        school = KitsukiMagistrateSchool()
        k.set_school(school)
        school.apply_special_ability(k)
        contribs = explain_modifier(k, "attack", 0)
        self.assertEqual(
            [], [c for c in contribs if "Kitsuki" in c[0]],
        )


class TestShinjoFreeRaiseAttribution(unittest.TestCase):
    def test_shinjo_2nd_dan_attributed_on_parry(self) -> None:
        s = Character("Shinjo")
        school = ShinjoBushiSchool()
        s.set_school(school)
        # Set school knack ranks so school_rank >= 2.
        for knack in school.school_knacks():
            s.set_skill(knack, 2)
        contribs = explain_modifier(s, "parry", 5)
        labels = [c[0] for c in contribs]
        self.assertIn("Shinjo 2nd Dan free raise", labels)
        self.assertEqual(
            5, next(c[1] for c in contribs if c[0] == "Shinjo 2nd Dan free raise"),
        )

    def test_shinjo_2nd_dan_not_attributed_on_attack(self) -> None:
        s = Character("Shinjo")
        school = ShinjoBushiSchool()
        s.set_school(school)
        for knack in school.school_knacks():
            s.set_skill(knack, 2)
        contribs = explain_modifier(s, "attack", 5)
        self.assertEqual(
            [], [c for c in contribs if "Shinjo" in c[0]],
        )


class TestHirumaThirdDanPostParryAttribution(unittest.TestCase):
    def test_hiruma_3rd_dan_modifier_attributed_on_attack(self) -> None:
        h = Character("Hiruma")
        school = HirumaScoutSchool()
        h.set_school(school)
        attacker = Character("Attacker")
        # Install a modifier tagged as Hiruma 3rd Dan targeting the attacker.
        modifier = Modifier(h, attacker, ["attack", "damage"], 10)
        modifier._hiruma_3rd_dan = True  # type: ignore[attr-defined]
        h.add_modifier(modifier)
        contribs = explain_modifier(
            h, "attack", 10, action=_fake_action(attacker),
        )
        labels = [c[0] for c in contribs]
        self.assertIn("Hiruma 3rd Dan: post-parry bonus", labels)

    def test_hiruma_3rd_dan_skipped_when_modifier_does_not_apply(self) -> None:
        h = Character("Hiruma")
        school = HirumaScoutSchool()
        h.set_school(school)
        attacker = Character("Attacker")
        other = Character("Other")
        # Modifier targets the attacker; action is against `other` → no apply.
        modifier = Modifier(h, attacker, ["attack", "damage"], 10)
        modifier._hiruma_3rd_dan = True  # type: ignore[attr-defined]
        h.add_modifier(modifier)
        contribs = explain_modifier(
            h, "attack", 0, action=_fake_action(other),
        )
        self.assertEqual(
            [], [c for c in contribs if "Hiruma" in c[0]],
        )

    def test_hiruma_3rd_dan_skipped_when_action_is_none(self) -> None:
        h = Character("Hiruma")
        school = HirumaScoutSchool()
        h.set_school(school)
        contribs = explain_modifier(h, "attack", 0, action=None)
        self.assertEqual(
            [], [c for c in contribs if "Hiruma" in c[0]],
        )

    def test_hiruma_3rd_dan_skips_non_3rd_dan_modifiers(self) -> None:
        """The Hiruma 3rd Dan attribution walks ``character._modifiers``
        looking for the ``_hiruma_3rd_dan`` tag and skips others —
        coverage for the ``continue`` branch when an unrelated modifier
        is present.
        """
        h = Character("Hiruma")
        school = HirumaScoutSchool()
        h.set_school(school)
        attacker = Character("Attacker")
        unrelated = Modifier(h, attacker, ["attack"], 5)
        # No _hiruma_3rd_dan tag → branch must `continue`.
        h.add_modifier(unrelated)
        contribs = explain_modifier(
            h, "attack", 5, action=_fake_action(attacker),
        )
        self.assertEqual(
            [], [c for c in contribs if "Hiruma" in c[0]],
        )


if __name__ == "__main__":  # pragma: no cover  # test entry
    unittest.main()
