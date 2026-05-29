#!/usr/bin/env python3

#
# test_otaku_school_trace.py
#
# Principle VII trace assertions for the Otaku Bushi School.
# Added per spec 014 trace-auditor + trace-reader audits (2026-05-29).
#
# rules/04-schools.md "Otaku Bushi School" + Constitution Principle VII.
#

import unittest

from web.adapters.trace_entries import SeriousWoundsDamageEntry


class TestOtaku5thDanSWAttribution(unittest.TestCase):
    """Spec 014 T-C2 / Principle VII: the SW emitted by the Otaku
    5th Dan dice-trade MUST surface with explicit source attribution
    in BOTH renderers, NOT as an unsourced "takes 1 serious wound".
    """

    def _make_5th_dan_sw_entry(self) -> SeriousWoundsDamageEntry:
        return SeriousWoundsDamageEntry(
            phase_prefix="Phase 5",
            target_name="Akodo",
            damage=1,
            from_double_attack=False,
            from_otaku_5th_dan=True,
        )

    def _make_plain_sw_entry(self) -> SeriousWoundsDamageEntry:
        return SeriousWoundsDamageEntry(
            phase_prefix="Phase 5",
            target_name="Akodo",
            damage=1,
            from_double_attack=False,
            from_otaku_5th_dan=False,
        )

    def _make_double_attack_sw_entry(self) -> SeriousWoundsDamageEntry:
        return SeriousWoundsDamageEntry(
            phase_prefix="Phase 5",
            target_name="Akodo",
            damage=1,
            from_double_attack=True,
            from_otaku_5th_dan=False,
        )

    def test_text_renderer_surfaces_otaku_5th_dan_attribution(self) -> None:
        from web.adapters.text_renderer import TextRenderer
        renderer = TextRenderer()
        entry = self._make_5th_dan_sw_entry()
        out = renderer._render_sw_damage(entry)
        self.assertEqual(1, len(out))
        self.assertIn("Otaku 5th Dan", out[0])
        self.assertIn("traded 10 rolled damage dice for 1 SW", out[0])

    def test_bulleted_renderer_surfaces_otaku_5th_dan_attribution(self) -> None:
        from web.adapters.bulleted_renderer import BulletedRenderer
        renderer = BulletedRenderer()
        entry = self._make_5th_dan_sw_entry()
        out = renderer._render_sw_damage(entry)
        self.assertEqual(1, len(out))
        self.assertIn("Otaku 5th Dan", out[0])

    def test_text_renderer_plain_sw_has_no_otaku_attribution(self) -> None:
        """An ordinary SW (not from Otaku 5th Dan) must NOT carry the
        Otaku attribution suffix."""
        from web.adapters.text_renderer import TextRenderer
        renderer = TextRenderer()
        entry = self._make_plain_sw_entry()
        out = renderer._render_sw_damage(entry)
        self.assertNotIn("Otaku", out[0])

    def test_double_attack_penalty_takes_priority_over_otaku(self) -> None:
        """If both flags were set (shouldn't happen but defensive),
        the double-attack-penalty label wins (since it predates Otaku
        in the conditional chain)."""
        from web.adapters.text_renderer import TextRenderer
        renderer = TextRenderer()
        entry = self._make_double_attack_sw_entry()
        out = renderer._render_sw_damage(entry)
        self.assertIn("double attack penalty", out[0])
        self.assertNotIn("Otaku", out[0])


class TestOtaku5thDanEntryWiring(unittest.TestCase):
    """Spec 014 T-C2: ``DetailedFormatter._entry_sw_damage`` MUST
    populate ``from_otaku_5th_dan`` from the SeriousWoundsDamageEvent's
    ``_from_otaku_5th_dan`` attribute."""

    def test_entry_sw_damage_reads_otaku_5th_dan_tag(self) -> None:
        from unittest.mock import MagicMock

        from web.adapters.detailed_formatter import DetailedEventFormatter

        formatter = DetailedEventFormatter()

        # Build a mock SW event with the Otaku 5th Dan tag.
        event = MagicMock()
        event.target.name.return_value = "Akodo"
        event.damage = 1
        event._from_double_attack = False
        event._from_otaku_5th_dan = True

        # Patch _phase_prefix to return a deterministic value.
        formatter._phase_prefix = lambda char_name: f"Phase X | {char_name}:"  # type: ignore[method-assign]
        entry = formatter._entry_sw_damage(event)
        self.assertTrue(entry.from_otaku_5th_dan)

    def test_entry_sw_damage_without_tag_defaults_false(self) -> None:
        from unittest.mock import MagicMock

        from web.adapters.detailed_formatter import DetailedEventFormatter

        formatter = DetailedEventFormatter()
        event = MagicMock(spec=["target", "damage"])
        event.target.name.return_value = "Akodo"
        event.damage = 1
        formatter._phase_prefix = lambda char_name: f"Phase X | {char_name}:"  # type: ignore[method-assign]
        entry = formatter._entry_sw_damage(event)
        self.assertFalse(entry.from_otaku_5th_dan)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
