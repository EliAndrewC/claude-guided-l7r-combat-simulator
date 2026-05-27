#!/usr/bin/env python3

#
# test_action_damage_breakdown.py
#
# Unit tests for the ``damage_breakdown()`` accessor on AttackAction and
# its subclasses (FeintAction, BayushiFeintAction).  Spec 009
# (Action-Level Damage Breakdown) — moves the breakdown computation
# from the formatter onto the action so subclasses that override
# ``damage_roll_params`` can keep their projection and per-source
# decomposition in agreement (no more 9k2-vs-5k1 mismatch on Bayushi
# feints).
#

import unittest
from typing import Any

from simulation.actions import AttackAction, FeintAction
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.mechanics.initiative_actions import InitiativeAction
from simulation.mechanics.roll_params import DefaultRollParameterProvider
from simulation.mechanics.roll_provider import CalvinistRollProvider
from simulation.schools import bayushi_school


class _RecordingProvider(DefaultRollParameterProvider):
    """RollParameterProvider that records the arguments passed to
    ``get_breakdown`` and returns a canned response.  Used to assert
    the action's default ``damage_breakdown()`` delegates correctly.
    """

    def __init__(self, response: list[tuple[str, int, int]]) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def get_breakdown(
        self,
        character: Any,
        target: Any,
        skill: str,
        kind: str = "damage",
        attack_extra_rolled: int = 0,
        vp: int = 0,
        contested_skill: str | None = None,
        ring: str | None = None,
    ) -> list[tuple[str, int, int]]:
        self.calls.append({
            "character": character,
            "target": target,
            "skill": skill,
            "kind": kind,
            "attack_extra_rolled": attack_extra_rolled,
            "vp": vp,
        })
        return self._response


