"""Trace coverage for school-identity events and their rendering.

Commit 9231894 ("more agent work") added a family of school-identity
trace events (Kitsuki 5th Dan ring debuff, Merchant 5th Dan reroll,
Shiba 5th Dan TN reduction, Yogo 3rd Dan LW reduction, Akodo 5th Dan
counter-damage) plus two conditional render branches (Mirumoto 4th Dan
auto-SW suffix, zero-magnitude floating-bonus suppression) and their
``DetailedEventFormatter`` conversions — but no test exercised the
event → formatter → renderer path, leaving these lines uncovered
across ``simulation/events.py``, ``web/adapters/detailed_formatter.py``,
and both renderers (Constitution Principle VI gap).

These tests drive each event through the real formatter and BOTH
renderers, assert the school attribution surfaces (Principle VII), and
cover the events' defensive input validation.
"""

import unittest
from unittest.mock import MagicMock

from simulation import events
from simulation.schools.merchant_school import (
    MerchantRollProvider,
    _drain_merchant_rerolls,
)
from web.adapters.bulleted_renderer import BulletedRenderer
from web.adapters.detailed_formatter import DetailedEventFormatter
from web.adapters.text_renderer import TextRenderer
from web.adapters.trace_entries import (
    SeriousWoundsDamageEntry,
    SpendFloatingBonusEntry,
)


def _actor(name: str) -> MagicMock:
    actor = MagicMock()
    actor.name.return_value = name
    return actor


def _render_both(event: object) -> tuple[str, str]:
    """Run a single event through formatter → both renderers.

    Returns ``(text, bulleted)`` rendered output as single strings.
    """
    text_entries = DetailedEventFormatter().entries([event])
    bullet_entries = DetailedEventFormatter().entries([event])
    text = "\n".join(TextRenderer().render_lines(text_entries))
    bulleted = BulletedRenderer().render(bullet_entries)
    return text, bulleted


class TestSchoolIdentityEventRendering(unittest.TestCase):
    def test_kitsuki_ring_reduction(self) -> None:
        event = events.KitsukiRingReductionEvent(
            subject=_actor("Kitsuki"),
            target=_actor("Bayushi"),
            ring_values_before={"fire": 4, "earth": 1},
        )
        text, bulleted = _render_both(event)
        for rendered in (text, bulleted):
            self.assertIn("Kitsuki 5th Dan: reduces Bayushi's rings", rendered)
            self.assertIn("Fire 4→3", rendered)
            self.assertIn("Earth 1→1", rendered)  # clamps at 1

    def test_merchant_reroll(self) -> None:
        event = events.MerchantRerollEvent(
            subject=_actor("Merchant"),
            roll_type="wound check",
            rerolled_pairs=[(1, 6), (2, 5)],
        )
        text, bulleted = _render_both(event)
        for rendered in (text, bulleted):
            self.assertIn("Merchant 5th Dan: rerolled 1→6, 2→5", rendered)
            self.assertIn("on wound check roll", rendered)

    def test_shiba_5th_dan_tn_reduction(self) -> None:
        event = events.ShibaFifthDanTnReductionEvent(
            subject=_actor("Shiba"),
            target=_actor("Bayushi"),
            margin=7,
        )
        text, bulleted = _render_both(event)
        for rendered in (text, bulleted):
            self.assertIn(
                "Shiba 5th Dan: TN to hit Bayushi lowered by 7", rendered,
            )

    def test_yogo_3rd_dan_lw_reduction(self) -> None:
        event = events.YogoThirdDanLwReductionEvent(
            subject=_actor("Yogo"),
            vp_spent=2,
            attack_skill=5,
            reduction=20,
            lw_after=4,
        )
        text, bulleted = _render_both(event)
        for rendered in (text, bulleted):
            self.assertIn(
                "Yogo 3rd Dan: LW -20 (= 2 × attack 5 × 2 VP) → total: 4",
                rendered,
            )

    def test_counter_damage_dealt(self) -> None:
        event = events.CounterDamageDealtEvent(
            subject=_actor("Bayushi"),
            source=_actor("Akodo"),
            damage=3,
            lw_after=12,
        )
        text, bulleted = _render_both(event)
        for rendered in (text, bulleted):
            self.assertIn("takes 3 light wounds", rendered)
            self.assertIn("total: 12", rendered)


