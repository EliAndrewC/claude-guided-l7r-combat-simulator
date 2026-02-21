"""Integration tests to verify dice data flows through DetailedCombatEngine.

These tests reproduce the bug where observer annotations show 0k0 [] for damage
and wound check rolls, and empty [] for attack dice.
"""

import unittest

from simulation import events
from simulation.character import Character
from simulation.context import EngineContext
from simulation.groups import Group
from simulation.mechanics.roll_provider import DefaultRollProvider
from web.adapters.combat_observer import CombatObserver, DetailedCombatEngine, TrackingRollProvider


def _build_simple_combat():
    """Build two characters and a context for a simple combat."""
    char1 = Character("Attacker")
    char1.set_ring("fire", 5)
    char1.set_ring("water", 3)
    char1.set_ring("earth", 3)
    char1.set_ring("air", 3)
    char1.set_ring("void", 3)
    char1.set_skill("attack", 5)

    char2 = Character("Defender")
    char2.set_ring("fire", 3)
    char2.set_ring("water", 3)
    char2.set_ring("earth", 3)
    char2.set_ring("air", 3)
    char2.set_ring("void", 3)
    char2.set_skill("attack", 3)

    group1 = Group("G1", [char1])
    group2 = Group("G2", [char2])
    context = EngineContext([group1, group2])
    context.initialize()
    return char1, char2, context


class TestDiceIntegration(unittest.TestCase):
    """Run a full combat through DetailedCombatEngine and verify dice annotations."""

    def test_attack_dice_are_captured(self):
        """AttackRolledEvent should have non-empty _detail_dice after a real combat."""
        char1, char2, context = _build_simple_combat()

        # Wrap per-character providers (same as run_single does)
        char1.set_roll_provider(TrackingRollProvider(char1.roll_provider()))
        char2.set_roll_provider(TrackingRollProvider(char2.roll_provider()))

        observer = CombatObserver()
        engine = DetailedCombatEngine(context, observer)
        engine.run()

        attack_events = [e for e in engine.history() if isinstance(e, events.AttackRolledEvent)]
        self.assertTrue(len(attack_events) > 0, "Should have at least one attack roll")

        for event in attack_events:
            self.assertTrue(hasattr(event, "_detail_dice"), "AttackRolledEvent should have _detail_dice")
            self.assertTrue(
                len(event._detail_dice) > 0,
                f"Attack dice should not be empty, got {event._detail_dice} "
                f"with params {event._detail_params}",
            )

    def test_damage_dice_are_captured(self):
        """LightWoundsDamageEvent should have non-zero rolled/kept after a real combat."""
        char1, char2, context = _build_simple_combat()

        char1.set_roll_provider(DefaultRollProvider())
        char2.set_roll_provider(DefaultRollProvider())

        observer = CombatObserver()
        engine = DetailedCombatEngine(context, observer)
        engine.run()

        damage_events = [e for e in engine.history() if isinstance(e, events.LightWoundsDamageEvent)]
        self.assertTrue(len(damage_events) > 0, "Should have at least one damage event")

        for event in damage_events:
            self.assertTrue(hasattr(event, "_detail_dice"), "LightWoundsDamageEvent should have _detail_dice")
            rolled, kept = event._detail_params
            self.assertGreater(
                rolled, 0,
                f"Damage rolled should be > 0, got {rolled}k{kept} "
                f"dice={event._detail_dice} damage={event.damage}",
            )
            self.assertTrue(
                len(event._detail_dice) > 0,
                f"Damage dice should not be empty, got {event._detail_dice} "
                f"params={event._detail_params} damage={event.damage}",
            )

    def test_wound_check_dice_are_captured(self):
        """WoundCheckRolledEvent should have non-zero rolled/kept after a real combat."""
        char1, char2, context = _build_simple_combat()

        char1.set_roll_provider(DefaultRollProvider())
        char2.set_roll_provider(DefaultRollProvider())

        observer = CombatObserver()
        engine = DetailedCombatEngine(context, observer)
        engine.run()

        wc_events = [e for e in engine.history() if isinstance(e, events.WoundCheckRolledEvent)]
        self.assertTrue(len(wc_events) > 0, "Should have at least one wound check")

        for event in wc_events:
            self.assertTrue(hasattr(event, "_detail_dice"), "WoundCheckRolledEvent should have _detail_dice")
            rolled, kept = event._detail_params
            self.assertGreater(
                rolled, 0,
                f"Wound check rolled should be > 0, got {rolled}k{kept} "
                f"dice={event._detail_dice} roll={event.roll}",
            )
            self.assertTrue(
                len(event._detail_dice) > 0,
                f"Wound check dice should not be empty, got {event._detail_dice} "
                f"params={event._detail_params} roll={event.roll}",
            )


