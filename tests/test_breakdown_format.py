"""Tests for the shared ``_breakdown_format`` helper (spec 008 FR-001/018).

Covers ``format_breakdown_component`` at 100%: the standard NkM case,
the 10k10-overflow special case across its parameter variants, and
the singular/plural noun selection.

Also includes a coverage-completeness test for ``_format_dice`` on
empty input, which is reachable via the spec 008 helper-migration
diff (the file's line layout shifted; the empty-dice fallback is
now uncovered by the prior implicit-coverage path).
"""

from web.adapters._breakdown_format import (
    EXCESS_10K10_SOURCE,
    format_breakdown_component,
)
from web.adapters.text_renderer import _format_dice


class TestFormatBreakdownComponent:
    """Standard cases — ``"{rolled}k{kept} {source}"`` form."""

    def test_standard_positive_case(self) -> None:
        """Positive rolled+kept with arbitrary source uses the NkM form."""
        result = format_breakdown_component(5, 5, "Fire ring")
        assert result == "5k5 Fire ring"

    def test_standard_with_zero_kept(self) -> None:
        """``Nk0`` (rolled-only contribution) uses the NkM form."""
        result = format_breakdown_component(5, 0, "attack skill")
        assert result == "5k0 attack skill"

    def test_standard_with_zero_rolled(self) -> None:
        """``0kM`` (kept-only contribution) uses the NkM form."""
        result = format_breakdown_component(0, 2, "VP raise")
        assert result == "0k2 VP raise"

    def test_zero_zero_with_unrelated_source(self) -> None:
        """``0k0`` with a non-overflow source still uses the NkM form
        (this rendering decision is preserved for symmetry; the caller
        filters zero-zero components before invoking the helper).
        """
        result = format_breakdown_component(0, 0, "Fire ring")
        assert result == "0k0 Fire ring"

    def test_overflow_source_but_nonnegative_values_uses_standard_form(
        self,
    ) -> None:
        """When the source is ``from dice in excess of 10k10`` but both
        ``rolled`` and ``kept`` are non-negative, the helper falls
        through to the standard form.

        This covers the reconciliation case where the overflow-label
        appears with positive deltas (the label is reused for
        missing-contribution gaps where the actual aggregate exceeds
        the breakdown sum — a pre-existing labeling quirk).
        """
        result = format_breakdown_component(2, 1, EXCESS_10K10_SOURCE)
        assert result == f"2k1 {EXCESS_10K10_SOURCE}"


class TestFormatBreakdownComponentOverflow:
    """Special-case the synthetic 10k10-overflow source with negative deltas."""

    def test_overflow_negative_rolled_only(self) -> None:
        """``-3k0 from dice in excess of 10k10`` renders as the narrative form."""
        result = format_breakdown_component(-3, 0, EXCESS_10K10_SOURCE)
        assert result == "+6 from 3 dropped dice in excess of 10k10"

    def test_overflow_negative_kept_only(self) -> None:
        """``0k-2 from dice in excess of 10k10`` renders as the narrative form.

        (Engine never emits kept-only overflow in practice but the
        helper handles it defensively to preserve the invariant that
        rolled<0 OR kept<0 triggers the special case.)
        """
        result = format_breakdown_component(0, -2, EXCESS_10K10_SOURCE)
        assert result == "+4 from 2 dropped dice in excess of 10k10"

    def test_overflow_both_negative(self) -> None:
        """When both rolled and kept are negative the dropped count is the sum."""
        result = format_breakdown_component(-3, -3, EXCESS_10K10_SOURCE)
        assert result == "+12 from 6 dropped dice in excess of 10k10"

    def test_overflow_one_dropped_singular_noun(self) -> None:
        """``dropped=1`` uses the singular noun ``"die"`` not ``"dice"``."""
        result = format_breakdown_component(-1, 0, EXCESS_10K10_SOURCE)
        assert result == "+2 from 1 dropped die in excess of 10k10"

    def test_overflow_multiple_dropped_plural_noun(self) -> None:
        """Any ``dropped >= 2`` uses the plural noun ``"dice"``."""
        result = format_breakdown_component(-2, 0, EXCESS_10K10_SOURCE)
        assert result == "+4 from 2 dropped dice in excess of 10k10"


class TestFormatDiceEmpty:
    """``_format_dice([])`` returns the ``"[]"`` literal.

    Pre-spec-008, this path was incidentally covered by the (then
    duplicated) ``_format_one_component`` block; after the spec 008
    helper migration the line count shifted and the empty-dice path
    is no longer hit by side-effect.  Cover it explicitly.
    """

    def test_format_dice_empty_returns_literal(self) -> None:
        assert _format_dice([], 0) == "[]"

    def test_format_dice_empty_with_nonzero_kept(self) -> None:
        # Defensive: even if ``kept`` is nonzero, an empty list
        # short-circuits to the literal (no items to enumerate).
        assert _format_dice([], 3) == "[]"
