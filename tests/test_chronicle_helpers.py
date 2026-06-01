"""Unit tests for the chronicle-render helpers in ``web.views._chronicle``.

Locks down the rank-formatter against the historical "0th Dan Dan"
double-suffix bug — the original formatter was duplicated across three
page modules, and one copy had the suffix in the default ordinal which
then got " Dan" appended a second time by the caller, producing
``"0th Dan Dan"`` on characters whose school knacks were missing
(rank computed as ``min(...) == 0``).
"""

from web.views._chronicle import clan_for, format_school_rank


class TestFormatSchoolRank:
    def test_none_returns_none(self):
        assert format_school_rank(None) is None

    def test_ranks_one_through_five_use_proper_ordinals(self):
        assert format_school_rank(1) == "1st Dan"
        assert format_school_rank(2) == "2nd Dan"
        assert format_school_rank(3) == "3rd Dan"
        assert format_school_rank(4) == "4th Dan"
        assert format_school_rank(5) == "5th Dan"

    def test_zero_rank_renders_as_zeroth_dan_not_doubled(self):
        """Regression: previously the Characters-page formatter produced
        "0th Dan Dan" because the default ordinal already included "Dan"
        AND the caller appended " Dan" a second time."""
        s = format_school_rank(0)
        assert s == "0th Dan"
        assert "Dan Dan" not in (s or "")

    def test_out_of_range_rank_does_not_double_dan(self):
        for rank in (0, 6, 7, 99):
            s = format_school_rank(rank)
            assert s is not None
            assert s.endswith(" Dan")
            assert "Dan Dan" not in s


class TestClanFor:
    def test_blank_returns_ronin(self):
        assert clan_for("") == "Ronin"
        assert clan_for(None) == "Ronin"

    def test_known_school_returns_clan(self):
        assert clan_for("Akodo Bushi School") == "Lion"
        assert clan_for("Bayushi Bushi School") == "Scorpion"

    def test_unknown_school_returns_ronin(self):
        assert clan_for("Made Up School") == "Ronin"