class TestDiceProviderIdentity(unittest.TestCase):
    """Verify the provider the observer reads is the same that performed the roll."""

    def test_provider_is_same_instance_for_skill_roll(self):
        """The provider on the character should be the same one that did the roll."""
        char1, char2, context = _build_simple_combat()

        provider1 = TrackingRollProvider(DefaultRollProvider())
        provider2 = TrackingRollProvider(DefaultRollProvider())
        char1.set_roll_provider(provider1)
        char2.set_roll_provider(provider2)

        # Track what the observer sees
        observed_providers = []

        class TracingObserver(CombatObserver):
            def _annotate_attack_rolled(self, event):
                subject = event.action.subject()
                provider = subject.roll_provider()
                observed_providers.append({
                    "subject": subject.name(),
                    "provider_id": id(provider),
                    "has_last_skill_info": hasattr(provider, "last_skill_info"),
                    "last_skill_info": provider.last_skill_info() if hasattr(provider, "last_skill_info") else "NO_ATTR",
                })
                super()._annotate_attack_rolled(event)

            def _annotate_damage(self, event):
                attacker = event.subject
                provider = attacker.roll_provider()
                observed_providers.append({
                    "type": "damage",
                    "attacker": attacker.name(),
                    "provider_id": id(provider),
                    "has_last_damage_info": hasattr(provider, "last_damage_info"),
                    "last_damage_info": provider.last_damage_info() if hasattr(provider, "last_damage_info") else "NO_ATTR",
                })
                super()._annotate_damage(event)

            def _annotate_wound_check(self, event):
                subject = event.subject
                provider = subject.roll_provider()
                observed_providers.append({
                    "type": "wound_check",
                    "subject": subject.name(),
                    "provider_id": id(provider),
                    "has_last_wc_info": hasattr(provider, "last_wound_check_info"),
                    "last_wc_info": provider.last_wound_check_info() if hasattr(provider, "last_wound_check_info") else "NO_ATTR",
                })
                super()._annotate_wound_check(event)

        observer = TracingObserver()
        engine = DetailedCombatEngine(context, observer)
        engine.run()

        # Verify all observed providers had data
        for obs in observed_providers:
            if "last_skill_info" in obs:
                info = obs["last_skill_info"]
                self.assertIsNotNone(info, f"Skill info was None for {obs['subject']}, provider_id={obs['provider_id']}")
                self.assertTrue(len(info["dice"]) > 0, f"Skill dice empty for {obs['subject']}: {info}")
            if obs.get("type") == "damage":
                info = obs["last_damage_info"]
                self.assertIsNotNone(info, f"Damage info was None for {obs['attacker']}, provider_id={obs['provider_id']}")
                self.assertTrue(len(info["dice"]) > 0, f"Damage dice empty for {obs['attacker']}: {info}")
            if obs.get("type") == "wound_check":
                info = obs["last_wc_info"]
                self.assertIsNotNone(info, f"WC info was None for {obs['subject']}, provider_id={obs['provider_id']}")
                self.assertTrue(len(info["dice"]) > 0, f"WC dice empty for {obs['subject']}: {info}")

        # Verify each character uses their injected provider
        self.assertEqual(id(char1.roll_provider()), id(provider1))
        self.assertEqual(id(char2.roll_provider()), id(provider2))


