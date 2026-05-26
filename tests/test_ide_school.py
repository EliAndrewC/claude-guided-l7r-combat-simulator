#!/usr/bin/env python3

#
# test_ide_school.py
#
# Unit tests for the Ide Diplomat School.
#

import logging
import sys
import unittest

from simulation import actions, events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.log import logger
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import ide_school

# set up logging
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)


class TestIdeDiplomatSchoolBasics(unittest.TestCase):
    def test_name(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual("Ide Diplomat School", school.name())

    def test_extra_rolled(self):
        school = ide_school.IdeDiplomatSchool()
        # Per specs/003-school-choices: precepts is mandatory per rules text
        # ("extra rolled die on precepts and any two rolls of your choice"),
        # and is prepended. Defaults preserve original behavior.
        self.assertEqual(["precepts", "wound check", "initiative"], school.extra_rolled())

    def test_school_ring(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_knacks(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual(["double attack", "feint", "worldliness"], school.school_knacks())

    def test_free_raise_skills(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual(["attack"], school.free_raise_skills())

    def test_ap_base_skill(self):
        school = ide_school.IdeDiplomatSchool()
        self.assertIsNone(school.ap_base_skill())


class TestIdeFeintSucceededListener(unittest.TestCase):
    def setUp(self):
        self.ide = Character("Ide")
        self.ide.set_actions([1])
        self.target = Character("Target")
        groups = [Group("Unicorn", self.ide), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_feint_succeeded_adds_modifier(self):
        action = actions.FeintAction(self.ide, self.target, "feint", self.initiative_action, self.context)
        event = events.AttackSucceededEvent(action)
        listener = ide_school.IdeFeintSucceededListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(1, len(responses))
        response = responses[0]
        self.assertIsInstance(response, events.AddModifierEvent)
        self.assertEqual(self.target, response.subject)
        # Modifier should reduce TN by 10
        self.assertEqual(-10, response.modifier.adjustment())

    def test_non_feint_attack_no_effect(self):
        action = actions.AttackAction(self.ide, self.target, "attack", self.initiative_action, self.context)
        event = events.AttackSucceededEvent(action)
        listener = ide_school.IdeFeintSucceededListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(0, len(responses))


class TestIdeFeintFailedListener(unittest.TestCase):
    def setUp(self):
        self.ide = Character("Ide")
        self.ide.set_actions([1])
        self.target = Character("Target")
        groups = [Group("Unicorn", self.ide), Group("Enemy", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_parried_feint_adds_modifier(self):
        action = actions.FeintAction(self.ide, self.target, "feint", self.initiative_action, self.context)
        action.set_parried()  # Simulate being parried
        event = events.AttackFailedEvent(action)
        listener = ide_school.IdeFeintFailedListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(1, len(responses))
        response = responses[0]
        self.assertIsInstance(response, events.AddModifierEvent)
        self.assertEqual(-10, response.modifier.adjustment())

    def test_missed_feint_no_modifier(self):
        action = actions.FeintAction(self.ide, self.target, "feint", self.initiative_action, self.context)
        # Not parried, just missed
        event = events.AttackFailedEvent(action)
        listener = ide_school.IdeFeintFailedListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(0, len(responses))


class TestIdeTactSubtractListener(unittest.TestCase):
    def setUp(self):
        self.ide = Character("Ide")
        self.ide.set_skill("tact", 3)
        self.ide.set_actions([1])
        self.attacker = Character("Attacker")
        self.attacker.set_actions([1])
        groups = [Group("Unicorn", self.ide), Group("Enemy", self.attacker)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_subtract_from_enemy_attack(self):
        # Use CalvinistRollProvider so tact roll is predictable
        roll_provider = CalvinistRollProvider()
        roll_provider.put_skill_roll("tact", 7)
        self.ide.set_roll_provider(roll_provider)
        action = actions.AttackAction(self.attacker, self.ide, "attack", self.initiative_action, self.context)
        action.set_skill_roll(30)
        event = events.AttackRolledEvent(action, 30)
        listener = ide_school.IdeTactSubtractListener()
        responses = list(listener.handle(self.ide, event, self.context))
        # Should spend VP, then yield new AttackRolledEvent
        self.assertEqual(2, len(responses))
        self.assertIsInstance(responses[0], events.SpendVoidPointsEvent)
        self.assertEqual(1, responses[0].amount)
        self.assertEqual("tact", responses[0].skill)
        self.assertIsInstance(responses[1], events.AttackRolledEvent)
        self.assertEqual(23, responses[1].roll)  # 30 - 7 = 23

    def test_no_subtract_when_no_vp(self):
        self.ide.spend_vp(self.ide.vp())  # Spend all VP
        action = actions.AttackAction(self.attacker, self.ide, "attack", self.initiative_action, self.context)
        action.set_skill_roll(30)
        event = events.AttackRolledEvent(action, 30)
        listener = ide_school.IdeTactSubtractListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(0, len(responses))

    def test_no_subtract_when_no_tact(self):
        self.ide.set_skill("tact", 0)
        action = actions.AttackAction(self.attacker, self.ide, "attack", self.initiative_action, self.context)
        action.set_skill_roll(30)
        event = events.AttackRolledEvent(action, 30)
        listener = ide_school.IdeTactSubtractListener()
        responses = list(listener.handle(self.ide, event, self.context))
        self.assertEqual(0, len(responses))


class TestIdeSpendVPListener(unittest.TestCase):
    def setUp(self):
        self.ide = Character("Ide")
        self.ide.set_actions([1])
        self.target = Character("Target")
        groups = [Group("Unicorn", self.ide), Group("Enemy", self.target)]
        self.context = EngineContext(groups)

    def test_gain_tvp_on_non_tact_vp_spend(self):
        event = events.SpendVoidPointsEvent(self.ide, "attack", 1)
        listener = ide_school.IdeSpendVPListener()
        responses = list(listener.handle(self.ide, event, self.context))
        # Should yield GainTemporaryVoidPointsEvent
        tvp_events = [r for r in responses if isinstance(r, events.GainTemporaryVoidPointsEvent)]
        self.assertEqual(1, len(tvp_events))
        self.assertEqual(1, tvp_events[0].amount)

    def test_no_tvp_on_tact_vp_spend(self):
        event = events.SpendVoidPointsEvent(self.ide, "tact", 1)
        listener = ide_school.IdeSpendVPListener()
        responses = list(listener.handle(self.ide, event, self.context))
        # Should NOT yield GainTemporaryVoidPointsEvent
        tvp_events = [r for r in responses if isinstance(r, events.GainTemporaryVoidPointsEvent)]
        self.assertEqual(0, len(tvp_events))


class TestIdeFourthDan(unittest.TestCase):
    def test_ring_raise_applied(self):
        ide = Character("Ide")
        ide.set_ring("water", 3)
        school = ide_school.IdeDiplomatSchool()
        school.apply_rank_four_ability(ide)
        self.assertEqual(4, ide.ring("water"))


class TestIdeDiplomatSchoolChoices(unittest.TestCase):
    """Phase 3 of the school-choices feature (specs/003-school-choices).

    The Ide Diplomat School honors three per-character build-time choices:
      - ``first_dan_extra_rolled``: list[str] (length 2) -- alongside the
        mandatory ``precepts`` per rules text ("Roll one extra die on
        precepts and any two rolls of your choice").
      - ``second_dan_free_raise``: str -- skill name for the 2nd Dan free
        raise ("You get a free raise on any type of roll of your choice").
      - ``school_ring``: str -- any non-Void ring (rules text "School Ring:
        Any non-Void"). The 4th Dan ring raise targets the chosen ring.

    Invalid choices warn and fall back to the school's hardcoded default
    (FR-007). Defaults preserve existing behavior when no choice is set
    (FR-006, FR-008).
    """

    # ------------------------------------------------------------------
    # first_dan_extra_rolled
    # ------------------------------------------------------------------

    def test_first_dan_extra_rolled_uses_default_when_no_choice(self):
        """FR-006 / FR-008: with no choice set, ``extra_rolled()`` returns
        the hardcoded default ``["precepts", "wound check", "initiative"]``.

        rules/04-schools.md "Ide Diplomat School: 1st Dan".
        """
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual(
            ["precepts", "wound check", "initiative"], school.extra_rolled(),
        )

    def test_first_dan_extra_rolled_honors_choice(self):
        """FR-006: setting ``first_dan_extra_rolled`` overrides the two
        choice-skills; ``"precepts"`` is always prepended.
        """
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("first_dan_extra_rolled", ["parry", "attack"])
        self.assertEqual(["precepts", "parry", "attack"], school.extra_rolled())

    def test_first_dan_extra_rolled_falls_back_on_wrong_length(self):
        """FR-007: a list of length != 2 logs a warning and uses the default."""
        school = ide_school.IdeDiplomatSchool()
        # Length 1
        school.set_choice("first_dan_extra_rolled", ["parry"])
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.extra_rolled()
        self.assertEqual(["precepts", "wound check", "initiative"], result)
        self.assertTrue(
            any("first_dan_extra_rolled" in m for m in cm.output),
            f"Expected warning about first_dan_extra_rolled, got {cm.output}",
        )
        # Length 3
        school.set_choice("first_dan_extra_rolled", ["parry", "attack", "kenjutsu"])
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.extra_rolled()
        self.assertEqual(["precepts", "wound check", "initiative"], result)
        self.assertTrue(
            any("first_dan_extra_rolled" in m for m in cm.output),
            f"Expected warning about first_dan_extra_rolled, got {cm.output}",
        )

    def test_first_dan_extra_rolled_falls_back_on_wrong_shape(self):
        """FR-007: non-list (string, dict) or list-with-non-strings logs a
        warning and uses default.
        """
        # String
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("first_dan_extra_rolled", "parry")
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.extra_rolled()
        self.assertEqual(["precepts", "wound check", "initiative"], result)
        self.assertTrue(
            any("first_dan_extra_rolled" in m for m in cm.output),
            f"Expected warning about first_dan_extra_rolled, got {cm.output}",
        )
        # Dict
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("first_dan_extra_rolled", {"a": "b"})
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.extra_rolled()
        self.assertEqual(["precepts", "wound check", "initiative"], result)
        self.assertTrue(
            any("first_dan_extra_rolled" in m for m in cm.output),
            f"Expected warning about first_dan_extra_rolled, got {cm.output}",
        )
        # List containing non-strings
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("first_dan_extra_rolled", ["parry", 7])
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.extra_rolled()
        self.assertEqual(["precepts", "wound check", "initiative"], result)

    # ------------------------------------------------------------------
    # second_dan_free_raise
    # ------------------------------------------------------------------

    def test_second_dan_free_raise_uses_default_when_no_choice(self):
        """FR-006 / FR-008: with no choice set, ``free_raise_skills()`` returns
        the Ide-specific default ``["attack"]`` (NOT precepts -- distinct from
        Ishi's default).

        rules/04-schools.md "Ide Diplomat School: 2nd Dan".
        """
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual(["attack"], school.free_raise_skills())

    def test_second_dan_free_raise_honors_choice(self):
        """FR-006: setting ``second_dan_free_raise`` overrides the default skill."""
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("second_dan_free_raise", "parry")
        self.assertEqual(["parry"], school.free_raise_skills())

    def test_second_dan_free_raise_falls_back_on_wrong_shape(self):
        """FR-007: a non-string value (list, int) logs a warning and uses
        the Ide default ``"attack"``.
        """
        # List
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("second_dan_free_raise", ["parry"])
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.free_raise_skills()
        self.assertEqual(["attack"], result)
        self.assertTrue(
            any("second_dan_free_raise" in m for m in cm.output),
            f"Expected warning about second_dan_free_raise, got {cm.output}",
        )
        # Int
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("second_dan_free_raise", 7)
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.free_raise_skills()
        self.assertEqual(["attack"], result)
        self.assertTrue(
            any("second_dan_free_raise" in m for m in cm.output),
            f"Expected warning about second_dan_free_raise, got {cm.output}",
        )

    # ------------------------------------------------------------------
    # school_ring (Pattern B -- new for Ide)
    # ------------------------------------------------------------------

    def test_school_ring_uses_default_when_no_choice(self):
        """FR-006 / FR-008: with no choice set, ``school_ring()`` returns the
        Ide default ``"water"``.

        rules/04-schools.md "Ide Diplomat School: School Ring: Any non-Void".
        """
        school = ide_school.IdeDiplomatSchool()
        self.assertEqual("water", school.school_ring())

    def test_school_ring_honors_choice(self):
        """FR-006: setting ``school_ring`` to a valid non-Void ring overrides
        the default. Verified for each of the four valid rings.
        """
        for chosen in ("air", "earth", "fire", "water"):
            school = ide_school.IdeDiplomatSchool()
            school.set_choice("school_ring", chosen)
            self.assertEqual(chosen, school.school_ring())

    def test_school_ring_rejects_void(self):
        """FR-007: ``"void"`` is forbidden by rules text ("Any non-Void");
        warn and fall back to the default ``"water"``.
        """
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("school_ring", "void")
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.school_ring()
        self.assertEqual("water", result)
        self.assertTrue(
            any("school_ring" in m for m in cm.output),
            f"Expected warning about school_ring, got {cm.output}",
        )

    def test_school_ring_rejects_unknown_ring(self):
        """FR-007: an unknown ring name (typo, made-up element) warns and
        falls back to ``"water"``.
        """
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("school_ring", "shadow")
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.school_ring()
        self.assertEqual("water", result)
        self.assertTrue(
            any("school_ring" in m for m in cm.output),
            f"Expected warning about school_ring, got {cm.output}",
        )

    def test_school_ring_rejects_wrong_shape(self):
        """FR-007: non-string (list, int, dict) warns and falls back."""
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("school_ring", ["fire"])
        with self.assertLogs(logger, level="WARNING") as cm:
            result = school.school_ring()
        self.assertEqual("water", result)
        self.assertTrue(
            any("school_ring" in m for m in cm.output),
            f"Expected warning about school_ring, got {cm.output}",
        )

    # ------------------------------------------------------------------
    # 4th Dan ring raise targets the CHOSEN ring (not hardcoded water)
    # ------------------------------------------------------------------

    def test_fourth_dan_raises_chosen_ring(self):
        """FR-006: when ``school_ring`` is overridden, ``apply_rank_four_ability``
        (which calls ``apply_school_ring_raise_and_discount``) targets the
        chosen ring, not the original default ``"water"``.

        rules/04-schools.md "Ide Diplomat School: 4th Dan" (Ring+1 / discount).
        """
        ide = Character("Ide")
        ide.set_ring("fire", 3)
        ide.set_ring("water", 3)
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("school_ring", "fire")
        school.apply_rank_four_ability(ide)
        # Fire was bumped; water was NOT touched.
        self.assertEqual(4, ide.ring("fire"))
        self.assertEqual(3, ide.ring("water"))

    # ------------------------------------------------------------------
    # Choices survive apply_rank_one / apply_rank_two (integration)
    # ------------------------------------------------------------------

    def test_choices_survive_apply_rank_chain(self):
        """FR-003 / FR-006: choices set BEFORE the rank-1 / rank-2 apply
        chain install the chosen skills (not the defaults) on the character.
        """
        from simulation.mechanics.modifiers import FreeRaise

        ide = Character("Ide")
        ide.set_ring("air", 3)
        ide.set_ring("earth", 3)
        ide.set_ring("fire", 3)
        ide.set_ring("water", 3)
        school = ide_school.IdeDiplomatSchool()
        school.set_choice("first_dan_extra_rolled", ["parry", "attack"])
        school.set_choice("second_dan_free_raise", "parry")
        ide.set_school(school)
        school.apply_rank_one_ability(ide)
        school.apply_rank_two_ability(ide)
        # 1st Dan: chosen skills + precepts each get +1 rolled.
        self.assertEqual(1, ide.extra_rolled("precepts"))
        self.assertEqual(1, ide.extra_rolled("parry"))
        self.assertEqual(1, ide.extra_rolled("attack"))
        # Defaults must NOT be installed.
        self.assertEqual(0, ide.extra_rolled("wound check"))
        self.assertEqual(0, ide.extra_rolled("initiative"))
        # 2nd Dan: FreeRaise on parry, not the default ``attack``.
        free_raise_skills_installed: list[str] = []
        for mod in ide._modifiers:
            if isinstance(mod, FreeRaise):
                free_raise_skills_installed.extend(mod.skills())
        self.assertIn("parry", free_raise_skills_installed)
        self.assertNotIn("attack", free_raise_skills_installed)

    # ------------------------------------------------------------------
    # End-to-end via config_to_character
    # ------------------------------------------------------------------

    def test_config_to_character_applies_school_choices_end_to_end(self):
        """FR-003 / FR-006 end-to-end: YAML choices land on the resulting
        Character's extra_rolled, FreeRaise modifier list, AND school_ring.

        Sets all three Ide-specific choices in one CharacterConfig and
        verifies each lands correctly. ``school_ring = "air"`` is exercised
        so the 4th Dan ring raise would land on air (verified separately
        in ``test_fourth_dan_raises_chosen_ring``).
        """
        from simulation.mechanics.modifiers import FreeRaise
        from web.adapters.character_adapter import config_to_character
        from web.models import CharacterConfig

        config = CharacterConfig(
            name="ChoiceIde",
            xp=500,
            char_type="school",
            school="Ide Diplomat School",
            rings={"air": 2, "earth": 2, "fire": 2, "water": 2, "void": 2},
            skills={
                # Knacks must all reach rank 2 to trigger the 2nd Dan ability.
                "double attack": 2,
                "feint": 2,
                "worldliness": 2,
            },
            school_choices={
                "first_dan_extra_rolled": ["parry", "wound check"],
                "second_dan_free_raise": "parry",
                "school_ring": "air",
            },
        )
        character = config_to_character(config)
        # 1st Dan honored: precepts (mandatory) + parry + wound check.
        self.assertEqual(1, character.extra_rolled("precepts"))
        self.assertEqual(1, character.extra_rolled("parry"))
        self.assertEqual(1, character.extra_rolled("wound check"))
        # Default "initiative" must NOT be installed.
        self.assertEqual(0, character.extra_rolled("initiative"))
        # 2nd Dan: FreeRaise on parry, not the Ide default ``attack``.
        free_raise_skills_installed: list[str] = []
        for mod in character._modifiers:
            if isinstance(mod, FreeRaise):
                free_raise_skills_installed.extend(mod.skills())
        self.assertIn("parry", free_raise_skills_installed)
        self.assertNotIn("attack", free_raise_skills_installed)
        # school_ring choice honored on the school instance.
        self.assertEqual("air", character.school().school_ring())
