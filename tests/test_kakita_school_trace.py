#!/usr/bin/env python3

#
# test_kakita_school_trace.py
#
# Principle VII trace assertions for the Kakita Duelist School.
# Added 2026-05-29 per spec branch 014 trace-auditor + trace-reader
# audits.
#
# rules/04-schools.md "Kakita Duelist School" + Constitution Principle VII.
#

import unittest
from typing import Any
from unittest.mock import MagicMock


def _make_kakita_at_rank(rank: int) -> Any:
    """Build a Kakita character at the given school rank (= the
    minimum of its three knack skills).  Used by trace-attribution
    tests that need `school_rank()` to return a specific value
    without mocking the school's `school_knacks()` iterator.
    """
    from simulation.character import Character
    from simulation.schools.kakita_school import KakitaBushiSchool
    character = Character("Kakita")
    character.set_school(KakitaBushiSchool())
    character.set_skill("double attack", rank)
    character.set_skill("iaijutsu", rank)
    character.set_skill("lunge", rank)
    return character


class TestKakita2ndDanFreeRaiseTraceAttribution(unittest.TestCase):
    """rules/04-schools.md "Kakita Duelist School: Second Dan":
    "You get a free raise on all iaijutsu rolls."  Per Principle VII
    (trace-auditor + trace-reader fix 2026-05-29), the +5 modifier on
    iaijutsu rolls MUST surface with explicit "Kakita 2nd Dan free
    raise" source attribution in the modifier breakdown.
    """

    def test_iaijutsu_modifier_has_kakita_2nd_dan_attribution(self) -> None:
        from web.adapters.modifier_breakdown import explain_modifier
        character = _make_kakita_at_rank(2)
        contributions = explain_modifier(
            character, "iaijutsu", modifier=5, vp=0, action=None,
        )
        labels = [label for (label, _) in contributions]
        self.assertIn(
            "Kakita 2nd Dan free raise", labels,
            f"Iaijutsu modifier must surface 'Kakita 2nd Dan free "
            f"raise' attribution; got labels: {labels}",
        )

    def test_non_iaijutsu_modifier_does_not_get_2nd_dan_attribution(self) -> None:
        """The 2nd Dan free raise applies ONLY to iaijutsu rolls — a
        Kakita's plain attack modifier MUST NOT get the attribution."""
        from web.adapters.modifier_breakdown import explain_modifier
        character = _make_kakita_at_rank(2)
        contributions = explain_modifier(
            character, "attack", modifier=5, vp=0, action=None,
        )
        labels = [label for (label, _) in contributions]
        self.assertNotIn("Kakita 2nd Dan free raise", labels)

    def test_pre_2nd_dan_kakita_does_not_get_attribution(self) -> None:
        """A Kakita below 2nd Dan does NOT get the free raise."""
        from web.adapters.modifier_breakdown import explain_modifier
        character = _make_kakita_at_rank(1)
        contributions = explain_modifier(
            character, "iaijutsu", modifier=0, vp=0, action=None,
        )
        labels = [label for (label, _) in contributions]
        self.assertNotIn("Kakita 2nd Dan free raise", labels)