class TestDiceIntegrationWithSchools(unittest.TestCase):
    """Run combat with school-built characters (closer to real usage)."""

    def _build_school_combat(self):
        """Build two school characters via CharacterBuilder."""
        from simulation.character_builder import CharacterBuilder
        from simulation.schools.akodo_school import AkodoBushiSchool
        from simulation.schools.kakita_school import KakitaBushiSchool

        builder1 = CharacterBuilder(xp=200).with_name("Akodo")
        builder1 = builder1.with_school(AkodoBushiSchool())
        builder1.buy_ring("fire", 5)
        builder1.buy_ring("earth", 4)
        builder1.buy_ring("air", 3)
        builder1.buy_ring("water", 3)
        builder1.buy_ring("void", 3)
        builder1.buy_skill("attack", 5)
        char1 = builder1.build()

        builder2 = CharacterBuilder(xp=200).with_name("Kakita")
        builder2 = builder2.with_school(KakitaBushiSchool())
        builder2.buy_ring("fire", 5)
        builder2.buy_ring("earth", 4)
        builder2.buy_ring("air", 4)
        builder2.buy_ring("water", 3)
        builder2.buy_ring("void", 3)
        builder2.buy_skill("attack", 5)
        char2 = builder2.build()

        group1 = Group("G1", [char1])
        group2 = Group("G2", [char2])
        context = EngineContext([group1, group2])
        context.initialize()

        # Wrap per-character providers (same as run_single does)
        for char in [char1, char2]:
            char.set_roll_provider(TrackingRollProvider(char.roll_provider()))

        return char1, char2, context

    def test_school_attack_dice_captured(self):
        char1, char2, context = self._build_school_combat()
        observer = CombatObserver()
        engine = DetailedCombatEngine(context, observer)
        engine.run()

        attack_events = [e for e in engine.history() if isinstance(e, events.AttackRolledEvent)]
        self.assertTrue(len(attack_events) > 0, "Should have at least one attack roll")
        for event in attack_events:
            self.assertTrue(hasattr(event, "_detail_dice"))
            self.assertTrue(
                len(event._detail_dice) > 0,
                f"Attack dice empty: params={event._detail_params}",
            )

    def test_school_damage_dice_captured(self):
        char1, char2, context = self._build_school_combat()
        observer = CombatObserver()
        engine = DetailedCombatEngine(context, observer)
        engine.run()

        damage_events = [e for e in engine.history() if isinstance(e, events.LightWoundsDamageEvent)]
        self.assertTrue(len(damage_events) > 0, "Should have at least one damage event")
        for event in damage_events:
            self.assertTrue(hasattr(event, "_detail_dice"))
            rolled, kept = event._detail_params
            # Feints deal 0 damage with 0k0 - skip those
            if event.damage > 0:
                self.assertGreater(rolled, 0, f"Damage 0k0: dice={event._detail_dice} damage={event.damage}")

    def test_school_wound_check_dice_captured(self):
        char1, char2, context = self._build_school_combat()
        observer = CombatObserver()
        engine = DetailedCombatEngine(context, observer)
        engine.run()

        wc_events = [e for e in engine.history() if isinstance(e, events.WoundCheckRolledEvent)]
        self.assertTrue(len(wc_events) > 0, "Should have at least one wound check")
        for event in wc_events:
            self.assertTrue(hasattr(event, "_detail_dice"))
            rolled, kept = event._detail_params
            self.assertGreater(rolled, 0, f"WC 0k0: dice={event._detail_dice} roll={event.roll}")