class TestAttackActionDamageBreakdown(unittest.TestCase):
    """``AttackAction.damage_breakdown()`` default delegates to the
    subject's RollParameterProvider with the same arguments the
    formatter call-sites previously used: skill, kind='damage',
    attack_extra_rolled (from ``calculate_extra_damage_dice``) and vp.
    """

    def setUp(self) -> None:
        self.attacker = Character("attacker")
        self.target = Character("target")
        self.target.set_skill("parry", 5)
        groups = [Group("attacker", self.attacker), Group("target", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def test_delegates_to_provider_with_correct_arguments(self) -> None:
        """Default ``damage_breakdown`` calls the subject's provider's
        ``get_breakdown`` with ``kind='damage'``, the action's
        attack-margin extras and the action's vp.
        """
        expected: list[tuple[str, int, int]] = [("katana", 4, 2), ("Fire ring", 3, 0)]
        recording_provider = _RecordingProvider(expected)
        self.attacker.set_roll_parameter_provider(recording_provider)
        attack = AttackAction(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context, vp=2,
        )
        # rig the attack roll to hit by 10 (2 extra damage dice)
        attack.set_skill_roll(self.target.tn_to_hit() + 10)

        result = attack.damage_breakdown()

        self.assertEqual(expected, result)
        self.assertEqual(1, len(recording_provider.calls))
        call = recording_provider.calls[0]
        self.assertEqual(self.attacker, call["character"])
        self.assertEqual(self.target, call["target"])
        self.assertEqual("attack", call["skill"])
        self.assertEqual("damage", call["kind"])
        self.assertEqual(2, call["attack_extra_rolled"])
        self.assertEqual(2, call["vp"])

    def test_returns_list_type_with_default_provider(self) -> None:
        """Smoke test: with the real default provider, the breakdown is
        a non-empty list of (label, rolled, kept) tuples summing to the
        aggregate from ``damage_roll_params``.
        """
        attack = AttackAction(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context,
        )
        attack.set_skill_roll(self.target.tn_to_hit())

        components = attack.damage_breakdown()

        self.assertIsInstance(components, list)
        self.assertGreater(len(components), 0)
        for entry in components:
            self.assertIsInstance(entry, tuple)
            self.assertEqual(3, len(entry))
            label, rolled, kept = entry
            self.assertIsInstance(label, str)
            self.assertIsInstance(rolled, int)
            self.assertIsInstance(kept, int)


class TestAttackActionDamageBreakdownDefensiveGuards(unittest.TestCase):
    """Defensive guards in ``AttackAction.damage_breakdown()`` —
    migrated from the deleted ``_compute_damage_breakdown`` helper.
    """

    def setUp(self) -> None:
        self.attacker = Character("attacker")
        self.target = Character("target")
        groups = [Group("A", self.attacker), Group("B", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)

    def _attack(self) -> AttackAction:
        attack = AttackAction(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context,
        )
        attack.set_skill_roll(self.target.tn_to_hit())
        return attack

    def test_provider_without_get_breakdown_returns_empty(self) -> None:
        """A provider object that lacks ``get_breakdown`` (legacy)
        causes the action to return ``[]`` rather than raise.
        """

        class LegacyProvider:
            pass

        # Bypass the Character.set_roll_parameter_provider type check.
        self.attacker._roll_parameter_provider = LegacyProvider()  # type: ignore[assignment]  # test injects a legacy stub to exercise the defensive guard

        result = self._attack().damage_breakdown()

        self.assertEqual([], result)

    def test_provider_raises_returns_empty(self) -> None:
        """An exception from ``get_breakdown`` is swallowed."""

        class RaisingProvider(DefaultRollParameterProvider):
            def get_breakdown(self, *args: Any, **kwargs: Any) -> list[tuple[str, int, int]]:
                raise RuntimeError("nope")

        self.attacker.set_roll_parameter_provider(RaisingProvider())

        result = self._attack().damage_breakdown()

        self.assertEqual([], result)

    def test_provider_returns_non_list_returns_empty(self) -> None:
        """A non-list return is normalized to ``[]``."""

        class BadProvider(DefaultRollParameterProvider):
            def get_breakdown(self, *args: Any, **kwargs: Any) -> Any:
                return "not a list"

        self.attacker.set_roll_parameter_provider(BadProvider())

        result = self._attack().damage_breakdown()

        self.assertEqual([], result)

    def test_no_skill_roll_set_uses_zero_extras(self) -> None:
        """When ``skill_roll`` is unset, ``calculate_extra_damage_dice``
        triggers an ``AssertionError`` internally.  The defensive
        fallback uses 0 extras instead of crashing — the breakdown
        still returns the per-source decomposition for the default
        case.
        """
        recording = _RecordingProvider([("katana", 4, 2)])
        self.attacker.set_roll_parameter_provider(recording)
        attack = AttackAction(
            self.attacker, self.target, "attack",
            self.initiative_action, self.context,
        )
        # No skill_roll set — calculate_extra_damage_dice would
        # otherwise assert.

        result = attack.damage_breakdown()

        self.assertEqual([("katana", 4, 2)], result)
        self.assertEqual(0, recording.calls[0]["attack_extra_rolled"])


class TestFeintActionDamageBreakdown(unittest.TestCase):
    """``FeintAction.damage_breakdown()`` returns ``[]`` — a standard
    feint deals zero deterministic damage (its ``damage_roll_params``
    is ``(0, 0, 0)``), so it has no per-source breakdown to display.
    """

    def test_returns_empty_list(self) -> None:
        attacker = Character("attacker")
        target = Character("target")
        groups = [Group("A", attacker), Group("B", target)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        action = FeintAction(attacker, target, "feint", initiative_action, context)

        self.assertEqual([], action.damage_breakdown())


class TestBayushiFeintActionDamageBreakdown(unittest.TestCase):
    """``BayushiFeintAction.damage_breakdown()`` mirrors its custom
    ``damage_roll_params``:

        rolled = attack_skill + vp
        kept   = 1 + vp

    Per-source labels: attack skill (rolled-only), base feint kept die
    (kept-only), VP on feint (rolled AND kept).
    """

    def setUp(self) -> None:
        self.bayushi = Character("Bayushi")
        self.target = Character("target")
        groups = [Group("Scorpion", self.bayushi), Group("target", self.target)]
        self.context = EngineContext(groups)
        self.initiative_action = InitiativeAction([1], 1)
        self.bayushi.set_roll_parameter_provider(
            bayushi_school.BayushiRollParameterProvider(),
        )

    def _action(self, vp: int = 0) -> bayushi_school.BayushiFeintAction:
        return bayushi_school.BayushiFeintAction(
            self.bayushi, self.target, "feint",
            self.initiative_action, self.context, vp=vp,
        )

    def test_breakdown_without_vp(self) -> None:
        """attack skill 5, no VP → 5k0 attack skill + 0k1 base feint
        kept die; sums to 5k1 — exactly what ``damage_roll_params``
        returns.
        """
        self.bayushi.set_skill("attack", 5)
        action = self._action(vp=0)

        result = action.damage_breakdown()

        self.assertEqual(
            [("attack skill", 5, 0), ("base feint kept die", 0, 1)],
            result,
        )

    def test_breakdown_with_vp(self) -> None:
        """attack skill 5, VP 2 → 5k0 + 0k1 + 2k2 = 7k3; matches
        Bayushi feint params ``(5+2, 1+2)``.
        """
        self.bayushi.set_skill("attack", 5)
        action = self._action(vp=2)

        result = action.damage_breakdown()

        self.assertEqual(
            [
                ("attack skill", 5, 0),
                ("base feint kept die", 0, 1),
                ("VP on feint", 2, 2),
            ],
            result,
        )

    def test_breakdown_with_zero_attack_skill(self) -> None:
        """Attack-skill component is omitted when the skill is 0 (no
        rolled contribution from the skill).  Base feint kept die is
        always present.
        """
        self.bayushi.set_skill("attack", 0)
        action = self._action(vp=0)

        result = action.damage_breakdown()

        self.assertEqual([("base feint kept die", 0, 1)], result)

    def test_breakdown_with_different_attack_skill_values(self) -> None:
        """Per-source rolled value tracks ``character.skill('attack')``
        directly.
        """
        for skill_value in [1, 3, 7]:
            with self.subTest(attack_skill=skill_value):
                self.bayushi.set_skill("attack", skill_value)
                action = self._action(vp=0)
                result = action.damage_breakdown()
                self.assertEqual(
                    [
                        ("attack skill", skill_value, 0),
                        ("base feint kept die", 0, 1),
                    ],
                    result,
                )

    def test_breakdown_sums_match_damage_roll_params(self) -> None:
        """Invariant: components' (sum_rolled, sum_kept) equals the
        Bayushi feint's (rolled, kept) — same invariant the
        ``_normalize_breakdown`` reconciliation enforces for the
        default-provider breakdown.
        """
        for attack_skill, vp in [(3, 0), (5, 2), (0, 3), (6, 1)]:
            with self.subTest(attack_skill=attack_skill, vp=vp):
                self.bayushi.set_skill("attack", attack_skill)
                action = self._action(vp=vp)
                rolled, kept, _modifier = action.damage_roll_params()
                components = action.damage_breakdown()
                sum_rolled = sum(r for _, r, _ in components)
                sum_kept = sum(k for _, _, k in components)
                self.assertEqual(rolled, sum_rolled)
                self.assertEqual(kept, sum_kept)

    def test_breakdown_does_not_include_katana_or_fire_ring(self) -> None:
        """Regression guard for spec 009: the pre-fix breakdown leaked
        the default-provider's ``katana + Fire ring + reconciliation``
        components into the Bayushi feint projection, mismatching the
        actual 5k1 roll.  None of those source labels may appear here.
        """
        self.bayushi.set_skill("attack", 5)
        self.bayushi.set_ring("fire", 5)
        action = self._action(vp=0)

        result = action.damage_breakdown()
        labels = {label for label, _, _ in result}

        self.assertNotIn("katana", labels)
        self.assertNotIn("Fire ring", labels)
        self.assertNotIn("reconciliation", labels)


class TestBayushiFeintIntegrationWithDamageRoll(unittest.TestCase):
    """End-to-end: rolling damage through ``BayushiFeintAction`` and
    inspecting its breakdown together — they must agree.
    """

    def test_damage_roll_and_breakdown_in_agreement(self) -> None:
        bayushi = Character("Bayushi")
        bayushi.set_skill("attack", 4)
        bayushi.set_skill("feint", 1)
        target = Character("target")
        groups = [Group("Scorpion", bayushi), Group("target", target)]
        context = EngineContext(groups)
        initiative_action = InitiativeAction([1], 1)
        bayushi.set_roll_parameter_provider(
            bayushi_school.BayushiRollParameterProvider(),
        )
        roll_provider = CalvinistRollProvider()
        roll_provider.put_damage_roll(9)
        bayushi.set_roll_provider(roll_provider)
        action = bayushi_school.BayushiFeintAction(
            bayushi, target, "feint", initiative_action, context,
        )
        action.set_skill_roll(9001)

        damage = action.roll_damage()
        rolled, kept, _ = action.damage_roll_params()
        components = action.damage_breakdown()

        self.assertEqual(9, damage)
        # observed params: rolled=4 (attack skill), kept=1 (base feint kept die)
        self.assertEqual((4, 1), roll_provider.pop_observed_params("damage"))
        # components must sum to the same (rolled, kept)
        self.assertEqual(rolled, sum(r for _, r, _ in components))
        self.assertEqual(kept, sum(k for _, _, k in components))


if __name__ == "__main__":
    unittest.main()