class TestKakita3rdDanTempoBonusTraceAttribution(unittest.TestCase):
    """rules/04-schools.md "Kakita Duelist School: Third Dan":
    "Your attacks get a bonus of X for each phase before the
    defender's next action they occur, where X is equal to your
    attack skill."  Per Principle VII (trace-auditor P0 + trace-
    reader Wrong #1 fix 2026-05-29), the bonus MUST surface with
    explicit "Kakita 3rd Dan tempo bonus (attack X × Y phases)"
    attribution in the modifier breakdown — NOT as a bare unsourced
    +N modifier.
    """

    def test_tempo_bonus_surfaces_with_explicit_source_label(self) -> None:
        from web.adapters.modifier_breakdown import explain_modifier
        character = _make_kakita_at_rank(5)
        # Synthesize an action tagged with the 3rd Dan tempo bonus.
        # The tag format is ``(tempo_bonus, tempo_diff, attack_skill)``.
        action = MagicMock()
        action._kakita_3rd_dan_tempo = (35, 7, 5)  # attack 5 × 7 phases = 35
        contributions = explain_modifier(
            character, "attack", modifier=35, vp=0, action=action,
        )
        labels = [label for (label, _) in contributions]
        self.assertTrue(
            any("Kakita 3rd Dan tempo bonus" in label for label in labels),
            f"Tempo bonus must surface with explicit attribution; "
            f"got labels: {labels}",
        )
        # The numeric breakdown (attack 5 × 7 phases) MUST appear so a
        # reader can reconstruct the formula.
        kakita_labels = [
            label for label in labels
            if "Kakita 3rd Dan tempo bonus" in label
        ]
        self.assertEqual(1, len(kakita_labels))
        self.assertIn("attack 5", kakita_labels[0])
        self.assertIn("7 phases", kakita_labels[0])

    def test_zero_tempo_bonus_does_not_surface_attribution(self) -> None:
        """A 0 tempo bonus (e.g., subject and target acting in same
        phase) MUST NOT surface the attribution."""
        from web.adapters.modifier_breakdown import explain_modifier
        character = _make_kakita_at_rank(5)
        action = MagicMock()
        action._kakita_3rd_dan_tempo = (0, 0, 5)
        contributions = explain_modifier(
            character, "attack", modifier=0, vp=0, action=action,
        )
        labels = [label for (label, _) in contributions]
        self.assertFalse(
            any("Kakita 3rd Dan tempo bonus" in label for label in labels),
        )

    def test_no_action_does_not_surface_attribution(self) -> None:
        """When no action is supplied to ``explain_modifier``, the
        tempo bonus cannot be computed and MUST NOT surface."""
        from web.adapters.modifier_breakdown import explain_modifier
        character = _make_kakita_at_rank(5)
        contributions = explain_modifier(
            character, "attack", modifier=0, vp=0, action=None,
        )
        labels = [label for (label, _) in contributions]
        self.assertFalse(
            any("Kakita 3rd Dan tempo bonus" in label for label in labels),
        )

    def test_pre_3rd_dan_kakita_does_not_surface_tempo_attribution(self) -> None:
        """A Kakita below 3rd Dan does NOT get the tempo bonus."""
        from web.adapters.modifier_breakdown import explain_modifier
        character = _make_kakita_at_rank(2)
        action = MagicMock()
        action._kakita_3rd_dan_tempo = (35, 7, 5)
        contributions = explain_modifier(
            character, "attack", modifier=0, vp=0, action=action,
        )
        labels = [label for (label, _) in contributions]
        self.assertFalse(
            any("Kakita 3rd Dan tempo bonus" in label for label in labels),
        )

    def test_malformed_tempo_tag_does_not_crash(self) -> None:
        """If the action's `_kakita_3rd_dan_tempo` tag is malformed
        (wrong shape, non-int values), the attribution clause MUST
        gracefully skip rather than crashing."""
        from web.adapters.modifier_breakdown import explain_modifier
        character = _make_kakita_at_rank(5)
        action = MagicMock()
        # Wrong shape (2-tuple instead of 3-tuple).
        action._kakita_3rd_dan_tempo = (5, 1)
        contributions = explain_modifier(
            character, "attack", modifier=0, vp=0, action=action,
        )
        # Doesn't surface but also doesn't crash.
        labels = [label for (label, _) in contributions]
        self.assertFalse(
            any("Kakita 3rd Dan tempo bonus" in label for label in labels),
        )

    def test_non_int_tempo_tag_values_are_ignored(self) -> None:
        """If the action's tag has non-int values, the attribution
        clause MUST gracefully skip."""
        from web.adapters.modifier_breakdown import explain_modifier
        character = _make_kakita_at_rank(5)
        action = MagicMock()
        action._kakita_3rd_dan_tempo = ("hi", 1, 5)  # str instead of int
        contributions = explain_modifier(
            character, "attack", modifier=0, vp=0, action=action,
        )
        labels = [label for (label, _) in contributions]
        self.assertFalse(
            any("Kakita 3rd Dan tempo bonus" in label for label in labels),
        )