class TestEndToEndPlayByPlay(unittest.TestCase):
    """End-to-end test that runs through the full run_single() path and checks output."""

    def _build_and_run(self):
        """Build characters, wrap providers, run combat, format output."""
        from simulation.character_builder import CharacterBuilder
        from simulation.schools.akodo_school import AkodoBushiSchool
        from simulation.schools.kakita_school import KakitaBushiSchool
        from web.adapters.detailed_formatter import DetailedEventFormatter

        builder1 = CharacterBuilder(xp=200).with_name("Akodo")
        builder1 = builder1.with_school(AkodoBushiSchool())
        builder1.buy_ring("fire", 5)
        builder1.buy_ring("earth", 4)
        builder1.buy_ring("air", 3)
        builder1.buy_ring("water", 3)
        builder1.buy_ring("void", 3)
        builder1.buy_skill("attack", 5)
        char1 = builder1.build()

        builder2 = CharacterBuilder(xp=200).with_name("Kakita")
        builder2 = builder2.with_school(KakitaBushiSchool())
        builder2.buy_ring("fire", 5)
        builder2.buy_ring("earth", 4)
        builder2.buy_ring("air", 4)
        builder2.buy_ring("water", 3)
        builder2.buy_ring("void", 3)
        builder2.buy_skill("attack", 5)
        char2 = builder2.build()

        group1 = Group("G1", [char1])
        group2 = Group("G2", [char2])
        context = EngineContext([group1, group2])
        context.initialize()

        # Wrap providers exactly like run_single() does
        for char in [char1, char2]:
            char.set_roll_provider(TrackingRollProvider(char.roll_provider()))

        observer = CombatObserver()
        engine = DetailedCombatEngine(context, observer)
        engine.run()

        play_by_play = DetailedEventFormatter().format_history(engine.history())
        return play_by_play, engine.history()

    def test_no_empty_dice_in_attack_lines(self):
        """Attack lines should show actual dice, not empty []."""
        play_by_play, _ = self._build_and_run()
        # Combined format: "attacks ... — 10k6 [...] vs TN ..."
        # Standalone format: "Attack: 10k6 [...] vs TN ..."
        attack_lines = [line for line in play_by_play if "vs TN" in line and ("attacks" in line or "Attack:" in line)]
        self.assertTrue(len(attack_lines) > 0, "Should have at least one attack line")
        for line in attack_lines:
            self.assertNotIn("[]", line, f"Empty dice in attack line: {line}")

    def test_no_empty_dice_in_damage_lines(self):
        """Damage lines should show actual dice, not empty []."""
        play_by_play, _ = self._build_and_run()
        damage_lines = [line for line in play_by_play if "Damage:" in line]
        self.assertTrue(len(damage_lines) > 0, "Should have at least one damage line")
        for line in damage_lines:
            # Feints produce "Damage: 0k0 [] -> ..." which is correct
            if "0k0" not in line:
                self.assertNotIn("[]", line, f"Empty dice in damage line: {line}")

    def test_no_empty_dice_in_wound_check_lines(self):
        """Wound check lines should show actual dice, not empty []."""
        play_by_play, _ = self._build_and_run()
        wc_lines = [line for line in play_by_play if "Wound Check:" in line]
        self.assertTrue(len(wc_lines) > 0, "Should have at least one wound check line")
        for line in wc_lines:
            self.assertNotIn("[]", line, f"Empty dice in wound check line: {line}")

    def test_no_empty_dice_in_initiative_lines(self):
        """Initiative lines should show actual dice, not empty []."""
        play_by_play, _ = self._build_and_run()
        init_lines = [line for line in play_by_play if "rolled [" in line or "rolled []" in line]
        self.assertTrue(len(init_lines) > 0, "Should have at least one initiative line")
        for line in init_lines:
            self.assertNotIn("rolled []", line, f"Empty dice in initiative line: {line}")

    def test_detail_dice_not_empty_on_events(self):
        """Verify _detail_dice is populated on all annotated events."""
        _, history = self._build_and_run()
        for event in history:
            if isinstance(event, events.AttackRolledEvent) and hasattr(event, "_detail_dice"):
                self.assertTrue(
                    len(event._detail_dice) > 0,
                    f"Empty _detail_dice on AttackRolledEvent, params={event._detail_params}",
                )
            if isinstance(event, events.LightWoundsDamageEvent) and hasattr(event, "_detail_dice"):
                self.assertTrue(
                    len(event._detail_dice) > 0,
                    f"Empty _detail_dice on LightWoundsDamageEvent, params={event._detail_params}",
                )
            if isinstance(event, events.WoundCheckRolledEvent) and hasattr(event, "_detail_dice"):
                self.assertTrue(
                    len(event._detail_dice) > 0,
                    f"Empty _detail_dice on WoundCheckRolledEvent, params={event._detail_params}",
                )


if __name__ == "__main__":
    unittest.main()