class TestConditionalRenderBranches(unittest.TestCase):
    """The two boolean-gated render branches that the school work added
    but left uncovered in both renderers."""

    def test_mirumoto_4th_dan_auto_sw_suffix(self) -> None:
        entry = SeriousWoundsDamageEntry(
            phase_prefix="P1",
            target_name="Bayushi",
            damage=1,
            from_double_attack=False,
            from_mirumoto_4th_dan=True,
        )
        text = TextRenderer().render_lines([entry])
        bulleted = BulletedRenderer().render([entry])
        for rendered in ("\n".join(text), bulleted):
            self.assertIn("Bayushi takes 1 serious wound", rendered)
            self.assertIn(
                "(Mirumoto 4th Dan: auto-SW lands despite failed parry)",
                rendered,
            )

    def test_zero_magnitude_floating_bonus_suppressed(self) -> None:
        entry = SpendFloatingBonusEntry(
            phase_prefix="P1",
            character_name="Bayushi",
            amount=0,
            source="kharmic spin",
        )
        self.assertEqual(TextRenderer().render_lines([entry]), [])
        self.assertEqual(BulletedRenderer().render([entry]), "")


class TestEventValidation(unittest.TestCase):
    """Defensive input validation on the school-identity events."""

    def test_kitsuki_rejects_non_dict_ring_values(self) -> None:
        with self.assertRaises(ValueError):
            events.KitsukiRingReductionEvent(
                subject=_actor("Kitsuki"),
                target=_actor("Bayushi"),
                ring_values_before="not a dict",  # type: ignore[arg-type]
            )

    def test_merchant_rejects_non_str_roll_type(self) -> None:
        with self.assertRaises(ValueError):
            events.MerchantRerollEvent(
                subject=_actor("Merchant"),
                roll_type=5,  # type: ignore[arg-type]
                rerolled_pairs=[(1, 6)],
            )

    def test_merchant_rejects_non_list_pairs(self) -> None:
        with self.assertRaises(ValueError):
            events.MerchantRerollEvent(
                subject=_actor("Merchant"),
                roll_type="skill",
                rerolled_pairs="nope",  # type: ignore[arg-type]
            )

    def test_shiba_rejects_non_int_margin(self) -> None:
        with self.assertRaises(ValueError):
            events.ShibaFifthDanTnReductionEvent(
                subject=_actor("Shiba"),
                target=_actor("Bayushi"),
                margin="big",  # type: ignore[arg-type]
            )

    def test_yogo_rejects_non_int_fields(self) -> None:
        good = dict(
            subject=_actor("Yogo"),
            vp_spent=1,
            attack_skill=5,
            reduction=10,
            lw_after=0,
        )
        for field in ("vp_spent", "attack_skill", "reduction", "lw_after"):
            bad = {**good, field: "x"}
            with self.assertRaises(ValueError):
                events.YogoThirdDanLwReductionEvent(**bad)  # type: ignore[arg-type]

    def test_counter_damage_rejects_non_int_fields(self) -> None:
        good = dict(
            subject=_actor("Bayushi"),
            source=_actor("Akodo"),
            damage=3,
            lw_after=12,
        )
        for field in ("damage", "lw_after"):
            bad = {**good, field: "x"}
            with self.assertRaises(ValueError):
                events.CounterDamageDealtEvent(**bad)  # type: ignore[arg-type]


class TestMerchantDrainNoPendingRerolls(unittest.TestCase):
    def test_drain_yields_nothing_when_no_pending_rerolls(self) -> None:
        # A fresh MerchantRollProvider has no pending rerolls, so the
        # drain generator returns immediately (merchant_school.py:58).
        provider = MerchantRollProvider(inner=MagicMock())
        character = MagicMock()
        character.roll_provider.return_value = provider
        self.assertEqual(list(_drain_merchant_rerolls(character)), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