class TestKakitaTempoBonusTaggedOnAction(unittest.TestCase):
    """Regression guard: the Kakita action classes (`KakitaAttackAction`,
    `KakitaDoubleAttackAction`, `KakitaLungeAction`) MUST tag the
    action with `_kakita_3rd_dan_tempo` so the trace formatter can
    surface the bonus per Principle VII.
    """

    def _build_setup(self, *, subject_phase: int = 1, target_actions: list[int] | None = None):
        """Build a Kakita + target + context with controllable phase
        and target actions."""
        from simulation.character import Character
        from simulation.context import EngineContext
        from simulation.groups import Group
        from simulation.mechanics.initiative_actions import InitiativeAction
        if target_actions is None:
            target_actions = [8]
        kakita = Character("Kakita")
        kakita.set_skill("attack", 5)
        kakita.set_skill("iaijutsu", 5)
        kakita.set_skill("double attack", 5)
        kakita.set_skill("lunge", 5)
        target = Character("Target")
        target.set_actions(target_actions)
        groups = [Group("Crane", kakita), Group("Target", target)]
        context = EngineContext(groups, phase=subject_phase)
        context.initialize()
        initiative_action = InitiativeAction([subject_phase], subject_phase)
        return kakita, target, context, initiative_action

    def test_kakita_attack_action_tags_tempo_bonus(self) -> None:
        from simulation.schools.kakita_school import KakitaAttackAction
        kakita, target, context, ia = self._build_setup(
            subject_phase=1, target_actions=[8],
        )
        action = KakitaAttackAction(
            kakita, target, "attack", ia, context,
        )
        # Trigger the skill_roll_params computation.
        action.skill_roll_params()
        # Verify the tag is set.
        tempo_tag = getattr(action, "_kakita_3rd_dan_tempo", None)
        self.assertIsNotNone(tempo_tag)
        assert tempo_tag is not None
        tempo_bonus, tempo_diff, attack_skill = tempo_tag
        # Subject phase 1, target phase 8 → diff 7, attack 5 → bonus 35.
        self.assertEqual(35, tempo_bonus)
        self.assertEqual(7, tempo_diff)
        self.assertEqual(5, attack_skill)

    def test_kakita_double_attack_action_tags_tempo_bonus(self) -> None:
        from simulation.schools.kakita_school import KakitaDoubleAttackAction
        kakita, target, context, ia = self._build_setup(
            subject_phase=3, target_actions=[5],
        )
        action = KakitaDoubleAttackAction(
            kakita, target, "double attack", ia, context,
        )
        action.skill_roll_params()
        tempo_tag = getattr(action, "_kakita_3rd_dan_tempo", None)
        self.assertIsNotNone(tempo_tag)
        assert tempo_tag is not None
        tempo_bonus, tempo_diff, attack_skill = tempo_tag
        self.assertEqual(10, tempo_bonus)  # 5 × 2
        self.assertEqual(2, tempo_diff)
        self.assertEqual(5, attack_skill)

    def test_kakita_lunge_action_tags_tempo_bonus(self) -> None:
        from simulation.schools.kakita_school import KakitaLungeAction
        kakita, target, context, ia = self._build_setup(
            subject_phase=0, target_actions=[],
        )
        action = KakitaLungeAction(
            kakita, target, "lunge", ia, context,
        )
        action.skill_roll_params()
        tempo_tag = getattr(action, "_kakita_3rd_dan_tempo", None)
        self.assertIsNotNone(tempo_tag)
        assert tempo_tag is not None
        tempo_bonus, tempo_diff, attack_skill = tempo_tag
        # Target with no actions → target_tempo = 11.
        # Subject phase 0 → diff 11, attack 5 → bonus 55.
        self.assertEqual(55, tempo_bonus)
        self.assertEqual(11, tempo_diff)
        self.assertEqual(5, attack_skill)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
